# -*- coding: utf-8 -*-
"""Pydantic schemas for the Alert Rule microservice."""

from __future__ import annotations

from typing import Any, Dict

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
    index_size: int = 0
    feature_count: int = 0


class FeatureRequest(BaseModel):
    """Feature request."""

    config: Dict[str, Any] = Field(default_factory=dict)


class FeatureResponse(BaseModel):
    """Feature response."""

    feature: str
    success: bool
    status: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
