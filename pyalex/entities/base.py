"""Base OpenAlex entity classes."""

import asyncio
import logging
import warnings
from urllib.parse import urlunparse

from pyalex.client.auth import OpenAlexAuth
from pyalex.core.config import MAX_PER_PAGE
from pyalex.core.config import MAX_RECORD_IDS
from pyalex.core.config import MIN_PER_PAGE
from pyalex.core.config import config
from pyalex.core.expressions import gt_
from pyalex.core.expressions import lt_
from pyalex.core.expressions import not_
from pyalex.core.expressions import or_
from pyalex.core.pagination import Paginator
from pyalex.core.query import flatten_kv
from pyalex.core.query import params_merge
from pyalex.core.query import wrap_values_nested_dict
from pyalex.core.response import OpenAlexResponseList
from pyalex.core.response import QueryError
from pyalex.core.utils import quote_oa_value

try:
    from pyalex.logger import get_logger
    logger = get_logger()
except ImportError:
    # Fallback if logging module is not available
    logger = logging.getLogger(__name__)


class BaseOpenAlex:
    """Base class for OpenAlex objects.

    Parameters
    ----------
    params : dict, optional
        Parameters for the API request.
    """

    def __init__(self, params=None):
        self.params = params

    def __getattr__(self, key):
        if key == "groupby":
            raise AttributeError(
                "Object has no attribute 'groupby'. Did you mean 'group_by'?"
            )

        if key == "filter_search":
            raise AttributeError(
                "Object has no attribute 'filter_search'. Did you mean 'search_filter'?"
            )

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{key}'"
        )

    def __getitem__(self, record_id):
        if isinstance(record_id, list):
            if len(record_id) > MAX_RECORD_IDS:
                raise ValueError(
                    f"OpenAlex does not support more than {MAX_RECORD_IDS} ids"
                )

            return asyncio.run(
                self.filter_or(openalex_id=record_id).get(per_page=len(record_id))
            )
        elif isinstance(record_id, str):
            self.params = record_id
            # Use async method internally
            return asyncio.run(self._get_from_url_async(self.url))
        elif isinstance(record_id, slice):
            # Handle slice notation for pagination (e.g., query[:200] or query[100:300])
            start = record_id.start or 0
            stop = record_id.stop
            step = record_id.step or 1
            
            if step != 1:
                raise ValueError("Slice step must be 1")
            if start < 0:
                raise ValueError("Slice start must be non-negative")
            if stop is not None and stop <= start:
                raise ValueError("Slice stop must be greater than start")
                
            # Convert slice to limit for get() method
            if stop is not None:
                limit = stop - start
                # If start > 0, we'd need to implement offset/skip functionality
                # For now, only support slices starting from 0
                if start > 0:
                    raise ValueError("Slice with non-zero start not supported yet")
                return asyncio.run(self.get(limit=limit))
            else:
                # Open-ended slice like query[100:] - not supported yet
                raise ValueError("Open-ended slices not supported")
        else:
            raise ValueError(
                "record_id should be a string, a list of strings, or a slice"
            )

    def _url_query(self):
        if isinstance(self.params, list):
            return self.filter_or(openalex_id=self.params)
        elif isinstance(self.params, dict):
            l_params = []
            for k, v in self.params.items():
                if v is None:
                    pass
                elif isinstance(v, list):
                    l_params.append(
                        "{}={}".format(k, ",".join(map(quote_oa_value, v)))
                    )
                elif k in ["filter", "sort"]:
                    l_params.append(f"{k}={flatten_kv(v)}")
                else:
                    l_params.append(f"{k}={quote_oa_value(v)}")

            if l_params:
                return "&".join(l_params)

        else:
            return ""

    @property
    def url(self):
        """Return the URL for the API request.

        The URL doens't include the identification, authentication,
        and pagination parameters.

        Returns
        -------
        str
            URL for the API request.
        """
        base_path = self.__class__.__name__.lower()

        if isinstance(self.params, str):
            path = f"{base_path}/{quote_oa_value(self.params)}"
            query = ""
        else:
            path = base_path
            query = self._url_query()

        return urlunparse(("https", "api.openalex.org", path, "", query, ""))

    def count(self):
        """Get the count of results.

        Returns
        -------
        int
            Count of results.
        """
        return asyncio.run(self.get(per_page=1)).meta["count"]

    async def _get_from_url_async(self, url):
        """Async method to fetch data from URL.
        
        Parameters
        ----------
        url : str
            URL to fetch data from.
            
        Returns
        -------
        OpenAlexResponseList or OpenAlexEntity
            Parsed response data.
        """
        from pyalex.client.httpx_session import async_get_with_retry, get_async_client
        
        async with await get_async_client() as client:
            res_json = await async_get_with_retry(client, url)

        if self.params and "group-by" in self.params:
            return OpenAlexResponseList(
                res_json["group_by"], res_json["meta"], self.resource_class
            )
        elif "results" in res_json:
            return OpenAlexResponseList(
                res_json["results"], res_json["meta"], self.resource_class
            )
        elif "id" in res_json:
            return self.resource_class(res_json)
        else:
            raise ValueError("Unknown response format")

    async def get(
        self, return_meta=False, page=None, per_page=None, cursor=None, limit=None
    ):
        """Async method for fetching data with async requests only.
        
        This method exclusively uses async requests for all operations.
        No sync fallbacks - all HTTP calls are non-blocking.
        
        Parameters
        ----------
        return_meta : bool, optional
            Whether to return metadata (deprecated).
        page : int, optional
            Page number for pagination.
        per_page : int, optional
            Number of results per page (1-200).
        cursor : str, optional
            Cursor for cursor-based pagination.
        limit : int, optional
            Maximum number of results to return.
            
        Returns
        -------
        OpenAlexResponseList or OpenAlexEntity
            Query results.
        """
        # Handle limit parameter
        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError("limit should be a positive integer")
            
            # For small limits, use single page fetch
            if limit <= MAX_PER_PAGE:
                per_page = limit
            else:
                # For larger limits, use async cursor pagination
                return await self._get_async_cursor_paging(limit, return_meta)

        # Set default per_page for efficiency
        if per_page is None:
            per_page = MAX_PER_PAGE
        
        # Validate per_page parameter
        if per_page is not None and (
            not isinstance(per_page, int) 
            or (per_page < MIN_PER_PAGE or per_page > MAX_PER_PAGE)
        ):
            raise ValueError("per_page should be an integer between 1 and 200")

        # Add pagination parameters
        if not isinstance(self.params, (str, list)):
            self._add_params("per-page", per_page)
            self._add_params("page", page)
            self._add_params("cursor", cursor)

        # Fetch data using async method
        resp_list = await self._get_from_url_async(self.url)

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return resp_list, resp_list.meta
        else:
            return resp_list

    async def _get_async_cursor_paging(self, limit, return_meta=False):
        """Async cursor-based pagination for large result sets.
        
        Uses cursor pagination with async requests to fetch all results efficiently.
        Exclusively async - no sync fallbacks.
        
        Parameters
        ----------
        limit : int
            Maximum number of results to return.
        return_meta : bool, optional
            Whether to return metadata (deprecated).
            
        Returns
        -------
        OpenAlexResponseList
            Paginated results.
        """
        from pyalex.client.httpx_session import async_get_with_retry, get_async_client
        
        all_results = []
        cursor = "*"
        per_page = MAX_PER_PAGE
        
        async with await get_async_client() as client:
            while len(all_results) < limit:
                # Create query with cursor
                params_copy = (
                    self.params.copy() if isinstance(self.params, dict) 
                    else self.params
                )
                page_query = self.__class__(params_copy)
                page_query._add_params("per-page", per_page)
                page_query._add_params("cursor", cursor)
                
                # Fetch page
                response_data = await async_get_with_retry(client, page_query.url)
                
                # Extract results
                if 'results' in response_data:
                    batch = response_data['results']
                    all_results.extend(batch)
                    
                    # Check if we have more pages
                    meta = response_data.get('meta', {})
                    next_cursor = meta.get('next_cursor')
                    
                    if not next_cursor or not batch:
                        break  # No more results
                    
                    cursor = next_cursor
                else:
                    break
        
        # Trim to exact limit
        all_results = all_results[:limit]
        
        # Create response object
        final_result = OpenAlexResponseList(
            all_results, {"count": len(all_results)}, self.resource_class
        )
        
        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return final_result, final_result.meta
        else:
            return final_result

    def paginate(
        self, 
        method="cursor", 
        page=1, 
        per_page=None, 
        cursor="*", 
        n_max=10000
    ):
        """Paginate results from the API.

        Parameters
        ----------
        method : str, optional
            Pagination method ('cursor' or 'page').
        page : int, optional
            Page number for pagination.
        per_page : int, optional
            Number of results per page. Defaults to 200 if not specified.
        cursor : str, optional
            Cursor for pagination.
        n_max : int, optional
            Maximum number of results. For 'page' method only - represents
            the maximum that basic paging can retrieve. For 'cursor' method,
            this parameter is ignored as cursor paging has no inherent limit.

        Returns
        -------
        Paginator
            Paginator object.
        """
        if method == "cursor":
            if isinstance(self.params, dict) and self.params.get("sample"):
                raise ValueError("method should be 'page' when using sample")
            value = cursor
            # For cursor pagination, ignore n_max as it has no inherent limit
            effective_n_max = None
        elif method == "page":
            value = page
            # For page pagination, use n_max to limit results
            effective_n_max = n_max
        else:
            raise ValueError("Method should be 'cursor' or 'page'")

        return Paginator(
            self, method=method, value=value, per_page=per_page, n_max=effective_n_max
        )

    def random(self):
        """Get a random result.

        Returns
        -------
        OpenAlexEntity
            Random result.
        """
        return self.__getitem__("random")

    def _add_params(self, argument, new_params, raise_if_exists=False):
        """Add parameters to the API request.

        Parameters
        ----------
        argument : str
            Parameter name.
        new_params : any
            Parameter value.
        raise_if_exists : bool, optional
            Whether to raise an error if the parameter already exists.
        """
        if raise_if_exists:
            raise NotImplementedError("raise_if_exists is not implemented")

        if self.params is None:
            self.params = {argument: new_params}
        elif argument in self.params and isinstance(self.params[argument], dict):
            params_merge(self.params[argument], new_params)
        else:
            self.params[argument] = new_params

    def filter(self, **kwargs):
        """Add filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("filter", kwargs)
        return self

    def filter_and(self, **kwargs):
        """Add AND filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        return self.filter(**kwargs)

    def filter_or(self, **kwargs):
        """Add OR filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("filter", or_(kwargs), raise_if_exists=False)
        return self

    def filter_not(self, **kwargs):
        """Add NOT filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("filter", wrap_values_nested_dict(kwargs, not_))
        return self

    def filter_gt(self, **kwargs):
        """Add greater than filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("filter", wrap_values_nested_dict(kwargs, gt_))
        return self

    def filter_lt(self, **kwargs):
        """Add less than filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("filter", wrap_values_nested_dict(kwargs, lt_))
        return self

    def search_filter(self, **kwargs):
        """Add search filter parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Filter parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("filter", {f"{k}.search": v for k, v in kwargs.items()})
        return self

    def sort(self, **kwargs):
        """Add sort parameters to the API request.

        Parameters
        ----------
        **kwargs : dict
            Sort parameters.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("sort", kwargs)
        return self

    def group_by(self, group_key):
        """Add group-by parameters to the API request.

        Parameters
        ----------
        group_key : str
            Group-by key.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("group-by", group_key)
        return self

    def search(self, s):
        """Add search parameters to the API request.

        Parameters
        ----------
        s : str
            Search string.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("search", s)
        return self

    def sample(self, n, seed=None):
        """Add sample parameters to the API request.

        Parameters
        ----------
        n : int
            Number of samples.
        seed : int, optional
            Seed for sampling.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("sample", n)
        self._add_params("seed", seed)
        return self

    def select(self, s):
        """Add select parameters to the API request.

        Parameters
        ----------
        s : str
            Select string.

        Returns
        -------
        BaseOpenAlex
            Updated object.
        """
        self._add_params("select", s)
        return self

    def autocomplete(self, s, return_meta=False):
        """Return the OpenAlex autocomplete results.
        
        Uses async requests internally for optimal performance.

        Parameters
        ----------
        s : str
            String to autocomplete.
        return_meta : bool, optional
            Whether to return metadata.

        Returns
        -------
        OpenAlexResponseList
            List of autocomplete results.
        """
        self._add_params("q", s)

        url = urlunparse(
            (
                "https",
                "api.openalex.org",
                f"autocomplete/{self.__class__.__name__.lower()}",
                "",
                self._url_query(),
                "",
            )
        )
        
        # Sync wrapper for backward compatibility
        resp_list = asyncio.run(self._get_from_url_async(url))

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return resp_list, resp_list.meta
        else:
            return resp_list
