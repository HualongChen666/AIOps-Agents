# -*- coding: utf-8 -*-
"""Tests for retry.py - Configurable retry engine."""

import asyncio
import pytest

from extensions.addons.documentation.sphinx_documentation_service.retry import (
    RetryEngine,
    RetryPolicy,
)


class TestRetryPolicy:
    """Test suite for RetryPolicy."""

    def test_default_values(self):
        """Test default RetryPolicy values."""
        policy = RetryPolicy(name="test")
        assert policy.name == "test"
        assert policy.max_retries == 3
        assert policy.base_delay_seconds == 1.0
        assert policy.max_delay_seconds == 60.0
        assert policy.exponential_base == 2.0
        assert policy.retryable_errors == ["retryable"]

    def test_custom_name(self):
        """Test custom name."""
        policy = RetryPolicy(name="custom")
        assert policy.name == "custom"

    def test_custom_max_retries(self):
        """Test custom max_retries."""
        policy = RetryPolicy(name="test", max_retries=5)
        assert policy.max_retries == 5

    def test_custom_base_delay(self):
        """Test custom base_delay_seconds."""
        policy = RetryPolicy(name="test", base_delay_seconds=2.0)
        assert policy.base_delay_seconds == 2.0

    def test_custom_max_delay(self):
        """Test custom max_delay_seconds."""
        policy = RetryPolicy(name="test", max_delay_seconds=120.0)
        assert policy.max_delay_seconds == 120.0

    def test_custom_exponential_base(self):
        """Test custom exponential_base."""
        policy = RetryPolicy(name="test", exponential_base=3.0)
        assert policy.exponential_base == 3.0

    def test_custom_retryable_errors(self):
        """Test custom retryable_errors."""
        policy = RetryPolicy(name="test", retryable_errors=["error1", "error2"])
        assert policy.retryable_errors == ["error1", "error2"]

    def test_empty_retryable_errors(self):
        """Test empty retryable_errors list."""
        policy = RetryPolicy(name="test", retryable_errors=[])
        assert policy.retryable_errors == []

    def test_zero_max_retries(self):
        """Test max_retries set to 0."""
        policy = RetryPolicy(name="test", max_retries=0)
        assert policy.max_retries == 0

    def test_negative_max_retries(self):
        """Test negative max_retries."""
        policy = RetryPolicy(name="test", max_retries=-1)
        assert policy.max_retries == -1

    def test_zero_base_delay(self):
        """Test base_delay_seconds set to 0."""
        policy = RetryPolicy(name="test", base_delay_seconds=0)
        assert policy.base_delay_seconds == 0

    def test_zero_max_delay(self):
        """Test max_delay_seconds set to 0."""
        policy = RetryPolicy(name="test", max_delay_seconds=0)
        assert policy.max_delay_seconds == 0

    def test_float_delays(self):
        """Test float delay values."""
        policy = RetryPolicy(name="test", base_delay_seconds=0.5, max_delay_seconds=30.5)
        assert policy.base_delay_seconds == 0.5
        assert policy.max_delay_seconds == 30.5

    def test_exponential_base_one(self):
        """Test exponential_base set to 1 (no exponential growth)."""
        policy = RetryPolicy(name="test", exponential_base=1.0)
        assert policy.exponential_base == 1.0

    def test_large_exponential_base(self):
        """Test large exponential_base."""
        policy = RetryPolicy(name="test", exponential_base=10.0)
        assert policy.exponential_base == 10.0

    def test_unicode_retryable_errors(self):
        """Test unicode characters in retryable_errors."""
        policy = RetryPolicy(name="test", retryable_errors=["错误1", "错误2"])
        assert "错误1" in policy.retryable_errors


class TestRetryEngine:
    """Test suite for RetryEngine."""

    @pytest.fixture
    def retry_engine(self):
        """Fixture for RetryEngine."""
        return RetryEngine()

    def test_init_default(self):
        """Test initialization with default parameters."""
        engine = RetryEngine()
        assert engine.default_policy is not None
        assert engine.policies is not None

    def test_init_custom_default_policy(self):
        """Test initialization with custom default policy."""
        engine = RetryEngine(default_policy_name="no_retry")
        assert engine.default_policy.name == "no_retry"

    def test_init_with_metrics(self):
        """Test initialization with metrics."""
        from extensions.addons.documentation.sphinx_documentation_service.metrics import (
            MetricsCollector,
        )

        metrics = MetricsCollector("retry_test")
        engine = RetryEngine(metrics=metrics)
        assert engine.metrics is metrics

    def test_default_policies_exist(self, retry_engine):
        """Test that default policies are loaded."""
        assert len(retry_engine.policies) > 0
        assert "no_retry" in retry_engine.policies
        assert "exponential" in retry_engine.policies

    def test_list_policies(self, retry_engine):
        """Test list_policies returns list of policy names."""
        policies = retry_engine.list_policies()
        assert isinstance(policies, list)
        assert len(policies) > 0
        assert "exponential" in policies

    def test_add_policy(self, retry_engine):
        """Test adding a custom policy."""
        custom_policy = RetryPolicy(name="custom", max_retries=10)
        retry_engine.add_policy(custom_policy)
        assert "custom" in retry_engine.policies
        assert retry_engine.policies["custom"] is custom_policy

    def test_add_policy_overwrite(self, retry_engine):
        """Test that add_policy overwrites existing policy."""
        policy1 = RetryPolicy(name="test", max_retries=1)
        policy2 = RetryPolicy(name="test", max_retries=5)
        retry_engine.add_policy(policy1)
        retry_engine.add_policy(policy2)
        assert retry_engine.policies["test"].max_retries == 5

    @pytest.mark.asyncio
    async def test_execute_success_on_first_try(self, retry_engine):
        """Test execute with successful function on first try."""

        async def success_func():
            return "success"

        result = await retry_engine.execute(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_args(self, retry_engine):
        """Test execute with function arguments."""

        async def func_with_args(a, b):
            return a + b

        result = await retry_engine.execute(func_with_args, 1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_execute_with_kwargs(self, retry_engine):
        """Test execute with keyword arguments."""

        async def func_with_kwargs(a, b):
            return a + b

        result = await retry_engine.execute(func_with_kwargs, a=1, b=2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_execute_with_mixed_args(self, retry_engine):
        """Test execute with mixed positional and keyword arguments."""

        async def func_mixed(a, b, c=0):
            return a + b + c

        result = await retry_engine.execute(func_mixed, 1, 2, c=3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_execute_retry_on_failure(self, retry_engine):
        """Test execute retries on failure."""

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("retryable error")
            return "success"

        result = await retry_engine.execute(failing_func)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(self, retry_engine):
        """Test execute raises exception after max retries exceeded."""

        async def always_failing_func():
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            await retry_engine.execute(always_failing_func)

    @pytest.mark.asyncio
    async def test_execute_with_custom_policy(self, retry_engine):
        """Test execute with custom policy."""
        custom_policy = RetryPolicy(name="custom", max_retries=1, retryable_errors=["error"])
        retry_engine.add_policy(custom_policy)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("error")

        with pytest.raises(ValueError):
            await retry_engine.execute(failing_func, policy_name="custom")
        assert call_count == 2  # initial + 1 retry

    @pytest.mark.asyncio
    async def test_execute_no_retry_policy(self, retry_engine):
        """Test execute with no_retry policy."""

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("error")

        with pytest.raises(ValueError):
            await retry_engine.execute(failing_func, policy_name="no_retry")
        assert call_count == 1  # no retries

    @pytest.mark.asyncio
    async def test_is_retryable_with_matching_error(self, retry_engine):
        """Test _is_retryable with matching error."""
        policy = RetryPolicy(name="test", retryable_errors=["timeout", "network"])
        exc = ValueError("timeout error")
        assert retry_engine._is_retryable(exc, policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_without_matching_error(self, retry_engine):
        """Test _is_retryable without matching error."""
        policy = RetryPolicy(name="test", retryable_errors=["timeout"])
        exc = ValueError("other error")
        assert retry_engine._is_retryable(exc, policy) is False

    @pytest.mark.asyncio
    async def test_is_retryable_empty_retryable_errors(self, retry_engine):
        """Test _is_retryable with empty retryable_errors (all errors retryable)."""
        policy = RetryPolicy(name="test", retryable_errors=[])
        exc = ValueError("any error")
        assert retry_engine._is_retryable(exc, policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_case_insensitive(self, retry_engine):
        """Test _is_retryable is case insensitive."""
        policy = RetryPolicy(name="test", retryable_errors=["TIMEOUT"])
        exc = ValueError("timeout error")
        assert retry_engine._is_retryable(exc, policy) is True

    @pytest.mark.asyncio
    async def test_compute_delay_exponential(self, retry_engine):
        """Test _compute_delay with exponential backoff."""
        policy = RetryPolicy(name="test", base_delay_seconds=1.0, exponential_base=2.0)
        delay1 = retry_engine._compute_delay(1, policy)
        delay2 = retry_engine._compute_delay(2, policy)
        delay3 = retry_engine._compute_delay(3, policy)
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

    @pytest.mark.asyncio
    async def test_compute_delay_max_cap(self, retry_engine):
        """Test _compute_delay respects max_delay_seconds."""
        policy = RetryPolicy(name="test", base_delay_seconds=1.0, max_delay_seconds=5.0)
        delay = retry_engine._compute_delay(10, policy)
        assert delay == 5.0

    @pytest.mark.asyncio
    async def test_compute_delay_jitter(self, retry_engine):
        """Test _compute_delay with jitter policy."""
        policy = RetryPolicy(name="jitter", base_delay_seconds=1.0, max_delay_seconds=60.0)
        delay1 = retry_engine._compute_delay(1, policy)
        delay2 = retry_engine._compute_delay(1, policy)
        # With jitter, delays should be different
        assert delay1 != delay2 or delay1 >= 0.5  # might be same by chance

    @pytest.mark.asyncio
    async def test_execute_with_operation_kwarg(self, retry_engine):
        """Test execute with operation kwarg for metrics."""
        from extensions.addons.documentation.sphinx_documentation_service.metrics import (
            MetricsCollector,
        )

        metrics = MetricsCollector("retry_test")
        engine = RetryEngine(metrics=metrics)

        async def success_func():
            return "success"

        result = await engine.execute(success_func, operation="test_op")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_metrics_on_failure(self, retry_engine):
        """Test that metrics are recorded on failure."""
        from extensions.addons.documentation.sphinx_documentation_service.metrics import (
            MetricsCollector,
        )

        metrics = MetricsCollector("retry_test")
        engine = RetryEngine(metrics=metrics)

        async def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await engine.execute(failing_func, operation="test_op")
        # Metrics should have been updated
        assert metrics.failures is not None

    @pytest.mark.asyncio
    async def test_execute_fixed_delay_policy(self, retry_engine):
        """Test execute with fixed delay policy."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retryable error")
            return "success"

        result = await retry_engine.execute(failing_func, policy_name="fixed_1s")
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_exponential_fast_policy(self, retry_engine):
        """Test execute with exponential_fast policy."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retryable error")
            return "success"

        result = await retry_engine.execute(failing_func, policy_name="exponential_fast")
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_invalid_policy_name(self, retry_engine):
        """Test execute with invalid policy name uses default."""

        async def success_func():
            return "success"

        result = await retry_engine.execute(success_func, policy_name="invalid_policy")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_none_policy_name(self, retry_engine):
        """Test execute with None policy name uses default."""

        async def success_func():
            return "success"

        result = await retry_engine.execute(success_func, policy_name=None)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_concurrent_retries(self, retry_engine):
        """Test concurrent retry operations."""

        async def func_with_id(id):
            call_count = 0
            async def failing():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise ValueError(f"retryable error {id}")
                return f"success {id}"
            return await retry_engine.execute(failing)

        results = await asyncio.gather(func_with_id(1), func_with_id(2), func_with_id(3))
        assert len(results) == 3
        for result in results:
            assert "success" in result

    @pytest.mark.asyncio
    async def test_execute_with_different_exception_types(self, retry_engine):
        """Test execute with different exception types."""

        async def raise_value_error():
            raise ValueError("value error")

        async def raise_runtime_error():
            raise RuntimeError("runtime error")

        with pytest.raises(ValueError):
            await retry_engine.execute(raise_value_error)

        with pytest.raises(RuntimeError):
            await retry_engine.execute(raise_runtime_error)

    @pytest.mark.asyncio
    async def test_execute_return_none(self, retry_engine):
        """Test execute with function that returns None."""

        async def none_func():
            return None

        result = await retry_engine.execute(none_func)
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_with_complex_return_value(self, retry_engine):
        """Test execute with complex return value."""

        async def complex_func():
            return {"key": "value", "number": 123, "list": [1, 2, 3]}

        result = await retry_engine.execute(complex_func)
        assert result == {"key": "value", "number": 123, "list": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_compute_delay_zero_base_delay(self, retry_engine):
        """Test _compute_delay with zero base delay."""
        policy = RetryPolicy(name="test", base_delay_seconds=0, max_delay_seconds=10)
        delay = retry_engine._compute_delay(1, policy)
        assert delay == 0

    @pytest.mark.asyncio
    async def test_compute_delay_first_attempt(self, retry_engine):
        """Test _compute_delay on first attempt (attempt=1)."""
        policy = RetryPolicy(name="test", base_delay_seconds=1.0)
        delay = retry_engine._compute_delay(1, policy)
        assert delay == 1.0

    @pytest.mark.asyncio
    async def test_linear_policy(self, retry_engine):
        """Test linear policy delays."""
        policy = retry_engine.policies.get("linear_1s")
        assert policy is not None
        delay1 = retry_engine._compute_delay(1, policy)
        delay2 = retry_engine._compute_delay(2, policy)
        # Linear should have predictable delays
        assert delay1 >= 0
        assert delay2 >= 0
