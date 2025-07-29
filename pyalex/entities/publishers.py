"""Publisher entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Publisher(dict):
    """Class representing a publisher entity in OpenAlex."""
    pass


class Publishers(BaseOpenAlex):
    """Class representing a collection of publisher entities in OpenAlex."""

    resource_class = Publisher
