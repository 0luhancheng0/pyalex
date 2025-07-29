"""Funder entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.models.funder import FunderEntity


class Funder(dict):
    """Class representing a funder entity in OpenAlex."""
    pass


class Funders(BaseOpenAlex):
    """Class representing a collection of funder entities in OpenAlex."""

    resource_class = Funder
    resource_entity_class = FunderEntity

    def filter_by_country(self, country_code=None, **kwargs):
        """Filter by country.
        
        Parameters
        ----------
        country_code : str, optional
            ISO country code (e.g., "US", "GB", "CA")
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Funders
            Updated Funders object
        """
        if country_code:
            return self.filter(country_code=country_code, **kwargs)
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
        Funders
            Updated Funders object
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
        Funders
            Updated Funders object
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)
        return self.filter(**kwargs)
