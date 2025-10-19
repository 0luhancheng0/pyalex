"""Funder entities for OpenAlex API."""

from typing import TYPE_CHECKING

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin

if TYPE_CHECKING:
    pass


class Funder(dict):
    """Class representing a funder entity in OpenAlex."""

    pass


class Funders(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of funder entities in OpenAlex."""

    resource_class = Funder

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
