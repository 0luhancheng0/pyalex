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
from pyalex.entities import Author
from pyalex.entities import Authors
from pyalex.entities import Autocomplete
from pyalex.entities import Domain
from pyalex.entities import Domains
from pyalex.entities import Field
from pyalex.entities import Fields
from pyalex.entities import Funder
from pyalex.entities import Funders
from pyalex.entities import Institution
from pyalex.entities import Institutions
from pyalex.entities import Journals
from pyalex.entities import Keyword
from pyalex.entities import Keywords
from pyalex.entities import People
from pyalex.entities import Publisher
from pyalex.entities import Publishers
from pyalex.entities import Source
from pyalex.entities import Sources
from pyalex.entities import Subfield
from pyalex.entities import Subfields
from pyalex.entities import Topic
from pyalex.entities import Topics
from pyalex.entities import Work
from pyalex.entities import Works
from pyalex.entities import autocomplete

# Utility functions
from pyalex.utils import from_id
from pyalex.utils import get_entity_type

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
