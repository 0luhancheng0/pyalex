try:
    from pyalex._version import __version__
    from pyalex._version import __version_tuple__
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)

# Import from the new refactored structure
from pyalex.core.config import config
from pyalex.core.response import OpenAlexResponseList
from pyalex.core.utils import invert_abstract
from pyalex.entities import Author
from pyalex.entities import Authors
from pyalex.entities import Concept
from pyalex.entities import Concepts
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

# Import logging configuration
from pyalex.logger import get_logger
from pyalex.logger import setup_logger

# New utility functions
from pyalex.utils import from_id
from pyalex.utils import get_entity_type

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
