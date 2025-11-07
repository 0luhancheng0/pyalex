"""Entity type detection for OpenAlex results.

This module provides centralized entity type detection logic based on
field signatures in API response dictionaries. This is used across
the codebase for formatting, batch processing, and other operations
that need to identify entity types dynamically.
"""

from typing import Any


class EntityTypeDetector:
    """Detects OpenAlex entity types from result dictionaries.

    Entity types are determined by checking for characteristic fields
    in the result dictionary. This provides a single source of truth
    for entity type detection across the codebase.

    Supported entity types:
    - works: Academic publications with publication_year
    - authors: Researchers with works_count and institution info
    - institutions: Organizations with country_code
    - sources: Journals/publications with ISSN
    - publishers: Publishing companies with hierarchy_level
    - topics: Research topics with works_count
    - domains: Research domains with works_count
    - fields: Research fields with works_count
    - subfields: Research subfields with works_count
    - funders: Funding organizations with works_count
    - generic: Generic entities with works_count (fallback for topics/domains/fields/subfields/funders)
    - grouped: Grouped/aggregated query results
    """

    # Entity type signatures - ordered from most specific to least specific
    ENTITY_SIGNATURES = [
        ("works", lambda r: "publication_year" in r),
        (
            "authors",
            lambda r: (
                "works_count" in r
                and ("last_known_institutions" in r or "last_known_institution" in r)
            ),
        ),
        # Check sources before institutions since sources can also have country_code
        ("sources", lambda r: "issn" in r or "issn_l" in r),
        ("institutions", lambda r: "country_code" in r and "works_count" in r),
        ("publishers", lambda r: "hierarchy_level" in r),
        ("funders", lambda r: ("works_count" in r and "grants_count" in r)),
        ("topics", lambda r: ("works_count" in r and "subfield" in r)),
        ("domains", lambda r: ("works_count" in r and "fields_count" in r)),
        (
            "fields",
            lambda r: ("works_count" in r and "domain" in r and "subfields_count" in r),
        ),
        (
            "subfields",
            lambda r: ("works_count" in r and "field" in r and "topics_count" in r),
        ),
        # Generic fallback for topics/domains/fields/subfields that might not match above
        ("generic", lambda r: "works_count" in r),
    ]

    GROUPED_RESULT_SIGNATURE = lambda r: "key" in r and "count" in r

    @classmethod
    def detect(cls, result: dict[str, Any]) -> str:
        """Detect entity type from a result dictionary.

        Args:
            result: Dictionary from OpenAlex API response

        Returns:
            Entity type string ('works', 'authors', 'institutions', etc.)
            Returns 'fallback' if type cannot be determined.

        Examples:
            >>> detector = EntityTypeDetector()
            >>> detector.detect({'publication_year': 2020, 'title': 'AI'})
            'works'
            >>> detector.detect({'country_code': 'US', 'works_count': 1000})
            'institutions'
        """
        # Check for grouped results first
        if cls.GROUPED_RESULT_SIGNATURE(result):
            return "grouped"

        # Check entity signatures in order (most specific first)
        for entity_type, signature_func in cls.ENTITY_SIGNATURES:
            if signature_func(result):
                return entity_type

        # Fallback for unrecognized types
        return "fallback"

    @classmethod
    def is_works(cls, result: dict[str, Any]) -> bool:
        """Check if result is a work entity."""
        return "publication_year" in result

    @classmethod
    def is_author(cls, result: dict[str, Any]) -> bool:
        """Check if result is an author entity."""
        return "works_count" in result and (
            "last_known_institutions" in result or "last_known_institution" in result
        )

    @classmethod
    def is_institution(cls, result: dict[str, Any]) -> bool:
        """Check if result is an institution entity."""
        return "country_code" in result and "works_count" in result

    @classmethod
    def is_source(cls, result: dict[str, Any]) -> bool:
        """Check if result is a source/journal entity."""
        return "issn" in result or "issn_l" in result

    @classmethod
    def is_publisher(cls, result: dict[str, Any]) -> bool:
        """Check if result is a publisher entity."""
        return "hierarchy_level" in result

    @classmethod
    def is_funder(cls, result: dict[str, Any]) -> bool:
        """Check if result is a funder entity."""
        return "works_count" in result and "grants_count" in result

    @classmethod
    def is_grouped(cls, result: dict[str, Any]) -> bool:
        """Check if result is a grouped/aggregated result."""
        return cls.GROUPED_RESULT_SIGNATURE(result)

    @classmethod
    def detect_from_list(cls, results: list) -> str:
        """Detect entity type from a list of results.

        Uses the first result in the list for detection.

        Args:
            results: List of result dictionaries

        Returns:
            Entity type string, or 'fallback' if list is empty
        """
        if not results or len(results) == 0:
            return "fallback"

        return cls.detect(results[0])

    @classmethod
    def get_entity_name(cls, entity_type: str) -> str:
        """Get human-readable name for entity type.

        Args:
            entity_type: Entity type string

        Returns:
            Human-readable entity name
        """
        entity_names = {
            "works": "Work",
            "authors": "Author",
            "institutions": "Institution",
            "sources": "Source",
            "publishers": "Publisher",
            "funders": "Funder",
            "topics": "Topic",
            "domains": "Domain",
            "fields": "Field",
            "subfields": "Subfield",
            "keywords": "Keyword",
            "generic": "Entity",
            "grouped": "Grouped Result",
            "fallback": "Unknown Entity",
        }

        return entity_names.get(entity_type, "Unknown")

    @classmethod
    def get_plural_name(cls, entity_type: str) -> str:
        """Get plural human-readable name for entity type.

        Args:
            entity_type: Entity type string

        Returns:
            Plural human-readable entity name
        """
        plural_names = {
            "works": "Works",
            "authors": "Authors",
            "institutions": "Institutions",
            "sources": "Sources",
            "publishers": "Publishers",
            "funders": "Funders",
            "topics": "Topics",
            "domains": "Domains",
            "fields": "Fields",
            "subfields": "Subfields",
            "keywords": "Keywords",
            "generic": "Entities",
            "grouped": "Grouped Results",
            "fallback": "Unknown Entities",
        }

        return plural_names.get(entity_type, "Unknown")
