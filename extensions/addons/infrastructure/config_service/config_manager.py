# -*- coding: utf-8 -*-
"""Centralized configuration management (task 30.2)."""

from __future__ import annotations

from typing import List, Optional

from services.config_service.repository import ConfigRepository
from services.config_service.schemas import ConfigValue


class ConfigManager:
    """Manages configuration values."""

    def __init__(self, repo: ConfigRepository) -> None:
        self.repo = repo

    async def create(self, config: ConfigValue) -> ConfigValue:
        await self.repo.save_config(config)
        return config

    async def get(self, config_id: str) -> Optional[ConfigValue]:
        return await self.repo.get_config(config_id)

    async def list(self, namespace: str, limit: int = 100) -> List[ConfigValue]:
        return await self.repo.list_configs(namespace, limit)

    async def update(
        self, config_id: str, value: str, updated_by: str = "system"
    ) -> Optional[ConfigValue]:
        config = await self.repo.get_config(config_id)
        if not config:
            return None
        config.value
        config.value = value
        config.updated_at = __import__("datetime").datetime.utcnow()
        config.updated_by = updated_by
        await self.repo.save_config(config)
        return config

    async def delete(self, config_id: str) -> bool:
        return await self.repo.delete_config(config_id)
