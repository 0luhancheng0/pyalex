"""Base Pydantic models for OpenAlex entities."""

from datetime import datetime
from typing import Any
from typing import Optional

from pydantic import BaseModel


class OpenAlexEntityMeta(BaseModel):
    """Metadata for OpenAlex API responses."""
    
    count: Optional[int] = None
    db_response_time_ms: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None
    groups_count: Optional[int] = None
    next_cursor: Optional[str] = None


class OpenAlexID(BaseModel):
    """OpenAlex ID information."""
    
    openalex: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    mag: Optional[str] = None
    wikidata: Optional[str] = None
    wikipedia: Optional[str] = None
    # Author-specific IDs
    orcid: Optional[str] = None
    scopus: Optional[str] = None
    twitter: Optional[str] = None


class DehydratedEntity(BaseModel):
    """A dehydrated (minimal) version of an OpenAlex entity."""
    
    id: str
    display_name: Optional[str] = None


class LocationInfo(BaseModel):
    """Location information for entities."""
    
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class OpenAlexEntity(BaseModel):
    """Base class for all OpenAlex entities."""
    
    model_config = {"extra": "allow"}  # Allow additional fields from API
    
    id: str
    display_name: Optional[str] = None
    ids: Optional[OpenAlexID] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility."""
        return getattr(self, key, None)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like assignment for backward compatibility."""
        setattr(self, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method for backward compatibility."""
        return getattr(self, key, default)
