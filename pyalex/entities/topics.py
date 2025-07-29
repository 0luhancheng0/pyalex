"""Topic entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex
from pyalex.models.topic import TopicEntity


class Topic(dict):
    """Class representing a topic entity in OpenAlex."""
    pass


class Topics(BaseOpenAlex):
    """Class representing a collection of topic entities in OpenAlex."""

    resource_class = Topic
    resource_entity_class = TopicEntity

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
        Topics
            Updated Topics object
        """
        if field_id:
            return self.filter(field={"id": field_id}, **kwargs)
        return self.filter(**kwargs)

    def filter_by_subfield(self, subfield_id=None, **kwargs):
        """Filter by subfield.
        
        Parameters
        ----------
        subfield_id : str, optional
            OpenAlex ID of the subfield
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Topics
            Updated Topics object
        """
        if subfield_id:
            return self.filter(subfield={"id": subfield_id}, **kwargs)
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
        Topics
            Updated Topics object
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
        Topics
            Updated Topics object
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
        Topics
            Updated Topics object
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)
        return self.filter(**kwargs)
