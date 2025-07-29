"""Source entity models."""

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel

from .base import DehydratedEntity
from .base import OpenAlexEntity


class SourceEntity(OpenAlexEntity):
    """Complete Source entity model."""
    
    # Basic information
    display_name: Optional[str] = None
    issn_l: Optional[str] = None
    issn: Optional[List[str]] = None
    
    # Publisher and host
    host_organization: Optional[str] = None
    host_organization_name: Optional[str] = None
    host_organization_lineage: Optional[List[str]] = None
    
    # Type and classification
    type: Optional[str] = None
    is_oa: Optional[bool] = None
    is_in_doaj: Optional[bool] = None
    
    # Metrics
    works_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    
    # Summary statistics
    summary_stats: Optional[dict] = None
    
    # APCs
    apc_prices: Optional[List[dict]] = None
    apc_usd: Optional[int] = None
    
    # Homepage and URLs
    homepage_url: Optional[str] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Topics
    topics: Optional[List[DehydratedEntity]] = None
    
    # Concepts (deprecated)
    x_concepts: Optional[List[dict]] = None
    
    # Societies
    societies: Optional[List[str]] = None
    
    # Abbreviation
    abbreviated_title: Optional[str] = None
    alternate_titles: Optional[List[str]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Source(dict):
    """Legacy Source class maintaining dict interface."""
    pass
