"""OpenAlex entities module."""

from .authors import Author
from .authors import Authors
from .autocomplete import autocomplete
from .autocomplete import Autocomplete
from .domains import Domain
from .domains import Domains
from .fields import Field
from .fields import Fields
from .funders import Funder
from .funders import Funders
from .institutions import Institution
from .institutions import Institutions
from .keywords import Keyword
from .keywords import Keywords
from .publishers import Publisher
from .publishers import Publishers
from .sources import Journals
from .sources import Source
from .sources import Sources
from .subfields import Subfield
from .subfields import Subfields
from .topics import Topic
from .topics import Topics
from .works import Work
from .works import Works

# Aliases
People = Authors

__all__ = [
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
    "Autocomplete",
    "autocomplete",
    "People",
    "Journals",
]
