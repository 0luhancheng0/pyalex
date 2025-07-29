"""Author entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel

from .base import DehydratedEntity
from .base import LocationInfo
from .base import OpenAlexEntity


class AuthorAffiliation(BaseModel):
    """Author affiliation information."""
    
    institution: Optional[DehydratedEntity] = None
    years: Optional[List[int]] = None


class AuthorCounts(BaseModel):
    """Author citation counts."""
    
    year: int
    works_count: int
    cited_by_count: int


class AuthorEntity(OpenAlexEntity):
    """Complete Author entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    display_name_alternatives: Optional[List[str]] = None
    
    # Identifiers
    orcid: Optional[str] = None
    
    # Affiliations
    last_known_institution: Optional[DehydratedEntity] = None
    last_known_institutions: Optional[List[DehydratedEntity]] = None
    affiliations: Optional[List[AuthorAffiliation]] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    i10_index: Optional[int] = None
    h_index: Optional[int] = None
    
    # Summary statistics
    summary_stats: Optional[dict] = None
    
    # Counts by year
    counts_by_year: Optional[List[AuthorCounts]] = None
    
    # Topics
    topics: Optional[List[DehydratedEntity]] = None
    
    # Concepts (deprecated)
    x_concepts: Optional[List[dict]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Author(dict):
    """Legacy Author class maintaining dict interface."""
    pass
