"""Type definitions for OpenAlex Funders entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.schemas.common import CountsByYear
from pyalex.schemas.common import IDs


class FunderCounts(BaseModel):
    """Citation and work counts for a funder."""

    model_config = ConfigDict(extra="allow")

    year: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    oa_works_count: int | None = None


class FunderSummaryStats(BaseModel):
    """Summary statistics for a funder."""

    model_config = ConfigDict(extra="allow")

    h_index: int | None = None
    i10_index: int | None = None


class Funder(BaseModel):
    """OpenAlex Funder entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    alternate_titles: list[str] | None = None
    country_code: str | None = None
    description: str | None = None
    homepage_url: str | None = None
    image_url: str | None = None
    image_thumbnail_url: str | None = None
    grants_count: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    summary_stats: FunderSummaryStats | None = None
    ids: IDs | None = None
    counts_by_year: list[CountsByYear] | None = None
    roles: list[dict] | None = None
    updated_date: str | None = None
    created_date: str | None = None
