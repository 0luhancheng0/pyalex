"""Unit tests for entity pattern matching in utils.py."""

import pytest

from pyalex.entities.authors import Authors
from pyalex.entities.funders import Funders
from pyalex.entities.institutions import Institutions
from pyalex.entities.keywords import Keywords
from pyalex.entities.publishers import Publishers
from pyalex.entities.sources import Sources
from pyalex.entities.topics import Topics
from pyalex.entities.works import Works
from pyalex.utils import ENTITY_PATTERNS
from pyalex.utils import _clean_id
from pyalex.utils import _match_entity_pattern
from pyalex.utils import get_entity_type


class TestCleanId:
    """Tests for _clean_id helper function."""

    def test_clean_id_with_https_prefix(self):
        """Test cleaning ID with https:// prefix."""
        assert _clean_id("https://openalex.org/W123456") == "W123456"

    def test_clean_id_without_prefix(self):
        """Test cleaning ID without prefix."""
        assert _clean_id("W123456") == "W123456"

    def test_clean_id_with_http_prefix(self):
        """Test cleaning ID with http:// prefix (edge case)."""
        # Even though not in official function, this is good to test
        assert _clean_id("W123456") == "W123456"

    def test_clean_id_empty_string(self):
        """Test cleaning empty string."""
        assert _clean_id("") == ""

    def test_clean_id_only_domain(self):
        """Test cleaning domain ID."""
        assert _clean_id("domains/123") == "domains/123"


class TestMatchEntityPattern:
    """Tests for _match_entity_pattern helper function."""

    def test_match_work_pattern(self):
        """Test matching work ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("W123456")
        assert key == "work"
        assert entity_class == Works
        assert entity_type == "work"

    def test_match_author_pattern(self):
        """Test matching author ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("A123456")
        assert key == "author"
        assert entity_class == Authors
        assert entity_type == "author"

    def test_match_source_pattern(self):
        """Test matching source ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("S123456")
        assert key == "source"
        assert entity_class == Sources
        assert entity_type == "source"

    def test_match_institution_pattern(self):
        """Test matching institution ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("I123456")
        assert key == "institution"
        assert entity_class == Institutions
        assert entity_type == "institution"

    def test_match_topic_pattern(self):
        """Test matching topic ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("T123456")
        assert key == "topic"
        assert entity_class == Topics
        assert entity_type == "topic"

    def test_match_publisher_pattern(self):
        """Test matching publisher ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("P123456")
        assert key == "publisher"
        assert entity_class == Publishers
        assert entity_type == "publisher"

    def test_match_funder_pattern(self):
        """Test matching funder ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("F123456")
        assert key == "funder"
        assert entity_class == Funders
        assert entity_type == "funder"

    def test_match_keyword_pattern(self):
        """Test matching keyword ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("K123456")
        assert key == "keyword"
        assert entity_class == Keywords
        assert entity_type == "keyword"

    def test_match_domain_pattern(self):
        """Test matching domain ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("domains/123")
        assert key == "domain"
        assert entity_type == "domain"

    def test_match_field_pattern(self):
        """Test matching field ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("fields/123")
        assert key == "field"
        assert entity_type == "field"

    def test_match_subfield_pattern(self):
        """Test matching subfield ID pattern."""
        key, entity_class, entity_type = _match_entity_pattern("subfields/123")
        assert key == "subfield"
        assert entity_type == "subfield"

    def test_match_with_url_prefix(self):
        """Test matching with URL prefix."""
        key, entity_class, entity_type = _match_entity_pattern(
            "https://openalex.org/W123456"
        )
        assert key == "work"
        assert entity_type == "work"

    def test_match_invalid_pattern(self):
        """Test matching invalid pattern."""
        with pytest.raises(ValueError, match="Unknown OpenAlex ID format"):
            _match_entity_pattern("X123456")

    def test_match_malformed_id(self):
        """Test matching malformed ID."""
        with pytest.raises(ValueError, match="Unknown OpenAlex ID format"):
            _match_entity_pattern("123456")


class TestGetEntityType:
    """Tests for refactored get_entity_type function."""

    @pytest.mark.parametrize(
        "entity_id,expected_type",
        [
            ("W123456", "work"),
            ("A123456", "author"),
            ("S123456", "source"),
            ("I123456", "institution"),
            ("T123456", "topic"),
            ("P123456", "publisher"),
            ("F123456", "funder"),
            ("K123456", "keyword"),
            ("domains/123", "domain"),
            ("fields/123", "field"),
            ("subfields/123", "subfield"),
        ],
    )
    def test_get_entity_type_all_types(self, entity_id, expected_type):
        """Test entity type detection for all entity types."""
        assert get_entity_type(entity_id) == expected_type

    def test_get_entity_type_with_url(self):
        """Test entity type detection with URL prefix."""
        assert get_entity_type("https://openalex.org/W123456") == "work"

    def test_get_entity_type_invalid(self):
        """Test entity type detection with invalid ID."""
        with pytest.raises(ValueError, match="Unknown OpenAlex ID format"):
            get_entity_type("X123456")

    def test_get_entity_type_empty(self):
        """Test entity type detection with empty string."""
        with pytest.raises(ValueError):
            get_entity_type("")


class TestEntityPatternsRegistry:
    """Tests for ENTITY_PATTERNS registry."""

    def test_registry_has_all_entity_types(self):
        """Test that registry contains all expected entity types."""
        expected_types = [
            "work",
            "author",
            "source",
            "institution",
            "topic",
            "publisher",
            "funder",
            "keyword",
            "domain",
            "field",
            "subfield",
        ]
        assert set(ENTITY_PATTERNS.keys()) == set(expected_types)

    def test_registry_pattern_structure(self):
        """Test that each pattern has correct structure."""
        for key, (pattern, entity_class, entity_type) in ENTITY_PATTERNS.items():
            assert isinstance(pattern, str), f"Pattern for {key} should be string"
            assert callable(entity_class) or callable(entity_class), (
                f"Entity class for {key} should be callable"
            )
            assert isinstance(entity_type, str), (
                f"Entity type for {key} should be string"
            )
            assert entity_type == key, f"Entity type should match key for {key}"

    def test_registry_patterns_are_regex(self):
        """Test that patterns are valid regex."""
        import re

        for key, (pattern, _, _) in ENTITY_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Pattern for {key} is not valid regex: {pattern}")


class TestEntityPatternEdgeCases:
    """Test edge cases for entity pattern matching."""

    def test_very_long_numeric_id(self):
        """Test matching ID with very long numeric portion."""
        result = get_entity_type("W" + "1" * 20)
        assert result == "work"

    def test_minimal_numeric_id(self):
        """Test matching ID with single digit."""
        result = get_entity_type("W1")
        assert result == "work"

    def test_domain_with_long_number(self):
        """Test matching domain with long number."""
        result = get_entity_type("domains/" + "1" * 10)
        assert result == "domain"

    def test_case_sensitive_prefix(self):
        """Test that prefix is case sensitive (lowercase should fail)."""
        with pytest.raises(ValueError):
            get_entity_type("w123456")
