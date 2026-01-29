"""Type definitions for OpenAlex Authors entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.schemas.common import CountsByYear
from pyalex.schemas.common import IDs


class AuthorCounts(BaseModel):
    """Citation and work counts for an author."""

    model_config = ConfigDict(extra="allow")

    year: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    oa_works_count: int | None = None


class AuthorSummaryStats(BaseModel):
    """Summary statistics for an author."""

    model_config = ConfigDict(extra="allow")

    h_index: int | None = None
    i10_index: int | None = None


class AuthorLastKnownInstitution(BaseModel):
    """Last known institutional affiliation."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    ror: str | None = None
    country_code: str | None = None
    type: str | None = None
    lineage: list[str] | None = None


class Author(BaseModel):
    """OpenAlex Author entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    orcid: str | None = None
    display_name: str | None = None
    display_name_alternatives: list[str] | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    summary_stats: AuthorSummaryStats | None = None
    ids: IDs | None = None
    last_known_institution: AuthorLastKnownInstitution | None = None
    last_known_institutions: list[AuthorLastKnownInstitution] | None = None
    affiliations: list[dict] | None = None
    x_concepts: list[dict] | None = None  # Legacy field
    topics: list[dict] | None = None
    counts_by_year: list[CountsByYear] | None = None
    works_api_url: str | None = None
    updated_date: str | None = None
    created_date: str | None = None
