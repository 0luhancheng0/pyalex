"""
Comprehensive tests for CLI utility functions.

This module tests CLI-specific utilities like range parsing, formatting,
and output handling.
"""

import pyalex.cli.utils as cli_utils
from pyalex import Works
from pyalex.cli.commands.utils import _parse_ids_from_json_input

try:  # pragma: no cover - ensure pytest required for test execution
    import pytest  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    raise ImportError("pytest is required to run tests") from exc


class DummyQuery:
    """Minimal query stub for testing CLI option helpers."""

    def __init__(self):
        self.sort_kwargs = None

    def sort(self, **kwargs):
        self.sort_kwargs = kwargs
        return self

    def select(self, *_args, **_kwargs):
        return self

    def sample(self, *_args, **_kwargs):
        return self


class TestSortOptionHandling:
    """Test behaviour of sort option parsing."""

    def test_sort_defaults_to_desc(self):
        """Unqualified sort fields should default to descending order."""
        query = DummyQuery()
        result = cli_utils._validate_and_apply_common_options(
            query,
            all_results=False,
            limit=None,
            sample=None,
            seed=0,
            sort_by="works_count",
            select=None,
        )

        assert result is query
        assert query.sort_kwargs == {"works_count": "desc"}

    def test_sort_respects_explicit_direction(self):
        """Explicit directions should override the default descending order."""
        query = DummyQuery()
        cli_utils._validate_and_apply_common_options(
            query,
            all_results=False,
            limit=None,
            sample=None,
            seed=0,
            sort_by="works_count:asc",
            select=None,
        )

        assert query.sort_kwargs == {"works_count": "asc"}

    def test_sort_handles_mixed_fields(self):
        """Multiple fields should honour per-field defaults and overrides."""
        query = DummyQuery()
        cli_utils._validate_and_apply_common_options(
            query,
            all_results=False,
            limit=None,
            sample=None,
            seed=0,
            sort_by="works_count,display_name:asc",
            select=None,
        )

        assert query.sort_kwargs == {
            "works_count": "desc",
            "display_name": "asc",
        }


class TestDataVersionPropagation:
    """Ensure helper functions include the default data version."""

    @pytest.mark.asyncio
    async def test_async_retrieve_single_includes_data_version(self, monkeypatch):
        """Single-entity retrieval URLs should include the data-version flag."""

        captured_urls: list[str] = []

        async def mock_batch_requests(urls, max_concurrent=None):
            captured_urls.extend(urls)
            return [{"id": "W123"}]

        monkeypatch.setattr(
            "pyalex.client.httpx_session.async_batch_requests",
            mock_batch_requests,
        )

        results = await cli_utils._async_retrieve_entities(Works, ["W123"], "Works")

        assert results  # Should yield at least one result
        assert captured_urls
        assert captured_urls[0].endswith("data-version=2")


class TestRangeFilterParsing:
    """Test range filter parsing functionality."""

    def test_parse_single_value(self):
        """Test parsing single value."""
        result = cli_utils.parse_range_filter("100")
        assert result == "100"

    def test_parse_range_both_values(self):
        """Test parsing range with both min and max."""
        result = cli_utils.parse_range_filter("100:1000")
        assert result == ">99,<1001"

    def test_parse_range_min_only(self):
        """Test parsing range with minimum only."""
        result = cli_utils.parse_range_filter("100:")
        assert result == ">99"

    def test_parse_range_max_only(self):
        """Test parsing range with maximum only."""
        result = cli_utils.parse_range_filter(":1000")
        assert result == "<1001"

    def test_parse_range_empty_string(self):
        """Test parsing empty string."""
        result = cli_utils.parse_range_filter("")
        assert result is None

    def test_parse_range_none(self):
        """Test parsing None value."""
        result = cli_utils.parse_range_filter(None)
        assert result is None

    def test_parse_range_invalid_empty_range(self):
        """Test that empty range raises ValueError."""
        with pytest.raises(ValueError, match="Invalid range format"):
            cli_utils.parse_range_filter(":")

    def test_parse_range_invalid_non_numeric(self):
        """Test that non-numeric value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid number format"):
            cli_utils.parse_range_filter("abc")

    def test_parse_range_invalid_non_numeric_in_range(self):
        """Test that non-numeric value in range raises ValueError."""
        with pytest.raises(ValueError, match="Invalid number format"):
            cli_utils.parse_range_filter("abc:100")

    def test_parse_range_with_whitespace(self):
        """Test parsing range with whitespace."""
        result = cli_utils.parse_range_filter(" 100 : 1000 ")
        assert result == ">99,<1001"

    def test_parse_range_large_numbers(self):
        """Test parsing range with large numbers."""
        result = cli_utils.parse_range_filter("1000000:9999999")
        assert result == ">999999,<10000000"

    def test_parse_range_zero_values(self):
        """Test parsing range with zero values."""
        result = cli_utils.parse_range_filter("0:100")
        assert result == ">-1,<101"

    def test_parse_range_single_zero(self):
        """Test parsing single zero value."""
        result = cli_utils.parse_range_filter("0")
        assert result == "0"


class TestGlobalStateManagement:
    """Test global state management functions."""

    def test_set_global_state(self):
        """Test setting global state."""
        from pyalex.cli.utils import set_global_state

        set_global_state(debug_mode=True, dry_run_mode=False, batch_size=50)
        # State should be set internally
        # We can't directly test private variables, but function should not raise
        assert True

    def test_set_batch_progress_context(self):
        """Test setting batch progress context."""
        from pyalex.cli.utils import get_batch_progress_context
        from pyalex.cli.utils import set_batch_progress_context

        mock_context = "test_context"
        set_batch_progress_context(mock_context)
        result = get_batch_progress_context()
        assert result == mock_context

    def test_is_in_batch_context(self):
        """Test checking if in batch context."""
        from pyalex.cli.utils import is_in_batch_context
        from pyalex.cli.utils import set_batch_progress_context

        set_batch_progress_context(None)
        assert not is_in_batch_context()
        set_batch_progress_context("context")
        assert is_in_batch_context()


class TestProgressContextManagement:
    """Test progress context management."""

    def test_enter_progress_context(self):
        """Test entering progress context."""
        from pyalex.cli.utils import _enter_progress_context
        from pyalex.cli.utils import _exit_progress_context

        # Reset depth
        _exit_progress_context()
        depth = _enter_progress_context()
        assert depth >= 1

    def test_exit_progress_context(self):
        """Test exiting progress context."""
        from pyalex.cli.utils import _enter_progress_context
        from pyalex.cli.utils import _exit_progress_context

        _enter_progress_context()
        depth = _exit_progress_context()
        assert depth >= 0

    def test_progress_depth_tracking(self):
        """Test progress depth tracking."""
        from pyalex.cli.utils import _enter_progress_context
        from pyalex.cli.utils import _exit_progress_context

        # Start fresh
        _exit_progress_context()
        _exit_progress_context()

        depth1 = _enter_progress_context()
        depth2 = _enter_progress_context()
        assert depth2 > depth1

        depth3 = _exit_progress_context()
        assert depth3 < depth2


class TestDebugPrinting:
    """Test debug printing functionality."""

    def test_debug_print_disabled(self):
        """Test debug print when debug mode is disabled."""
        from pyalex.cli.utils import _debug_print
        from pyalex.cli.utils import set_global_state

        set_global_state(debug_mode=False, dry_run_mode=False, batch_size=50)
        # Should not raise even when debug is off
        _debug_print("Test message")
        assert True

    def test_debug_print_levels(self):
        """Test debug print with different levels."""
        from pyalex.cli.utils import _debug_print
        from pyalex.cli.utils import set_global_state

        set_global_state(debug_mode=True, dry_run_mode=False, batch_size=50)

        # Test different levels - should not raise
        _debug_print("Error message", level="ERROR")
        _debug_print("Warning message", level="WARNING")
        _debug_print("Info message", level="INFO")
        _debug_print("Success message", level="SUCCESS")
        assert True


class TestSimplePaginateAll:
    """Test simple pagination functionality."""

    def test_simple_paginate_all_function_exists(self):
        """Test that _simple_paginate_all function exists."""
        from pyalex.cli.utils import _simple_paginate_all

        assert callable(_simple_paginate_all)


class TestParseIdsFromJsonInput:
    """Test helper for parsing ID inputs."""

    def test_parse_single_object(self):
        """Single object with id returns single-item list."""
        payload = '{"id": "F1"}'
        assert _parse_ids_from_json_input(payload) == ["F1"]

    def test_parse_list_of_objects(self):
        """List of objects produces list of ids."""
        payload = '[{"id": "F1"}, {"id": "F2"}]'
        assert _parse_ids_from_json_input(payload) == ["F1", "F2"]

    def test_parse_list_of_strings(self):
        """List of strings is returned unchanged."""
        payload = '["F1", "F2"]'
        assert _parse_ids_from_json_input(payload) == ["F1", "F2"]

    def test_missing_id_field_raises(self):
        """Missing id field should raise ValueError."""
        payload = '[{"name": "Example"}]'
        with pytest.raises(ValueError, match="Missing 'id' field"):
            _parse_ids_from_json_input(payload)


class TestMaxWidth:
    """Test MAX_WIDTH configuration."""

    def test_max_width_exists(self):
        """Test that MAX_WIDTH is defined."""
        from pyalex.cli.utils import MAX_WIDTH

        assert MAX_WIDTH is not None
        assert isinstance(MAX_WIDTH, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
