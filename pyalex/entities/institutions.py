"""Institution entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Institution(dict):
    """Class representing an institution entity in OpenAlex."""
    pass


class Institutions(BaseOpenAlex):
    """Class representing a collection of institution entities in OpenAlex."""

    resource_class = Institution
