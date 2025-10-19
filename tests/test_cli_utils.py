"""
Comprehensive tests for CLI utility functions.

This module tests CLI-specific utilities like range parsing, formatting,
and output handling.
"""

import pytest

from pyalex.cli.utils import parse_range_filter


class TestRangeFilterParsing:
    """Test range filter parsing functionality."""

    def test_parse_single_value(self):
        """Test parsing single value."""
        result = parse_range_filter("100")
        assert result == "100"

    def test_parse_range_both_values(self):
        """Test parsing range with both min and max."""
        result = parse_range_filter("100:1000")
        assert result == ">99,<1001"

    def test_parse_range_min_only(self):
        """Test parsing range with minimum only."""
        result = parse_range_filter("100:")
        assert result == ">99"

    def test_parse_range_max_only(self):
        """Test parsing range with maximum only."""
        result = parse_range_filter(":1000")
        assert result == "<1001"

    def test_parse_range_empty_string(self):
        """Test parsing empty string."""
        result = parse_range_filter("")
        assert result is None

    def test_parse_range_none(self):
        """Test parsing None value."""
        result = parse_range_filter(None)
        assert result is None

    def test_parse_range_invalid_empty_range(self):
        """Test that empty range raises ValueError."""
        with pytest.raises(ValueError, match="Invalid range format"):
            parse_range_filter(":")

    def test_parse_range_invalid_non_numeric(self):
        """Test that non-numeric value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid number format"):
            parse_range_filter("abc")

    def test_parse_range_invalid_non_numeric_in_range(self):
        """Test that non-numeric value in range raises ValueError."""
        with pytest.raises(ValueError, match="Invalid number format"):
            parse_range_filter("abc:100")

    def test_parse_range_with_whitespace(self):
        """Test parsing range with whitespace."""
        result = parse_range_filter(" 100 : 1000 ")
        assert result == ">99,<1001"

    def test_parse_range_large_numbers(self):
        """Test parsing range with large numbers."""
        result = parse_range_filter("1000000:9999999")
        assert result == ">999999,<10000000"

    def test_parse_range_zero_values(self):
        """Test parsing range with zero values."""
        result = parse_range_filter("0:100")
        assert result == ">-1,<101"

    def test_parse_range_single_zero(self):
        """Test parsing single zero value."""
        result = parse_range_filter("0")
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


class TestMaxWidth:
    """Test MAX_WIDTH configuration."""

    def test_max_width_exists(self):
        """Test that MAX_WIDTH is defined."""
        from pyalex.cli.utils import MAX_WIDTH

        assert MAX_WIDTH is not None
        assert isinstance(MAX_WIDTH, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
