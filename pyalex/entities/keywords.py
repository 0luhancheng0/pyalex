"""Keyword entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin


class Keyword(dict):
    """Class representing a keyword entity in OpenAlex."""

    pass


class Keywords(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of keyword entities in OpenAlex."""

    resource_class = Keyword
