"""Subfield entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from .base import DehydratedEntity
from .base import OpenAlexEntity


class SubfieldEntity(OpenAlexEntity):
    """Complete Subfield entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    description: Optional[str] = None
    
    # Hierarchy
    field: Optional[DehydratedEntity] = None
    domain: Optional[DehydratedEntity] = None
    
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
class Subfield(dict):
    """Legacy Subfield class maintaining dict interface."""
    pass
