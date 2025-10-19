"""Domain entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin


class Domain(dict):
    """Class representing a domain entity in OpenAlex."""

    pass


class Domains(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of domain entities in OpenAlex."""

    resource_class = Domain
