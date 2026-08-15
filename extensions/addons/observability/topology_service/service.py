# -*- coding: utf-8 -*-
"""Core service logic for the Topology microservice."""

from __future__ import annotations

from typing import Any, List, Optional

from .config import settings
from ...engines.monitoring_provider import BaseObservabilityService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "discover_topology",
    "analyze_topology",
    "visualize_topology",
]


class TopologyService(BaseObservabilityService):
    """Domain service for Topology."""

    OPERATIONS = OPERATIONS
    BASE_METHODS = BASE_METHODS

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[Any] = None,
        cache: Optional[Any] = None,
    ) -> None:
        super().__init__(metrics=metrics, cache=cache, settings=settings)


Service = TopologyService
