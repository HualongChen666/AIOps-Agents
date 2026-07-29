# -*- coding: utf-8 -*-
"""Topology version management based on Git snapshots."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List

from loguru import logger

from services.topology_service.metrics import TOPOLOGY_VERSION_COMMITS
from services.topology_service.schemas import ServiceTopology, TopologyVersion


class TopologyVersionManager:
    """Manage topology versions using content-addressed snapshots."""

    def __init__(self) -> None:
        self._versions: Dict[str, List[TopologyVersion]] = {}

    async def commit(
        self,
        topology: ServiceTopology,
        message: str = "Topology snapshot",
    ) -> TopologyVersion:
        """Create a new version snapshot of the topology."""
        start = time.perf_counter()
        content = json.dumps(topology.model_dump(), sort_keys=True, default=str)
        commit_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        version = TopologyVersion(
            version=f"v{len(self._versions.get(topology.topology_id, [])) + 1}.0.0",
            topology_id=topology.topology_id,
            commit_hash=commit_hash,
            message=message,
        )
        self._versions.setdefault(topology.topology_id, []).append(version)
        TOPOLOGY_VERSION_COMMITS.labels(topology_id=topology.topology_id).inc()
        logger.info(
            f"Committed topology {topology.topology_id} version {version.version} "
            f"in {time.perf_counter() - start:.4f}s"
        )
        return version

    async def list_versions(
        self,
        topology_id: str,
        limit: int = 100,
    ) -> List[TopologyVersion]:
        """List versions for a topology."""
        return self._versions.get(topology_id, [])[-limit:]

    async def compare(
        self,
        topology_id: str,
        from_version: str,
        to_version: str,
    ) -> Dict[str, Any]:
        """Compare two topology versions (simplified diff)."""
        versions = self._versions.get(topology_id, [])
        from_idx = next((i for i, v in enumerate(versions) if v.version == from_version), -1)
        to_idx = next((i for i, v in enumerate(versions) if v.version == to_version), -1)
        return {
            "topology_id": topology_id,
            "from_version": from_version,
            "to_version": to_version,
            "version_count": len(versions),
            "from_index": from_idx,
            "to_index": to_idx,
            "diff": "content-addressed comparison default_value",
        }

    async def rollback(
        self,
        topology_id: str,
        version: str,
    ) -> bool:
        """Mark a rollback target version (metadata only)."""
        versions = self._versions.get(topology_id, [])
        target = next((v for v in versions if v.version == version), None)
        if not target:
            return False
        logger.info(f"Rollback topology {topology_id} to {version}")
        return True
