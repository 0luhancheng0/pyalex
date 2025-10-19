"""Subfield entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin


class Subfield(dict):
    """Class representing a subfield entity in OpenAlex."""

    pass


class Subfields(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of subfield entities in OpenAlex."""

    resource_class = Subfield

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
        Subfields
            Updated Subfields object
        """
        if field_id:
            return self.filter(field={"id": field_id}, **kwargs)
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
        Subfields
            Updated Subfields object
        """
        if domain_id:
            return self.filter(domain={"id": domain_id}, **kwargs)
        return self.filter(**kwargs)
