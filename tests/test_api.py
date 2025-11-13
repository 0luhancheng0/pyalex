"""
Comprehensive tests for PyAlex API components.

This module tests the core API functionality, including entity classes,
filters, pagination, and query building.
"""

from unittest.mock import Mock
from unittest.mock import patch

try:  # pragma: no cover - ensure pytest required for test execution
    import pytest  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    raise ImportError("pytest is required to run tests") from exc

from pyalex import Authors
from pyalex import Institutions
from pyalex import Sources
from pyalex import Topics
from pyalex import Works
from pyalex import config
from pyalex.core.expressions import gt_
from pyalex.core.expressions import lt_
from pyalex.core.expressions import not_
from pyalex.core.expressions import or_
from pyalex.core.response import OpenAlexResponseList
from pyalex.core.response import QueryError
from pyalex.entities.works import Work
from pyalex.utils import from_id
from pyalex.utils import get_entity_type


class TestEntityInitialization:
    """Test initialization of entity classes."""

    def test_works_initialization(self):
        """Test Works entity initialization."""
        works = Works()
        assert works.params is None
        assert "works" in works.url.lower()

    def test_authors_initialization(self):
        """Test Authors entity initialization."""
        authors = Authors()
        assert authors.params is None
        assert "authors" in authors.url.lower()

    def test_sources_initialization(self):
        """Test Sources entity initialization."""
        sources = Sources()
        assert sources.params is None
        assert "sources" in sources.url.lower()

    def test_institutions_initialization(self):
        """Test Institutions entity initialization."""
        institutions = Institutions()
        assert institutions.params is None
        assert "institutions" in institutions.url.lower()

    def test_topics_initialization(self):
        """Test Topics entity initialization."""
        topics = Topics()
        assert topics.params is None
        assert "topics" in topics.url.lower()


class TestWorkEntityBehaviour:
    """Ensure Work entity performs abstract normalization."""

    def test_work_converts_inverted_abstract(self):
        payload = {
            "id": "https://openalex.org/W123",
            "abstract_inverted_index": {
                "hello": [0],
                "world": [1],
            },
        }

        work = Work(payload)

        assert "abstract" in work
        assert work["abstract"] == "hello world"
        assert "abstract_inverted_index" not in work

    def test_work_handles_missing_abstract(self):
        payload = {
            "id": "https://openalex.org/W999",
            "abstract_inverted_index": None,
        }

        work = Work(payload)

        assert "abstract" in work
        assert work["abstract"] is None


class TestEntityFiltering:
    """Test filtering capabilities of entity classes."""

    def test_simple_filter(self):
        """Test simple filter on Works."""
        works = Works().filter(publication_year=2020)
        assert "publication_year" in str(works.params)

    def test_multiple_filters(self):
        """Test multiple filters on Works."""
        works = Works().filter(publication_year=2020, cited_by_count=100)
        params = works.params
        assert params is not None

    def test_filter_chaining(self):
        """Test chaining multiple filter calls."""
        works = Works().filter(publication_year=2020).filter(cited_by_count=100)
        params = works.params
        assert params is not None

    def test_search_filter(self):
        """Test search_filter method."""
        works = Works().search_filter(title="machine learning")
        assert works.params is not None


class TestEntitySearch:
    """Test search functionality."""

    def test_search_method(self):
        """Test search method on Works."""
        works = Works().search("artificial intelligence")
        assert works.params is not None
        assert "search" in str(works.params)


class TestLogicalExpressions:
    """Test logical expression operators."""

    def test_or_expression(self):
        """Test OR logical expression."""
        expr = or_({"field": ["value1", "value2"]})
        assert expr is not None
        assert isinstance(expr, dict)

    def test_not_expression(self):
        """Test NOT logical expression."""
        expr = not_("value")
        assert expr is not None

    def test_gt_expression(self):
        """Test greater than expression."""
        expr = gt_(100)
        assert expr is not None

    def test_lt_expression(self):
        """Test less than expression."""
        expr = lt_(1000)
        assert expr is not None


class TestURLGeneration:
    """Test URL generation for different queries."""

    def test_basic_url(self):
        """Test basic URL generation."""
        works = Works()
        url = works.url
        assert "https://api.openalex.org" in url
        assert "works" in url
        assert "data-version=2" in url
        assert "include_xpac=true" in url

    def test_filtered_url(self):
        """Test URL with filters."""
        works = Works().filter(publication_year=2020)
        url = works.url
        assert "filter" in url
        assert "data-version=2" in url
        assert "include_xpac=true" in url

    def test_search_url(self):
        """Test URL with search parameter."""
        works = Works().search("test")
        url = works.url
        assert "search" in url
        assert "data-version=2" in url
        assert "include_xpac=true" in url


class TestEntityIndexing:
    """Test entity indexing and ID-based retrieval."""

    def test_single_id_format(self):
        """Test single ID format creates correct params."""
        works = Works()

        # Mock the _get_from_url_async to avoid actual API calls
        captured_url: dict[str, str] = {}

        async def mock_get_from_url_async(url):
            captured_url["value"] = url
            return {"id": "W123"}

        with patch.object(
            works, "_get_from_url_async", side_effect=mock_get_from_url_async
        ):
            works["W123"]
            assert works.params == "W123"
            assert "data-version=2" in captured_url.get("value", "")
            assert "include_xpac=true" in captured_url.get("value", "")

    def test_list_id_format(self):
        """Test list of IDs creates filter_or query."""
        works = Works()
        result = works[["W123", "W456"]]
        # Should create a filter_or query
        assert result is not None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_entity_type_work(self):
        """Test entity type detection for Works."""
        entity_type = get_entity_type("W1234567890")
        assert entity_type == "work"

    def test_get_entity_type_author(self):
        """Test entity type detection for Authors."""
        entity_type = get_entity_type("A1234567890")
        assert entity_type == "author"

    def test_get_entity_type_source(self):
        """Test entity type detection for Sources."""
        entity_type = get_entity_type("S1234567890")
        assert entity_type == "source"

    def test_get_entity_type_institution(self):
        """Test entity type detection for Institutions."""
        entity_type = get_entity_type("I1234567890")
        assert entity_type == "institution"

    def test_get_entity_type_topic(self):
        """Test entity type detection for Topics."""
        entity_type = get_entity_type("T1234567890")
        assert entity_type == "topic"

    def test_get_entity_type_funder(self):
        """Test entity type detection for Funders."""
        entity_type = get_entity_type("F1234567890")
        assert entity_type == "funder"

    def test_get_entity_type_publisher(self):
        """Test entity type detection for Publishers."""
        entity_type = get_entity_type("P1234567890")
        assert entity_type == "publisher"

    def test_get_entity_type_keyword(self):
        """Test entity type detection for Keywords."""
        entity_type = get_entity_type("K1234567890")
        assert entity_type == "keyword"

    def test_get_entity_type_with_url(self):
        """Test entity type detection with full URL."""
        entity_type = get_entity_type("https://openalex.org/W1234567890")
        assert entity_type == "work"

    def test_get_entity_type_invalid(self):
        """Test entity type detection with invalid ID."""
        with pytest.raises(ValueError, match="Unknown OpenAlex ID format"):
            get_entity_type("INVALID123")

    def test_from_id_work(self):
        """Test from_id with Work ID."""

        # Mock the async HTTP request
        async def mock_get_with_retry(session, url):
            return {"id": "W1234567890", "title": "Test"}

        with patch(
            "pyalex.client.async_session.async_get_with_retry",
            side_effect=mock_get_with_retry,
        ):
            with patch("pyalex.client.async_session.get_async_session") as mock_session:
                mock_session.return_value.__aenter__.return_value = Mock()
                mock_session.return_value.__aexit__.return_value = None

                result = from_id("W1234567890")
                assert result is not None

    def test_from_id_with_url(self):
        """Test from_id with full URL."""

        # Mock the async HTTP request
        async def mock_get_with_retry(session, url):
            return {"id": "W1234567890", "title": "Test"}

        with patch(
            "pyalex.client.async_session.async_get_with_retry",
            side_effect=mock_get_with_retry,
        ):
            with patch("pyalex.client.async_session.get_async_session") as mock_session:
                mock_session.return_value.__aenter__.return_value = Mock()
                mock_session.return_value.__aexit__.return_value = None

                result = from_id("https://openalex.org/W1234567890")
                assert result is not None


class TestConfiguration:
    """Test configuration settings."""

    def test_config_exists(self):
        """Test that config object exists."""
        assert config is not None

    def test_config_max_per_page(self):
        """Test max per page configuration."""
        from pyalex.core.config import MAX_PER_PAGE

        assert MAX_PER_PAGE > 0

    def test_config_min_per_page(self):
        """Test min per page configuration."""
        from pyalex.core.config import MIN_PER_PAGE

        assert MIN_PER_PAGE > 0


class TestResponseList:
    """Test OpenAlexResponseList functionality."""

    def test_response_list_creation(self):
        """Test creating OpenAlexResponseList."""
        data = [{"id": "W123", "title": "Test"}]
        meta = {"count": 1}
        response_list = OpenAlexResponseList(data, meta)
        assert len(response_list) == 1
        assert response_list.meta["count"] == 1

    def test_response_list_iteration(self):
        """Test iterating over OpenAlexResponseList."""
        data = [{"id": "W123"}, {"id": "W456"}]
        meta = {"count": 2}
        response_list = OpenAlexResponseList(data, meta)
        ids = [item["id"] for item in response_list]
        assert "W123" in ids
        assert "W456" in ids

    def test_response_list_indexing(self):
        """Test indexing OpenAlexResponseList."""
        data = [{"id": "W123"}, {"id": "W456"}]
        meta = {"count": 2}
        response_list = OpenAlexResponseList(data, meta)
        assert response_list[0]["id"] == "W123"
        assert response_list[1]["id"] == "W456"


class TestQueryError:
    """Test QueryError exception."""

    def test_query_error_creation(self):
        """Test creating QueryError."""
        error = QueryError("Test error message")
        assert str(error) == "Test error message"

    def test_query_error_is_exception(self):
        """Test that QueryError is an Exception."""
        assert issubclass(QueryError, Exception)


class TestSliceNotation:
    """Test slice notation for pagination."""

    def test_slice_basic(self):
        """Test basic slice notation."""
        works = Works()
        # This should not raise an error during construction
        # Actual execution would require mocking
        with patch.object(works, "get", return_value=[]) as mock_get:
            works[:10]
            mock_get.assert_called_once_with(limit=10)

    def test_slice_with_step_raises_error(self):
        """Test that slice with step != 1 raises ValueError."""
        works = Works()
        with pytest.raises(ValueError, match="Slice step must be 1"):
            works[::2]

    def test_slice_with_negative_start_raises_error(self):
        """Test that slice with negative start raises ValueError."""
        works = Works()
        with pytest.raises(ValueError, match="Slice start must be non-negative"):
            works[-10:]

    def test_slice_with_start_raises_error(self):
        """Test that slice with non-zero start raises ValueError."""
        works = Works()
        with pytest.raises(ValueError, match="Slice with non-zero start not supported"):
            works[10:20]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
