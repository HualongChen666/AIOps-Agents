# -*- coding: utf-8 -*-
"""Retry engine for the Scenario Memory microservice."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

from loguru import logger


class ScenarioRetryEngine:
    """Retry engine with exponential backoff."""

    POLICIES: Dict[str, Dict[str, Any]] = {
        "exponential": {"max_retries": 3, "base_delay": 1.0, "max_delay": 30.0},
        "linear": {"max_retries": 3, "base_delay": 0.5, "max_delay": 10.0},
        "none": {"max_retries": 0, "base_delay": 0.0, "max_delay": 0.0},
    }

    def __init__(self, policy: str = "exponential") -> None:
        self._policy = policy if policy in self.POLICIES else "exponential"
        self._config = self.POLICIES[self._policy]

    @property
    def max_retries(self) -> int:
        return int(self._config["max_retries"])

    @property
    def base_delay(self) -> float:
        return float(self._config["base_delay"])

    def list_policies(self) -> list:
        """List available retry policies."""
        return list(self.POLICIES.keys())

    async def execute(
        self,
        fn: Callable[..., Any],
        *args: Any,
        operation: str = "unknown",
        **kwargs: Any,
    ) -> Any:
        """Execute a function with retries."""
        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exception = exc
                logger.warning(f"Operation {operation} failed (attempt {attempt + 1}): {exc}")
                if attempt >= self.max_retries:
                    break
                delay = min(
                    self.base_delay * (2**attempt),
                    self._config["max_delay"],
                )
                await asyncio.sleep(delay)
        if last_exception is not None:
            raise last_exception
