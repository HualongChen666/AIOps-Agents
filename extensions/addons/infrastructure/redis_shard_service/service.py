# -*- coding: utf-8 -*-
"""redis shard cluster service — real consistent-hash cluster on the shared engine."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.shard_cluster import ShardClusterServiceBase

OPERATIONS: List[str] = ["cache_get", "cache_set", "get_stats"]


class Service(ShardClusterServiceBase):
    """redis shard cluster service (consistent-hash routing, replication, HA)."""

    backend = "redis"
    SCHEMAS_MODULE = "extensions.addons.infrastructure.redis_shard_service.schemas"
    OPERATIONS = OPERATIONS


Service.OPERATIONS = OPERATIONS

ShardClusterService = Service
