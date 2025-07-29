"""Topic entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Topic(dict):
    """Class representing a topic entity in OpenAlex."""
    pass


class Topics(BaseOpenAlex):
    """Class representing a collection of topic entities in OpenAlex."""

    resource_class = Topic
