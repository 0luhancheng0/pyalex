"""Base OpenAlex entity classes."""

import logging
import warnings
from urllib.parse import quote_plus
from urllib.parse import urlunparse

from pyalex.client.auth import OpenAlexAuth
from pyalex.client.session import get_requests_session
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

            return self.filter_or(openalex_id=record_id).get(per_page=len(record_id))
        elif isinstance(record_id, str):
            self.params = record_id
            return self._get_from_url(self.url)
        else:
            raise ValueError("record_id should be a string or a list of strings")

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
        return self.get(per_page=1).meta["count"]

    def _get_from_url(self, url, session=None):
        if session is None:
            session = get_requests_session()

        logger.debug(f"Requesting URL: {url}")
        res = session.get(url, auth=OpenAlexAuth(config))

        if res.status_code == 403:
            if (
                isinstance(res.json()["error"], str)
                and "query parameters" in res.json()["error"]
            ):
                raise QueryError(res.json()["message"])

        res.raise_for_status()
        res_json = res.json()

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

    def get(self, return_meta=False, page=None, per_page=None, cursor=None, limit=None):
        # Handle the new limit parameter
        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError("limit should be a positive integer")
            
            # If limit is <= MAX_PER_PAGE, use regular pagination
            if limit <= MAX_PER_PAGE:
                per_page = limit
            else:
                # Use cursor pagination for larger limits
                # Collect all results using the existing paginate method
                results = []
                paginator = self.paginate(
                    method="cursor", 
                    cursor=cursor or "*", 
                    per_page=MAX_PER_PAGE, 
                    n_max=limit
                )
                for batch in paginator:
                    results.extend(batch)
                    if len(results) >= limit:
                        break
                
                # Trim to exact limit
                results = results[:limit]
                
                # Create a result object similar to what _get_from_url returns
                if results:
                    # Use the meta from the last batch but update count
                    final_result = OpenAlexResponseList(
                        [dict(r) for r in results], 
                        {"count": len(results)}, 
                        self.resource_class
                    )
                else:
                    # Return empty result with proper structure
                    final_result = OpenAlexResponseList(
                        [], {"count": 0}, self.resource_class
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

        # Always use MAX_PER_PAGE (200) when per_page is not explicitly provided
        # This ensures we always get the maximum efficiency from the OpenAlex API
        if per_page is None:
            per_page = MAX_PER_PAGE
        
        # Validate per_page parameter
        if per_page is not None and (
            not isinstance(per_page, int) 
            or (per_page < MIN_PER_PAGE or per_page > MAX_PER_PAGE)
        ):
            raise ValueError("per_page should be an integer between 1 and 200")

        if not isinstance(self.params, (str, list)):
            self._add_params("per-page", per_page)
            self._add_params("page", page)
            self._add_params("cursor", cursor)

        resp_list = self._get_from_url(self.url)

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return resp_list, resp_list.meta
        else:
            return resp_list

    def should_use_async(self, limit=None):
        """Determine if async should be used based on conditions."""
        if limit is None:
            return False
        
        # Use async if limit is reasonable and not a raw URL query
        return (
            limit <= 10000 and 
            not isinstance(self.params, str)
        )

    async def get_async(
        self, return_meta=False, page=None, per_page=None, cursor=None, limit=None
    ):
        """Async version of get method with smart pagination strategy.
        
        Uses basic paging with async requests when:
        1. Total count ≤ 10,000, OR
        2. User-specified limit ≤ 10,000
        Otherwise uses sync cursor paging.
        """
        # For single entity retrieval or small limits, use sync method
        if isinstance(self.params, str) or (limit and limit <= MAX_PER_PAGE):
            return self.get(
                return_meta=return_meta, page=page, per_page=per_page, 
                cursor=cursor, limit=limit
            )
        
        # Get count first to decide on pagination strategy
        count_result = self.get(per_page=1)
        total_count = count_result.meta.get('count', 0)
        
        # Determine effective limit for async decision
        effective_limit = limit if limit is not None else total_count
        
        # Use async if either total count ≤ 10,000 OR user limit ≤ 10,000
        if total_count <= 10000 or effective_limit <= 10000:
            return await self._get_async_basic_paging(
                total_count, per_page, limit, return_meta
            )
        else:
            # Use sync cursor paging for larger datasets
            logger.info(
                f"Large dataset ({total_count:,} results, limit: {limit}). "
                "Using sync cursor paging."
            )
            return self.get(
                return_meta=return_meta, page=page, per_page=per_page, 
                cursor=cursor, limit=limit
            )

    async def _get_async_basic_paging(
        self, total_count, per_page=None, limit=None, return_meta=False
    ):
        """Async basic paging implementation with rich progress bar."""
        from pyalex.client.async_session import async_batch_requests_with_progress
        
        # Use MAX_PER_PAGE for efficiency
        effective_per_page = per_page or MAX_PER_PAGE
        effective_limit = min(limit or total_count, total_count)
        
        # Check if this is a group-by query
        has_group_by = (hasattr(self, 'params') and self.params and 
                        isinstance(self.params, dict) and 'group-by' in self.params)
        
        if has_group_by:
            # For group-by operations, only page 1 is supported (max 200 results)
            page_query = self.__class__(self.params.copy())
            page_query._add_params("per-page", 200)
            urls = [page_query.url]
            logger.info("Fetching group-by results (page 1 only)...")
        else:
            # Calculate number of pages needed
            num_pages = (effective_limit + effective_per_page - 1) // effective_per_page
            
            # Create URLs for all pages
            urls = []
            for page_num in range(1, num_pages + 1):
                # Create a copy of self with page parameters
                params_copy = (
                    self.params.copy() if isinstance(self.params, dict) 
                    else self.params
                )
                page_query = self.__class__(params_copy)
                page_query._add_params("per-page", effective_per_page)
                page_query._add_params("page", page_num)
                urls.append(page_query.url)
            
            logger.info(f"Fetching {num_pages} pages asynchronously...")
        
        # Execute async requests with progress tracking
        try:
            responses = await async_batch_requests_with_progress(
                urls, 
                max_concurrent=10,
                description=f"Fetching {self.__class__.__name__.lower()}"
            )
        except ImportError:
            # Fall back to sync if aiohttp not available
            logger.warning("aiohttp not available, falling back to sync pagination")
            return self.get(return_meta=return_meta, limit=limit)
        
        # Combine results
        all_results = []
        final_meta = {}
        
        for response_data in responses:
            if 'results' in response_data:
                all_results.extend(response_data['results'])
                if not final_meta and 'meta' in response_data:
                    final_meta = response_data['meta'].copy()
        
        # Trim to exact limit if specified
        if limit and len(all_results) > limit:
            all_results = all_results[:limit]
        
        # Update meta count
        final_meta['count'] = len(all_results)
        
        # Create response object
        final_result = OpenAlexResponseList(
            all_results, final_meta, self.resource_class
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

        resp_list = self._get_from_url(
            urlunparse(
                (
                    "https",
                    "api.openalex.org",
                    f"autocomplete/{self.__class__.__name__.lower()}",
                    "",
                    self._url_query(),
                    "",
                )
            )
        )

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return resp_list, resp_list.meta
        else:
            return resp_list
