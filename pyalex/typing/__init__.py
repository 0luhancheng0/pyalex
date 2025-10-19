"""Type definitions for OpenAlex entities.

This module provides TypedDict definitions for all OpenAlex API entities,
making it easier to work with typed data in PyAlex.
"""

from pyalex.typing.authors import Author
from pyalex.typing.authors import AuthorCounts
from pyalex.typing.authors import AuthorLastKnownInstitution
from pyalex.typing.authors import AuthorSummaryStats
from pyalex.typing.common import CountsByYear
from pyalex.typing.common import DehydratedEntity
from pyalex.typing.common import IDs
from pyalex.typing.common import InternationalDisplay
from pyalex.typing.funders import Funder
from pyalex.typing.funders import FunderCounts
from pyalex.typing.funders import FunderSummaryStats
from pyalex.typing.institutions import Institution
from pyalex.typing.institutions import InstitutionCounts
from pyalex.typing.institutions import InstitutionGeo
from pyalex.typing.institutions import InstitutionRepository
from pyalex.typing.institutions import InstitutionSummaryStats
from pyalex.typing.publishers import Publisher
from pyalex.typing.publishers import PublisherCounts
from pyalex.typing.publishers import PublisherSummaryStats
from pyalex.typing.sources import APCPrice
from pyalex.typing.sources import Source
from pyalex.typing.sources import SourceCounts
from pyalex.typing.sources import SourceSummaryStats
from pyalex.typing.topics import Topic as TopicEntity
from pyalex.typing.topics import TopicDomain
from pyalex.typing.topics import TopicField
from pyalex.typing.topics import TopicSiblings
from pyalex.typing.topics import TopicSubfield
from pyalex.typing.works import APC
from pyalex.typing.works import AuthorPosition
from pyalex.typing.works import Authorship
from pyalex.typing.works import Biblio
from pyalex.typing.works import Grant
from pyalex.typing.works import Keyword
from pyalex.typing.works import Location
from pyalex.typing.works import OpenAccess
from pyalex.typing.works import Topic
from pyalex.typing.works import Work

__all__ = [
    # Works
    "Work",
    "Authorship",
    "AuthorPosition",
    "Location",
    "OpenAccess",
    "APC",
    "Biblio",
    "Grant",
    "Topic",
    "Keyword",
    # Authors
    "Author",
    "AuthorCounts",
    "AuthorSummaryStats",
    "AuthorLastKnownInstitution",
    # Sources
    "Source",
    "SourceCounts",
    "SourceSummaryStats",
    "APCPrice",
    # Institutions
    "Institution",
    "InstitutionGeo",
    "InstitutionCounts",
    "InstitutionSummaryStats",
    "InstitutionRepository",
    # Topics
    "TopicEntity",
    "TopicDomain",
    "TopicField",
    "TopicSubfield",
    "TopicSiblings",
    # Publishers
    "Publisher",
    "PublisherCounts",
    "PublisherSummaryStats",
    # Funders
    "Funder",
    "FunderCounts",
    "FunderSummaryStats",
    # Common
    "DehydratedEntity",
    "CountsByYear",
    "IDs",
    "InternationalDisplay",
]
