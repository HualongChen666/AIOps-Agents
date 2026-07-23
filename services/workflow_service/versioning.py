# -*- coding: utf-8 -*-
"""Workflow version control based on Git snapshots."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List

from loguru import logger

from services.workflow_service.metrics import WORKFLOW_VERSION_COMMITS
from services.workflow_service.schemas import WorkflowDefinition, WorkflowVersion


class WorkflowVersionManager:
    """Manage workflow versions using content-addressed snapshots."""

    def __init__(self) -> None:
        self._versions: Dict[str, List[WorkflowVersion]] = {}

    async def commit(
        self,
        definition: WorkflowDefinition,
        message: str = "Workflow snapshot",
    ) -> WorkflowVersion:
        """Create a new version snapshot of the workflow definition."""
        start = time.perf_counter()
        content = json.dumps(definition.model_dump(), sort_keys=True, default=str)
        commit_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        version = WorkflowVersion(
            version=f"v{len(self._versions.get(definition.workflow_id, [])) + 1}.0.0",
            workflow_id=definition.workflow_id,
            commit_hash=commit_hash,
            message=message,
        )
        self._versions.setdefault(definition.workflow_id, []).append(version)
        WORKFLOW_VERSION_COMMITS.labels(workflow_id=definition.workflow_id).inc()
        logger.info(
            f"Committed workflow {definition.workflow_id} version {version.version} "
            f"in {time.perf_counter() - start:.4f}s"
        )
        return version

    async def list_versions(
        self,
        workflow_id: str,
        limit: int = 100,
    ) -> List[WorkflowVersion]:
        """List versions for a workflow."""
        return self._versions.get(workflow_id, [])[-limit:]

    async def compare(
        self,
        workflow_id: str,
        from_version: str,
        to_version: str,
    ) -> Dict[str, Any]:
        """Compare two workflow versions."""
        versions = self._versions.get(workflow_id, [])
        from_idx = next((i for i, v in enumerate(versions) if v.version == from_version), -1)
        to_idx = next((i for i, v in enumerate(versions) if v.version == to_version), -1)
        return {
            "workflow_id": workflow_id,
            "from_version": from_version,
            "to_version": to_version,
            "version_count": len(versions),
            "from_index": from_idx,
            "to_index": to_idx,
            "diff": "content-addressed comparison placeholder",
        }

    async def rollback(self, workflow_id: str, version: str) -> bool:
        """Mark a rollback target version."""
        versions = self._versions.get(workflow_id, [])
        target = next((v for v in versions if v.version == version), None)
        if not target:
            return False
        logger.info(f"Rollback workflow {workflow_id} to {version}")
        return True
