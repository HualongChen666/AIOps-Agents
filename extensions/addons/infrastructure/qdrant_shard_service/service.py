# -*- coding: utf-8 -*-
"""qdrant shard cluster service — real consistent-hash cluster on the shared engine."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.shard_cluster import ShardClusterServiceBase

OPERATIONS: List[str] = [
    "vector_create_collection",
    "vector_upsert",
    "vector_search",
    "get_stats",
]


class Service(ShardClusterServiceBase):
    """qdrant shard cluster service (consistent-hash routing, replication, HA)."""

    backend = "qdrant"
    SCHEMAS_MODULE = "extensions.addons.infrastructure.qdrant_shard_service.schemas"
    OPERATIONS = OPERATIONS


Service.OPERATIONS = OPERATIONS

ShardClusterService = Service
