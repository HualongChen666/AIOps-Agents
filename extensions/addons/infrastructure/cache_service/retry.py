# -*- coding: utf-8 -*-
"""Configurable retry engine."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List, Optional

from loguru import logger

from .metrics import MetricsCollector


@dataclass
class RetryPolicy:
    """Retry policy with exponential backoff."""

    name: str
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    retryable_errors: List[str] = field(default_factory=lambda: ["retryable"])


class RetryEngine:
    """Execute coroutines with configurable exponential backoff."""

    DEFAULT_POLICIES: List[RetryPolicy] = [
        RetryPolicy(name="no_retry", max_retries=0, base_delay_seconds=0, max_delay_seconds=0),
        RetryPolicy(name="fixed_1s", max_retries=3, base_delay_seconds=1, max_delay_seconds=1),
        RetryPolicy(name="fixed_5s", max_retries=3, base_delay_seconds=5, max_delay_seconds=5),
        RetryPolicy(name="linear_1s", max_retries=5, base_delay_seconds=1, max_delay_seconds=5),
        RetryPolicy(
            name="exponential",
            max_retries=3,
            base_delay_seconds=1,
            max_delay_seconds=30,
        ),
        RetryPolicy(
            name="exponential_fast",
            max_retries=3,
            base_delay_seconds=0.1,
            max_delay_seconds=1,
        ),
        RetryPolicy(
            name="jitter",
            max_retries=5,
            base_delay_seconds=1,
            max_delay_seconds=60,
        ),
    ]

    def __init__(
        self,
        default_policy_name: str = "exponential",
        metrics: Optional[MetricsCollector] = None,
    ) -> None:
        self.policies: dict[str, RetryPolicy] = {p.name: p for p in self.DEFAULT_POLICIES}
        self.default_policy = self.policies.get(default_policy_name) or self.policies["exponential"]
        self.metrics = metrics

    def add_policy(self, policy: RetryPolicy) -> None:
        self.policies[policy.name] = policy

    def list_policies(self) -> List[str]:
        return list(self.policies.keys())

    async def execute(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args: Any,
        policy_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        policy = self.policies.get(policy_name) if policy_name else self.default_policy
        if not policy:
            policy = self.default_policy

        last_error: Optional[Exception] = None
        attempt = 0
        operation = kwargs.pop("operation", None) or (args[0] if args else "unknown")

        while attempt <= policy.max_retries:
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                attempt += 1
                if self.metrics:
                    self.metrics.inc_failure(str(operation), type(exc).__name__)
                if not self._is_retryable(exc, policy) or attempt > policy.max_retries:
                    raise exc
                delay = self._compute_delay(attempt, policy)
                logger.warning(
                    f"Retry attempt {attempt} for {fn.__name__} after {delay:.2f}s: {exc}"
                )
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        return None  # pragma: no cover

    def _is_retryable(self, exc: Exception, policy: RetryPolicy) -> bool:
        error_text = str(exc).lower()
        if not policy.retryable_errors:
            return True
        return any(err.lower() in error_text for err in policy.retryable_errors)

    def _compute_delay(self, attempt: int, policy: RetryPolicy) -> float:
        delay = policy.base_delay_seconds * (policy.exponential_base ** (attempt - 1))
        delay = min(delay, policy.max_delay_seconds)
        if policy.name == "jitter":
            delay = delay * (0.5 + secrets.SystemRandom().random())
        return delay
