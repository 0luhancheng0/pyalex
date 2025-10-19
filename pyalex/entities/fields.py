"""Field entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin


class Field(dict):
    """Class representing a field entity in OpenAlex."""

    pass


class Fields(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of field entities in OpenAlex."""

    resource_class = Field

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
        Fields
            Updated Fields object
        """
        if domain_id:
            return self.filter(domain={"id": domain_id}, **kwargs)
        return self.filter(**kwargs)
