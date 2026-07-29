# -*- coding: utf-8 -*-
"""Git-like configuration version control (task 30.3)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import List

from services.config_service.repository import ConfigRepository
from services.config_service.schemas import ConfigVersion


class ConfigVersionControl:
    """Manages config version commits."""

    def __init__(self, repo: ConfigRepository) -> None:
        self.repo = repo

    async def commit(self, namespace: str, message: str, author: str = "system") -> ConfigVersion:
        configs = await self.repo.list_configs(namespace, limit=10000)
        payload = "".join(f"{c.key}={c.value}" for c in sorted(configs, key=lambda x: x.key))
        commit_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        version = ConfigVersion(
            version_id=f"v-{namespace}-{datetime.utcnow().timestamp()}",
            namespace=namespace,
            commit_hash=commit_hash,
            message=message,
            author=author,
        )
        await self.repo.save_version(version)
        return version

    async def list(self, namespace: str, limit: int = 100) -> List[ConfigVersion]:
        return await self.repo.list_versions(namespace, limit)
