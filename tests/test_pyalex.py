"""
Fast unit tests for PyAlex core functionality.
"""
import pytest

from pyalex.cli.utils import parse_range_filter


def test_parse_range_filter_single_value():
    """Test parsing single value."""
    result = parse_range_filter("100")
    assert result == "100"


def test_parse_range_filter_range():
    """Test parsing range values."""
    result = parse_range_filter("100:1000")
    assert result == ">99,<1001"


def test_parse_range_filter_min_only():
    """Test parsing minimum only."""
    result = parse_range_filter("100:")
    assert result == ">99"


def test_parse_range_filter_max_only():
    """Test parsing maximum only."""
    result = parse_range_filter(":1000")
    assert result == "<1001"


def test_parse_range_filter_invalid():
    """Test that invalid range format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid range format"):
        parse_range_filter(":")  # Empty range


def test_parse_range_filter_non_numeric():
    """Test that non-numeric values raise ValueError."""
    with pytest.raises(ValueError, match="Invalid number format"):
        parse_range_filter("abc")


def test_parse_range_filter_empty():
    """Test that empty string returns None."""
    result = parse_range_filter("")
    assert result is None


def test_parse_range_filter_none():
    """Test that None returns None."""
    result = parse_range_filter(None)
    assert result is None
