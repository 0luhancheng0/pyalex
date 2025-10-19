"""Base OpenAlex entity classes."""

import asyncio
import logging
import warnings
from urllib.parse import urlunparse

from pyalex.core.config import MAX_PER_PAGE
from pyalex.core.config import MAX_RECORD_IDS
from pyalex.core.config import MIN_PER_PAGE
from pyalex.core.expressions import gt_
from pyalex.core.expressions import lt_
from pyalex.core.expressions import not_
from pyalex.core.expressions import or_
from pyalex.core.pagination import Paginator
from pyalex.core.query import flatten_kv
from pyalex.core.query import params_merge
from pyalex.core.query import wrap_values_nested_dict
from pyalex.core.utils import quote_oa_value

try:
    from pyalex.logger import get_logger

    logger = get_logger()
except ImportError:
    # Fallback if logging module is not available
    logger = logging.getLogger(__name__)


def _run_async_safely(coro):
    """Run an async coroutine safely, handling both sync and async contexts.

    This function detects if we're already in an event loop (e.g., Jupyter notebook)
    and handles the execution appropriately.

    Parameters
    ----------
    coro : coroutine
        The coroutine to execute

    Returns
    -------
    any
        The result of the coroutine execution
    """
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
        # We're in an async context (e.g., Jupyter notebook with ipykernel)
        # We can't use asyncio.run() here, so we need to handle it differently

        # Try using nest_asyncio if available (allows nested event loops)
        try:
            import nest_asyncio

            nest_asyncio.apply()
            return asyncio.run(coro)
        except ImportError:
            # nest_asyncio not available - we need to schedule in the current loop
            # Create a new task and wait for it
            import threading

            result_container = {}
            exception_container = {}

            def run_in_thread():
                """Run the coroutine in a new event loop in a separate thread."""
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result_container["result"] = new_loop.run_until_complete(coro)
                    new_loop.close()
                except Exception as e:
                    exception_container["exception"] = e

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if "exception" in exception_container:
                raise exception_container["exception"]
            return result_container["result"]

    except RuntimeError as e:
        if "no running event loop" in str(e).lower():
            # No event loop running, safe to use asyncio.run
            return asyncio.run(coro)
        else:
            raise


class RangeFilterMixin:
    """Mixin for common range filter operations across entity types.

    This mixin provides standardized range filtering methods that are
    commonly used across different entity types (Authors, Institutions,
    Sources, Funders, etc.). It eliminates code duplication by centralizing
    the range filter logic.
    """

    def _filter_range(self, field_name, min_val=None, max_val=None, **kwargs):
        """Generic range filter for any numeric field.

        Parameters
        ----------
        field_name : str
            Field name to filter on (supports dot notation for nested fields)
        min_val : int or float, optional
            Minimum value (inclusive)
        max_val : int or float, optional
            Maximum value (inclusive)
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        self
            Updated entity object for method chaining
        """
        if min_val is not None:
            self.filter_gt(**{field_name: min_val - 1})
        if max_val is not None:
            self.filter_lt(**{field_name: max_val + 1})
        return self.filter(**kwargs)

    def filter_by_works_count(self, min_count=None, max_count=None, **kwargs):
        """Filter by works count range.

        Parameters
        ----------
        min_count : int, optional
            Minimum number of works
        max_count : int, optional
            Maximum number of works
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        self
            Updated entity object
        """
        return self._filter_range("works_count", min_count, max_count, **kwargs)

    def filter_by_cited_by_count(self, min_count=None, max_count=None, **kwargs):
        """Filter by citation count range.

        Parameters
        ----------
        min_count : int, optional
            Minimum citation count
        max_count : int, optional
            Maximum citation count
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        self
            Updated entity object
        """
        return self._filter_range("cited_by_count", min_count, max_count, **kwargs)

    def filter_by_h_index(self, min_h=None, max_h=None, **kwargs):
        """Filter by h-index range.

        Parameters
        ----------
        min_h : int, optional
            Minimum h-index
        max_h : int, optional
            Maximum h-index
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        self
            Updated entity object
        """
        return self._filter_range("summary_stats.h_index", min_h, max_h, **kwargs)

    def filter_by_i10_index(self, min_i10=None, max_i10=None, **kwargs):
        """Filter by i10-index range.

        Parameters
        ----------
        min_i10 : int, optional
            Minimum i10-index
        max_i10 : int, optional
            Maximum i10-index
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        self
            Updated entity object
        """
        return self._filter_range("summary_stats.i10_index", min_i10, max_i10, **kwargs)

    def filter_by_2yr_mean_citedness(
        self, min_citedness=None, max_citedness=None, **kwargs
    ):
        """Filter by 2-year mean citedness range.

        Parameters
        ----------
        min_citedness : float, optional
            Minimum 2-year mean citedness
        max_citedness : float, optional
            Maximum 2-year mean citedness
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        self
            Updated entity object
        """
        return self._filter_range(
            "summary_stats.2yr_mean_citedness", min_citedness, max_citedness, **kwargs
        )


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
        """Retrieve record(s) by ID, list of IDs, or slice.

        Supports three access patterns:
        - Single ID: entity['W123456'] or entity['10.1234/abc']
        - List of IDs: entity[['W123', 'W456']]
        - Slice: entity[:100] or entity[10:50]

        Parameters
        ----------
        record_id : str, list, or slice
            Record identifier(s) to retrieve

        Returns
        -------
        pd.DataFrame or dict
            Query results as DataFrame (for lists/slices) or single record dict

        Raises
        ------
        ValueError
            If record_id type is unsupported or parameters are invalid
        """
        # Dispatch to appropriate handler based on record_id type
        if isinstance(record_id, list):
            return self._handle_list_id(record_id)
        elif isinstance(record_id, str):
            return self._handle_string_id(record_id)
        elif isinstance(record_id, slice):
            return self._handle_slice_id(record_id)
        else:
            type_name = type(record_id).__name__
            raise ValueError(
                f"record_id should be a string, list, or slice, got {type_name}"
            )

    def _handle_list_id(self, record_id):
        """Handle list of record IDs.

        Parameters
        ----------
        record_id : list
            List of record identifiers

        Returns
        -------
        pd.DataFrame
            Query results containing all requested records

        Raises
        ------
        ValueError
            If list contains more than MAX_RECORD_IDS items
        """
        if len(record_id) > MAX_RECORD_IDS:
            raise ValueError(
                f"OpenAlex does not support more than {MAX_RECORD_IDS} ids"
            )

        return _run_async_safely(
            self.filter_or(openalex_id=record_id).get(per_page=len(record_id))
        )

    def _handle_string_id(self, record_id):
        """Handle single string record ID.

        Parameters
        ----------
        record_id : str
            Single record identifier (OpenAlex ID, DOI, etc.)

        Returns
        -------
        dict
            Single record data
        """
        self.params = record_id
        return _run_async_safely(self._get_from_url_async(self.url))

    def _handle_slice_id(self, record_id):
        """Handle slice notation for pagination.

        Supports slices like [:100], [10:50], etc. Currently only supports
        slices starting from 0.

        Parameters
        ----------
        record_id : slice
            Slice object defining pagination range

        Returns
        -------
        pd.DataFrame
            Query results for the specified range

        Raises
        ------
        ValueError
            If slice parameters are invalid or unsupported
        """
        start = record_id.start or 0
        stop = record_id.stop
        step = record_id.step or 1

        # Validate slice parameters
        if step != 1:
            raise ValueError("Slice step must be 1")
        if start < 0:
            raise ValueError("Slice start must be non-negative")
        if stop is not None and stop <= start:
            raise ValueError("Slice stop must be greater than start")

        # Execute slice query
        if stop is not None:
            limit = stop - start
            if start > 0:
                raise ValueError("Slice with non-zero start not supported yet")
            return _run_async_safely(self.get(limit=limit))
        else:
            raise ValueError("Open-ended slices not supported")

    def _url_query(self):
        if isinstance(self.params, list):
            return self.filter_or(openalex_id=self.params)
        elif isinstance(self.params, dict):
            l_params = []
            for k, v in self.params.items():
                if v is None:
                    pass
                elif isinstance(v, list):
                    l_params.append("{}={}".format(k, ",".join(map(quote_oa_value, v))))
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
        result = _run_async_safely(self.get(per_page=1))
        meta = result.attrs.get("meta", {}) if hasattr(result, "attrs") else {}
        return meta.get("count", 0)

    async def _get_from_url_async(self, url):
        """Async method to fetch data from URL.

        Parameters
        ----------
        url : str
            URL to fetch data from.

        Returns
        -------
        pd.DataFrame or OpenAlexEntity
            Parsed response data as pandas DataFrame or single entity dict.
        """
        from pyalex.client.httpx_session import async_get_with_retry
        from pyalex.client.httpx_session import get_async_client

        async with await get_async_client() as client:
            res_json = await async_get_with_retry(client, url)

        # Handle different response types
        if self.params and "group-by" in self.params:
            results = res_json["group_by"]
            meta = res_json["meta"]
        elif "results" in res_json:
            results = res_json["results"]
            meta = res_json["meta"]
        elif "id" in res_json:
            # Single entity - always return as dict
            return self.resource_class(res_json)
        else:
            raise ValueError("Unknown response format")

        # Always return DataFrame
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame output. "
                "Install it with: pip install pandas"
            )

        # Convert results to resource class
        converted_results = [self.resource_class(ent) for ent in results]

        # Create DataFrame with metadata
        df = pd.DataFrame(converted_results)
        if meta:
            df.attrs["meta"] = meta

        return df

    async def get(
        self,
        return_meta=False,
        page=None,
        per_page=None,
        cursor=None,
        limit=MAX_PER_PAGE,
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
        limit : int or None, optional
            Maximum number of results to return. Defaults to MAX_PER_PAGE (200).
            Set to None to retrieve all available results (uses a very large limit).

        Returns
        -------
        pd.DataFrame or OpenAlexEntity
            Query results as pandas DataFrame or single entity dict.
        """
        # Handle limit parameter
        if limit is None:
            # User explicitly wants all results - use a very large limit
            limit = 10_000_000  # 10 million should be enough for all practical cases

        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError(
                    "limit should be a positive integer or None for all results"
                )

            # For small limits, use single page fetch
            if limit <= MAX_PER_PAGE:
                per_page = limit
            else:
                # Choose pagination strategy based on limit
                # OpenAlex API limits page-based pagination to 10,000 results (50 pages)
                # Beyond that, we must use cursor-based pagination
                MAX_PAGE_BASED_RESULTS = 10_000

                if limit <= MAX_PAGE_BASED_RESULTS:
                    # Use parallel page-based pagination (faster)
                    return await self._get_async_parallel_paging(limit, return_meta)
                else:
                    # Use sequential cursor-based pagination (required for >10k results)
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
                "return_meta is deprecated, access metadata via .attrs['meta']",
                DeprecationWarning,
                stacklevel=2,
            )
            meta = (
                resp_list.attrs.get("meta", {}) if hasattr(resp_list, "attrs") else {}
            )
            return resp_list, meta
        else:
            return resp_list

    async def _get_async_parallel_paging(self, limit, return_meta=False):
        """Async parallel pagination for medium-sized result sets (up to 10k).

        Uses parallel async requests to fetch multiple pages concurrently for maximum speed.
        Much faster than sequential cursor pagination for moderate limits.

        **Important:** OpenAlex API limits page-based pagination to 10,000 results maximum.
        For larger queries, use cursor-based pagination instead.

        Parameters
        ----------
        limit : int
            Maximum number of results to return (must be ≤ 10,000).
        return_meta : bool, optional
            Whether to return metadata (deprecated).

        Returns
        -------
        pd.DataFrame
            Paginated results as pandas DataFrame.
        """
        from pyalex.client.httpx_session import async_batch_requests_with_progress

        # Calculate how many pages we need
        per_page = MAX_PER_PAGE  # Always use max for efficiency
        num_pages = (limit + per_page - 1) // per_page  # Ceiling division

        # Build URLs for all pages using page-based pagination
        urls = []
        for page_num in range(1, num_pages + 1):
            # Create a query for this page
            params_copy = (
                self.params.copy() if isinstance(self.params, dict) else self.params
            )
            page_query = self.__class__(params_copy)
            page_query._add_params("per-page", per_page)
            page_query._add_params("page", page_num)
            urls.append(page_query.url)

        # Fetch all pages in parallel with progress bar
        description = f"Fetching {limit:,} results ({num_pages} pages)"
        all_responses = await async_batch_requests_with_progress(
            urls, description=description
        )

        # Combine all results
        all_results = []
        for response_data in all_responses:
            if response_data and "results" in response_data:
                all_results.extend(response_data["results"])

        # Trim to exact limit
        all_results = all_results[:limit]

        # Always return DataFrame
        try:
            import pandas as pd
        except ImportError:
            # If pandas not available, return list
            if return_meta:
                warnings.warn(
                    "return_meta is deprecated, access metadata via .attrs['meta']",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return all_results, {"count": len(all_results)}
            return all_results

        # Convert to DataFrame
        df = pd.DataFrame(all_results)

        # Add metadata as attrs
        if hasattr(df, "attrs"):
            df.attrs["meta"] = {"count": len(all_results)}

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, access metadata via .attrs['meta']",
                DeprecationWarning,
                stacklevel=2,
            )
            return df, {"count": len(all_results)}

        return df

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
        pd.DataFrame
            Paginated results as pandas DataFrame.
        """
        from pyalex.client.httpx_session import async_get_with_retry
        from pyalex.client.httpx_session import get_async_client

        all_results = []
        cursor = "*"
        per_page = MAX_PER_PAGE

        from rich.progress import BarColumn
        from rich.progress import MofNCompleteColumn
        from rich.progress import Progress
        from rich.progress import SpinnerColumn
        from rich.progress import TextColumn
        from rich.progress import TimeElapsedColumn
        from rich.progress import TimeRemainingColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Fetching results...", total=limit)

            async with await get_async_client() as client:
                page_count = 0
                while len(all_results) < limit:
                    page_count += 1
                    # Create query with cursor
                    params_copy = (
                        self.params.copy()
                        if isinstance(self.params, dict)
                        else self.params
                    )
                    page_query = self.__class__(params_copy)
                    page_query._add_params("per-page", per_page)
                    page_query._add_params("cursor", cursor)

                    # Fetch page
                    response_data = await async_get_with_retry(client, page_query.url)

                    # Extract results
                    if "results" in response_data:
                        batch = response_data["results"]
                        all_results.extend(batch)

                        # Update progress with current page info
                        current_count = min(len(all_results), limit)
                        progress.update(
                            task,
                            completed=current_count,
                            description=f"[cyan]Fetching results (page {page_count}, {current_count:,}/{limit:,})...",
                        )

                        # Check if we have more pages
                        meta = response_data.get("meta", {})
                        next_cursor = meta.get("next_cursor")

                        if not next_cursor or not batch:
                            break  # No more results

                        cursor = next_cursor
                    else:
                        break

        # Trim to exact limit
        all_results = all_results[:limit]

        # Always return DataFrame
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame output. "
                "Install it with: pip install pandas"
            )

        # Convert results to resource class
        converted_results = [self.resource_class(ent) for ent in all_results]

        # Create DataFrame with metadata
        meta_dict = {"count": len(all_results)}
        df = pd.DataFrame(converted_results)
        df.attrs["meta"] = meta_dict

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, access metadata via .attrs['meta']",
                DeprecationWarning,
                stacklevel=2,
            )
            return df, df.attrs["meta"]
        else:
            return df

    def paginate(self, method="cursor", page=1, per_page=None, cursor="*", n_max=10000):
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
        resp_list = _run_async_safely(self._get_from_url_async(url))

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, access metadata via .attrs['meta']",
                DeprecationWarning,
                stacklevel=2,
            )
            meta = (
                resp_list.attrs.get("meta", {}) if hasattr(resp_list, "attrs") else {}
            )
            return resp_list, meta
        else:
            return resp_list
