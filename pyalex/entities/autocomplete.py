"""Autocomplete functionality for OpenAlex API."""

import warnings
from urllib.parse import quote_plus
from urllib.parse import urlunparse

from pyalex.entities.base import BaseOpenAlex


class Autocomplete(dict):
    """Class representing an autocomplete entity in OpenAlex."""
    pass


class AutocompleteCollection(BaseOpenAlex):
    """Class to autocomplete without being based on the type of entity."""

    resource_class = Autocomplete

    def __getitem__(self, key):
        return self._get_from_url(
            urlunparse(
                (
                    "https",
                    "api.openalex.org",
                    "autocomplete",
                    "",
                    f"q={quote_plus(key)}",
                    "",
                )
            )
        )


def autocomplete(s):
    """Autocomplete with any type of entity.

    Parameters
    ----------
    s : str
        String to autocomplete.

    Returns
    -------
    OpenAlexResponseList
        List of autocomplete results.
    """
    return AutocompleteCollection()[s]
