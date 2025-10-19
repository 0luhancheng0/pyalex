"""Pagination utilities for OpenAlex API."""

import asyncio
import logging

from pyalex.core.config import CURSOR_START_VALUE
from pyalex.core.config import MAX_PER_PAGE
from pyalex.core.config import MIN_PER_PAGE
from pyalex.core.config import PAGE_START_VALUE

try:
    from pyalex.logger import get_logger

    logger = get_logger()
except ImportError:
    # Fallback if logging module is not available
    logger = logging.getLogger(__name__)


class Paginator:
    """Paginator for OpenAlex API results.

    Attributes
    ----------
    VALUE_CURSOR_START : str
        Starting value for cursor pagination.
    VALUE_NUMBER_START : int
        Starting value for page pagination.

    Parameters
    ----------
    endpoint_class : class
        Class of the endpoint to paginate.
    method : str, optional
        Pagination method ('cursor' or 'page').
    value : any, optional
        Starting value for pagination.
    per_page : int, optional
        Number of results per page.
    n_max : int, optional
        Maximum number of results.
    """

    VALUE_CURSOR_START = CURSOR_START_VALUE
    VALUE_NUMBER_START = PAGE_START_VALUE

    def __init__(
        self, endpoint_class, method="cursor", value=None, per_page=None, n_max=None
    ):
        self.method = method
        self.endpoint_class = endpoint_class
        self.value = value
        # Always use MAX_PER_PAGE (200) when per_page is not explicitly provided
        self.per_page = per_page if per_page is not None else MAX_PER_PAGE
        self.n_max = n_max
        self.n = 0
        self._first_page = True  # Track if this is the first page

        self._next_value = value

    def __iter__(self):
        return self

    def _is_max(self):
        if self.n_max and self.n >= self.n_max:
            return True
        return False

    def _fetch_next_page(self):
        """Fetch the next page of results.

        Returns:
            Response from the API
        """
        # Set pagination parameters
        if self.method == "cursor":
            self.endpoint_class._add_params("cursor", self._next_value)
        elif self.method == "page":
            self.endpoint_class._add_params("page", self._next_value)
        else:
            raise ValueError("Method should be 'cursor' or 'page'")

        if self.per_page is not None and (
            not isinstance(self.per_page, int)
            or (self.per_page < MIN_PER_PAGE or self.per_page > MAX_PER_PAGE)
        ):
            raise ValueError("per_page should be a integer between 1 and 200")

        if self.per_page is not None:
            self.endpoint_class._add_params("per-page", self.per_page)

        # Use async method internally (asyncio.run wraps async call)
        return asyncio.run(
            self.endpoint_class._get_from_url_async(self.endpoint_class.url)
        )

    def _process_page_metadata(self, response, meta):
        """Process page metadata and update pagination state.

        Args:
            response: The API response
            meta: Metadata from the response
        """
        # Print count information on first page
        if self._first_page and meta and "count" in meta:
            total_count = meta["count"]
            logger.info(f"Total results found: {total_count:,}")
            self._first_page = False

        # Update next value based on pagination method
        if self.method == "cursor":
            self._next_value = meta.get("next_cursor") if meta else None
        elif self.method == "page":
            if len(response) > 0 and meta:
                self._next_value = meta.get("page", 0) + 1
            else:
                self._next_value = None

        self.n = self.n + len(response)

    def __next__(self):
        if self._next_value is None or self._is_max():
            raise StopIteration

        # Check if this is a group-by query - group-by only supports page 1
        has_group_by = (
            hasattr(self.endpoint_class, "params")
            and self.endpoint_class.params
            and isinstance(self.endpoint_class.params, dict)
            and "group-by" in self.endpoint_class.params
        )

        if has_group_by and self.method == "page" and self._next_value > 1:
            # Group-by queries only support page 1, stop pagination
            raise StopIteration

        # Fetch the next page
        r = self._fetch_next_page()

        # Extract metadata from DataFrame attrs or direct attribute
        meta = None
        if hasattr(r, "attrs") and "meta" in r.attrs:
            meta = r.attrs["meta"]
        elif hasattr(r, "meta"):
            meta = r.meta

        # Process metadata and update state
        self._process_page_metadata(r, meta)

        return r
