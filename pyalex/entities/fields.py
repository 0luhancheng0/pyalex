"""Field entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.models.field import FieldEntity


class Field(dict):
    """Class representing a field entity in OpenAlex."""
    pass


class Fields(BaseOpenAlex):
    """Class representing a collection of field entities in OpenAlex."""

    resource_class = Field
    resource_entity_class = FieldEntity

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

    def filter_by_works_count(self, min_count=None, max_count=None, **kwargs):
        """Filter by number of works.
        
        Parameters
        ----------
        min_count : int, optional
            Minimum number of works
        max_count : int, optional
            Maximum number of works
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Fields
            Updated Fields object
        """
        if min_count is not None:
            self.filter_gt(works_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(works_count=max_count + 1)
        return self.filter(**kwargs)

    def filter_by_cited_by_count(self, min_count=None, max_count=None, **kwargs):
        """Filter by citation count.
        
        Parameters
        ----------
        min_count : int, optional
            Minimum citation count
        max_count : int, optional
            Maximum citation count
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Fields
            Updated Fields object
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)
        return self.filter(**kwargs)
