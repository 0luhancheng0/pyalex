"""Work entity models."""

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
    """Work concept information (deprecated)."""
    
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
    
    funder: Optional[str] = None  # OpenAlex ID
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
    oa_status: Optional[str] = None
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


class WorkAPC(BaseModel):
    """Work APC (Article Processing Charge) information."""
    
    value: Optional[int] = None
    currency: Optional[str] = None
    provenance: Optional[str] = None
    value_usd: Optional[int] = None


class WorkCountsByYear(BaseModel):
    """Work citation counts by year."""
    
    year: int
    cited_by_count: int


class WorkCitationNormalizedPercentile(BaseModel):
    """Work citation normalized percentile information."""
    
    value: Optional[float] = None
    is_in_top_1_percent: Optional[bool] = None
    is_in_top_10_percent: Optional[bool] = None


class WorkTopic(BaseModel):
    """Work topic information with hierarchical structure."""
    
    id: str
    display_name: str
    score: float
    subfield: Optional[DehydratedEntity] = None
    field: Optional[DehydratedEntity] = None
    domain: Optional[DehydratedEntity] = None


class WorkEntity(OpenAlexEntity):
    """Complete Work entity model."""
    
    # Basic information - inherited from OpenAlexEntity:
    # id: str
    # display_name: Optional[str] = None
    # ids: Optional[OpenAlexID] = None  
    # created_date: Optional[datetime] = None
    # updated_date: Optional[datetime] = None
    
    # Title (same as display_name)
    title: Optional[str] = None
    
    # Publication information
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None  # ISO 8601 date string
    
    # Abstract
    abstract_inverted_index: Optional[dict] = None  # Using dict to allow dynamic keys
    
    # Identifiers and URLs
    doi: Optional[str] = None
    language: Optional[str] = None  # ISO 639-1 format
    
    # Locations
    primary_location: Optional[WorkLocation] = None
    locations: Optional[List[WorkLocation]] = None
    locations_count: Optional[int] = None
    best_oa_location: Optional[WorkLocation] = None
    
    # Type and classification
    type: Optional[str] = None
    type_crossref: Optional[str] = None
    
    # Authors and institutions
    authorships: Optional[List[WorkAuthorship]] = None
    corresponding_author_ids: Optional[List[str]] = None
    corresponding_institution_ids: Optional[List[str]] = None
    institutions_distinct_count: Optional[int] = None
    countries_distinct_count: Optional[int] = None
    
    # Topics and concepts
    primary_topic: Optional[WorkTopic] = None
    topics: Optional[List[WorkTopic]] = None
    keywords: Optional[List[WorkKeyword]] = None
    concepts: Optional[List[WorkConcept]] = None  # Deprecated
    
    # MeSH terms
    mesh: Optional[List[WorkMesh]] = None
    
    # Citations and references
    cited_by_count: Optional[int] = None
    cited_by_api_url: Optional[str] = None
    referenced_works: Optional[List[str]] = None
    related_works: Optional[List[str]] = None
    citation_normalized_percentile: Optional[WorkCitationNormalizedPercentile] = None
    fwci: Optional[float] = None  # Field-weighted Citation Impact
    
    # Counts by year
    counts_by_year: Optional[List[WorkCountsByYear]] = None
    
    # Bibliographic info
    biblio: Optional[WorkBiblio] = None
    
    # Flags
    is_retracted: Optional[bool] = None
    is_paratext: Optional[bool] = None
    has_fulltext: Optional[bool] = None
    fulltext_origin: Optional[str] = None  # "pdf" or "ngrams"
    
    # Open access
    open_access: Optional[WorkOpenAccess] = None
    license: Optional[str] = None
    
    # Grants and funding
    grants: Optional[List[WorkGrant]] = None
    
    # APCs (Article Processing Charges)
    apc_list: Optional[WorkAPC] = None
    apc_paid: Optional[WorkAPC] = None
    
    # Sustainable development goals
    sustainable_development_goals: Optional[List[WorkSustainableDevelopmentGoal]] = None
    
    # Indexing information
    indexed_in: Optional[List[str]] = None


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
