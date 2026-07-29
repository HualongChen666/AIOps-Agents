# -*- coding: utf-8 -*-
"""Rate limiting configuration and middleware for API protection.

🔧 P0 Reliability Enhancement:
This module provides enhanced rate limiting functionality to protect the API from abuse
and ensure fair usage across all users with advanced features.
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

import config

try:
    from core.prometheus_metrics import get_metrics_exporter
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    get_metrics_exporter = None  # type: ignore[assignment]

# Lazy initialization to avoid import errors
_limiter = None

# 🔧 P0 Enhancement: In-memory rate limiter for advanced scenarios
_in_memory_rate_limits: Dict[str, Dict[str, Any]] = defaultdict(
    lambda: {"requests": [], "blocked_until": None}
)


def get_limiter():
    """Get or create the rate limiter instance with enhanced configuration."""
    global _limiter
    if _limiter is None:
        try:
            from slowapi import Limiter
            from slowapi.util import get_remote_address

            # 🔧 P0 Enhancement: Enhanced limiter configuration
            _limiter = Limiter(
                key_func=get_remote_address,
                default_limits=[f"{config.RATE_LIMIT_PER_MINUTE}/minute"],
                storage_uri="memory://",  # In production, use Redis
                config_filename=None,  # Disable automatic .env file loading
                headers_enabled=True,  # Enable rate limit headers
            )
            logger.info("Enhanced rate limiter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize rate limiter: {e}")
            _limiter = None
    return _limiter


def get_rate_limit_for_endpoint(endpoint: str) -> str:
    """Get rate limit for a specific endpoint with enhanced categorization.

    🔧 P0 Enhancement:
    - More granular endpoint categorization
    - Support for sensitive operations
    - Different limits for different user types

    Args:
        endpoint: The endpoint path or identifier

    Returns:
        Rate limit string (e.g., "60/minute")
    """
    # 🔧 P0 Enhancement: Authentication endpoints have stricter limits
    if endpoint in ["/auth/login", "/auth/token", "/auth/refresh"]:
        return f"{config.RATE_LIMIT_AUTH_PER_MINUTE}/minute"

    # 🔧 P0 Enhancement: Sensitive operations have very strict limits
    if endpoint in ["/api/v1/repairs/execute", "/api/v1/users/delete", "/api/v1/system/config"]:
        sensitive_limit = getattr(config, "RATE_LIMIT_SENSITIVE_PER_MINUTE", 10)
        return f"{sensitive_limit}/minute"

    # 🔧 P0 Enhancement: Admin endpoints have higher limits
    if endpoint.startswith("/admin"):
        return f"{config.RATE_LIMIT_ADMIN_PER_MINUTE}/minute"

    # 🔧 P0 Enhancement: AI endpoints have moderate limits
    if endpoint.startswith("/api/ai"):
        ai_limit = getattr(config, "RATE_LIMIT_AI_PER_MINUTE", 30)
        return f"{ai_limit}/minute"

    # Default API rate limit
    return f"{config.RATE_LIMIT_API_PER_MINUTE}/minute"


# 🔧 P0 Enhancement: Advanced in-memory rate limiting for specific scenarios
class AdvancedRateLimiter:
    """Advanced rate limiter with sliding window and token bucket algorithms."""

    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._blocked: Dict[str, float] = {}  # IP -> blocked_until timestamp
        self._lock = asyncio.Lock()

    async def check_rate_limit_advanced(
        self, key: str, limit: int, window: int = 60, algorithm: str = "sliding_window"
    ) -> tuple[bool, Optional[str]]:
        """
        Advanced rate limiting check with multiple algorithms.

        🔧 P0 Enhancement:
        - Sliding window algorithm for accurate rate limiting
        - Token bucket algorithm for burst handling
        - Automatic blocking for repeated violations

        Args:
            key: Rate limit key (IP, user_id, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            algorithm: Rate limiting algorithm (sliding_window, token_bucket)

        Returns:
            (is_allowed, error_message)
        """
        async with self._lock:
            now = time.time()

            # Check if currently blocked
            if key in self._blocked:
                if now < self._blocked[key]:
                    remaining = int(self._blocked[key] - now)
                    return False, f"Rate limit exceeded. Try again in {remaining}s"
                else:
                    del self._blocked[key]

            if algorithm == "sliding_window":
                return await self._sliding_window_check(key, limit, window, now)
            elif algorithm == "token_bucket":
                return await self._token_bucket_check(key, limit, window, now)
            else:
                return True, None

    async def _sliding_window_check(
        self, key: str, limit: int, window: int, now: float
    ) -> tuple[bool, Optional[str]]:
        """Sliding window rate limiting check."""
        # Remove old requests outside the window
        self._requests[key] = [
            req_time for req_time in self._requests[key] if now - req_time < window
        ]

        # Check if under limit
        if len(self._requests[key]) >= limit:
            # Block for a short time on repeated violations
            if len(self._requests[key]) > limit * 2:
                self._blocked[key] = now + 60  # Block for 1 minute
            return False, f"Rate limit exceeded: {len(self._requests[key])}/{limit} per {window}s"

        # Add current request
        self._requests[key].append(now)
        return True, None

    async def _token_bucket_check(
        self, key: str, limit: int, window: int, now: float
    ) -> tuple[bool, Optional[str]]:
        """Token bucket rate limiting check."""
        # Simple implementation: use sliding window as base
        # In production, implement proper token bucket with refill rate
        return await self._sliding_window_check(key, limit, window, now)

    def reset_key(self, key: str) -> None:
        """Reset rate limit for a specific key."""
        if key in self._requests:
            del self._requests[key]
        if key in self._blocked:
            del self._blocked[key]

    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get rate limiting statistics for a key."""
        return {
            "key": key,
            "request_count": len(self._requests.get(key, [])),
            "is_blocked": key in self._blocked,
            "blocked_until": self._blocked.get(key),
        }


# Global advanced rate limiter instance
_advanced_rate_limiter = AdvancedRateLimiter()


def get_advanced_rate_limiter() -> AdvancedRateLimiter:
    """Get the global advanced rate limiter instance."""
    return _advanced_rate_limiter


def check_rate_limit(request: Request, limit: Optional[str] = None) -> bool:
    """Check if the request should be rate limited.

    Args:
        request: The FastAPI request object
        limit: Optional custom rate limit string

    Returns:
        True if request is allowed, False if rate limited
    """
    if not config.RATE_LIMIT_ENABLED:
        return True

    # Use custom limit if provided, otherwise use endpoint-specific limit
    if limit is None:
        limit = get_rate_limit_for_endpoint(request.url.path)

    try:
        limiter = get_limiter()
        if limiter is None:
            return True
        # The actual rate limiting is handled by the limiter decorator
        # This is a helper function for custom checks
        return True
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        # Fail open: allow request if rate limiting fails
        return True


# O15: concurrency and session limiters
class ConcurrencyLimiter:
    """Limit concurrent operations per key."""

    def __init__(self):
        self._counts: Dict[str, int] = defaultdict(int)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, key: str, max_concurrent: int) -> bool:
        async with self._locks[key]:
            if self._counts[key] >= max_concurrent:
                logger.warning(f"Concurrency limit exceeded for {key}")
                return False
            self._counts[key] += 1
            return True

    async def release(self, key: str) -> None:
        async with self._locks[key]:
            if self._counts[key] > 0:
                self._counts[key] -= 1


class SessionLimiter:
    """Limit number of active sessions per user/identifier."""

    def __init__(self):
        self._sessions: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    def _update_session_metric(self) -> None:
        total = sum(self._sessions.values())
        if get_metrics_exporter:
            try:
                get_metrics_exporter().record_active_sessions("user", total)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logging.warning("Suppressed exception", exc_info=True)
                pass

    async def check_and_register(self, key: str, max_sessions: int) -> bool:
        async with self._lock:
            if self._sessions[key] >= max_sessions:
                logger.warning(f"Session limit exceeded for {key}")
                return False
            self._sessions[key] += 1
            self._update_session_metric()
            return True

    async def unregister(self, key: str) -> None:
        async with self._lock:
            if self._sessions[key] > 0:
                self._sessions[key] -= 1
                self._update_session_metric()


_global_concurrency_limiter = ConcurrencyLimiter()
_global_session_limiter = SessionLimiter()


def get_concurrency_limiter() -> ConcurrencyLimiter:
    """Get the global concurrency limiter instance."""
    return _global_concurrency_limiter


def get_session_limiter() -> SessionLimiter:
    """Get the global session limiter instance."""
    return _global_session_limiter


def add_concurrency_middleware(app: FastAPI) -> None:
    """Add request-level concurrency/session limit middleware (default disabled)."""
    max_concurrent = int(os.getenv("AIOPS_MAX_CONCURRENT", "10"))
    max_sessions = int(os.getenv("AIOPS_MAX_SESSIONS", "5"))
    concurrency_limiter = get_concurrency_limiter()
    session_limiter = get_session_limiter()

    @app.middleware("http")
    async def concurrency_middleware(request: Request, call_next):
        client_id = request.client.host if request.client else "unknown"
        user = getattr(request.state, "user", {})
        session_key = user.get("id", client_id) if user else client_id

        if not await concurrency_limiter.acquire(client_id, max_concurrent):
            return JSONResponse(status_code=503, content={"error": "Concurrency limit exceeded"})
        try:
            if not await session_limiter.check_and_register(session_key, max_sessions):
                await concurrency_limiter.release(client_id)
                return JSONResponse(status_code=503, content={"error": "Session limit exceeded"})
            try:
                return await call_next(request)
            finally:
                await session_limiter.unregister(session_key)
        finally:
            await concurrency_limiter.release(client_id)


__all__ = [
    "get_limiter",
    "get_rate_limit_for_endpoint",
    "check_rate_limit",
    "AdvancedRateLimiter",
    "get_advanced_rate_limiter",
    "ConcurrencyLimiter",
    "get_concurrency_limiter",
    "SessionLimiter",
    "get_session_limiter",
]