"""
Comprehensive tests for core utility functions.

This module tests core utilities like abstract inversion and value quoting.
"""

import pytest

from pyalex.core.expressions import or_
from pyalex.core.utils import invert_abstract
from pyalex.core.utils import quote_oa_value


class TestInvertAbstract:
    """Test abstract inversion functionality."""
    
    def test_invert_abstract_simple(self):
        """Test inverting a simple abstract index."""
        inv_index = {
            "the": [0, 5],
            "cat": [1],
            "sat": [2],
            "on": [3],
            "mat": [4, 6]
        }
        result = invert_abstract(inv_index)
        assert "the" in result
        assert "cat" in result
        assert "mat" in result
    
    def test_invert_abstract_order(self):
        """Test that abstract inversion maintains correct word order."""
        inv_index = {
            "world": [1],
            "hello": [0]
        }
        result = invert_abstract(inv_index)
        assert result == "hello world"
    
    def test_invert_abstract_none(self):
        """Test inverting None returns None."""
        result = invert_abstract(None)
        assert result is None
    
    def test_invert_abstract_empty(self):
        """Test inverting empty dict returns empty string."""
        result = invert_abstract({})
        assert result == ""
    
    def test_invert_abstract_multiple_positions(self):
        """Test words appearing at multiple positions."""
        inv_index = {
            "the": [0, 3],
            "cat": [1],
            "ate": [2]
        }
        result = invert_abstract(inv_index)
        words = result.split()
        assert words[0] == "the"
        assert words[3] == "the"
    
    def test_invert_abstract_single_word(self):
        """Test inverting single word abstract."""
        inv_index = {"word": [0]}
        result = invert_abstract(inv_index)
        assert result == "word"


class TestQuoteOAValue:
    """Test OpenAlex value quoting functionality."""
    
    def test_quote_string(self):
        """Test quoting a regular string."""
        result = quote_oa_value("test value")
        assert "test" in result
        # URL encoding replaces space with +
        assert "+" in result or "%20" in result
    
    def test_quote_boolean_true(self):
        """Test quoting boolean True."""
        result = quote_oa_value(True)
        assert result == "true"
    
    def test_quote_boolean_false(self):
        """Test quoting boolean False."""
        result = quote_oa_value(False)
        assert result == "false"
    
    def test_quote_integer(self):
        """Test quoting integer (should return as-is)."""
        result = quote_oa_value(42)
        assert result == 42
    
    def test_quote_none(self):
        """Test quoting None (should return as-is)."""
        result = quote_oa_value(None)
        assert result is None
    
    def test_quote_special_characters(self):
        """Test quoting string with special characters."""
        result = quote_oa_value("test@example.com")
        # @ should be URL encoded
        assert isinstance(result, str)
    
    def test_quote_logical_expression_string(self):
        """Test quoting logical expression with string value."""
        expr = or_({"field": ["value1", "value2"]})
        result = quote_oa_value(expr)
        # Should handle logical expressions (which are dicts)
        assert result is not None
    
    def test_quote_empty_string(self):
        """Test quoting empty string."""
        result = quote_oa_value("")
        assert result == ""
    
    def test_quote_url(self):
        """Test quoting URL string."""
        url = "https://example.com/path?query=value"
        result = quote_oa_value(url)
        assert isinstance(result, str)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_invert_abstract_large_index(self):
        """Test inverting large abstract index."""
        inv_index = {f"word{i}": [i] for i in range(1000)}
        result = invert_abstract(inv_index)
        words = result.split()
        assert len(words) == 1000
    
    def test_quote_very_long_string(self):
        """Test quoting very long string."""
        long_string = "a" * 10000
        result = quote_oa_value(long_string)
        assert isinstance(result, str)
    
    def test_invert_abstract_gaps_in_positions(self):
        """Test abstract with gaps in word positions."""
        inv_index = {
            "word1": [0],
            "word2": [5],
            "word3": [10]
        }
        result = invert_abstract(inv_index)
        words = result.split()
        assert len(words) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
