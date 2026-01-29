"""Type definitions for OpenAlex entities.

This module provides TypedDict definitions for all OpenAlex API entities,
making it easier to work with typed data in PyAlex.
"""

from pyalex.schemas.authors import Author
from pyalex.schemas.authors import AuthorCounts
from pyalex.schemas.authors import AuthorLastKnownInstitution
from pyalex.schemas.authors import AuthorSummaryStats
from pyalex.schemas.common import CountsByYear
from pyalex.schemas.common import DehydratedEntity
from pyalex.schemas.common import IDs
from pyalex.schemas.common import InternationalDisplay
from pyalex.schemas.funders import Funder
from pyalex.schemas.funders import FunderCounts
from pyalex.schemas.funders import FunderSummaryStats
from pyalex.schemas.institutions import Institution
from pyalex.schemas.institutions import InstitutionCounts
from pyalex.schemas.institutions import InstitutionGeo
from pyalex.schemas.institutions import InstitutionRepository
from pyalex.schemas.institutions import InstitutionSummaryStats
from pyalex.schemas.publishers import Publisher
from pyalex.schemas.publishers import PublisherCounts
from pyalex.schemas.publishers import PublisherSummaryStats
from pyalex.schemas.sources import APCPrice
from pyalex.schemas.sources import Source
from pyalex.schemas.sources import SourceCounts
from pyalex.schemas.sources import SourceSummaryStats
from pyalex.schemas.topics import Topic as TopicEntity
from pyalex.schemas.topics import TopicDomain
from pyalex.schemas.topics import TopicField
from pyalex.schemas.topics import TopicSiblings
from pyalex.schemas.topics import TopicSubfield
from pyalex.schemas.works import APC
from pyalex.schemas.works import AuthorPosition
from pyalex.schemas.works import Authorship
from pyalex.schemas.works import Biblio
from pyalex.schemas.works import Grant
from pyalex.schemas.works import Keyword
from pyalex.schemas.works import Location
from pyalex.schemas.works import OpenAccess
from pyalex.schemas.works import Topic
from pyalex.schemas.works import Work

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
