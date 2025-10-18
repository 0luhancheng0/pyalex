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

    def __next__(self):
        if self._next_value is None or self._is_max():
            raise StopIteration

        # Check if this is a group-by query - group-by only supports page 1
        has_group_by = (hasattr(self.endpoint_class, 'params') and 
                       self.endpoint_class.params and 
                       isinstance(self.endpoint_class.params, dict) and 
                       'group-by' in self.endpoint_class.params)
        
        if has_group_by and self.method == "page" and self._next_value > 1:
            # Group-by queries only support page 1, stop pagination
            raise StopIteration

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

        # Use async method internally (syncio.run wraps async call)
        r = asyncio.run(self.endpoint_class._get_from_url_async(self.endpoint_class.url))

        # Print count information on first page and check for approval if needed
        if self._first_page and hasattr(r, 'meta') and r.meta and 'count' in r.meta:
            total_count = r.meta['count']
            logger.info(f"Total results found: {total_count:,}")
            
            self._first_page = False

        if self.method == "cursor":
            self._next_value = r.meta["next_cursor"]

        if self.method == "page":
            if len(r) > 0:
                self._next_value = r.meta["page"] + 1
            else:
                self._next_value = None

        self.n = self.n + len(r)

        return r
