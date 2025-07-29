"""Field entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Field(dict):
    """Class representing a field entity in OpenAlex."""
    pass


class Fields(BaseOpenAlex):
    """Class representing a collection of field entities in OpenAlex."""

    resource_class = Field
