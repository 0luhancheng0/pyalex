"""Author entities for OpenAlex API."""

from typing import TYPE_CHECKING

from pyalex.entities.base import BaseOpenAlex
from pyalex.entities.base import RangeFilterMixin

if TYPE_CHECKING:
    pass


class Author(dict):
    """Class representing an author entity in OpenAlex."""

    pass


class Authors(BaseOpenAlex, RangeFilterMixin):
    """Class representing a collection of author entities in OpenAlex."""

    resource_class = Author

    def filter_by_affiliation(self, institution_id=None, **kwargs):
        """Filter by author affiliation.

        Parameters
        ----------
        institution_id : str, optional
            OpenAlex ID of the institution
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        Authors
            Updated Authors object
        """
        if institution_id:
            return self.filter(last_known_institutions={"id": institution_id}, **kwargs)
        return self.filter(**kwargs)

    def filter_by_orcid(self, orcid_id, **kwargs):
        """Filter by ORCID ID.

        Parameters
        ----------
        orcid_id : str
            ORCID identifier
        **kwargs : dict
            Additional filter parameters

        Returns
        -------
        Authors
            Updated Authors object
        """
        return self.filter(orcid=orcid_id, **kwargs)
