"""Source entities for OpenAlex API."""

from pyalex.entities.base import BaseOpenAlex


class Source(dict):
    """Class representing a source entity in OpenAlex."""
    pass


class Sources(BaseOpenAlex):
    """Class representing a collection of source entities in OpenAlex."""

    resource_class = Source

    def filter_by_type(self, source_type, **kwargs):
        """Filter by source type.
        
        Parameters
        ----------
        source_type : str
            Type of source (e.g., "journal", "repository", "conference", 
            "ebook platform", "book series")
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Sources
            Updated Sources object
        """
        return self.filter(type=source_type, **kwargs)

    def filter_by_publisher(self, publisher_id=None, **kwargs):
        """Filter by publisher.
        
        Parameters
        ----------
        publisher_id : str, optional
            OpenAlex ID of the publisher
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Sources
            Updated Sources object
        """
        if publisher_id:
            return self.filter(host_organization=publisher_id, **kwargs)
        return self.filter(**kwargs)

    def filter_by_issn(self, issn, **kwargs):
        """Filter by ISSN.
        
        Parameters
        ----------
        issn : str
            ISSN identifier
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Sources
            Updated Sources object
        """
        return self.filter(issn=issn, **kwargs)

    def filter_by_is_oa(self, is_oa=True, **kwargs):
        """Filter by open access status.
        
        Parameters
        ----------
        is_oa : bool
            Whether to filter for open access sources
        **kwargs : dict
            Additional filter parameters
            
        Returns
        -------
        Sources
            Updated Sources object
        """
        return self.filter(is_oa=is_oa, **kwargs)

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
        Sources
            Updated Sources object
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
        Sources
            Updated Sources object
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)
        return self.filter(**kwargs)


# Aliases
Journals = Sources
