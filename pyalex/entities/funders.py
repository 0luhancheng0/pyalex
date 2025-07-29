"""Funder entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Funder(dict):
    """Class representing a funder entity in OpenAlex."""
    pass


class Funders(BaseOpenAlex):
    """Class representing a collection of funder entities in OpenAlex."""

    resource_class = Funder
