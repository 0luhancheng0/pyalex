"""Entity identification and type detection utilities."""

import re
from typing import TYPE_CHECKING

from pyalex.entities.authors import Author
from pyalex.entities.authors import Authors
from pyalex.entities.domains import Domains
from pyalex.entities.fields import Fields
from pyalex.entities.funders import Funder
from pyalex.entities.funders import Funders
from pyalex.entities.institutions import Institution
from pyalex.entities.institutions import Institutions
from pyalex.entities.keywords import Keywords
from pyalex.entities.publishers import Publisher
from pyalex.entities.publishers import Publishers
from pyalex.entities.sources import Source
from pyalex.entities.sources import Sources
from pyalex.entities.subfields import Subfields
from pyalex.entities.topics import Topic
from pyalex.entities.topics import Topics
from pyalex.entities.works import Work
from pyalex.entities.works import Works

if TYPE_CHECKING:
    pass

# Entity pattern definitions - single source of truth for all entity types
ENTITY_PATTERNS: dict[str, tuple[str, type, str]] = {
    "work": (r"^W\d+$", Works, "work"),
    "author": (r"^A\d+$", Authors, "author"),
    "source": (r"^S\d+$", Sources, "source"),
    "institution": (r"^I\d+$", Institutions, "institution"),
    "topic": (r"^T\d+$", Topics, "topic"),
    "publisher": (r"^P\d+$", Publishers, "publisher"),
    "funder": (r"^F\d+$", Funders, "funder"),
    "keyword": (r"^K\d+$", Keywords, "keyword"),
    "domain": (r"^domains/\d+$", Domains, "domain"),
    "field": (r"^fields/\d+$", Fields, "field"),
    "subfield": (r"^subfields/\d+$", Subfields, "subfield"),
}


def _clean_id(openalex_id: str) -> str:
    """Clean OpenAlex ID by removing URL prefix.

    Args:
        openalex_id: The OpenAlex ID (may include URL prefix)

    Returns:
        Cleaned ID string
    """
    if openalex_id.startswith("https://openalex.org/"):
        return openalex_id.replace("https://openalex.org/", "")
    return openalex_id


def _match_entity_pattern(openalex_id: str) -> tuple[str, type, str]:
    """Match ID against entity patterns.

    Args:
        openalex_id: The OpenAlex ID to match

    Returns:
        Tuple of (pattern_key, entity_class, entity_type)

    Raises:
        ValueError: If no pattern matches
    """
    cleaned_id = _clean_id(openalex_id)

    for key, (pattern, entity_class, entity_type) in ENTITY_PATTERNS.items():
        if re.match(pattern, cleaned_id):
            return key, entity_class, entity_type

    raise ValueError(f"Unknown OpenAlex ID format: {openalex_id}")


def from_id(
    openalex_id: str,
) -> Work | Author | Source | Institution | Topic | Publisher | Funder | dict | None:
    """Get an OpenAlex entity from its ID with automatic type detection.

    This function analyzes the OpenAlex ID to determine the entity type
    and returns the appropriate entity object.

    Args:
        openalex_id: The OpenAlex ID (e.g., 'W2741809807', 'A2208157607', etc.).

    Returns:
        The OpenAlex entity object, or None if ID format is not recognized.

    Raises:
        ValueError: If the ID format is not recognized.

    Examples:
        >>> work = from_id('W2741809807')
        >>> author = from_id('A2208157607')
        >>> source = from_id('S2764455177')
    """
    _, entity_class, _ = _match_entity_pattern(openalex_id)
    cleaned_id = _clean_id(openalex_id)

    # Handle special cases for hierarchical IDs
    if "/" in cleaned_id:
        # Extract numeric portion for domains, fields, subfields
        numeric_id = cleaned_id.split("/")[-1]
        return entity_class()[numeric_id]

    return entity_class()[cleaned_id]


def get_entity_type(openalex_id: str) -> str:
    """Get the entity type from an OpenAlex ID.

    Args:
        openalex_id: The OpenAlex ID.

    Returns:
        The entity type ('work', 'author', 'source', etc.).

    Raises:
        ValueError: If the ID format is not recognized.

    Examples:
        >>> get_entity_type('W2741809807')
        'work'
        >>> get_entity_type('A2208157607')
        'author'
    """
    _, _, entity_type = _match_entity_pattern(openalex_id)
    return entity_type
