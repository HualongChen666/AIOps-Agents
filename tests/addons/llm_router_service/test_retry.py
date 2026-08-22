# -*- coding: utf-8 -*-
"""Unit tests for retry.py - Configurable retry engine for LLM provider calls."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from extensions.addons.ai_plus.llm_router_service.retry import (
    RetryPolicy,
    LLMRetryEngine,
)


class TestRetryPolicy:
    """Test RetryPolicy dataclass."""

    def test_retry_policy_default_values(self):
        """Test retry policy with default values."""
        policy = RetryPolicy(name="test_policy")
        assert policy.name == "test_policy"
        assert policy.max_retries == 3
        assert policy.base_delay_seconds == 1.0
        assert policy.max_delay_seconds == 60.0
        assert policy.exponential_base == 2.0
        assert policy.retryable_errors == ["retryable"]

    def test_retry_policy_custom_values(self):
        """Test retry policy with custom values."""
        policy = RetryPolicy(
            name="custom_policy",
            max_retries=5,
            base_delay_seconds=0.5,
            max_delay_seconds=30.0,
            exponential_base=3.0,
            retryable_errors=["timeout", "rate_limit", "server_error"],
        )
        assert policy.name == "custom_policy"
        assert policy.max_retries == 5
        assert policy.base_delay_seconds == 0.5
        assert policy.max_delay_seconds == 30.0
        assert policy.exponential_base == 3.0
        assert len(policy.retryable_errors) == 3

    def test_retry_policy_empty_retryable_errors(self):
        """Test retry policy with empty retryable errors list."""
        policy = RetryPolicy(name="test", retryable_errors=[])
        assert policy.retryable_errors == []

    def test_retry_policy_zero_retries(self):
        """Test retry policy with zero retries."""
        policy = RetryPolicy(name="no_retry", max_retries=0)
        assert policy.max_retries == 0

    def test_retry_policy_zero_delays(self):
        """Test retry policy with zero delays."""
        policy = RetryPolicy(
            name="immediate", base_delay_seconds=0, max_delay_seconds=0
        )
        assert policy.base_delay_seconds == 0
        assert policy.max_delay_seconds == 0


class TestLLMRetryEngine:
    """Test LLMRetryEngine class."""

    def test_retry_engine_initialization(self):
        """Test retry engine initialization."""
        engine = LLMRetryEngine()
        assert len(engine.policies) == len(engine.DEFAULT_POLICIES)
        assert engine.default_policy.name == "exponential"

    def test_retry_engine_custom_default_policy(self):
        """Test retry engine with custom default policy."""
        engine = LLMRetryEngine(default_policy_name="aggressive")
        assert engine.default_policy.name == "aggressive"

    def test_retry_engine_invalid_default_policy(self):
        """Test retry engine with invalid default policy falls back to exponential."""
        engine = LLMRetryEngine(default_policy_name="invalid_policy")
        assert engine.default_policy.name == "exponential"

    def test_retry_engine_default_policies_count(self):
        """Test that all default policies are loaded."""
        engine = LLMRetryEngine()
        expected_policies = [
            "no_retry",
            "fixed_1s",
            "fixed_5s",
            "linear_1s",
            "exponential",
            "exponential_fast",
            "exponential_slow",
            "aggressive",
            "conservative",
            "jitter",
            "constant",
        ]
        for policy_name in expected_policies:
            assert policy_name in engine.policies

    def test_add_policy(self):
        """Test adding a custom retry policy."""
        engine = LLMRetryEngine()
        custom_policy = RetryPolicy(
            name="custom", max_retries=2, base_delay_seconds=0.5
        )
        engine.add_policy(custom_policy)

        assert "custom" in engine.policies
        assert engine.policies["custom"] == custom_policy

    def test_add_policy_override(self):
        """Test that adding a policy overrides existing one."""
        engine = LLMRetryEngine()
        original_policy = engine.policies["exponential"]

        new_policy = RetryPolicy(name="exponential", max_retries=10)
        engine.add_policy(new_policy)

        assert engine.policies["exponential"] == new_policy
        assert engine.policies["exponential"].max_retries == 10

    def test_list_policies(self):
        """Test listing all available policies."""
        engine = LLMRetryEngine()
        policies = engine.list_policies()

        assert isinstance(policies, list)
        assert len(policies) == len(engine.policies)
        assert "exponential" in policies
        assert "no_retry" in policies

    @pytest.mark.asyncio
    async def test_execute_success_on_first_attempt(self):
        """Test execute with success on first attempt."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(return_value="success")

        result = await engine.execute(mock_fn)

        assert result == "success"
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retryable_error(self):
        """Test execute with retryable error."""
        engine = LLMRetryEngine()
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("retryable error")
            return "success"

        result = await engine.execute(failing_fn)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_no_retry_policy(self):
        """Test execute with no_retry policy."""
        engine = LLMRetryEngine(default_policy_name="no_retry")
        mock_fn = AsyncMock(side_effect=Exception("error"))

        with pytest.raises(Exception, match="error"):
            await engine.execute(mock_fn)

        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_custom_policy_name(self):
        """Test execute with custom policy name."""
        engine = LLMRetryEngine()
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("error")
            return "success"

        result = await engine.execute(failing_fn, policy_name="aggressive")

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_invalid_policy_name(self):
        """Test execute with invalid policy name uses default."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(return_value="success")

        result = await engine.execute(mock_fn, policy_name="invalid")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(self):
        """Test execute when max retries are exceeded."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(side_effect=Exception("persistent error"))

        with pytest.raises(Exception, match="persistent error"):
            await engine.execute(mock_fn)

        # Should be called max_retries + 1 times (initial + retries)
        assert mock_fn.call_count == engine.default_policy.max_retries + 1

    @pytest.mark.asyncio
    async def test_execute_with_args_and_kwargs(self):
        """Test execute with function arguments."""
        engine = LLMRetryEngine()

        async def fn_with_args(a, b, c=None):
            return {"a": a, "b": b, "c": c}

        result = await engine.execute(fn_with_args, 1, 2, c=3)

        assert result == {"a": 1, "b": 2, "c": 3}

    @pytest.mark.asyncio
    async def test_execute_with_model_and_provider_kwargs(self):
        """Test execute with model and provider in kwargs."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(return_value="result")

        await engine.execute(mock_fn, model="gpt-4", provider="openai")

        mock_fn.assert_called_once_with(model="gpt-4", provider="openai")

    @pytest.mark.asyncio
    async def test_execute_delay_calculation(self):
        """Test that delay is calculated correctly."""
        engine = LLMRetryEngine()
        call_times = []

        async def delayed_fn():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 2:
                raise Exception("error")
            return "success"

        await engine.execute(delayed_fn)

        assert len(call_times) == 2
        # There should be a delay between calls
        delay = call_times[1] - call_times[0]
        assert delay >= engine.default_policy.base_delay_seconds

    @pytest.mark.asyncio
    async def test_is_retryable_with_empty_list(self):
        """Test _is_retryable with empty retryable errors list."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", retryable_errors=[])

        assert engine._is_retryable(Exception("any error"), policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_with_matching_error(self):
        """Test _is_retryable with matching error."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", retryable_errors=["timeout", "rate_limit"])

        assert engine._is_retryable(Exception("Request timeout"), policy) is True
        assert engine._is_retryable(Exception("Rate limit exceeded"), policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_with_non_matching_error(self):
        """Test _is_retryable with non-matching error."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", retryable_errors=["timeout"])

        assert engine._is_retryable(Exception("Authentication error"), policy) is False

    @pytest.mark.asyncio
    async def test_is_retryable_case_insensitive(self):
        """Test _is_retryable is case insensitive."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", retryable_errors=["TIMEOUT"])

        assert engine._is_retryable(Exception("timeout error"), policy) is True
        assert engine._is_retryable(Exception("TIMEOUT ERROR"), policy) is True

    @pytest.mark.asyncio
    async def test_compute_delay_exponential(self):
        """Test _compute_delay with exponential backoff."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", base_delay_seconds=1, exponential_base=2)

        delay1 = engine._compute_delay(1, policy)
        delay2 = engine._compute_delay(2, policy)
        delay3 = engine._compute_delay(3, policy)

        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

    @pytest.mark.asyncio
    async def test_compute_delay_max_delay(self):
        """Test _compute_delay respects max_delay_seconds."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", base_delay_seconds=1, max_delay_seconds=5, exponential_base=10)

        delay = engine._compute_delay(10, policy)

        assert delay == 5.0

    @pytest.mark.asyncio
    async def test_compute_delay_jitter(self):
        """Test _compute_delay with jitter policy."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="jitter", base_delay_seconds=1, max_delay_seconds=60)

        delay1 = engine._compute_delay(1, policy)
        delay2 = engine._compute_delay(1, policy)

        # Jitter should produce different delays
        assert delay1 != delay2
        # But within reasonable bounds
        assert 0.5 <= delay1 <= 1.0
        assert 0.5 <= delay2 <= 1.0

    @pytest.mark.asyncio
    async def test_compute_delay_constant(self):
        """Test _compute_delay with constant policy."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="constant", base_delay_seconds=2, max_delay_seconds=2)

        delay1 = engine._compute_delay(1, policy)
        delay2 = engine._compute_delay(5, policy)

        assert delay1 == 2.0
        assert delay2 == 2.0

    @pytest.mark.asyncio
    async def test_execute_fixed_1s_policy(self):
        """Test execute with fixed_1s policy."""
        engine = LLMRetryEngine()
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("error")
            return "success"

        result = await engine.execute(failing_fn, policy_name="fixed_1s")

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_exponential_fast_policy(self):
        """Test execute with exponential_fast policy."""
        engine = LLMRetryEngine()
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("error")
            return "success"

        result = await engine.execute(failing_fn, policy_name="exponential_fast")

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_conservative_policy(self):
        """Test execute with conservative policy."""
        engine = LLMRetryEngine()
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("error")
            return "success"

        result = await engine.execute(failing_fn, policy_name="conservative")

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_sync_function_error(self):
        """Test execute with sync function that raises error."""
        engine = LLMRetryEngine()

        async def sync_error_fn():
            raise ValueError("sync error")

        with pytest.raises(ValueError, match="sync error"):
            await engine.execute(sync_error_fn)

    @pytest.mark.asyncio
    async def test_execute_with_none_return(self):
        """Test execute with function returning None."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(return_value=None)

        result = await engine.execute(mock_fn)

        assert result is None

    @pytest.mark.asyncio
    async def test_execute_with_complex_return_value(self):
        """Test execute with complex return value."""
        engine = LLMRetryEngine()
        complex_value = {"nested": {"data": [1, 2, 3]}, "string": "test"}
        mock_fn = AsyncMock(return_value=complex_value)

        result = await engine.execute(mock_fn)

        assert result == complex_value

    @pytest.mark.asyncio
    async def test_execute_with_zero_max_retries(self):
        """Test execute with policy that has zero max retries."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(side_effect=Exception("error"))

        with pytest.raises(Exception, match="error"):
            await engine.execute(mock_fn, policy_name="no_retry")

        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_large_max_retries(self):
        """Test execute with policy that has large max retries."""
        engine = LLMRetryEngine()
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise Exception("error")
            return "success"

        result = await engine.execute(failing_fn, policy_name="aggressive")

        assert result == "success"
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_execute_error_propagation(self):
        """Test that the final error is propagated after retries."""
        engine = LLMRetryEngine()
        custom_error = ValueError("custom error message")
        mock_fn = AsyncMock(side_effect=custom_error)

        with pytest.raises(ValueError, match="custom error message"):
            await engine.execute(mock_fn)

    @pytest.mark.asyncio
    async def test_execute_with_different_exception_types(self):
        """Test execute with different exception types."""
        engine = LLMRetryEngine()

        for exception_class in [ValueError, KeyError, TypeError, RuntimeError, IOError]:
            mock_fn = AsyncMock(side_effect=exception_class("test"))

            with pytest.raises(exception_class):
                await engine.execute(mock_fn)

    @pytest.mark.asyncio
    async def test_execute_concurrent_retries(self):
        """Test concurrent retry executions."""
        engine = LLMRetryEngine()

        async def fn_with_id(id):
            if id % 2 == 0:
                raise Exception(f"error {id}")
            return f"success {id}"

        tasks = [engine.execute(fn_with_id, i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Even IDs should have exceptions, odd IDs should succeed
        assert sum(1 for r in results if isinstance(r, Exception)) == 5
        assert sum(1 for r in results if isinstance(r, str)) == 5

    @pytest.mark.asyncio
    async def test_execute_with_args_positional(self):
        """Test execute with positional arguments."""
        engine = LLMRetryEngine()

        async def pos_fn(a, b, c):
            return a + b + c

        result = await engine.execute(pos_fn, 1, 2, 3)

        assert result == 6

    @pytest.mark.asyncio
    async def test_execute_with_mixed_args(self):
        """Test execute with mixed positional and keyword arguments."""
        engine = LLMRetryEngine()

        async def mixed_fn(a, b, c=None, d=None):
            return {"a": a, "b": b, "c": c, "d": d}

        result = await engine.execute(mixed_fn, 1, 2, c=3, d=4)

        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}

    @pytest.mark.asyncio
    async def test_compute_delay_zero_base_delay(self):
        """Test _compute_delay with zero base delay."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", base_delay_seconds=0, max_delay_seconds=0)

        delay = engine._compute_delay(1, policy)

        assert delay == 0.0

    @pytest.mark.asyncio
    async def test_compute_delay_very_small_base_delay(self):
        """Test _compute_delay with very small base delay."""
        engine = LLMRetryEngine()
        policy = RetryPolicy(name="test", base_delay_seconds=0.001, max_delay_seconds=1.0)

        delay = engine._compute_delay(1, policy)

        assert delay == 0.001

    @pytest.mark.asyncio
    async def test_execute_model_extraction_from_args(self):
        """Test that model is extracted from args for metrics."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(return_value="result")

        await engine.execute(mock_fn, "prompt", "gpt-4")

        mock_fn.assert_called_once_with("prompt", "gpt-4")

    @pytest.mark.asyncio
    async def test_execute_provider_extraction_from_kwargs(self):
        """Test that provider is extracted from kwargs for metrics."""
        engine = LLMRetryEngine()
        mock_fn = AsyncMock(return_value="result")

        await engine.execute(mock_fn, provider="anthropic")

        mock_fn.assert_called_once_with(provider="anthropic")
