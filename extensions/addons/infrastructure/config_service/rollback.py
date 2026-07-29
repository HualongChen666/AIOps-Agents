# -*- coding: utf-8 -*-
"""Configuration rollback based on snapshots (task 30.7)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from services.config_service.repository import ConfigRepository
from services.config_service.schemas import ConfigSnapshot


class RollbackManager:
    """Creates and restores config snapshots."""

    def __init__(self, repo: ConfigRepository) -> None:
        self.repo = repo

    async def snapshot(self, namespace: str) -> ConfigSnapshot:
        configs = await self.repo.list_configs(namespace, limit=10000)
        snapshot = ConfigSnapshot(
            snapshot_id=f"snap-{namespace}-{datetime.utcnow().timestamp()}",
            namespace=namespace,
            version="1.0.0",
            configs={c.key: c.value for c in configs},
        )
        await self.repo.save_snapshot(snapshot)
        return snapshot

    async def restore(self, snapshot_id: str) -> List[str]:
        snapshot = await self.repo.get_snapshot(snapshot_id)
        if not snapshot:
            return []
        restored = []
        for key, value in snapshot.configs.items():
            from services.config_service.schemas import ConfigValue

            config = ConfigValue(
                config_id=f"{snapshot.namespace}-{key}",
                key=key,
                value=value,
                namespace=snapshot.namespace,
            )
            await self.repo.save_config(config)
            restored.append(config.config_id)
        return restored
