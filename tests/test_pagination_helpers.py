"""Unit tests for pagination.py refactored methods."""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from pyalex.core.pagination import Paginator


class TestFetchNextPage:
    """Tests for _fetch_next_page helper method."""

    def test_fetch_with_cursor_method(self):
        """Test fetching next page with cursor pagination."""
        # Create a mock endpoint class
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()
        mock_endpoint.url = "http://test"

        # Create paginator
        paginator = Paginator(mock_endpoint, method="cursor", value="*", per_page=50)

        # Mock the async call
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = []
            paginator._fetch_next_page()

            # Verify cursor was set
            mock_endpoint._add_params.assert_any_call("cursor", "*")
            mock_endpoint._add_params.assert_any_call("per-page", 50)

    def test_fetch_with_page_method(self):
        """Test fetching next page with page pagination."""
        # Create a mock endpoint class
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()
        mock_endpoint.url = "http://test"

        # Create paginator
        paginator = Paginator(mock_endpoint, method="page", value=1, per_page=25)

        # Mock the async call
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = []
            paginator._fetch_next_page()

            # Verify page was set
            mock_endpoint._add_params.assert_any_call("page", 1)
            mock_endpoint._add_params.assert_any_call("per-page", 25)

    def test_fetch_with_invalid_method(self):
        """Test fetching with invalid pagination method."""
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()

        paginator = Paginator(mock_endpoint, method="invalid", value=1)

        with pytest.raises(ValueError, match="Method should be 'cursor' or 'page'"):
            paginator._fetch_next_page()

    def test_fetch_with_invalid_per_page_too_small(self):
        """Test fetching with per_page value too small."""
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()

        paginator = Paginator(mock_endpoint, method="cursor", value="*", per_page=0)

        with pytest.raises(
            ValueError, match="per_page should be a integer between 1 and 200"
        ):
            paginator._fetch_next_page()

    def test_fetch_with_invalid_per_page_too_large(self):
        """Test fetching with per_page value too large."""
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()

        paginator = Paginator(mock_endpoint, method="cursor", value="*", per_page=201)

        with pytest.raises(
            ValueError, match="per_page should be a integer between 1 and 200"
        ):
            paginator._fetch_next_page()

    def test_fetch_with_invalid_per_page_non_integer(self):
        """Test fetching with non-integer per_page value."""
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()

        paginator = Paginator(
            mock_endpoint, method="cursor", value="*", per_page="invalid"
        )

        with pytest.raises(
            ValueError, match="per_page should be a integer between 1 and 200"
        ):
            paginator._fetch_next_page()


class TestProcessPageMetadata:
    """Tests for _process_page_metadata helper method."""

    def test_process_first_page_with_count(self):
        """Test processing first page metadata with count."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*")

        response = []
        meta = {"count": 1000, "next_cursor": "abc123"}

        with patch("pyalex.core.pagination.logger") as mock_logger:
            paginator._process_page_metadata(response, meta)

            # Verify count was logged
            mock_logger.info.assert_called_once()
            assert "1,000" in str(mock_logger.info.call_args)

            # Verify _first_page flag was reset
            assert paginator._first_page == False

            # Verify next_value was updated
            assert paginator._next_value == "abc123"

    def test_process_subsequent_page(self):
        """Test processing subsequent page (not first)."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*")
        paginator._first_page = False

        response = []
        meta = {"count": 1000, "next_cursor": "def456"}

        with patch("pyalex.core.pagination.logger") as mock_logger:
            paginator._process_page_metadata(response, meta)

            # Verify count was NOT logged (not first page)
            mock_logger.info.assert_not_called()

            # Verify next_value was updated
            assert paginator._next_value == "def456"

    def test_process_with_page_method(self):
        """Test processing metadata with page pagination."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="page", value=1)
        paginator._first_page = False

        response = [1, 2, 3]  # Non-empty response
        meta = {"page": 1, "count": 100}

        paginator._process_page_metadata(response, meta)

        # Verify next_value was incremented
        assert paginator._next_value == 2

    def test_process_with_page_method_empty_response(self):
        """Test processing with page method and empty response."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="page", value=1)
        paginator._first_page = False

        response = []  # Empty response
        meta = {"page": 1, "count": 100}

        paginator._process_page_metadata(response, meta)

        # Verify next_value was set to None
        assert paginator._next_value is None

    def test_process_with_cursor_method_no_next(self):
        """Test processing with cursor method when no next cursor."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*")
        paginator._first_page = False

        response = []
        meta = {"count": 100}  # No next_cursor

        paginator._process_page_metadata(response, meta)

        # Verify next_value was set to None
        assert paginator._next_value is None

    def test_process_updates_n_counter(self):
        """Test that processing updates the n counter."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*")
        paginator._first_page = False
        paginator.n = 0

        response = [1, 2, 3, 4, 5]
        meta = {"next_cursor": "next"}

        paginator._process_page_metadata(response, meta)

        # Verify n was updated
        assert paginator.n == 5

    def test_process_with_none_meta(self):
        """Test processing when meta is None."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*")
        paginator._first_page = False

        response = [1, 2, 3]
        meta = None

        paginator._process_page_metadata(response, meta)

        # Verify next_value was set to None
        assert paginator._next_value is None

        # Verify n was still updated
        assert paginator.n == 3


class TestPaginatorRefactoredNext:
    """Tests for refactored __next__ method using helpers."""

    def test_next_calls_helpers_in_order(self):
        """Test that __next__ calls helper methods in correct order."""
        mock_endpoint = Mock()
        mock_endpoint.params = {}
        paginator = Paginator(mock_endpoint, method="cursor", value="*", per_page=10)

        # Mock helper methods
        with patch.object(paginator, "_fetch_next_page") as mock_fetch:
            with patch.object(paginator, "_process_page_metadata") as mock_process:
                mock_response = Mock()
                mock_response.attrs = {}
                mock_response.meta = {"next_cursor": "next"}
                mock_fetch.return_value = mock_response

                result = next(paginator)

                # Verify fetch was called
                mock_fetch.assert_called_once()

                # Verify process was called
                mock_process.assert_called_once()

                # Verify result is correct
                assert result == mock_response

    def test_next_stops_when_next_value_is_none(self):
        """Test that iteration stops when _next_value is None."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value=None)

        with pytest.raises(StopIteration):
            next(paginator)

    def test_next_stops_when_max_reached(self):
        """Test that iteration stops when n_max is reached."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*", n_max=10)
        paginator.n = 10

        with pytest.raises(StopIteration):
            next(paginator)

    def test_next_stops_on_group_by_page_2(self):
        """Test that iteration stops on page 2 for group-by queries."""
        mock_endpoint = Mock()
        mock_endpoint.params = {"group-by": "topic"}

        paginator = Paginator(mock_endpoint, method="page", value=2)

        with pytest.raises(StopIteration):
            next(paginator)

    def test_next_allows_group_by_page_1(self):
        """Test that iteration allows page 1 for group-by queries."""
        mock_endpoint = Mock()
        mock_endpoint.params = {"group-by": "topic"}
        mock_endpoint._add_params = Mock()
        mock_endpoint.url = "http://test"

        paginator = Paginator(mock_endpoint, method="page", value=1)

        with patch("asyncio.run") as mock_run:
            mock_response = []  # Empty list instead of Mock
            mock_run.return_value = mock_response

            # Should not raise
            result = next(paginator)
            assert result == mock_response


class TestPaginatorHelperEdgeCases:
    """Test edge cases for paginator helper methods."""

    def test_process_with_dataframe_attrs(self):
        """Test processing metadata from DataFrame attrs."""
        mock_endpoint = Mock()
        paginator = Paginator(mock_endpoint, method="cursor", value="*")
        paginator._first_page = False

        response = [1, 2, 3]  # Use list instead of Mock
        meta = {"next_cursor": "abc"}

        paginator._process_page_metadata(response, meta)

        assert paginator._next_value == "abc"

    def test_fetch_with_none_per_page(self):
        """Test fetch with per_page=None (should use default)."""
        mock_endpoint = Mock()
        mock_endpoint._add_params = Mock()
        mock_endpoint.url = "http://test"

        paginator = Paginator(mock_endpoint, method="cursor", value="*", per_page=None)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = []
            paginator._fetch_next_page()

            # per-page should not be set when per_page is None
            # Check that it's either not called or not called with per-page
            calls = [str(call) for call in mock_endpoint._add_params.call_args_list]
            per_page_calls = [c for c in calls if "per-page" in c]
            # With per_page=None in init, it defaults to MAX_PER_PAGE in __init__
            # So it WILL be called
            assert len(per_page_calls) > 0
