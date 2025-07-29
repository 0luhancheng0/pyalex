"""Institution entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from .base import DehydratedEntity
from .base import LocationInfo
from .base import OpenAlexEntity


class InstitutionEntity(OpenAlexEntity):
    """Complete Institution entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    display_name_alternatives: Optional[List[str]] = None
    display_name_acronyms: Optional[List[str]] = None
    
    # Location
    country_code: Optional[str] = None
    geo: Optional[LocationInfo] = None
    
    # Type and classification
    type: Optional[str] = None
    lineage: Optional[List[str]] = None
    
    # Identifiers
    ror: Optional[str] = None
    homepage_url: Optional[str] = None
    image_url: Optional[str] = None
    image_thumbnail_url: Optional[str] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    
    # Summary statistics
    summary_stats: Optional[dict] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Topics and concepts
    topics: Optional[List[DehydratedEntity]] = None
    x_concepts: Optional[List[dict]] = None
    
    # Associated institutions
    associated_institutions: Optional[List[DehydratedEntity]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Institution(dict):
    """Legacy Institution class maintaining dict interface."""
    pass
