"""Type definitions for OpenAlex Sources entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.schemas.common import CountsByYear
from pyalex.schemas.common import DehydratedEntity
from pyalex.schemas.common import IDs


class SourceCounts(BaseModel):
    """Citation and work counts for a source."""

    model_config = ConfigDict(extra="allow")

    year: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    oa_works_count: int | None = None


class SourceSummaryStats(BaseModel):
    """Summary statistics for a source."""

    model_config = ConfigDict(extra="allow")

    h_index: int | None = None
    i10_index: int | None = None


class APCPrice(BaseModel):
    """Article Processing Charge pricing information."""

    model_config = ConfigDict(extra="allow")

    price: int | None = None
    currency: str | None = None


class Source(BaseModel):
    """OpenAlex Source entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    issn_l: str | None = None
    issn: list[str] | None = None
    display_name: str | None = None
    host_organization: str | None = None
    host_organization_name: str | None = None
    host_organization_lineage: list[str] | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    summary_stats: SourceSummaryStats | None = None
    is_oa: bool | None = None
    is_in_doaj: bool | None = None
    ids: IDs | None = None
    homepage_url: str | None = None
    apc_prices: list[APCPrice] | None = None
    apc_usd: int | None = None
    country_code: str | None = None
    societies: list[DehydratedEntity] | None = None
    alternate_titles: list[str] | None = None
    abbreviated_title: str | None = None
    type: str | None = None
    x_concepts: list[dict] | None = None  # Legacy field
    topics: list[dict] | None = None
    counts_by_year: list[CountsByYear] | None = None
    works_api_url: str | None = None
    updated_date: str | None = None
    created_date: str | None = None
