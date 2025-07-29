"""Subfield entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Subfield(dict):
    """Class representing a subfield entity in OpenAlex."""
    pass


class Subfields(BaseOpenAlex):
    """Class representing a collection of subfield entities in OpenAlex."""

    resource_class = Subfield
