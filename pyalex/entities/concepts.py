"""Concept entities for OpenAlex API."""

from typing import TYPE_CHECKING

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin

if TYPE_CHECKING:
    pass


class Concept(dict):
    """Class representing a concept entity in OpenAlex."""

    pass


class Concepts(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of concept entities in OpenAlex."""

    resource_class = Concept

    def filter_by_ancestor(self, concept_id=None, **kwargs):
        """Filter by ancestor concept ID."""

        if concept_id:
            return self.filter(ancestors={"id": concept_id}, **kwargs)
        return self.filter(**kwargs)
