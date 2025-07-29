"""Keyword entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Keyword(dict):
    """Class representing a keyword entity in OpenAlex."""
    pass


class Keywords(BaseOpenAlex):
    """Class representing a collection of keyword entities in OpenAlex."""

    resource_class = Keyword
