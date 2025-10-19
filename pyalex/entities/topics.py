"""Topic entities for OpenAlex API."""

from typing import TYPE_CHECKING

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin

if TYPE_CHECKING:
    pass


class Topic(dict):
    """Class representing a topic entity in OpenAlex."""

    pass


class Topics(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of topic entities in OpenAlex."""

    resource_class = Topic

    def filter_by_field(self, field_id=None, **kwargs):
        """Filter by field.

        Parameters
        ----------
        field_id : str, optional
            OpenAlex ID of the field
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        Topics
            Updated Topics object
        """
        if field_id:
            return self.filter(field={"id": field_id}, **kwargs)
        return self.filter(**kwargs)

    def filter_by_subfield(self, subfield_id=None, **kwargs):
        """Filter by subfield.

        Parameters
        ----------
        subfield_id : str, optional
            OpenAlex ID of the subfield
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        Topics
            Updated Topics object
        """
        if subfield_id:
            return self.filter(subfield={"id": subfield_id}, **kwargs)
        return self.filter(**kwargs)

    def filter_by_domain(self, domain_id=None, **kwargs):
        """Filter by domain.

        Parameters
        ----------
        domain_id : str, optional
            OpenAlex ID of the domain
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        Topics
            Updated Topics object
        """
        if domain_id:
            return self.filter(domain={"id": domain_id}, **kwargs)
        return self.filter(**kwargs)
