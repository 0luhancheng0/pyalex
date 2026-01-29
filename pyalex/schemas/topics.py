"""Type definitions for OpenAlex Topics entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.schemas.common import CountsByYear
from pyalex.schemas.common import IDs


class TopicDomain(BaseModel):
    """Domain information for a topic."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None


class TopicField(BaseModel):
    """Field information for a topic."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None


class TopicSubfield(BaseModel):
    """Subfield information for a topic."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None


class TopicSiblings(BaseModel):
    """Sibling topics."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None


class Topic(BaseModel):
    """OpenAlex Topic entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    ids: IDs | None = None
    subfield: TopicSubfield | None = None
    field: TopicField | None = None
    domain: TopicDomain | None = None
    siblings: list[TopicSiblings] | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    counts_by_year: list[CountsByYear] | None = None
    works_api_url: str | None = None
    updated_date: str | None = None
    created_date: str | None = None
