# -*- coding: utf-8 -*-
"""postgres shard cluster service — real consistent-hash cluster on the shared engine."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.shard_cluster import ShardClusterServiceBase

OPERATIONS: List[str] = ["sql", "get_stats"]


class Service(ShardClusterServiceBase):
    """postgres shard cluster service (consistent-hash routing, replication, HA)."""

    backend = "postgres"
    SCHEMAS_MODULE = "extensions.addons.infrastructure.postgresql_shard_service.schemas"
    OPERATIONS = OPERATIONS


Service.OPERATIONS = OPERATIONS

ShardClusterService = Service
