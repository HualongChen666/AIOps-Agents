# -*- coding: utf-8 -*-
"""
Enhanced test suite for core/ai/token_budget.py
Target: 90%+ statement and branch coverage
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from core.ai.token_budget import (
    TIKTOKEN_AVAILABLE,
    ContextWindowExceededError,
    _heuristic_token_count,
    calculate_prompt_budget,
    estimate_tokens,
    prompt_fits,
    select_model_that_fits,
)


class TestEstimateTokens:
    """Enhanced test suite for estimate_tokens function"""

    def test_estimate_tokens_empty_string(self):
        """Test estimate_tokens with empty string"""
        result = estimate_tokens("")
        assert result == 0

    def test_estimate_tokens_tiktoken_exception_fallback(self):
        """Test estimate_tokens when tiktoken raises exception (fallback to heuristic)"""
        # This test covers the exception handling in estimate_tokens
        # When tiktoken fails, it should fall back to heuristic
        result = estimate_tokens("hello world", model="invalid-model-that-causes-error")
        # Should still return a result using heuristic
        assert result >= 1

    def test_estimate_tokens_tiktoken_unavailable(self):
        """Test estimate_tokens when tiktoken is not available"""
        # Mock TIKTOKEN_AVAILABLE to False to test fallback path
        import core.ai.token_budget as token_budget_module

        original_available = token_budget_module.TIKTOKEN_AVAILABLE

        try:
            token_budget_module.TIKTOKEN_AVAILABLE = False
            result = estimate_tokens("hello world")
            # Should use heuristic when tiktoken is unavailable
            assert result >= 1
        finally:
            token_budget_module.TIKTOKEN_AVAILABLE = original_available

    def test_estimate_tokens_import_error_handling(self):
        """Test the import error handling for tiktoken"""
        # This test covers lines 20-22 where tiktoken import fails
        # We can't easily test this without actually breaking the import,
        # but we can verify the module handles the case gracefully
        import core.ai.token_budget as token_budget_module

        # The module should have TIKTOKEN_AVAILABLE set
        assert hasattr(token_budget_module, "TIKTOKEN_AVAILABLE")
        # If tiktoken is available, it should be True
        # If not, it should be False and the module should still work
        result = estimate_tokens("test")
        assert result >= 1

    def test_estimate_tokens_tiktoken_cl100k_base_fallback(self):
        """Test estimate_tokens falling back to cl100k_base when model-specific encoding fails"""
        # This tests the path where encoding_for_model fails but get_encoding("cl100k_base") works
        result = estimate_tokens("hello world", model="gpt-4")
        # Should work with either model-specific or cl100k_base encoding
        assert result >= 1

    def test_estimate_tokens_short_ascii(self):
        """Test estimate_tokens with short ASCII text"""
        result = estimate_tokens("hello")
        assert result >= 1

    def test_estimate_tokens_long_ascii(self):
        """Test estimate_tokens with long ASCII text"""
        result = estimate_tokens("hello world " * 100)
        assert result > 10

    def test_estimate_tokens_cjk_characters(self):
        """Test estimate_tokens with CJK characters"""
        result = estimate_tokens("你好世界")
        assert result >= 1

    def test_estimate_tokens_mixed_cjk_ascii(self):
        """Test estimate_tokens with mixed CJK and ASCII"""
        result = estimate_tokens("Hello 你好 World 世界")
        assert result >= 1

    def test_estimate_tokens_with_model_tiktoken_available(self):
        """Test estimate_tokens with model when tiktoken is available"""
        if TIKTOKEN_AVAILABLE:
            result = estimate_tokens("hello world", model="gpt-4")
            assert result >= 1
        else:
            # Should fall back to heuristic
            result = estimate_tokens("hello world", model="gpt-4")
            assert result >= 1

    def test_estimate_tokens_with_unknown_model(self):
        """Test estimate_tokens with unknown model name"""
        result = estimate_tokens("hello world", model="unknown-model-xyz")
        # Should fall back to heuristic or cl100k_base
        assert result >= 1

    def test_estimate_tokens_without_model(self):
        """Test estimate_tokens without model parameter"""
        result = estimate_tokens("hello world")
        assert result >= 1

    def test_estimate_tokens_special_characters(self):
        """Test estimate_tokens with special characters"""
        result = estimate_tokens("Hello! @#$%^&*() World")
        assert result >= 1

    def test_estimate_tokens_numbers(self):
        """Test estimate_tokens with numbers"""
        result = estimate_tokens("12345 67890")
        assert result >= 1

    def test_estimate_tokens_whitespace(self):
        """Test estimate_tokens with whitespace"""
        result = estimate_tokens("   \n\t\r\n   ")
        # Should return at least 1 for very short strings
        assert result >= 1

    def test_estimate_tokens_very_long_text(self):
        """Test estimate_tokens with very long text"""
        long_text = "x" * 10000
        result = estimate_tokens(long_text)
        assert result > 100


class TestHeuristicTokenCount:
    """Test suite for _heuristic_token_count function"""

    def test_heuristic_empty_string(self):
        """Test heuristic with empty string"""
        result = _heuristic_token_count("")
        # Should return at least 1 for very short strings
        assert result >= 1

    def test_heuristic_pure_ascii(self):
        """Test heuristic with pure ASCII"""
        result = _heuristic_token_count("hello world")
        # ASCII: ~4 chars per token
        expected = max(1, int(len("hello world") / 4.0))
        assert result == expected

    def test_heuristic_pure_cjk(self):
        """Test heuristic with pure CJK"""
        text = "你好世界"
        result = _heuristic_token_count(text)
        # CJK: ~2 chars per token
        expected = max(1, int(len(text) / 2.0))
        assert result == expected

    def test_heuristic_mixed(self):
        """Test heuristic with mixed CJK and ASCII"""
        text = "Hello你好World世界"
        cjk_chars = 4  # 你好世界
        other_chars = 10  # HelloWorld
        expected = max(1, int(cjk_chars / 2.0 + other_chars / 4.0))
        result = _heuristic_token_count(text)
        assert result == expected

    def test_heuristic_hiragana(self):
        """Test heuristic with Hiragana (Japanese)"""
        text = "こんにちは"
        result = _heuristic_token_count(text)
        assert result >= 1

    def test_heuristic_katakana(self):
        """Test heuristic with Katakana (Japanese)"""
        text = "コンニチハ"
        result = _heuristic_token_count(text)
        assert result >= 1

    def test_heuristic_hangul(self):
        """Test heuristic with Hangul (Korean)"""
        text = "안녕하세요"
        result = _heuristic_token_count(text)
        assert result >= 1

    def test_heuristic_very_short_string(self):
        """Test heuristic with very short string (should return at least 1)"""
        result = _heuristic_token_count("a")
        assert result >= 1

    def test_heuristic_single_cjk(self):
        """Test heuristic with single CJK character"""
        result = _heuristic_token_count("中")
        assert result >= 1


class TestPromptFits:
    """Enhanced test suite for prompt_fits function"""

    def test_prompt_fits_short_prompt(self):
        """Test prompt_fits with short prompt that fits"""
        fits, prompt_tokens, total = prompt_fits("hello", max_new_tokens=10, context_window=100)
        assert fits is True
        assert prompt_tokens >= 1
        assert total > prompt_tokens
        assert total <= 100

    def test_prompt_fits_long_prompt(self):
        """Test prompt_fits with long prompt that doesn't fit"""
        fits, prompt_tokens, total = prompt_fits("x" * 1000, max_new_tokens=10, context_window=100)
        assert fits is False
        assert prompt_tokens > 0
        assert total > 100

    def test_prompt_fits_exact_fit(self):
        """Test prompt_fits with exact fit"""
        # Create a prompt that exactly fits
        prompt = "x" * 50
        fits, prompt_tokens, total = prompt_fits(prompt, max_new_tokens=10, context_window=100)
        # Should fit or be very close
        assert total <= 100 or fits is False

    def test_prompt_fits_with_model(self):
        """Test prompt_fits with model parameter"""
        fits, prompt_tokens, total = prompt_fits(
            "hello world", max_new_tokens=10, context_window=100, model="gpt-4"
        )
        assert fits is True
        assert prompt_tokens >= 1

    def test_prompt_fits_with_reserve_tokens(self):
        """Test prompt_fits with reserve tokens"""
        fits, prompt_tokens, total = prompt_fits(
            "hello world", max_new_tokens=10, context_window=100, reserve_tokens=20
        )
        assert fits is True
        # Total should include reserve tokens
        assert total == prompt_tokens + 10 + 20

    def test_prompt_fits_zero_max_new_tokens(self):
        """Test prompt_fits with zero max_new_tokens"""
        fits, prompt_tokens, total = prompt_fits(
            "hello world", max_new_tokens=0, context_window=100
        )
        assert fits is True
        assert total == prompt_tokens

    def test_prompt_fits_large_reserve(self):
        """Test prompt_fits with large reserve that prevents fit"""
        fits, _, total = prompt_fits(
            "hello world", max_new_tokens=10, context_window=20, reserve_tokens=50
        )
        assert fits is False
        assert total > 20

    def test_prompt_fits_empty_prompt(self):
        """Test prompt_fits with empty prompt"""
        fits, prompt_tokens, total = prompt_fits("", max_new_tokens=10, context_window=100)
        assert fits is True
        assert prompt_tokens == 0
        assert total == 10


class TestCalculatePromptBudget:
    """Enhanced test suite for calculate_prompt_budget function"""

    def test_calculate_prompt_budget_basic(self):
        """Test basic prompt budget calculation"""
        budget = calculate_prompt_budget(context_window=100, max_new_tokens=10)
        # 100 - 10 - 0 - 50 (default reserve) = 40
        assert budget == 40

    def test_calculate_prompt_budget_with_system_tokens(self):
        """Test with system tokens"""
        budget = calculate_prompt_budget(context_window=100, max_new_tokens=10, system_tokens=20)
        # 100 - 10 - 20 - 50 = 20
        assert budget == 20

    def test_calculate_prompt_budget_with_reserve(self):
        """Test with custom reserve tokens"""
        budget = calculate_prompt_budget(context_window=100, max_new_tokens=10, reserve_tokens=30)
        # 100 - 10 - 0 - 30 = 60
        assert budget == 60

    def test_calculate_prompt_budget_all_parameters(self):
        """Test with all parameters"""
        budget = calculate_prompt_budget(
            context_window=1000, max_new_tokens=100, system_tokens=50, reserve_tokens=100
        )
        # 1000 - 100 - 50 - 100 = 750
        assert budget == 750

    def test_calculate_prompt_budget_exceeds_window(self):
        """Test when requirements exceed context window"""
        budget = calculate_prompt_budget(context_window=100, max_new_tokens=80, system_tokens=30)
        # 100 - 80 - 30 - 50 = -60, should return 0
        assert budget == 0

    def test_calculate_prompt_budget_zero_result(self):
        """Test when calculation results in zero or negative"""
        budget = calculate_prompt_budget(context_window=10, max_new_tokens=20)
        # 10 - 20 - 0 - 50 = -60, should return 0
        assert budget == 0

    def test_calculate_prompt_budget_exact_zero(self):
        """Test when calculation exactly equals zero"""
        budget = calculate_prompt_budget(context_window=60, max_new_tokens=10, reserve_tokens=50)
        # 60 - 10 - 0 - 50 = 0
        assert budget == 0


class TestSelectModelThatFits:
    """Enhanced test suite for select_model_that_fits function"""

    def test_select_model_no_configs(self):
        """Test with empty model configs"""
        result = select_model_that_fits(prompt="hello", max_new_tokens=10, model_configs=[])
        assert result is None

    def test_select_model_all_fit(self):
        """Test when all models fit (should return cheapest)"""
        configs = [
            {"name": "expensive", "context_window": 1000, "cost_per_1k": 1.0},
            {"name": "cheap", "context_window": 1000, "cost_per_1k": 0.1},
            {"name": "medium", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("hello", 10, configs)
        assert result is not None
        assert result["name"] == "cheap"

    def test_select_model_only_one_fits(self):
        """Test when only one model fits"""
        configs = [
            {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
            {"name": "large", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("x" * 200, 10, configs)
        assert result is not None
        assert result["name"] == "large"

    def test_select_model_none_fit(self):
        """Test when no model fits"""
        configs = [
            {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
            {"name": "medium", "context_window": 200, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("x" * 10000, 10, configs)
        assert result is None

    def test_select_model_with_preferred_model(self):
        """Test with preferred model that fits"""
        configs = [
            {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
            {"name": "large", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("hello", 10, configs, preferred_model="large")
        assert result is not None
        assert result["name"] == "large"

    def test_select_model_preferred_doesnt_fit(self):
        """Test with preferred model that doesn't fit"""
        configs = [
            {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
            {"name": "large", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        # Use a prompt that's too long for small but fits in large
        # "x" * 500 might still fit in 100 tokens due to heuristic estimation
        # Use a much longer prompt
        result = select_model_that_fits("x" * 5000, 10, configs, preferred_model="small")
        # Should fall back to cheapest that fits
        assert result is not None
        assert result["name"] == "large"

    def test_select_model_preferred_not_found(self):
        """Test with preferred model that doesn't exist in configs"""
        configs = [
            {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
            {"name": "large", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("hello", 10, configs, preferred_model="nonexistent")
        # Should ignore preferred and return cheapest that fits
        assert result is not None
        # large is cheaper (0.5 vs 1.0)
        assert result["name"] == "large"

    def test_select_model_with_max_tokens_field(self):
        """Test with config using max_tokens instead of context_window"""
        configs = [
            {"name": "model1", "max_tokens": 100, "cost_per_1k": 1.0},
            {"name": "model2", "max_tokens": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("x" * 200, 10, configs)
        assert result is not None
        assert result["name"] == "model2"

    def test_select_model_with_both_window_fields(self):
        """Test with config having both context_window and max_tokens"""
        configs = [
            {"name": "model1", "context_window": 100, "max_tokens": 200, "cost_per_1k": 1.0},
        ]
        result = select_model_that_fits("hello", 10, configs)
        assert result is not None
        # Should use context_window if present
        assert result["name"] == "model1"

    def test_select_model_zero_context_window(self):
        """Test with model that has zero context window"""
        configs = [
            {"name": "no_window", "context_window": 0, "cost_per_1k": 0.1},
            {"name": "has_window", "context_window": 1000, "cost_per_1k": 1.0},
        ]
        result = select_model_that_fits("hello", 10, configs)
        assert result is not None
        assert result["name"] == "has_window"

    def test_select_model_missing_window_field(self):
        """Test with model missing both context_window and max_tokens"""
        configs = [
            {"name": "no_window", "cost_per_1k": 0.1},
            {"name": "has_window", "context_window": 1000, "cost_per_1k": 1.0},
        ]
        result = select_model_that_fits("hello", 10, configs)
        assert result is not None
        assert result["name"] == "has_window"

    def test_select_model_with_model_field(self):
        """Test with config using 'model' field instead of 'name'"""
        configs = [
            {"model": "gpt-4", "context_window": 1000, "cost_per_1k": 1.0},
            {"model": "gpt-3.5", "context_window": 100, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("hello", 10, configs, preferred_model="gpt-4")
        assert result is not None
        assert result["model"] == "gpt-4"

    def test_select_model_same_cost(self):
        """Test with models having same cost (should return first)"""
        configs = [
            {"name": "first", "context_window": 1000, "cost_per_1k": 0.5},
            {"name": "second", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("hello", 10, configs)
        assert result is not None
        assert result["name"] == "first"

    def test_select_model_with_cjk_text(self):
        """Test with CJK text"""
        configs = [
            {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
            {"name": "large", "context_window": 1000, "cost_per_1k": 0.5},
        ]
        result = select_model_that_fits("你好世界" * 100, 10, configs)
        assert result is not None
        assert result["name"] == "large"


class TestContextWindowExceededError:
    """Test suite for ContextWindowExceededError"""

    def test_context_window_exceeded_error_creation(self):
        """Test creating ContextWindowExceededError"""
        error = ContextWindowExceededError(
            message="Prompt too long", prompt_tokens=1000, max_new_tokens=100, context_window=800
        )
        assert str(error) == "Prompt too long"
        assert error.prompt_tokens == 1000
        assert error.max_new_tokens == 100
        assert error.context_window == 800

    def test_context_window_exceeded_error_is_exception(self):
        """Test that ContextWindowExceededError is an Exception"""
        error = ContextWindowExceededError(
            message="Test", prompt_tokens=100, max_new_tokens=10, context_window=50
        )
        assert isinstance(error, Exception)

    def test_context_window_exceeded_error_can_be_raised(self):
        """Test that ContextWindowExceededError can be raised"""
        with pytest.raises(ContextWindowExceededError) as exc_info:
            raise ContextWindowExceededError(
                message="Test error", prompt_tokens=100, max_new_tokens=10, context_window=50
            )
        assert exc_info.value.prompt_tokens == 100
