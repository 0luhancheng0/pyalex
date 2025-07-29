"""Keyword entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from .base import OpenAlexEntity


class KeywordEntity(OpenAlexEntity):
    """Complete Keyword entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Keyword(dict):
    """Legacy Keyword class maintaining dict interface."""
    pass
