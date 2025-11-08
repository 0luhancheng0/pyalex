"""Autocomplete functionality for OpenAlex API."""

from urllib.parse import quote_plus
from urllib.parse import urlunparse

from pyalex.core.response import OpenAlexResponseList
from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import _run_async_safely


class Autocomplete(dict):
    """Class representing an autocomplete entity in OpenAlex."""

    pass


class AutocompleteCollection(BaseOpenAlex):
    """Class to autocomplete without being based on the type of entity."""

    resource_class = Autocomplete

    def __getitem__(self, key: str) -> OpenAlexResponseList:
        query = self._apply_default_query_params(f"q={quote_plus(key)}")
        url = urlunparse(
            (
                "https",
                "api.openalex.org",
                "autocomplete",
                "",
                query,
                "",
            )
        )
        return _run_async_safely(self._get_from_url_async(url))


def autocomplete(s: str) -> OpenAlexResponseList:
    """Autocomplete with any type of entity.

    Args:
        s: String to autocomplete.

    Returns:
        List of autocomplete results.
    """
    return AutocompleteCollection()[s]
