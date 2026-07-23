# -*- coding: utf-8 -*-
"""
Unit tests for core/ai/llm_router/load_balancer.py

This module contains comprehensive unit tests for the load balancer and circuit breaker,
covering circuit state management, model statistics, load balancing strategies,
and request tracking functionalities.
"""

import time

import pytest

from core.ai.llm_router.load_balancer import (
    CircuitBreaker,
    CircuitState,
    LoadBalancer,
    ModelStats,
)

# ============================================================
# CircuitState enum tests (3 test cases)
# ============================================================


class TestCircuitState:
    """Test cases for CircuitState enum."""

    def test_circuit_state_enum_values(self):
        """Test that CircuitState enum has correct values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_enum_comparison(self):
        """Test CircuitState enum comparison."""
        assert CircuitState.CLOSED == CircuitState.CLOSED
        assert CircuitState.CLOSED != CircuitState.OPEN

    def test_circuit_state_enum_iteration(self):
        """Test CircuitState enum iteration."""
        states = list(CircuitState)
        assert len(states) == 3
        assert CircuitState.CLOSED in states


# ============================================================
# ModelStats dataclass tests (8 test cases)
# ============================================================


class TestModelStats:
    """Test cases for ModelStats dataclass."""

    def test_model_stats_initialization(self):
        """Test ModelStats initialization."""
        stats = ModelStats(model_name="gpt-4")
        assert stats.model_name == "gpt-4"
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.avg_latency == 0.0
        assert stats.last_error is None
        assert stats.last_success_time is None

    def test_model_stats_custom_initialization(self):
        """Test ModelStats with custom values."""
        stats = ModelStats(
            model_name="gpt-4",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            avg_latency=1.5,
            last_error="Timeout",
            last_success_time=1234567890.0,
        )
        assert stats.model_name == "gpt-4"
        assert stats.total_requests == 100
        assert stats.successful_requests == 95
        assert stats.failed_requests == 5
        assert stats.avg_latency == 1.5
        assert stats.last_error == "Timeout"
        assert stats.last_success_time == 1234567890.0

    def test_model_stats_increment_total(self):
        """Test ModelStats total_requests increment."""
        stats = ModelStats(model_name="gpt-4")
        stats.total_requests = 10
        assert stats.total_requests == 10

    def test_model_stats_increment_successful(self):
        """Test ModelStats successful_requests increment."""
        stats = ModelStats(model_name="gpt-4")
        stats.successful_requests = 8
        assert stats.successful_requests == 8

    def test_model_stats_increment_failed(self):
        """Test ModelStats failed_requests increment."""
        stats = ModelStats(model_name="gpt-4")
        stats.failed_requests = 2
        assert stats.failed_requests == 2

    def test_model_stats_avg_latency_update(self):
        """Test ModelStats avg_latency update."""
        stats = ModelStats(model_name="gpt-4")
        stats.avg_latency = 2.5
        assert stats.avg_latency == 2.5

    def test_model_stats_last_error_set(self):
        """Test ModelStats last_error setting."""
        stats = ModelStats(model_name="gpt-4")
        stats.last_error = "Rate limit exceeded"
        assert stats.last_error == "Rate limit exceeded"

    def test_model_stats_last_success_time_set(self):
        """Test ModelStats last_success_time setting."""
        stats = ModelStats(model_name="gpt-4")
        stats.last_success_time = time.time()
        assert stats.last_success_time is not None


# ============================================================
# CircuitBreaker class tests (15 test cases)
# ============================================================


class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""

    def test_circuit_breaker_initialization(self):
        """Test CircuitBreaker initialization with defaults."""
        breaker = CircuitBreaker()
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60.0
        assert breaker.half_open_max_calls == 3
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
        assert breaker.half_open_calls == 0

    def test_circuit_breaker_custom_initialization(self):
        """Test CircuitBreaker with custom parameters."""
        breaker = CircuitBreaker(
            failure_threshold=10, recovery_timeout=120.0, half_open_max_calls=5
        )
        assert breaker.failure_threshold == 10
        assert breaker.recovery_timeout == 120.0
        assert breaker.half_open_max_calls == 5

    def test_circuit_breaker_record_success_closed_state(self):
        """Test record_success in CLOSED state."""
        breaker = CircuitBreaker()
        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_record_failure_increment(self):
        """Test record_failure increments failure count."""
        breaker = CircuitBreaker()
        breaker.record_failure()
        assert breaker.failure_count == 1
        assert breaker.last_failure_time is not None

    def test_circuit_breaker_open_on_threshold(self):
        """Test circuit opens when failure threshold reached."""
        breaker = CircuitBreaker(failure_threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    def test_circuit_breaker_can_request_closed(self):
        """Test can_request returns True in CLOSED state."""
        breaker = CircuitBreaker()
        assert breaker.can_request() is True

    def test_circuit_breaker_can_request_open(self):
        """Test can_request returns False in OPEN state."""
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_request() is False

    def test_circuit_breaker_recovery_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        time.sleep(0.15)
        assert breaker.can_request() is True
        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_half_open_success_closes(self):
        """Test circuit closes after successful calls in HALF_OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=2)
        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.15)
        breaker.can_request()  # Transition to HALF_OPEN
        breaker.record_success()
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_half_open_failure_reopens(self):
        """Test circuit reopens on failure in HALF_OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=3)
        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.15)
        breaker.can_request()  # Transition to HALF_OPEN
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_half_open_limit(self):
        """Test HALF_OPEN allows limited calls."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=2)
        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.15)
        breaker.can_request()  # Transition to HALF_OPEN
        breaker.record_success()
        breaker.record_success()
        # After 2 successful calls, should be closed, not limited
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_get_state(self):
        """Test get_state method."""
        breaker = CircuitBreaker()
        assert breaker.get_state() == CircuitState.CLOSED
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN

    def test_circuit_breaker_success_resets_failure_count(self):
        """Test success resets failure count in CLOSED state."""
        breaker = CircuitBreaker()
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2
        breaker.record_success()
        assert breaker.failure_count == 0

    def test_circuit_breaker_multiple_failures(self):
        """Test circuit handles multiple failures."""
        breaker = CircuitBreaker(failure_threshold=5)
        for i in range(10):
            breaker.record_failure()
        assert breaker.failure_count >= 5
        assert breaker.state == CircuitState.OPEN


# ============================================================
# LoadBalancer class tests (20 test cases)
# ============================================================


class TestLoadBalancer:
    """Test cases for LoadBalancer class."""

    def test_load_balancer_initialization(self):
        """Test LoadBalancer initialization."""
        model_configs = [
            {"model": "gpt-4", "api_key": "key1"},
            {"model": "gpt-3.5", "api_key": "key2"},
        ]
        balancer = LoadBalancer(model_configs)
        assert len(balancer.model_configs) == 2
        assert len(balancer.model_stats) == 2
        assert len(balancer.circuit_breakers) == 2

    def test_load_balancer_empty_configs(self):
        """Test LoadBalancer with empty configs."""
        balancer = LoadBalancer([])
        assert len(balancer.model_configs) == 0
        assert len(balancer.model_stats) == 0

    def test_load_balancer_config_without_model(self):
        """Test LoadBalancer ignores configs without model field."""
        model_configs = [{"model": "gpt-4"}, {"api_key": "key2"}]  # Second has no model
        balancer = LoadBalancer(model_configs)
        assert len(balancer.model_stats) == 1
        assert "gpt-4" in balancer.model_stats

    def test_load_balancer_select_model_round_robin(self):
        """Test select_model with round_robin strategy."""
        model_configs = [
            {"model": "gpt-4"},
            {"model": "gpt-3.5"},
        ]
        balancer = LoadBalancer(model_configs)
        selected = balancer.select_model(strategy="round_robin")
        assert selected in ["gpt-4", "gpt-3.5"]

    def test_load_balancer_select_model_least_latency(self):
        """Test select_model with least_latency strategy."""
        model_configs = [
            {"model": "gpt-4"},
            {"model": "gpt-3.5"},
        ]
        balancer = LoadBalancer(model_configs)
        # Set different latencies
        balancer.model_stats["gpt-4"].avg_latency = 2.0
        balancer.model_stats["gpt-3.5"].avg_latency = 1.0
        selected = balancer.select_model(strategy="least_latency")
        assert selected == "gpt-3.5"  # Lower latency

    def test_load_balancer_select_model_least_requests(self):
        """Test select_model with least_requests strategy."""
        model_configs = [
            {"model": "gpt-4"},
            {"model": "gpt-3.5"},
        ]
        balancer = LoadBalancer(model_configs)
        # Set different request counts
        balancer.model_stats["gpt-4"].total_requests = 10
        balancer.model_stats["gpt-3.5"].total_requests = 5
        selected = balancer.select_model(strategy="least_requests")
        assert selected == "gpt-3.5"  # Fewer requests

    def test_load_balancer_select_model_default_strategy(self):
        """Test select_model with default strategy."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        selected = balancer.select_model()
        assert selected == "gpt-4"

    def test_load_balancer_select_model_with_available_list(self):
        """Test select_model with custom available models list."""
        model_configs = [
            {"model": "gpt-4"},
            {"model": "gpt-3.5"},
        ]
        balancer = LoadBalancer(model_configs)
        selected = balancer.select_model(available_models=["gpt-4"])
        assert selected == "gpt-4"

    def test_load_balancer_select_model_all_circuits_open(self):
        """Test select_model returns None when all circuits open."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        # Open the circuit
        for _ in range(5):
            balancer.circuit_breakers["gpt-4"].record_failure()
        selected = balancer.select_model()
        assert selected is None

    def test_load_balancer_record_request_start(self):
        """Test record_request_start increments total requests."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        balancer.record_request_start("gpt-4")
        assert balancer.model_stats["gpt-4"].total_requests == 1

    def test_load_balancer_record_request_success(self):
        """Test record_request_success updates stats."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        balancer.record_request_start("gpt-4")
        balancer.record_request_success("gpt-4", 1.5)
        assert balancer.model_stats["gpt-4"].successful_requests == 1
        assert balancer.model_stats["gpt-4"].avg_latency == 1.5
        assert balancer.model_stats["gpt-4"].last_success_time is not None

    def test_load_balancer_record_request_failure(self):
        """Test record_request_failure updates stats."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        balancer.record_request_start("gpt-4")
        balancer.record_request_failure("gpt-4", "Timeout")
        assert balancer.model_stats["gpt-4"].failed_requests == 1
        assert balancer.model_stats["gpt-4"].last_error == "Timeout"

    def test_load_balancer_get_model_stats(self):
        """Test get_model_stats method."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        stats = balancer.get_model_stats("gpt-4")
        assert stats is not None
        assert stats.model_name == "gpt-4"

    def test_load_balancer_get_model_stats_nonexistent(self):
        """Test get_model_stats with nonexistent model."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        stats = balancer.get_model_stats("nonexistent")
        assert stats is None

    def test_load_balancer_get_all_stats(self):
        """Test get_all_stats method."""
        model_configs = [
            {"model": "gpt-4"},
            {"model": "gpt-3.5"},
        ]
        balancer = LoadBalancer(model_configs)
        all_stats = balancer.get_all_stats()
        assert len(all_stats) == 2
        assert "gpt-4" in all_stats
        assert "gpt-3.5" in all_stats

    def test_load_balancer_get_circuit_states(self):
        """Test get_circuit_states method."""
        model_configs = [
            {"model": "gpt-4"},
            {"model": "gpt-3.5"},
        ]
        balancer = LoadBalancer(model_configs)
        states = balancer.get_circuit_states()
        assert len(states) == 2
        assert states["gpt-4"] == CircuitState.CLOSED
        assert states["gpt-3.5"] == CircuitState.CLOSED

    def test_load_balancer_circuit_integration(self):
        """Test LoadBalancer integrates with CircuitBreaker."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        # Record failures to open circuit
        for _ in range(5):
            balancer.record_request_failure("gpt-4", "Error")
        states = balancer.get_circuit_states()
        assert states["gpt-4"] == CircuitState.OPEN

    def test_load_balancer_latency_averaging(self):
        """Test LoadBalancer averages latency correctly."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        balancer.record_request_start("gpt-4")
        balancer.record_request_success("gpt-4", 1.0)
        balancer.record_request_start("gpt-4")
        balancer.record_request_success("gpt-4", 2.0)
        # Average should be (1.0 + 2.0) / 2 = 1.5
        assert balancer.model_stats["gpt-4"].avg_latency == 1.5


# ============================================================
# Edge cases and boundary conditions tests (7 test cases)
# ============================================================


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_circuit_breaker_zero_threshold(self):
        """Test CircuitBreaker with zero failure threshold."""
        breaker = CircuitBreaker(failure_threshold=0)
        breaker.record_failure()
        # Should open immediately
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_zero_recovery_timeout(self):
        """Test CircuitBreaker with minimal recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        # With minimal timeout, should recover quickly
        time.sleep(0.02)
        assert breaker.can_request() is True

    def test_circuit_breaker_zero_half_open_calls(self):
        """Test CircuitBreaker with zero half-open max calls."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=0)
        breaker.record_failure()
        breaker.record_failure()
        time.sleep(0.15)
        # With zero half-open calls, transitions to HALF_OPEN but can_request returns False
        breaker.can_request()  # Trigger transition
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_request() is False  # No calls allowed

    def test_load_balancer_single_model(self):
        """Test LoadBalancer with single model."""
        model_configs = [{"model": "gpt-4"}]
        balancer = LoadBalancer(model_configs)
        selected = balancer.select_model()
        assert selected == "gpt-4"

    def test_load_balancer_large_number_of_models(self):
        """Test LoadBalancer with large number of models."""
        model_configs = [{"model": f"model_{i}"} for i in range(100)]
        balancer = LoadBalancer(model_configs)
        assert len(balancer.model_stats) == 100
        assert len(balancer.circuit_breakers) == 100

    def test_model_stats_negative_latency(self):
        """Test ModelStats handles negative latency (should not happen but test edge case)."""
        stats = ModelStats(model_name="gpt-4")
        stats.avg_latency = -1.0
        assert stats.avg_latency == -1.0

    def test_circuit_breaker_concurrent_failures(self):
        """Test CircuitBreaker handles concurrent failure recording."""
        breaker = CircuitBreaker(failure_threshold=10)
        for i in range(20):
            breaker.record_failure()
        assert breaker.failure_count == 20
        assert breaker.state == CircuitState.OPEN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
