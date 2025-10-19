"""Type definitions for OpenAlex Institutions entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.typing.common import CountsByYear
from pyalex.typing.common import DehydratedEntity
from pyalex.typing.common import IDs


class InstitutionGeo(BaseModel):
    """Geographic information for an institution."""

    model_config = ConfigDict(extra="allow")

    city: str | None = None
    geonames_city_id: str | None = None
    region: str | None = None
    country_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class InstitutionCounts(BaseModel):
    """Citation and work counts for an institution."""

    model_config = ConfigDict(extra="allow")

    year: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    oa_works_count: int | None = None


class InstitutionSummaryStats(BaseModel):
    """Summary statistics for an institution."""

    model_config = ConfigDict(extra="allow")

    h_index: int | None = None
    i10_index: int | None = None


class InstitutionRepository(BaseModel):
    """Repository hosted by an institution."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    host_organization: str | None = None
    host_organization_name: str | None = None


class Institution(BaseModel):
    """OpenAlex Institution entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    ror: str | None = None
    display_name: str | None = None
    country_code: str | None = None
    type: str | None = None
    type_id: str | None = None
    homepage_url: str | None = None
    image_url: str | None = None
    image_thumbnail_url: str | None = None
    display_name_acronyms: list[str] | None = None
    display_name_alternatives: list[str] | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    summary_stats: InstitutionSummaryStats | None = None
    ids: IDs | None = None
    geo: InstitutionGeo | None = None
    international: dict[str, str] | None = None
    associated_institutions: list[DehydratedEntity] | None = None
    repositories: list[InstitutionRepository] | None = None
    lineage: list[str] | None = None
    x_concepts: list[dict] | None = None  # Legacy field
    topics: list[dict] | None = None
    counts_by_year: list[CountsByYear] | None = None
    works_api_url: str | None = None
    updated_date: str | None = None
    created_date: str | None = None
