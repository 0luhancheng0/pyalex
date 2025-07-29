"""Domain entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Domain(dict):
    """Class representing a domain entity in OpenAlex."""
    pass


class Domains(BaseOpenAlex):
    """Class representing a collection of domain entities in OpenAlex."""

    resource_class = Domain
