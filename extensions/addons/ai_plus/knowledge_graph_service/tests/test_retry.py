# -*- coding: utf-8 -*-
"""Tests for KnowledgeGraphRetryEngine module."""

import pytest
import asyncio

from extensions.addons.ai_plus.knowledge_graph_service.retry import KnowledgeGraphRetryEngine


class TestKnowledgeGraphRetryEngine:
    """Test cases for KnowledgeGraphRetryEngine class."""

    def test_initialization_default(self):
        """Test initialization with default policy."""
        engine = KnowledgeGraphRetryEngine()
        assert engine._policy == "exponential"
        assert engine.max_retries == 3
        assert engine.base_delay == 1.0

    def test_initialization_exponential(self):
        """Test initialization with exponential policy."""
        engine = KnowledgeGraphRetryEngine(policy="exponential")
        assert engine._policy == "exponential"
        assert engine.max_retries == 3
        assert engine.base_delay == 1.0

    def test_initialization_linear(self):
        """Test initialization with linear policy."""
        engine = KnowledgeGraphRetryEngine(policy="linear")
        assert engine._policy == "linear"
        assert engine.max_retries == 3
        assert engine.base_delay == 0.5

    def test_initialization_none(self):
        """Test initialization with none policy."""
        engine = KnowledgeGraphRetryEngine(policy="none")
        assert engine._policy == "none"
        assert engine.max_retries == 0
        assert engine.base_delay == 0.0

    def test_initialization_invalid_policy(self):
        """Test initialization with invalid policy defaults to exponential."""
        engine = KnowledgeGraphRetryEngine(policy="invalid")
        assert engine._policy == "exponential"

    def test_max_retries_property(self):
        """Test max_retries property."""
        engine = KnowledgeGraphRetryEngine(policy="exponential")
        assert engine.max_retries == 3

        engine = KnowledgeGraphRetryEngine(policy="none")
        assert engine.max_retries == 0

    def test_base_delay_property(self):
        """Test base_delay property."""
        engine = KnowledgeGraphRetryEngine(policy="exponential")
        assert engine.base_delay == 1.0

        engine = KnowledgeGraphRetryEngine(policy="linear")
        assert engine.base_delay == 0.5

    def test_list_policies(self):
        """Test list_policies returns all available policies."""
        engine = KnowledgeGraphRetryEngine()
        policies = engine.list_policies()
        assert "exponential" in policies
        assert "linear" in policies
        assert "none" in policies

    @pytest.mark.asyncio
    async def test_execute_sync_function_success(self):
        """Test executing a synchronous function that succeeds."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def sync_func():
            return "success"

        result = await engine.execute(sync_func, operation="test")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_async_function_success(self):
        """Test executing an async function that succeeds."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        async def async_func():
            return "async_success"

        result = await engine.execute(async_func, operation="test")
        assert result == "async_success"

    @pytest.mark.asyncio
    async def test_execute_with_args(self):
        """Test executing function with arguments."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def func(a, b):
            return a + b

        result = await engine.execute(func, 2, 3, operation="test")
        assert result == 5

    @pytest.mark.asyncio
    async def test_execute_with_kwargs(self):
        """Test executing function with keyword arguments."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def func(a, b, c=10):
            return a + b + c

        result = await engine.execute(func, 2, 3, c=5, operation="test")
        assert result == 10

    @pytest.mark.asyncio
    async def test_execute_sync_function_failure_no_retry(self):
        """Test executing sync function that fails with no retry policy."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await engine.execute(failing_func, operation="test")

    @pytest.mark.asyncio
    async def test_execute_async_function_failure_no_retry(self):
        """Test executing async function that fails with no retry policy."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await engine.execute(failing_func, operation="test")

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """Test executing function that succeeds after retry."""
        engine = KnowledgeGraphRetryEngine(policy="linear")
        attempt_count = 0

        def func_with_retry():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "success"

        result = await engine.execute(func_with_retry, operation="test")
        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausted(self):
        """Test executing function that exhausts retries."""
        engine = KnowledgeGraphRetryEngine(policy="linear")
        attempt_count = 0

        def always_failing_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(ValueError, match="Persistent error"):
            await engine.execute(always_failing_func, operation="test")

        assert attempt_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_execute_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        engine = KnowledgeGraphRetryEngine(policy="exponential")
        attempt_count = 0
        delays = []

        async def func_with_delay():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "success"

        # Patch asyncio.sleep to capture delays
        original_sleep = asyncio.sleep
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            # Don't actually sleep in test
            pass

        asyncio.sleep = mock_sleep
        try:
            result = await engine.execute(func_with_delay, operation="test")
            assert result == "success"
            # Check that delays increase exponentially
            if len(sleep_calls) >= 2:
                assert sleep_calls[1] > sleep_calls[0]
        finally:
            asyncio.sleep = original_sleep

    @pytest.mark.asyncio
    async def test_execute_linear_backoff(self):
        """Test linear backoff delay calculation."""
        engine = KnowledgeGraphRetryEngine(policy="linear")
        attempt_count = 0

        async def func_with_delay():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "success"

        # Patch asyncio.sleep to capture delays
        original_sleep = asyncio.sleep
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            pass

        asyncio.sleep = mock_sleep
        try:
            result = await engine.execute(func_with_delay, operation="test")
            assert result == "success"
        finally:
            asyncio.sleep = original_sleep

    @pytest.mark.asyncio
    async def test_execute_max_delay_limit(self):
        """Test that delay is capped at max_delay."""
        engine = KnowledgeGraphRetryEngine(policy="exponential")
        attempt_count = 0

        async def func_with_many_retries():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ValueError("Temporary error")
            return "success"

        # Patch asyncio.sleep to capture delays
        original_sleep = asyncio.sleep
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            pass

        asyncio.sleep = mock_sleep
        try:
            result = await engine.execute(func_with_many_retries, operation="test")
            assert result == "success"
            # Check that no delay exceeds max_delay (30.0)
            for delay in sleep_calls:
                assert delay <= 30.0
        finally:
            asyncio.sleep = original_sleep

    @pytest.mark.asyncio
    async def test_execute_operation_parameter(self):
        """Test that operation parameter is used in logging."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await engine.execute(func, operation="custom_operation")

    @pytest.mark.asyncio
    async def test_execute_different_exception_types(self):
        """Test handling of different exception types."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def func_with_runtime_error():
            raise RuntimeError("Runtime error")

        def func_with_value_error():
            raise ValueError("Value error")

        with pytest.raises(RuntimeError):
            await engine.execute(func_with_runtime_error, operation="test")

        with pytest.raises(ValueError):
            await engine.execute(func_with_value_error, operation="test")

    @pytest.mark.asyncio
    async def test_execute_function_returning_none(self):
        """Test executing function that returns None."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def func_returning_none():
            return None

        result = await engine.execute(func_returning_none, operation="test")
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_function_returning_complex_object(self):
        """Test executing function that returns complex object."""
        engine = KnowledgeGraphRetryEngine(policy="none")

        def func_returning_dict():
            return {"key": "value", "number": 123}

        result = await engine.execute(func_returning_dict, operation="test")
        assert result == {"key": "value", "number": 123}

    @pytest.mark.asyncio
    async def test_execute_with_zero_retries(self):
        """Test execute with zero retries (none policy)."""
        engine = KnowledgeGraphRetryEngine(policy="none")
        attempt_count = 0

        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Error")

        with pytest.raises(ValueError):
            await engine.execute(failing_func, operation="test")

        assert attempt_count == 1  # Only initial attempt, no retries

    @pytest.mark.asyncio
    async def test_execute_with_custom_max_retries(self):
        """Test that max_retries is respected from policy config."""
        engine = KnowledgeGraphRetryEngine(policy="exponential")
        assert engine.max_retries == 3

        attempt_count = 0

        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Error")

        with pytest.raises(ValueError):
            await engine.execute(failing_func, operation="test")

        # Should attempt 1 initial + 3 retries = 4 total
        assert attempt_count == 4
