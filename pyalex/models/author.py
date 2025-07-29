"""Author entity models."""

from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from .base import DehydratedEntity
from .base import OpenAlexEntity


class AuthorAffiliation(BaseModel):
    """Author affiliation information."""
    
    institution: Optional[DehydratedEntity] = None
    years: Optional[List[int]] = None


class AuthorCounts(BaseModel):
    """Author citation counts by year."""
    
    year: int
    works_count: int
    cited_by_count: int


class AuthorSummaryStats(BaseModel):
    """Author summary statistics."""
    
    two_yr_mean_citedness: Optional[float] = Field(
        None, 
        alias='2yr_mean_citedness'
    )
    h_index: Optional[int] = None
    i10_index: Optional[int] = None


class AuthorXConcept(BaseModel):
    """Deprecated concept information for authors."""
    
    id: str
    wikidata: Optional[str] = None
    display_name: Optional[str] = None
    level: Optional[int] = None
    score: Optional[float] = None


class AuthorEntity(OpenAlexEntity):
    """Complete Author entity model."""
    
    # Basic information - inherited from OpenAlexEntity:
    # id: str
    # display_name: Optional[str] = None
    # ids: Optional[OpenAlexID] = None  
    # created_date: Optional[datetime] = None
    # updated_date: Optional[datetime] = None
    
    display_name_alternatives: Optional[List[str]] = None
    
    # Identifiers
    orcid: Optional[str] = None
    
    # Affiliations
    last_known_institution: Optional[DehydratedEntity] = None  # Deprecated
    last_known_institutions: Optional[List[DehydratedEntity]] = None
    affiliations: Optional[List[AuthorAffiliation]] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    
    # Summary statistics
    summary_stats: Optional[AuthorSummaryStats] = None
    
    # Counts by year
    counts_by_year: Optional[List[AuthorCounts]] = None
    
    # API URL for works
    works_api_url: Optional[str] = None
    
    # Topics (new concept system)
    topics: Optional[List[DehydratedEntity]] = None
    
    # Concepts (deprecated)
    x_concepts: Optional[List[AuthorXConcept]] = None


# Legacy class for backward compatibility
class Author(dict):
    """Legacy Author class maintaining dict interface."""
    pass
