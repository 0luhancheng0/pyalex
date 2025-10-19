"""Unit tests for validation.py refactored functions."""

from pyalex.cli.validation import _parse_range_value
from pyalex.cli.validation import _parse_single_value
from pyalex.cli.validation import parse_range_filter


class TestParseSingleValue:
    """Tests for _parse_single_value helper function."""

    def test_valid_positive_integer(self):
        """Test parsing valid positive integer."""
        assert _parse_single_value("100") == "100"

    def test_valid_zero(self):
        """Test parsing zero."""
        assert _parse_single_value("0") == "0"

    def test_valid_negative_integer(self):
        """Test parsing negative integer."""
        assert _parse_single_value("-100") == "-100"

    def test_invalid_non_numeric(self):
        """Test parsing non-numeric string."""
        assert _parse_single_value("abc") is None

    def test_invalid_decimal(self):
        """Test parsing decimal number."""
        assert _parse_single_value("10.5") is None

    def test_invalid_mixed_content(self):
        """Test parsing mixed alphanumeric content."""
        assert _parse_single_value("100abc") is None


class TestParseRangeValue:
    """Tests for _parse_range_value helper function."""

    def test_full_range_valid(self):
        """Test parsing valid range with both bounds."""
        assert _parse_range_value("100", "500") == "100-500"

    def test_full_range_equal_bounds(self):
        """Test parsing range where lower equals upper."""
        assert _parse_range_value("100", "100") == "100-100"

    def test_full_range_inverted(self):
        """Test parsing range where lower > upper."""
        assert _parse_range_value("500", "100") is None

    def test_upper_bound_only(self):
        """Test parsing range with only upper bound."""
        assert _parse_range_value("", "500") == "<500"

    def test_lower_bound_only(self):
        """Test parsing range with only lower bound."""
        assert _parse_range_value("100", "") == ">100"

    def test_both_bounds_empty(self):
        """Test parsing range with both bounds empty."""
        assert _parse_range_value("", "") is None

    def test_upper_bound_invalid(self):
        """Test parsing range with invalid upper bound."""
        assert _parse_range_value("", "abc") is None

    def test_lower_bound_invalid(self):
        """Test parsing range with invalid lower bound."""
        assert _parse_range_value("abc", "") is None

    def test_both_bounds_invalid(self):
        """Test parsing range with both bounds invalid."""
        assert _parse_range_value("abc", "def") is None

    def test_negative_bounds(self):
        """Test parsing range with negative numbers."""
        assert _parse_range_value("-100", "-50") == "-100--50"

    def test_zero_bounds(self):
        """Test parsing range with zeros."""
        assert _parse_range_value("0", "100") == "0-100"


class TestParseRangeFilterRefactored:
    """Tests for refactored parse_range_filter function."""

    def test_single_value(self):
        """Test parsing single value."""
        assert parse_range_filter("100") == "100"

    def test_full_range(self):
        """Test parsing full range."""
        assert parse_range_filter("100-500") == "100-500"

    def test_lower_bound_only(self):
        """Test parsing lower bound only."""
        assert parse_range_filter("100-") == ">100"

    def test_upper_bound_only(self):
        """Test parsing upper bound only."""
        assert parse_range_filter("-500") == "<500"

    def test_explicit_greater_than(self):
        """Test explicit > operator."""
        assert parse_range_filter(">100") == ">100"

    def test_explicit_less_than(self):
        """Test explicit < operator."""
        assert parse_range_filter("<500") == "<500"

    def test_explicit_greater_equal(self):
        """Test explicit >= operator."""
        assert parse_range_filter(">=100") == ">=100"

    def test_explicit_less_equal(self):
        """Test explicit <= operator."""
        assert parse_range_filter("<=500") == "<=500"

    def test_empty_string(self):
        """Test empty string."""
        assert parse_range_filter("") is None

    def test_none_value(self):
        """Test None value."""
        assert parse_range_filter(None) is None

    def test_whitespace_trimming(self):
        """Test whitespace is trimmed."""
        assert parse_range_filter("  100-500  ") == "100-500"

    def test_invalid_range(self):
        """Test invalid range where lower > upper."""
        assert parse_range_filter("500-100") is None

    def test_invalid_non_numeric(self):
        """Test invalid non-numeric input."""
        assert parse_range_filter("abc") is None

    def test_invalid_empty_range(self):
        """Test invalid empty range."""
        assert parse_range_filter("-") is None


class TestRangeFilterEdgeCases:
    """Test edge cases for range filter parsing."""

    def test_large_numbers(self):
        """Test parsing very large numbers."""
        assert parse_range_filter("1000000-9999999") == "1000000-9999999"

    def test_zero_value(self):
        """Test parsing zero."""
        assert parse_range_filter("0") == "0"

    def test_zero_range(self):
        """Test parsing range starting at zero."""
        assert parse_range_filter("0-100") == "0-100"

    def test_negative_numbers(self):
        """Test parsing negative numbers."""
        assert parse_range_filter("-100") == "<100"

    def test_multiple_dashes(self):
        """Test handling multiple dashes (edge case)."""
        # This should parse as empty lower bound and "-500" as upper
        assert parse_range_filter("--500") == "<-500"
