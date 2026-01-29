"""Common type definitions shared across OpenAlex entities."""

from pydantic import BaseModel
from pydantic import ConfigDict


class DehydratedEntity(BaseModel):
    """A minimal representation of an entity with just ID and display name."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    display_name: str | None = None


class CountsByYear(BaseModel):
    """Counts aggregated by year."""

    model_config = ConfigDict(extra="allow")

    year: int | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    oa_works_count: int | None = None


class IDs(BaseModel):
    """Collection of external identifiers for an entity."""

    model_config = ConfigDict(extra="allow")

    openalex: str | None = None
    doi: str | None = None
    mag: int | None = None
    pmid: str | None = None
    pmcid: str | None = None
    arxiv: str | None = None
    wikidata: str | None = None
    wikipedia: str | None = None
    issn_l: str | None = None
    issn: list[str] | None = None
    ror: str | None = None
    grid: str | None = None
    orcid: str | None = None
    scopus: str | None = None


class InternationalDisplay(BaseModel):
    """Multilingual display names for an entity."""

    model_config = ConfigDict(extra="allow")

    ar: str | None = None
    de: str | None = None
    en: str | None = None
    es: str | None = None
    fr: str | None = None
    hi: str | None = None
    it: str | None = None
    ja: str | None = None
    ko: str | None = None
    nl: str | None = None
    pl: str | None = None
    pt: str | None = None
    ru: str | None = None
    zh: str | None = None


class Geo(BaseModel):
    """Geographic information."""

    model_config = ConfigDict(extra="allow")

    city: str | None = None
    region: str | None = None
    country_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class SummaryStats(BaseModel):
    """Summary statistics common across entities."""

    model_config = ConfigDict(extra="allow")

    h_index: int | None = None
    i10_index: int | None = None
