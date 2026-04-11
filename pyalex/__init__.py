try:
    from pyalex._version import __version__
    from pyalex._version import __version_tuple__
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)

# Import from the new refactored structure
from .core.config import config
from .core.response import OpenAlexResponseList
from .core.utils import invert_abstract
from .entities import Author
from .entities import Authors
from .entities import Concept
from .entities import Concepts
from .entities import Domain
from .entities import Domains
from .entities import Field
from .entities import Fields
from .entities import Funder
from .entities import Funders
from .entities import Institution
from .entities import Institutions
from .entities import Journals
from .entities import Keyword
from .entities import Keywords
from .entities import People
from .entities import Publisher
from .entities import Publishers
from .entities import Source
from .entities import Sources
from .entities import Subfield
from .entities import Subfields
from .entities import Topic
from .entities import Topics
from .entities import Work
from .entities import Works
from .entities import autocomplete

# Import logging configuration
from .logger import get_logger
from .logger import setup_logger

# New utility functions
from .utils import from_id
from .utils import get_entity_type

__all__ = [
    "Works",
    "Work",
    "Authors",
    "Author",
    "Sources",
    "Source",
    "Funder",
    "Funders",
    "Keywords",
    "Keyword",
    "Concepts",
    "Concept",
    "Publishers",
    "Publisher",
    "Institutions",
    "Institution",
    "Domains",
    "Domain",
    "Fields",
    "Field",
    "Subfields",
    "Subfield",
    "Topics",
    "Topic",
    "People",
    "Journals",
    "autocomplete",
    "config",
    "invert_abstract",
    "OpenAlexResponseList",
    "setup_logger",
    "get_logger",
    "from_id",
    "get_entity_type",
]
