# -*- coding: utf-8 -*-
"""Pydantic schemas for the cache microservice."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    index_size: int = 0


class StatsResponse(BaseModel):
    """Service statistics response."""

    total_requests: int
    cache_hits: int
    cache_misses: int
    operations: Dict[str, int] = Field(default_factory=dict)
    index_size: int


class CacheGetRequest(BaseModel):
    """Get a value from cache."""

    key: str


class CacheGetResponse(BaseModel):
    """Cache get response."""

    key: str
    value: Optional[Any] = None
    hit: bool = False


class CacheSetRequest(BaseModel):
    """Set a value in cache."""

    key: str
    value: Any
    ttl: int = 300
    tags: List[str] = Field(default_factory=list)


class CacheDeleteRequest(BaseModel):
    """Delete a key from cache."""

    key: str


class CacheClearRequest(BaseModel):
    """Clear the cache."""

    pass


class CachePreheatRequest(BaseModel):
    """Preheat cache with key-value pairs."""

    data: Dict[str, Any]
    ttl: int = 300


class CachePreheatResponse(BaseModel):
    """Cache preheat response."""

    keys_loaded: int


class CacheStrategy(str, Enum):
    """Supported caching strategies."""

    CACHE_ASIDE = "cache-aside"
    WRITE_THROUGH = "write-through"
    WRITE_BEHIND = "write-behind"
    REFRESH_AHEAD = "refresh-ahead"


class CacheStrategyRequest(BaseModel):
    """Execute a caching strategy."""

    strategy: CacheStrategy
    key: str
    value: Any
    ttl: int = 300


class CacheStrategyResponse(BaseModel):
    """Cache strategy execution response."""

    strategy: str
    key: str
    value: Any
    status: str
    backend_written: bool = False


class BreakdownProtectRequest(BaseModel):
    """Breakdown protection request."""

    key: str
    value: Optional[Any] = None
    ttl: int = 300


class BreakdownProtectResponse(BaseModel):
    """Breakdown protection response."""

    key: str
    locked: bool
    value: Any


class AvalancheProtectRequest(BaseModel):
    """Avalanche protection request."""

    key: str
    value: Any
    base_ttl: int = 300
    jitter_seconds: int = 30


class AvalancheProtectResponse(BaseModel):
    """Avalanche protection response."""

    key: str
    ttl: int
    value: Any


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""

    hits: int
    misses: int
    size: int
    total_requests: int
