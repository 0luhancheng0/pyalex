"""Table formatter classes for different entity types.

This module implements a factory pattern for generating PrettyTable output
for different OpenAlex entity types (works, authors, institutions, etc.).
"""

from abc import ABC
from abc import abstractmethod
from typing import Any

from prettytable import PrettyTable

from pyalex.core.config import config
from pyalex.core.entity_detection import EntityTypeDetector

MAX_WIDTH = 100


class TableFormatter(ABC):
    """Base class for entity-specific table formatters."""

    def __init__(self, max_width: int = MAX_WIDTH):
        """Initialize formatter with max column width."""
        self.max_width = max_width

    @abstractmethod
    def get_field_names(self) -> list[str]:
        """Return the list of column headers for this entity type."""
        pass

    @abstractmethod
    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        """Extract data from a single result dict for table row."""
        pass

    def format_table(self, results: list[dict[str, Any]]) -> PrettyTable:
        """Create and populate a PrettyTable from results.

        Args:
            results: List of result dictionaries

        Returns:
            Populated PrettyTable instance
        """
        table = PrettyTable()
        table.field_names = self.get_field_names()
        table.max_width = self.max_width
        table.align = "l"

        for result in results:
            table.add_row(self.extract_row_data(result))

        return table


class WorksTableFormatter(TableFormatter):
    """Formatter for Works entities."""

    def get_field_names(self) -> list[str]:
        return ["Name", "Year", "Journal", "Citations", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        title = (result.get("display_name") or result.get("title") or "Unknown")[
            : self.max_width
        ]
        year = result.get("publication_year", "N/A")

        journal = "N/A"
        if "primary_location" in result and result["primary_location"]:
            source = result["primary_location"].get("source", {})
            if source and source.get("display_name"):
                journal = (source.get("display_name") or "N/A")[:30]

        citations = result.get("cited_by_count", 0)
        openalex_id = result.get("id", "").split("/")[-1]

        return [title, year, journal, citations, openalex_id]


class AuthorsTableFormatter(TableFormatter):
    """Formatter for Authors entities."""

    def get_field_names(self) -> list[str]:
        return ["Name", "Works", "Citations", "Institution", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        name = (result.get("display_name") or "Unknown")[:40]
        works = result.get("works_count", 0)
        citations = result.get("cited_by_count", 0)

        institution = "N/A"
        # Handle new field (list) and old field (single object) for compatibility
        if result.get("last_known_institutions"):
            institutions = result["last_known_institutions"]
            if institutions and len(institutions) > 0:
                inst = institutions[0]
                institution = (inst.get("display_name") or "Unknown")[:30]
        elif result.get("last_known_institution"):
            inst = result["last_known_institution"]
            institution = (inst.get("display_name") or "Unknown")[:30]

        openalex_id = result.get("id", "").split("/")[-1]

        return [name, works, citations, institution, openalex_id]


class InstitutionsTableFormatter(TableFormatter):
    """Formatter for Institutions entities."""

    def get_field_names(self) -> list[str]:
        return ["Name", "Country", "Works", "Citations", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        name = (result.get("display_name") or "Unknown")[:40]
        country = result.get("country_code", "N/A")
        works = result.get("works_count", 0)
        citations = result.get("cited_by_count", 0)
        openalex_id = result.get("id", "").split("/")[-1]

        return [name, country, works, citations, openalex_id]


class SourcesTableFormatter(TableFormatter):
    """Formatter for Sources/Journals entities."""

    def get_field_names(self) -> list[str]:
        return ["Name", "Type", "ISSN", "Works", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        name = (result.get("display_name") or "Unknown")[:40]
        source_type = result.get("type", "N/A")
        issn = result.get("issn_l", result.get("issn", ["N/A"]))
        if isinstance(issn, list):
            issn = issn[0] if issn else "N/A"
        works = result.get("works_count", 0)
        openalex_id = result.get("id", "").split("/")[-1]

        return [name, source_type, issn, works, openalex_id]


class PublishersTableFormatter(TableFormatter):
    """Formatter for Publishers entities."""

    def get_field_names(self) -> list[str]:
        return ["Name", "Level", "Works", "Sources", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        name = (result.get("display_name") or "Unknown")[:40]
        level = result.get("hierarchy_level", "N/A")
        works = result.get("works_count", 0)
        sources = result.get("sources_count", 0)
        openalex_id = result.get("id", "").split("/")[-1]

        return [name, level, works, sources, openalex_id]


class GenericEntityTableFormatter(TableFormatter):
    """Formatter for generic entities (Topics, Domains, Fields, Subfields, Funders)."""

    def get_field_names(self) -> list[str]:
        return ["Name", "Works", "Citations", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        name = (result.get("display_name") or "Unknown")[
            : config.cli_name_truncate_length
        ]
        works = result.get("works_count", 0)
        citations = result.get("cited_by_count", 0)
        openalex_id = result.get("id", "").split("/")[-1]

        return [name, works, citations, openalex_id]


class GroupedResultsTableFormatter(TableFormatter):
    """Formatter for grouped/aggregated results."""

    def get_field_names(self) -> list[str]:
        return ["Key", "Display Name", "Count"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        key = result.get("key", "Unknown")
        display_name = result.get("key_display_name", key)
        count = result.get("count", 0)

        return [key, display_name, f"{count:,}"]


class FallbackTableFormatter(TableFormatter):
    """Fallback formatter for unrecognized entity types."""

    def get_field_names(self) -> list[str]:
        return ["Name", "ID"]

    def extract_row_data(self, result: dict[str, Any]) -> list[Any]:
        name = (result.get("display_name") or result.get("title") or "Unknown")[
            : self.max_width
        ]
        openalex_id = result.get("id", "").split("/")[-1]

        return [name, openalex_id]


class TableFormatterFactory:
    """Factory for creating appropriate table formatters based on entity type detection."""

    @staticmethod
    def detect_entity_type(first_result: dict[str, Any]) -> str:
        """Detect entity type from the first result dictionary.

        Delegates to EntityTypeDetector for centralized detection logic.

        Args:
            first_result: First result dictionary from API response

        Returns:
            Entity type string: 'works', 'authors', 'institutions', etc.
        """
        return EntityTypeDetector.detect(first_result)

    @staticmethod
    def create_formatter(
        entity_type: str, max_width: int = MAX_WIDTH
    ) -> TableFormatter:
        """Create appropriate formatter for entity type.

        Args:
            entity_type: Type of entity ('works', 'authors', etc.)
            max_width: Maximum column width

        Returns:
            Appropriate TableFormatter instance
        """
        formatters = {
            "works": WorksTableFormatter,
            "authors": AuthorsTableFormatter,
            "institutions": InstitutionsTableFormatter,
            "sources": SourcesTableFormatter,
            "publishers": PublishersTableFormatter,
            "generic": GenericEntityTableFormatter,
            "grouped": GroupedResultsTableFormatter,
            "fallback": FallbackTableFormatter,
        }

        formatter_class = formatters.get(entity_type, FallbackTableFormatter)
        return formatter_class(max_width=max_width)

    @classmethod
    def format_results(
        cls,
        results: list[dict[str, Any]],
        grouped: bool = False,
        max_width: int = MAX_WIDTH,
    ) -> PrettyTable:
        """Detect entity type and format results as table.

        Args:
            results: List of result dictionaries
            grouped: Whether results are grouped/aggregated
            max_width: Maximum column width

        Returns:
            Populated PrettyTable instance
        """
        if not results or len(results) == 0:
            # Return empty table for empty results
            table = PrettyTable()
            table.field_names = ["Message"]
            table.add_row(["No results found."])
            return table

        # Detect entity type from first result
        if grouped:
            entity_type = "grouped"
        else:
            entity_type = cls.detect_entity_type(results[0])

        # Create appropriate formatter and generate table
        formatter = cls.create_formatter(entity_type, max_width=max_width)
        return formatter.format_table(results)
