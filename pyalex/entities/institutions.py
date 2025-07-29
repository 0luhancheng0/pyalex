"""Institution entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.models.institution import InstitutionEntity


class Institution(dict):
    """Class representing an institution entity in OpenAlex."""
    pass


class Institutions(BaseOpenAlex):
    """Class representing a collection of institution entities in OpenAlex."""

    resource_class = Institution
    resource_entity_class = InstitutionEntity

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
        Institutions
            Updated Institutions object
        """
        if country_code:
            return self.filter(country_code=country_code, **kwargs)
        return self.filter(**kwargs)
        
    def filter_by_type(self, institution_type, **kwargs):
        """Filter by institution type.
        
        Parameters
        ----------
        institution_type : str
            Type of institution (e.g., "education", "healthcare", "company", 
            "archive", "nonprofit", "government", "facility", "other")
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Institutions
            Updated Institutions object
        """
        return self.filter(type=institution_type, **kwargs)

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
        Institutions
            Updated Institutions object
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
        Institutions
            Updated Institutions object
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)
        return self.filter(**kwargs)

    def filter_by_location(self, city=None, region=None, **kwargs):
        """Filter by geographic location.
        
        Parameters
        ----------
        city : str, optional
            City name
        region : str, optional  
            Region/state name
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Institutions
            Updated Institutions object
        """
        location_filters = {}
        if city:
            location_filters["city"] = city
        if region:
            location_filters["region"] = region
        return self.filter(**location_filters, **kwargs)

    def filter_by_is_global_south(self, is_global_south=True, **kwargs):
        """Filter by Global South status.
        
        Parameters
        ----------
        is_global_south : bool
            Whether to filter for Global South institutions
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Institutions
            Updated Institutions object
        """
        return self.filter(is_global_south=is_global_south, **kwargs)
