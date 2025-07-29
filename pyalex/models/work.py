"""Work entity models."""

from datetime import datetime
from typing import Any
from typing import List
from typing import Optional

from pydantic import BaseModel

from .base import DehydratedEntity
from .base import OpenAlexEntity


class AbstractInvertedIndex(BaseModel):
    """Inverted index for abstract text."""
    
    model_config = {"extra": "allow"}  # Allow any word as key


class WorkLocation(BaseModel):
    """Work location information."""
    
    source: Optional[DehydratedEntity] = None
    landing_page_url: Optional[str] = None
    pdf_url: Optional[str] = None
    is_oa: Optional[bool] = None
    version: Optional[str] = None
    license: Optional[str] = None


class WorkAuthorship(BaseModel):
    """Work authorship information."""
    
    author_position: Optional[str] = None
    author: Optional[DehydratedEntity] = None
    institutions: Optional[List[DehydratedEntity]] = None
    countries: Optional[List[str]] = None
    is_corresponding: Optional[bool] = None
    raw_author_name: Optional[str] = None
    raw_affiliation_strings: Optional[List[str]] = None


class WorkConcept(BaseModel):
    """Work concept information."""
    
    id: str
    wikidata: Optional[str] = None
    display_name: str
    level: int
    score: float


class WorkMesh(BaseModel):
    """Work MeSH term information."""
    
    descriptor_ui: str
    descriptor_name: str
    qualifier_ui: Optional[str] = None
    qualifier_name: Optional[str] = None
    is_major_topic: bool


class WorkGrant(BaseModel):
    """Work grant information."""
    
    funder: Optional[DehydratedEntity] = None
    funder_display_name: Optional[str] = None
    award_id: Optional[str] = None


class WorkBiblio(BaseModel):
    """Work bibliographic information."""
    
    volume: Optional[str] = None
    issue: Optional[str] = None
    first_page: Optional[str] = None
    last_page: Optional[str] = None


class WorkOpenAccess(BaseModel):
    """Work open access information."""
    
    is_oa: bool
    oa_date: Optional[datetime] = None
    oa_url: Optional[str] = None
    any_repository_has_fulltext: bool


class WorkSustainableDevelopmentGoal(BaseModel):
    """Work sustainable development goal information."""
    
    id: str
    display_name: str
    score: float


class WorkKeyword(BaseModel):
    """Work keyword information."""
    
    id: str
    display_name: str
    score: float


class WorkEntity(OpenAlexEntity):
    """Complete Work entity model."""
    
    # Basic information
    title: Optional[str] = None
    display_name: Optional[str] = None
    publication_year: Optional[int] = None
    publication_date: Optional[datetime] = None
    
    # Abstract
    abstract_inverted_index: Optional[AbstractInvertedIndex] = None
    
    # Identifiers and URLs
    doi: Optional[str] = None
    language: Optional[str] = None
    primary_location: Optional[WorkLocation] = None
    locations: Optional[List[WorkLocation]] = None
    best_oa_location: Optional[WorkLocation] = None
    
    # Type and classification
    type: Optional[str] = None
    type_crossref: Optional[str] = None
    
    # Authors and institutions
    authorships: Optional[List[WorkAuthorship]] = None
    
    # Source information
    host_venue: Optional[DehydratedEntity] = None  # Deprecated
    primary_topic: Optional[DehydratedEntity] = None
    topics: Optional[List[DehydratedEntity]] = None
    keywords: Optional[List[WorkKeyword]] = None
    
    # Concepts (deprecated)
    concepts: Optional[List[WorkConcept]] = None
    
    # MeSH terms
    mesh: Optional[List[WorkMesh]] = None
    
    # Citations and references
    cited_by_count: Optional[int] = None
    citing_works_count: Optional[int] = None
    referenced_works_count: Optional[int] = None
    related_works: Optional[List[str]] = None
    referenced_works: Optional[List[str]] = None
    
    # Bibliographic info
    biblio: Optional[WorkBiblio] = None
    
    # Open access
    is_retracted: Optional[bool] = None
    is_paratext: Optional[bool] = None
    open_access: Optional[WorkOpenAccess] = None
    
    # Grants and funding
    grants: Optional[List[WorkGrant]] = None
    
    # Sustainable development goals
    sustainable_development_goals: Optional[List[WorkSustainableDevelopmentGoal]] = None
    
    # APCs (Article Processing Charges)
    apc_list: Optional[dict] = None
    apc_paid: Optional[dict] = None
    
    # Counts by year
    counts_by_year: Optional[List[dict]] = None
    
    # Updated date
    updated_date: Optional[datetime] = None


# Legacy class for backward compatibility
class Work(dict):
    """Legacy Work class maintaining dict interface."""
    
    def __getitem__(self, key):
        if key == "abstract":
            from pyalex.utils import invert_abstract
            return invert_abstract(self.get("abstract_inverted_index"))
        return super().__getitem__(key)
    
    def ngrams(self, return_meta=False):
        """Get n-grams for the work."""
        from pyalex.client.session import get_requests_session
        from pyalex.client.auth import OpenAlexAuth
        from pyalex.api import config
        from pyalex.api import OpenAlexResponseList
        import warnings
        
        openalex_id = self["id"].split("/")[-1]
        n_gram_url = f"{config.openalex_url}/works/{openalex_id}/ngrams"

        res = get_requests_session().get(n_gram_url, auth=OpenAlexAuth(config))
        res.raise_for_status()
        results = res.json()

        resp_list = OpenAlexResponseList(results["ngrams"], results["meta"])

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return resp_list, resp_list.meta
        else:
            return resp_list
