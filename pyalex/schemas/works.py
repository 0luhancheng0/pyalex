"""Type definitions for OpenAlex Works entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.schemas.common import CountsByYear
from pyalex.schemas.common import DehydratedEntity
from pyalex.schemas.common import IDs


class Biblio(BaseModel):
    """Bibliographic information for a work."""

    model_config = ConfigDict(extra="allow")

    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None


class OpenAccess(BaseModel):
    """Open access status and location information."""

    model_config = ConfigDict(extra="allow")

    is_oa: bool | None = None
    oa_status: str | None = None
    oa_url: str | None = None
    any_repository_has_fulltext: bool | None = None


class APC(BaseModel):
    """Article Processing Charge information."""

    model_config = ConfigDict(extra="allow")

    value: int | None = None
    currency: str | None = None
    value_usd: int | None = None
    provenance: str | None = None


class Location(BaseModel):
    """Location where a work is hosted."""

    model_config = ConfigDict(extra="allow")

    is_oa: bool | None = None
    landing_page_url: str | None = None
    pdf_url: str | None = None
    source: DehydratedEntity | None = None
    license: str | None = None
    license_id: str | None = None
    version: str | None = None
    is_accepted: bool | None = None
    is_published: bool | None = None


class AuthorPosition(BaseModel):
    """Author position information within authorship."""

    model_config = ConfigDict(extra="allow")

    first: bool | None = None
    middle: bool | None = None
    last: bool | None = None


class Authorship(BaseModel):
    """Authorship information for a work."""

    model_config = ConfigDict(extra="allow")

    author: DehydratedEntity | None = None
    author_position: str | None = None
    countries: list[str] | None = None
    institutions: list[DehydratedEntity] | None = None
    is_corresponding: bool | None = None
    raw_affiliation_string: str | None = None
    raw_affiliation_strings: list[str] | None = None
    raw_author_name: str | None = None


class Topic(BaseModel):
    """Topic associated with a work."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    score: float | None = None
    subfield: DehydratedEntity | None = None
    field: DehydratedEntity | None = None
    domain: DehydratedEntity | None = None


class Keyword(BaseModel):
    """Keyword associated with a work."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    score: float | None = None


class Grant(BaseModel):
    """Grant funding information."""

    model_config = ConfigDict(extra="allow")

    funder: str | None = None
    funder_display_name: str | None = None
    award_id: str | None = None


class Work(BaseModel):
    """OpenAlex Work entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    doi: str | None = None
    title: str | None = None
    display_name: str | None = None
    publication_year: int | None = None
    publication_date: str | None = None
    type: str | None = None
    type_crossref: str | None = None
    indexed_in: list[str] | None = None
    open_access: OpenAccess | None = None
    authorships: list[Authorship] | None = None
    author_countries: list[str] | None = None
    countries_distinct_count: int | None = None
    institutions_distinct_count: int | None = None
    corresponding_author_ids: list[str] | None = None
    corresponding_institution_ids: list[str] | None = None
    apc_list: APC | None = None
    apc_paid: APC | None = None
    fwci: float | None = None
    has_fulltext: bool | None = None
    fulltext_origin: str | None = None
    cited_by_count: int | None = None
    cited_by_percentile_year: dict[str, float] | None = None
    biblio: Biblio | None = None
    is_retracted: bool | None = None
    is_paratext: bool | None = None
    primary_location: Location | None = None
    best_oa_location: Location | None = None
    locations: list[Location] | None = None
    locations_count: int | None = None
    language: str | None = None
    grants: list[Grant] | None = None
    datasets: list[str] | None = None
    versions: list[str] | None = None
    referenced_works_count: int | None = None
    referenced_works: list[str] | None = None
    related_works: list[str] | None = None
    abstract_inverted_index: dict[str, list[int]] | None = None
    abstract: str | None = None
    cited_by_api_url: str | None = None
    counts_by_year: list[CountsByYear] | None = None
    updated_date: str | None = None
    created_date: str | None = None
    topics: list[Topic] | None = None
    keywords: list[Keyword] | None = None
    concepts: list[dict] | None = None  # Legacy field
    mesh: list[dict] | None = None
    sustainable_development_goals: list[dict] | None = None
    ids: IDs | None = None
    ngrams_url: str | None = None
