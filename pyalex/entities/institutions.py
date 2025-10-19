"""Institution entities for OpenAlex API."""

from typing import TYPE_CHECKING

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin

if TYPE_CHECKING:
    pass


class Institution(dict):
    """Class representing an institution entity in OpenAlex."""

    pass


class Institutions(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of institution entities in OpenAlex."""

    resource_class = Institution

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
