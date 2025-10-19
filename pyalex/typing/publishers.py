"""Type definitions for OpenAlex Publishers entity."""

from pydantic import BaseModel
from pydantic import ConfigDict

from pyalex.typing.common import CountsByYear
from pyalex.typing.common import DehydratedEntity
from pyalex.typing.common import IDs


class PublisherCounts(BaseModel):
    """Citation and work counts for a publisher."""

    model_config = ConfigDict(extra="allow")

    year: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    oa_works_count: int | None = None


class PublisherSummaryStats(BaseModel):
    """Summary statistics for a publisher."""

    model_config = ConfigDict(extra="allow")

    h_index: int | None = None
    i10_index: int | None = None


class Publisher(BaseModel):
    """OpenAlex Publisher entity."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None
    alternate_titles: list[str] | None = None
    hierarchy_level: int | None = None
    parent_publisher: DehydratedEntity | None = None
    lineage: list[str] | None = None
    country_codes: list[str] | None = None
    homepage_url: str | None = None
    image_url: str | None = None
    image_thumbnail_url: str | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    summary_stats: PublisherSummaryStats | None = None
    ids: IDs | None = None
    sources_api_url: str | None = None
    counts_by_year: list[CountsByYear] | None = None
    updated_date: str | None = None
    created_date: str | None = None
