"""
PyAlex API module.

This module imports from the refactored structure for better organization:
- models/: Pydantic models for type safety
- client/: HTTP client and authentication 
- core/: Core functionality like pagination, filtering
- entities/: Entity-specific classes

Note: Concept entities have been deprecated by OpenAlex in favor of Topics.
"""

# Core configuration and response classes
from pyalex.core.config import config
from pyalex.core.pagination import Paginator  
from pyalex.core.response import OpenAlexResponseList
from pyalex.core.response import QueryError
from pyalex.core.utils import invert_abstract

# Entity classes
from pyalex.entities import (
    Author, Authors,
    Autocomplete, autocomplete,
    Domain, Domains,
    Field, Fields,
    Funder, Funders,
    Institution, Institutions,
    Journals,
    Keyword, Keywords,
    People,
    Publisher, Publishers,
    Source, Sources,
    Subfield, Subfields,
    Topic, Topics,
    Work, Works,
)

# Utility functions
from pyalex.utils import from_id, get_entity_type

__all__ = [
    # Configuration
    "config",
    
    # Response classes
    "OpenAlexResponseList",
    "QueryError",
    "Paginator",
    
    # Main entity classes
    "Work",
    "Works", 
    "Author",
    "Authors",
    "Source",
    "Sources", 
    "Institution",
    "Institutions",
    "Topic",
    "Topics",
    "Publisher", 
    "Publishers",
    "Funder",
    "Funders",
    "Keyword",
    "Keywords",
    "Domain",
    "Domains",
    "Field", 
    "Fields",
    "Subfield",
    "Subfields",
    
    # Autocomplete
    "Autocomplete",
    "autocomplete",
    
    # Aliases
    "People",
    "Journals",
    
    # Utility functions
    "invert_abstract",
    "from_id",
    "get_entity_type",
]
