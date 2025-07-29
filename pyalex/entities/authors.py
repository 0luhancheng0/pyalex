"""Author entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.models.author import Author as AuthorModel


class Author(dict):
    """Class representing an author entity in OpenAlex."""
    pass


class Authors(BaseOpenAlex):
    """Class representing a collection of author entities in OpenAlex."""

    resource_class = Author
