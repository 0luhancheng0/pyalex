"""Funder entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from .base import OpenAlexEntity


class FunderEntity(OpenAlexEntity):
    """Complete Funder entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    alternate_titles: Optional[List[str]] = None
    description: Optional[str] = None
    
    # Country
    country_code: Optional[str] = None
    
    # URLs
    homepage_url: Optional[str] = None
    image_url: Optional[str] = None
    image_thumbnail_url: Optional[str] = None
    
    # Identifiers
    crossref_id: Optional[str] = None
    doi: Optional[str] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    grants_count: Optional[int] = None
    
    # Summary statistics
    summary_stats: Optional[dict] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Roles
    roles: Optional[List[dict]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Funder(dict):
    """Legacy Funder class maintaining dict interface."""
    pass
