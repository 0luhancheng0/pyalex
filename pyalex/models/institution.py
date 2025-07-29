"""Institution entity models."""

from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from .base import DehydratedEntity
from .base import OpenAlexEntity


class InstitutionGeo(BaseModel):
    """Institution geographic information."""
    
    city: Optional[str] = None
    geonames_city_id: Optional[str] = None
    region: Optional[str] = None
    country_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InstitutionInternational(BaseModel):
    """Institution international display names."""
    
    display_name: Optional[dict] = None  # Language code -> display name mapping


class InstitutionAssociated(BaseModel):
    """Associated institution information."""
    
    id: str
    ror: Optional[str] = None
    display_name: Optional[str] = None
    country_code: Optional[str] = None
    type: Optional[str] = None
    relationship: Optional[str] = None  # "parent", "child", "related"


class InstitutionRepository(BaseModel):
    """Repository information for institution."""
    
    id: str
    display_name: Optional[str] = None
    host_organization: Optional[str] = None
    host_organization_name: Optional[str] = None
    host_organization_lineage: Optional[List[str]] = None


class InstitutionRole(BaseModel):
    """Institution role information."""
    
    role: str  # "institution", "funder", "publisher"
    id: str
    works_count: Optional[int] = None


class InstitutionSummaryStats(BaseModel):
    """Institution summary statistics."""
    
    two_yr_mean_citedness: Optional[float] = Field(
        None, 
        alias='2yr_mean_citedness'
    )
    h_index: Optional[int] = None
    i10_index: Optional[int] = None


class InstitutionCounts(BaseModel):
    """Institution counts by year."""
    
    year: int
    works_count: int
    cited_by_count: int


class InstitutionXConcept(BaseModel):
    """Deprecated concept information for institutions."""
    
    id: str
    wikidata: Optional[str] = None
    display_name: Optional[str] = None
    level: Optional[int] = None
    score: Optional[float] = None


class InstitutionEntity(OpenAlexEntity):
    """Complete Institution entity model."""
    
    # Basic information - inherited from OpenAlexEntity:
    # id: str
    # display_name: Optional[str] = None
    # ids: Optional[OpenAlexID] = None  
    # created_date: Optional[datetime] = None
    # updated_date: Optional[datetime] = None
    
    display_name_alternatives: Optional[List[str]] = None
    display_name_acronyms: Optional[List[str]] = None
    
    # Location and geographic information
    country_code: Optional[str] = None
    geo: Optional[InstitutionGeo] = None
    
    # Type and classification
    type: Optional[str] = None  # ROR controlled vocabulary
    lineage: Optional[List[str]] = None
    is_super_system: Optional[bool] = None
    
    # External identifiers
    ror: Optional[str] = None
    
    # URLs and media
    homepage_url: Optional[str] = None
    image_url: Optional[str] = None
    image_thumbnail_url: Optional[str] = None
    
    # Internationalization
    international: Optional[InstitutionInternational] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    works_api_url: Optional[str] = None
    
    # Summary statistics
    summary_stats: Optional[InstitutionSummaryStats] = None
    
    # Counts by year
    counts_by_year: Optional[List[InstitutionCounts]] = None
    
    # Relationships
    associated_institutions: Optional[List[InstitutionAssociated]] = None
    repositories: Optional[List[InstitutionRepository]] = None
    roles: Optional[List[InstitutionRole]] = None
    
    # Topics and concepts (deprecated)
    topics: Optional[List[DehydratedEntity]] = None
    x_concepts: Optional[List[InstitutionXConcept]] = None


# Legacy class for backward compatibility
class Institution(dict):
    """Legacy Institution class maintaining dict interface."""
    pass
