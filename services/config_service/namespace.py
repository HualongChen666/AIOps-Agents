# -*- coding: utf-8 -*-
"""Configuration environment isolation by namespace (task 30.8)."""

from __future__ import annotations

from typing import List

from services.config_service.repository import ConfigRepository
from services.config_service.schemas import ConfigNamespace, ConfigValue


class NamespaceManager:
    """Isolates configuration per namespace."""

    def __init__(self, repo: ConfigRepository) -> None:
        self.repo = repo

    async def list_namespaces(self) -> List[str]:
        return [n.value for n in ConfigNamespace]

    async def create(self, namespace: str, key: str, value: str) -> ConfigValue:
        config = ConfigValue(
            config_id=f"{namespace}-{key}",
            key=key,
            value=value,
            namespace=namespace,
        )
        await self.repo.save_config(config)
        return config

    async def list(self, namespace: str) -> List[ConfigValue]:
        return await self.repo.list_configs(namespace)
