"""Author entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.models.author import AuthorEntity


class Author(dict):
    """Class representing an author entity in OpenAlex."""
    pass


class Authors(BaseOpenAlex):
    """Class representing a collection of author entities in OpenAlex."""

    resource_class = Author
    resource_entity_class = AuthorEntity

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
        Authors
            Updated Authors object
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
        Authors
            Updated Authors object
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)
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

    def filter_by_h_index(self, min_h=None, max_h=None, **kwargs):
        """Filter by h-index.
        
        Parameters
        ----------
        min_h : int, optional
            Minimum h-index
        max_h : int, optional
            Maximum h-index
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Authors
            Updated Authors object
        """
        if min_h is not None:
            self.filter_gt(summary_stats={"h_index": min_h - 1})
        if max_h is not None:
            self.filter_lt(summary_stats={"h_index": max_h + 1})
        return self.filter(**kwargs)
