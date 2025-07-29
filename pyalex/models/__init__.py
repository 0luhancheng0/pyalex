"""Pydantic models for OpenAlex entities."""

from .base import OpenAlexEntity, OpenAlexEntityMeta
from .work import Work, WorkEntity
from .author import Author, AuthorEntity
from .source import Source, SourceEntity
from .institution import Institution, InstitutionEntity
from .topic import Topic, TopicEntity
from .publisher import Publisher, PublisherEntity
from .funder import Funder, FunderEntity
from .keyword import Keyword, KeywordEntity
from .domain import Domain, DomainEntity
from .field import Field, FieldEntity
from .subfield import Subfield, SubfieldEntity

__all__ = [
    "OpenAlexEntity",
    "OpenAlexEntityMeta",
    "Work",
    "WorkEntity",
    "Author",
    "AuthorEntity",
    "Source",
    "SourceEntity",
    "Institution",
    "InstitutionEntity",
    "Topic",
    "TopicEntity",
    "Publisher",
    "PublisherEntity",
    "Funder",
    "FunderEntity",
    "Keyword",
    "KeywordEntity",
    "Domain",
    "DomainEntity",
    "Field",
    "FieldEntity",
    "Subfield",
    "SubfieldEntity",
]
