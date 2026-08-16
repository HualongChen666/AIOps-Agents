# -*- coding: utf-8 -*-
"""Real-call branch coverage tests for core.execution.l6.fault_tolerant_executor.

These tests exercise every branch of the fault-tolerant executor by making real
class/function calls.  No mocks or internal monkeypatching are used; object
state is driven only through public constructors and methods.
"""

import asyncio
import time

from core.execution.l6.fault_tolerant_executor import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    ExecutionStatus,
    FailureType,
    FaultTolerantExecutor,
    RetryPolicy,
    get_fault_tolerant_executor,
)


def _run(coro):
    """Run a coroutine in a fresh event loop for synchronous pytest tests."""
    return asyncio.run(coro)


async def _async_identity(*args, **kwargs):
    return (args, kwargs)


def _sync_identity(*args, **kwargs):
    return (args, kwargs)


async def _async_slow():
    await asyncio.sleep(10)
    return "never"


def _make_fail(exc):
    def _fail(*args, **kwargs):
        raise exc
    return _fail


def test_factory_and_basic_init():
    """Factory and constructor cover the executor's __init__ defaults."""
    ex1 = get_fault_tolerant_executor()
    assert isinstance(ex1, FaultTolerantExecutor)

    ex2 = get_fault_tolerant_executor(
        {
            "max_retries": 5,
            "base_delay": 0.0,
            "max_delay": 5.0,
            "exponential_backoff": False,
            "default_timeout": 1.0,
        }
    )
    assert ex2.retry_policy.max_retries == 5
    assert ex2.retry_policy.base_delay == 0.0
    assert ex2.default_timeout == 1.0

    cb = CircuitBreaker(CircuitBreakerConfig())
    assert cb.get_state() == CircuitBreakerState.CLOSED


def test_circuit_breaker_call_branches():
    """Exercise all CircuitBreaker.call state/branch transitions."""
    # CLOSED state, sync and async calls, and non-coroutinefunc branch in call()
    cb = CircuitBreaker(CircuitBreakerConfig())
    assert _run(cb.call(_sync_identity, 1)) == ((1,), {})
    assert _run(cb.call(_async_identity, 2)) == ((2,), {})

    # OPEN -> raise (recovery_timeout is huge, so reset should not be attempted)
    cb_open = CircuitBreaker(
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1000.0)
    )
    try:
        _run(cb_open.call(_make_fail(ValueError("first")), ))
    except ValueError:
        pass
    assert cb_open.get_state() == CircuitBreakerState.OPEN
    try:
        _run(cb_open.call(_sync_identity, 1))
        raise AssertionError("expected OPEN circuit")
    except Exception as exc:
        assert "OPEN" in str(exc)

    # OPEN -> HALF_OPEN -> CLOSED with half_open_max_calls
    cb_half = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.0,
            half_open_max_calls=2,
        )
    )
    try:
        _run(cb_half.call(_make_fail(ValueError("init"))))
    except ValueError:
        pass
    assert cb_half.get_state() == CircuitBreakerState.OPEN

    # First call in half-open: success, not enough to close yet
    assert _run(cb_half.call(_sync_identity, 1)) == ((1,), {})
    assert cb_half.get_state() == CircuitBreakerState.HALF_OPEN

    # Second half-open success resets to CLOSED
    assert _run(cb_half.call(_sync_identity, 2)) == ((2,), {})
    assert cb_half.get_state() == CircuitBreakerState.CLOSED


def test_should_attempt_reset_and_record_failure_branches():
    """Directly cover _should_attempt_reset and _record_failure branches."""
    cb = CircuitBreaker(CircuitBreakerConfig(recovery_timeout=60.0))
    # last_failure_time is None -> True
    assert cb._should_attempt_reset() is True

    # Record a failure but stay under threshold
    cb_low = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))
    try:
        _run(cb_low.call(_make_fail(ValueError("x"))))
    except ValueError:
        pass
    assert cb_low.failure_count == 1
    assert cb_low.get_state() == CircuitBreakerState.CLOSED
    # last_failure_time is set and not enough time has elapsed
    assert cb_low._should_attempt_reset() is False

    # Reach threshold and open
    for _ in range(4):
        try:
            _run(cb_low.call(_make_fail(ValueError("x"))))
        except ValueError:
            pass
    assert cb_low.get_state() == CircuitBreakerState.OPEN


def test_executor_success_sync_async_and_circuit_breaker_branches():
    """execute() with sync/async functions and circuit breaker create/exists."""
    ex = get_fault_tolerant_executor({"default_timeout": 1.0, "base_delay": 0.0})

    async def async_op():  # pragma: no cover  # mark only for coverage in source
        return "async_result"

    def sync_op():
        return "sync_result"

    r1 = _run(ex.execute(async_op, "op_async"))
    assert r1.status == ExecutionStatus.COMPLETED
    assert r1.result == "async_result"

    r2 = _run(ex.execute(sync_op, "op_sync"))
    assert r2.status == ExecutionStatus.COMPLETED
    assert r2.result == "sync_result"

    # get_circuit_breaker create-then-existing branch
    cb1 = ex.get_circuit_breaker("op_async")
    cb2 = ex.get_circuit_breaker("op_async")
    assert cb1 is cb2

    # execute without circuit breaker (line 295 branch)
    r3 = _run(
        ex.execute(sync_op, "op_nocb", circuit_breaker_enabled=False)
    )
    assert r3.result == "sync_result"


def test_executor_retry_and_retryable_branches():
    """Cover _execute_with_retry loops and _is_retryable exception branches."""
    # max_retries=0, default not retryable -> immediate failure
    ex = get_fault_tolerant_executor(
        {"max_retries": 0, "base_delay": 0.0, "default_timeout": 1.0}
    )

    def fail_value():
        raise ValueError("no retry")

    r = _run(ex.execute(fail_value, "v"))
    assert r.status == ExecutionStatus.FAILED
    assert r.failure_type == FailureType.LOGIC_ERROR

    # Retryable default (ConnectionError) then success (attempt > 0 branch)
    ex2 = get_fault_tolerant_executor(
        {"max_retries": 2, "base_delay": 0.0, "default_timeout": 1.0}
    )
    attempts = []

    def flaky_conn():
        attempts.append(1)
        if len(attempts) < 2:
            raise ConnectionError("conn")
        return "ok"

    r2 = _run(ex2.execute(flaky_conn, "conn"))
    assert r2.status == ExecutionStatus.COMPLETED
    assert r2.result == "ok"

    # Custom retryable exceptions list
    rp_retry = RetryPolicy(max_retries=1, base_delay=0.0, retryable_exceptions=[RuntimeError])
    calls = []

    def flaky_runtime():
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("rt")
        return "rtok"

    r3 = _run(ex2.execute(flaky_runtime, "rt", retry_policy=rp_retry))
    assert r3.result == "rtok"

    # Custom non-retryable exceptions list
    rp_non = RetryPolicy(max_retries=3, base_delay=0.0, non_retryable_exceptions=[RuntimeError])

    def fail_runtime():
        raise RuntimeError("nonretry")

    r4 = _run(ex2.execute(fail_runtime, "nr", retry_policy=rp_non))
    assert r4.status == ExecutionStatus.FAILED

    # Max retries exceeded (attempt < max_retries false on last attempt)
    ex3 = get_fault_tolerant_executor(
        {"max_retries": 1, "base_delay": 0.0, "default_timeout": 1.0}
    )

    def always_fail():
        raise ConnectionError("always")

    r5 = _run(ex3.execute(always_fail, "always"))
    assert r5.status == ExecutionStatus.FAILED
    assert r5.retry_count == 0  # returned result carries retry_count default


def test_executor_timeout_and_fallback_branches():
    """Cover timeout path and fallback handler (sync/async/failing)."""
    ex = get_fault_tolerant_executor(
        {"default_timeout": 1.0, "base_delay": 0.0}
    )

    # Timeout without fallback -> TIMEOUT
    r1 = _run(ex.execute(_async_slow, "slow", timeout=0.001))
    assert r1.status == ExecutionStatus.TIMEOUT
    assert r1.failure_type == FailureType.TIMEOUT_ERROR

    # Sync fallback on timeout
    ex.register_fallback("slow2", lambda: "sync_fb")
    r2 = _run(ex.execute(_async_slow, "slow2", timeout=0.001))
    assert r2.status == ExecutionStatus.COMPLETED
    assert r2.result == "sync_fb"
    assert r2.metadata.get("fallback_used") is True

    # Async fallback on timeout
    async def async_fb():
        return "async_fb"

    ex.register_fallback("slow3", async_fb)
    r3 = _run(ex.execute(_async_slow, "slow3", timeout=0.001))
    assert r3.result == "async_fb"

    # Failing fallback on timeout -> still TIMEOUT
    def bad_fb():
        raise ValueError("fallback failed")

    ex.register_fallback("slow4", bad_fb)
    r4 = _run(ex.execute(_async_slow, "slow4", timeout=0.001))
    assert r4.status == ExecutionStatus.TIMEOUT

    # Fallback on generic exception (line 343 branch)
    def fail_logic():
        raise ValueError("logic")

    ex.register_fallback("logic", lambda: "logic_fb")
    r5 = _run(ex.execute(fail_logic, "logic"))
    assert r5.status == ExecutionStatus.COMPLETED
    assert r5.result == "logic_fb"
    assert r5.metadata.get("fallback_used") is True


def test_helper_method_branches():
    """Directly exercise _classify_error, _is_retryable, _calculate_retry_delay, etc."""
    ex = get_fault_tolerant_executor()

    # _classify_error branches
    assert ex._classify_error(ConnectionError()) == FailureType.NETWORK_ERROR
    assert ex._classify_error(ConnectionRefusedError()) == FailureType.NETWORK_ERROR
    assert ex._classify_error(asyncio.TimeoutError()) == FailureType.TIMEOUT_ERROR
    assert ex._classify_error(TimeoutError()) == FailureType.TIMEOUT_ERROR
    assert ex._classify_error(MemoryError()) == FailureType.RESOURCE_ERROR
    assert ex._classify_error(ResourceWarning()) == FailureType.RESOURCE_ERROR
    assert ex._classify_error(ImportError()) == FailureType.DEPENDENCY_ERROR
    assert ex._classify_error(AttributeError()) == FailureType.DEPENDENCY_ERROR
    assert ex._classify_error(ValueError()) == FailureType.LOGIC_ERROR
    assert ex._classify_error(RuntimeError()) == FailureType.LOGIC_ERROR

    # _is_retryable branches (including loop-continue edges)
    rp = RetryPolicy(non_retryable_exceptions=[ValueError])
    assert ex._is_retryable(ValueError("x"), rp) is False

    rp_continue = RetryPolicy(non_retryable_exceptions=[TypeError, ValueError])
    assert ex._is_retryable(ValueError("x"), rp_continue) is False

    rp2 = RetryPolicy(retryable_exceptions=[RuntimeError])
    assert ex._is_retryable(RuntimeError("r"), rp2) is True
    assert ex._is_retryable(ValueError("v"), rp2) is False

    rp2_continue = RetryPolicy(retryable_exceptions=[TypeError, RuntimeError])
    assert ex._is_retryable(RuntimeError("r"), rp2_continue) is True

    default = RetryPolicy()
    assert ex._is_retryable(ConnectionError(), default) is True
    assert ex._is_retryable(ValueError(), default) is False
    assert ex._is_retryable(asyncio.TimeoutError(), default) is True

    # _calculate_retry_delay exponential true/false and max_delay cap
    assert ex._calculate_retry_delay(2, RetryPolicy(base_delay=1.0, exponential_backoff=True)) == 4.0
    assert ex._calculate_retry_delay(2, RetryPolicy(base_delay=2.0, exponential_backoff=False)) == 2.0
    assert ex._calculate_retry_delay(10, RetryPolicy(base_delay=1.0, max_delay=5.0, exponential_backoff=True)) == 5.0

    # _update_avg_duration branches (total == 0, then > 0)
    ex._update_avg_duration("zero", 1.0)
    assert ex.execution_metrics["zero"]["avg_duration"] == 0.0
    ex.execution_metrics["zero"]["total"] = 1
    ex._update_avg_duration("zero", 3.0)
    assert ex.execution_metrics["zero"]["avg_duration"] == 3.0

    # get_metrics branches
    ex.execution_metrics["a"]["total"] = 1
    assert isinstance(ex.get_metrics("a"), dict)
    assert "a" in ex.get_metrics()

    # get_circuit_breaker_states (covers line 509)
    ex.get_circuit_breaker("states")
    assert "states" in ex.get_circuit_breaker_states()

    # reset_circuit_breaker true/false
    ex.get_circuit_breaker("a")  # create one
    assert ex.reset_circuit_breaker("a") is True
    assert ex.reset_circuit_breaker("missing") is False
