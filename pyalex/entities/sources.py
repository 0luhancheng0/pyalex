"""Source entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Source(dict):
    """Class representing a source entity in OpenAlex."""
    pass


class Sources(BaseOpenAlex):
    """Class representing a collection of source entities in OpenAlex."""

    resource_class = Source


# Aliases
Journals = Sources
