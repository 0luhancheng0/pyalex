"""Topic entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from .base import DehydratedEntity
from .base import OpenAlexEntity


class TopicEntity(OpenAlexEntity):
    """Complete Topic entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    description: Optional[str] = None
    
    # Keywords
    keywords: Optional[List[str]] = None
    
    # Hierarchy
    domain: Optional[DehydratedEntity] = None
    field: Optional[DehydratedEntity] = None
    subfield: Optional[DehydratedEntity] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    
    # Summary statistics
    summary_stats: Optional[dict] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Topic(dict):
    """Legacy Topic class maintaining dict interface."""
    pass
