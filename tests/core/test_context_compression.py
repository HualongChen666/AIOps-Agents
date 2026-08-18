# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/context_compression.py
Target: 90%+ statement and branch coverage
"""

import pytest
import sys
import os
from unittest.mock import patch
import json

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.context_compression import (
    compress_context,
    compress_prompt_text,
    _json_summary,
    _summarize_list,
    _truncate_text,
    _serialize,
    _PROTECTED_KEYS,
    _SUMMARIZABLE_KEYS,
)


class TestJsonSummary:
    """Test suite for _json_summary helper function"""

    def test_empty_list(self):
        """Test with empty list"""
        result = _json_summary([])
        assert result == "[]"

    def test_list_with_items(self):
        """Test with list containing items"""
        result = _json_summary([1, 2, 3])
        assert "[1, 2, 3]" in result

    def test_list_with_more_than_max_items(self):
        """Test with list exceeding max_items"""
        result = _json_summary([1, 2, 3, 4, 5, 6], max_items=3)
        assert "(+3 more)" in result

    def test_dict(self):
        """Test with dictionary"""
        result = _json_summary({"key1": "value1", "key2": "value2"})
        assert "key1" in result
        assert "value1" in result

    def test_dict_with_more_than_max_items(self):
        """Test with dict exceeding max_items"""
        result = _json_summary(
            {"key1": "v1", "key2": "v2", "key3": "v3", "key4": "v4"},
            max_items=2
        )
        assert "key1" in result
        assert "key2" in result

    def test_string_truncation(self):
        """Test that long strings are truncated"""
        result = _json_summary(["x" * 100], max_chars=20)
        assert len(result) < 100

    def test_other_type(self):
        """Test with non-list/dict type"""
        result = _json_summary(42)
        assert result == "42"


class TestSummarizeList:
    """Test suite for _summarize_list helper function"""

    def test_list_shorter_than_keep_last(self):
        """Test with list shorter than keep_last"""
        result = _summarize_list([1, 2], keep_last=3)
        assert result == [1, 2]

    def test_list_equal_to_keep_last(self):
        """Test with list equal to keep_last"""
        result = _summarize_list([1, 2, 3], keep_last=3)
        assert result == [1, 2, 3]

    def test_list_longer_than_keep_last(self):
        """Test with list longer than keep_last"""
        result = _summarize_list([1, 2, 3, 4, 5], keep_last=2)
        assert len(result) == 3  # 1 summary + 2 kept
        assert "[... 3 earlier items:" in result[0]
        assert result[1] == 4
        assert result[2] == 5

    def test_custom_keep_last(self):
        """Test with custom keep_last value"""
        result = _summarize_list([1, 2, 3, 4, 5, 6, 7], keep_last=4)
        assert len(result) == 5  # 1 summary + 4 kept
        assert result[-1] == 7


class TestTruncateText:
    """Test suite for _truncate_text helper function"""

    def test_text_shorter_than_max(self):
        """Test with text shorter than max_chars"""
        result = _truncate_text("short", max_chars=100)
        assert result == "short"

    def test_text_equal_to_max(self):
        """Test with text equal to max_chars"""
        text = "x" * 50
        result = _truncate_text(text, max_chars=50)
        assert result == text

    def test_text_longer_than_max(self):
        """Test with text longer than max_chars"""
        text = "x" * 100
        result = _truncate_text(text, max_chars=50)
        assert len(result) == 50
        assert "omitted" in result

    def test_truncation_preserves_ends(self):
        """Test that truncation preserves beginning and end"""
        text = "BEGINNING" + "x" * 50 + "END"
        result = _truncate_text(text, max_chars=30)
        assert "BEGINNING" in result
        assert "END" in result
        assert "omitted" in result


class TestSerialize:
    """Test suite for _serialize helper function"""

    def test_string(self):
        """Test with string input"""
        result = _serialize("test string")
        assert result == "test string"

    def test_dict(self):
        """Test with dict input"""
        result = _serialize({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_list(self):
        """Test with list input"""
        result = _serialize([1, 2, 3])
        assert "[1, 2, 3]" in result

    def test_non_serializable(self):
        """Test with non-serializable object"""
        class CustomObj:
            def __str__(self):
                return "custom"
        
        result = _serialize(CustomObj())
        assert "custom" in result

    def test_exception_handling(self):
        """Test exception handling during serialization"""
        with patch('json.dumps', side_effect=Exception("Serialization failed")):
            result = _serialize({"key": "value"})
            assert isinstance(result, str)


class TestCompressContext:
    """Test suite for compress_context function"""

    def test_empty_context(self):
        """Test with empty context"""
        result = compress_context({}, max_tokens=1000)
        assert result == {}

    def test_context_under_budget(self):
        """Test with context already under token budget"""
        context = {"key": "value"}
        with patch('core.context_compression.estimate_tokens', return_value=100):
            result = compress_context(context, max_tokens=1000)
            assert result == context

    def test_context_over_budget_summarize_lists(self):
        """Test summarizing long lists when over budget"""
        context = {
            "history": [i for i in range(100)],
            "goal": "test goal"
        }
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000  # First call: over budget
            return 500  # After summarization: under budget
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_context(context, max_tokens=1000)
            assert "goal" in result  # Protected key preserved
            assert len(result["history"]) < 100  # List summarized

    def test_protected_keys_preserved(self):
        """Test that protected keys are preserved"""
        context = {
            "goal": "test goal",
            "system_prompt": "system prompt",
            "long_data": "x" * 1000
        }
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_context(context, max_tokens=1000)
            assert result["goal"] == "test goal"
            assert result["system_prompt"] == "system prompt"

    def test_custom_protected_keys(self):
        """Test with custom protected keys"""
        context = {
            "custom_key": "keep this",
            "other_key": "remove this"
        }
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_context(
                context,
                max_tokens=1000,
                protected_keys={"custom_key"}
            )
            assert result["custom_key"] == "keep this"
            assert "other_key" not in result

    def test_truncate_long_strings(self):
        """Test truncating long strings"""
        context = {
            "long_string": "x" * 500,
            "short_string": "short"
        }
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_context(context, max_tokens=1000)
            assert len(result["long_string"]) < 500
            assert result["short_string"] == "short"

    def test_drop_low_priority_keys(self):
        """Test dropping low priority keys"""
        context = {
            "auxiliary_data": "x" * 100,
            "more_auxiliary": "y" * 100
        }
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] <= 2:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_context(context, max_tokens=1000)
            # Should drop keys to fit budget
            assert len(result) <= 1

    def test_summarizable_keys(self):
        """Test that summarizable keys are summarized"""
        context = {
            "history": [i for i in range(50)],
            "execution_log": [i for i in range(50)]
        }
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_context(context, max_tokens=1000)
            assert len(result["history"]) < 50

    def test_model_parameter(self):
        """Test that model parameter is passed to estimate_tokens"""
        context = {"key": "value"}
        
        with patch('core.context_compression.estimate_tokens', return_value=100) as mock:
            compress_context(context, max_tokens=1000, model="gpt-4")
            mock.assert_called_with(json.dumps(context, ensure_ascii=False, default=str), "gpt-4")

    def test_all_keys_dropped_still_returns_dict(self):
        """Test that even if all keys are dropped, returns dict"""
        context = {"key1": "x" * 1000, "key2": "y" * 1000}
        
        with patch('core.context_compression.estimate_tokens', return_value=2000):
            result = compress_context(context, max_tokens=100)
            assert isinstance(result, dict)


class TestCompressPromptText:
    """Test suite for compress_prompt_text function"""

    def test_empty_text(self):
        """Test with empty text"""
        result = compress_prompt_text("", max_tokens=1000)
        assert result == ""

    def test_text_under_budget(self):
        """Test with text already under token budget"""
        text = "short text"
        with patch('core.context_compression.estimate_tokens', return_value=10):
            result = compress_prompt_text(text, max_tokens=1000)
            assert result == text

    def test_text_over_budget_summarize_sections(self):
        """Test summarizing long sections"""
        text = "Section 1\n\n" + "x" * 500 + "\n\nSection 2\n\n" + "y" * 500
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_prompt_text(text, max_tokens=1000)
            assert "summarized" in result or len(result) < len(text)

    def test_protected_prefixes(self):
        """Test that sections with protected prefixes are preserved"""
        text = "用户问题\n\nTest question\n\nOther content\n\n" + "x" * 500
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_prompt_text(text, max_tokens=1000)
            assert "用户问题" in result
            assert "Test question" in result

    def test_custom_protected_prefixes(self):
        """Test with custom protected prefixes"""
        text = "CUSTOM_PREFIX\n\nKeep this\n\nOther\n\n" + "x" * 500
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_prompt_text(
                text,
                max_tokens=1000,
                protected_prefixes=["CUSTOM_PREFIX"]
            )
            assert "CUSTOM_PREFIX" in result
            assert "Keep this" in result

    def test_case_insensitive_prefix_matching(self):
        """Test that prefix matching is case-insensitive"""
        text = "SYSTEM METRICS\n\nData\n\n" + "x" * 500
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_prompt_text(text, max_tokens=1000)
            assert "SYSTEM METRICS" in result or "system metrics" in result.lower()

    def test_drop_sections_from_middle(self):
        """Test that sections are dropped from middle outward"""
        text = "Start\n\n" + "x" * 100 + "\n\nMiddle\n\n" + "y" * 100 + "\n\nEnd"
        
        call_count = [0]
        def mock_estimate(text, model=None):
            call_count[0] += 1
            if call_count[0] <= 2:
                return 2000
            return 500
        
        with patch('core.context_compression.estimate_tokens', side_effect=mock_estimate):
            result = compress_prompt_text(text, max_tokens=1000)
            # Should preserve start and end
            assert "Start" in result
            assert "End" in result

    def test_model_parameter(self):
        """Test that model parameter is passed to estimate_tokens"""
        text = "test text"
        
        with patch('core.context_compression.estimate_tokens', return_value=10) as mock:
            compress_prompt_text(text, max_tokens=1000, model="gpt-4")
            mock.assert_called_with(text, "gpt-4")

    def test_none_sections_handling(self):
        """Test handling of None sections after splitting"""
        text = "Section 1\n\n\n\nSection 2"
        
        with patch('core.context_compression.estimate_tokens', return_value=10):
            result = compress_prompt_text(text, max_tokens=1000)
            assert isinstance(result, str)


class TestConstants:
    """Test suite for module constants"""

    def test_protected_keys(self):
        """Test protected keys constant"""
        assert "goal" in _PROTECTED_KEYS
        assert "query" in _PROTECTED_KEYS
        assert "system_prompt" in _PROTECTED_KEYS
        assert "diagnostic_state" in _PROTECTED_KEYS

    def test_summarizable_keys(self):
        """Test summarizable keys constant"""
        assert "history" in _SUMMARIZABLE_KEYS
        assert "execution_log" in _SUMMARIZABLE_KEYS
        assert "recent_alerts" in _SUMMARIZABLE_KEYS
        assert "correlated_alerts" in _SUMMARIZABLE_KEYS


class TestEdgeCases:
    """Test suite for edge cases and error handling"""

    def test_compress_context_with_none_values(self):
        """Test compressing context with None values"""
        context = {"key": None, "other": "value"}
        
        with patch('core.context_compression.estimate_tokens', return_value=100):
            result = compress_context(context, max_tokens=1000)
            assert result["key"] is None

    def test_compress_context_with_nested_structures(self):
        """Test compressing context with nested structures"""
        context = {
            "nested": {
                "deep": {
                    "value": "test"
                }
            }
        }
        
        with patch('core.context_compression.estimate_tokens', return_value=100):
            result = compress_context(context, max_tokens=1000)
            assert result["nested"]["deep"]["value"] == "test"

    def test_compress_prompt_text_single_section(self):
        """Test compressing single section text"""
        text = "Single section"
        
        with patch('core.context_compression.estimate_tokens', return_value=10):
            result = compress_prompt_text(text, max_tokens=1000)
            assert result == text

    def test_compress_prompt_text_no_double_newlines(self):
        """Test compressing text without double newlines"""
        text = "No double newlines here"
        
        with patch('core.context_compression.estimate_tokens', return_value=10):
            result = compress_prompt_text(text, max_tokens=1000)
            assert result == text
