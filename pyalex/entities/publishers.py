"""Publisher entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin


class Publisher(dict):
    """Class representing a publisher entity in OpenAlex."""

    pass


class Publishers(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of publisher entities in OpenAlex."""

    resource_class = Publisher

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
        Publishers
            Updated Publishers object
        """
        if country_code:
            return self.filter(country_codes=country_code, **kwargs)
        return self.filter(**kwargs)
