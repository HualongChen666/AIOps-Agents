# -*- coding: utf-8 -*-
"""
Load Balancer and Circuit Breaker
Imelligent load balancing for LLM model requests
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class CircuitState(Enum):
    """Circuit breaker state"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ModelStats:
    """Model performance statistics"""

    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency: float = 0.0
    last_error: Optional[str] = None
    last_success_time: Optional[float] = None


class CircuitBreaker:
    """
    Circuit breaker for model availability
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds to wait before trying recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    def record_success(self) -> None:
        """Record successful request"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.half_open_calls = 0
                logger.info("Circuit breaker closed after successful recovery")

    def record_failure(self) -> None:
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_request(self) -> bool:
        """
        Check if request is allowed

        Returns:
            True if request can proceed
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout passed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker moved to half-open state")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state


class LoadBalancer:
    """
    Load balancer for model requests
    """

    def __init__(self, model_configs: List[Dict[str, Any]]):
        """
        Initialize load balancer

        Args:
            model_configs: Model configurations
        """
        self.model_configs = model_configs
        self.model_stats: Dict[str, ModelStats] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Initialize stats and circuit breakers
        for config in model_configs:
            model_name = config.get("model")
            if model_name is None:
                continue
            self.model_stats[model_name] = ModelStats(model_name=model_name)
            self.circuit_breakers[model_name] = CircuitBreaker()

    def select_model(
        self, available_models: Optional[List[str]] = None, strategy: str = "round_robin"
    ) -> Optional[str]:
        """
        Select model based on load balancing strategy

        Args:
            available_models: List of available models
            strategy: Selection strategy

        Returns:
            Selected model name
        """
        if available_models is None:
            available_models = [
                str(config.get("model"))
                for config in self.model_configs
                if config.get("model") is not None
            ]

        # Filter out models with open circuit
        available = [
            model for model in available_models if self.circuit_breakers[model].can_request()
        ]

        if not available:
            logger.warning("No models available (all circuits open)")
            return None

        if strategy == "round_robin":
            return self._round_robin_select(available)
        elif strategy == "least_latency":
            return self._least_latency_select(available)
        elif strategy == "least_requests":
            return self._least_requests_select(available)
        else:
            return available[0]

    def _round_robin_select(self, models: List[str]) -> str:
        """Round-robin selection"""
        # Simple round-robin based on request count
        models.sort(key=lambda m: self.model_stats[m].total_requests)
        return models[0]

    def _least_latency_select(self, models: List[str]) -> str:
        """Select model with lowest average latency"""
        models.sort(key=lambda m: self.model_stats[m].avg_latency)
        return models[0]

    def _least_requests_select(self, models: List[str]) -> str:
        """Select model with least requests"""
        models.sort(key=lambda m: self.model_stats[m].total_requests)
        return models[0]

    def record_request_start(self, model_name: str) -> None:
        """Record request start"""
        self.model_stats[model_name].total_requests += 1

    def record_request_success(self, model_name: str, latency: float) -> None:
        """
        Record successful request

        Args:
            model_name: Model name
            latency: Request latency in seconds
        """
        stats = self.model_stats[model_name]
        stats.successful_requests += 1
        stats.last_success_time = time.time()

        # Update average latency
        if stats.total_requests == 0:
            stats.total_requests = 1
        total = stats.total_requests
        stats.avg_latency = (stats.avg_latency * (total - 1) + latency) / total

        # Update circuit breaker
        self.circuit_breakers[model_name].record_success()

    def record_request_failure(self, model_name: str, error: str) -> None:
        """
        Record failed request

        Args:
            model_name: Model name
            error: Error message
        """
        stats = self.model_stats[model_name]
        stats.failed_requests += 1
        stats.last_error = error

        # Update circuit breaker
        self.circuit_breakers[model_name].record_failure()

    def get_model_stats(self, model_name: str) -> Optional[ModelStats]:
        """Get model statistics"""
        return self.model_stats.get(model_name)

    def get_all_stats(self) -> Dict[str, ModelStats]:
        """Get all model statistics"""
        return self.model_stats.copy()

    def get_circuit_states(self) -> Dict[str, CircuitState]:
        """Get all circuit breaker states"""
        return {model: breaker.get_state() for model, breaker in self.circuit_breakers.items()}
