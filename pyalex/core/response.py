"""Response classes for OpenAlex API."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pyalex.models.base import OpenAlexEntity


class QueryError(ValueError):
    """Exception raised for errors in the query."""
    pass


class OpenAlexResponseList(list):
    """A list of OpenAlexEntity objects with metadata.

    Attributes:
        meta: a dictionary with metadata about the results
        resource_class: the class to use for each entity in the results

    Arguments:
        results: a list of OpenAlexEntity objects
        meta: a dictionary with metadata about the results
        resource_class: the class to use for each entity in the results

    Returns:
        a OpenAlexResponseList object
    """

    def __init__(self, results, meta=None, resource_class=OpenAlexEntity):
        self.resource_class = resource_class
        self.meta = meta

        super().__init__([resource_class(ent) for ent in results])
