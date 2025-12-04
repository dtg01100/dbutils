"""Unit tests for dbutils.utils module.

Tests for:
- Utility functions like edit_distance and fuzzy_match
- Query runner functionality
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import os

from dbutils.utils import (
    query_runner,
    edit_distance,
    edit_distance_fast,
    fuzzy_match,
    _has_exact_substring,
    _word_prefix_or_edit,
    _sequential_char_match
)


class TestQueryRunner:
    """Test the query_runner function."""

    @patch.dict('os.environ', {'DBUTILS_JDBC_PROVIDER': 'test_provider'})
    def test_query_runner_with_jdbc(self):
        """Test query runner with JDBC provider."""
        # Create all mocks inline to ensure proper chain
        # The JDBCConnection object has a query method, not execute on cursor
        mock_conn = MagicMock()
        expected_result = [{'col1': 'value1', 'col2': 'value2'}]
        mock_conn.query.return_value = expected_result

        with patch('dbutils.jdbc_provider.connect', return_value=mock_conn) as mock_connect:
            result = query_runner("SELECT * FROM TEST")

            # Verify connection was established and query executed
            mock_connect.assert_called_once()
            mock_conn.query.assert_called_once_with("SELECT * FROM TEST")
            assert result == expected_result
    
    def test_query_runner_no_provider(self):
        """Test query runner without provider raises error."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="DBUTILS_JDBC_PROVIDER"):
                query_runner("SELECT * FROM TEST")


class TestEditDistance:
    """Test the edit distance functions."""

    def test_edit_distance_identical(self):
        """Test identical strings have distance 0."""
        assert edit_distance("hello", "hello") == 0

    def test_edit_distance_single_char_diff(self):
        """Test single character difference."""
        assert edit_distance("hello", "hallo") == 1

    def test_edit_distance_insertion_deletion(self):
        """Test insertion and deletion operations."""
        assert edit_distance("hello", "helo") == 1  # deletion
        assert edit_distance("hello", "helllo") == 1  # insertion
        assert edit_distance("hello", "jello") == 1  # substitution

    def test_edit_distance_symmetric(self):
        """Test that edit distance is symmetric."""
        assert edit_distance("abc", "def") == edit_distance("def", "abc")

    def test_edit_distance_empty_strings(self):
        """Test edit distance with empty strings."""
        assert edit_distance("", "") == 0
        assert edit_distance("hello", "") == 5
        assert edit_distance("", "hello") == 5

    def test_edit_distance_different_lengths(self):
        """Test edit distance with significantly different lengths."""
        # Edit distance between "a" and "hello" is 5: replace "hello" with "a" needs 4 deletions + 1 substitution
        assert edit_distance("a", "hello") == 5
        assert edit_distance("hello", "a") == 5

    def test_edit_distance_optimization(self):
        """Test edit distance optimization by comparing with shorter string first."""
        # This should be the same as edit_distance("hello", "world")
        assert edit_distance("world", "hello") == edit_distance("hello", "world")


class TestEditDistanceFast:
    """Test the optimized edit distance function."""

    def test_edit_distance_fast_identical(self):
        """Test fast edit distance with identical strings."""
        assert edit_distance_fast("hello", "hello", 5) == 0

    def test_edit_distance_fast_length_check(self):
        """Test fast edit distance length difference optimization."""
        # If length difference is greater than max_dist, return max_dist + 1
        assert edit_distance_fast("hello", "hello world", 2) > 2

    def test_edit_distance_fast_consistency(self):
        """Test that fast version gives same results as slow version."""
        test_cases = [
            ("hello", "world", 5),
            ("test", "testing", 10),
            ("", "hello", 5),
            ("hello", "", 5),
        ]
        
        for s1, s2, max_dist in test_cases:
            slow_result = edit_distance(s1, s2)
            fast_result = edit_distance_fast(s1, s2, max_dist)
            
            # If slow result <= max_dist, they should be equal
            if slow_result <= max_dist:
                assert slow_result == fast_result
            else:
                # If slow result > max_dist, fast result should be > max_dist
                assert fast_result > max_dist


class TestFuzzyMatch:
    """Test the fuzzy matching functions."""

    def test_fuzzy_match_exact(self):
        """Test exact matches work."""
        assert fuzzy_match("hello", "hello") is True
        assert fuzzy_match("hello", "HELLO") is True

    def test_fuzzy_match_substring(self):
        """Test substring matches work."""
        assert fuzzy_match("hello world", "hello") is True
        assert fuzzy_match("hello world", "world") is True

    def test_fuzzy_match_word_boundaries(self):
        """Test word boundary matching."""
        assert fuzzy_match("user_name", "name") is True
        assert fuzzy_match("customer_order", "cus") is True
        assert fuzzy_match("testTable", "test") is True

    def test_fuzzy_match_no_match(self):
        """Test non-matches return False."""
        assert fuzzy_match("hello", "xyz") is False
        assert fuzzy_match("", "hello") is False
        assert fuzzy_match("hello", "") is True  # Empty query should match anything

    def test_fuzzy_match_short_query(self):
        """Test short query handling."""
        assert fuzzy_match("hello", "h") is True   # Single char is substring of "hello"
        assert fuzzy_match("hello", "he") is True  # Two chars are substring of "hello"
        assert fuzzy_match("hello", "hel") is True # Three chars are substring of "hello"
        assert fuzzy_match("hello", "xyz") is False  # Non-matching substring should not match

    def test_fuzzy_match_edit_distance(self):
        """Test edit distance based matching."""
        # These should match based on edit distance
        assert fuzzy_match("customer", "custer") is True  # edit distance 1
        assert fuzzy_match("hello", "helo") is True     # edit distance 1
        assert fuzzy_match("hello", "cello") is True    # edit distance 1


class TestInternalFuzzyFunctions:
    """Test internal fuzzy matching helper functions."""

    def test_has_exact_substring(self):
        """Test exact substring function."""
        assert _has_exact_substring("hello world", "hello") is True
        assert _has_exact_substring("hello world", "world") is True
        assert _has_exact_substring("hello world", "xyz") is False
        assert _has_exact_substring("hello world", "HELLO") is False  # Case sensitive at this level

    def test_word_prefix_or_edit(self):
        """Test word prefix or edit function."""
        # Test prefix matching
        assert _word_prefix_or_edit("hello_world", "hello") is True
        assert _word_prefix_or_edit("user_name", "nam") is True  # prefix of second word
        assert _word_prefix_or_edit("test_table_name", "tabl") is True  # prefix of middle word
        
        # Test edit distance matching for similar words
        assert _word_prefix_or_edit("customer", "custer") is True  # edit distance 1
        assert _word_prefix_or_edit("hello", "xyz") is False   # no match

    def test_sequential_char_match(self):
        """Test sequential character matching."""
        assert _sequential_char_match("hello", "hlo") is True   # h, l, o appear in sequence
        assert _sequential_char_match("hello", "hel") is True   # h, e, l appear in sequence
        assert _sequential_char_match("hello", "ole") is False  # o, l, e not in sequence
        assert _sequential_char_match("programming", "pram") is True  # p, r, a, m in sequence
        assert _sequential_char_match("hello", "xyz") is False  # x, y, z not in sequence
        assert _sequential_char_match("short", "verylongquery") is False  # query longer than text