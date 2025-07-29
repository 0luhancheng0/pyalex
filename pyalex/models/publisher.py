"""Publisher entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from .base import DehydratedEntity
from .base import OpenAlexEntity


class PublisherEntity(OpenAlexEntity):
    """Complete Publisher entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    alternate_titles: Optional[List[str]] = None
    
    # Hierarchy
    hierarchy_level: Optional[int] = None
    parent_publisher: Optional[str] = None
    lineage: Optional[List[str]] = None
    
    # Country
    country_codes: Optional[List[str]] = None
    
    # URLs
    homepage_url: Optional[str] = None
    image_url: Optional[str] = None
    image_thumbnail_url: Optional[str] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    
    # Sources
    sources_api_url: Optional[str] = None
    
    # Summary statistics
    summary_stats: Optional[dict] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Publisher(dict):
    """Legacy Publisher class maintaining dict interface."""
    pass
