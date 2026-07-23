# -*- coding: utf-8 -*-
"""Config orchestrator domain logic."""

from __future__ import annotations

from typing import List, Optional

from services.config_service.audit_logger import ConfigAuditLogger
from services.config_service.config_manager import ConfigManager
from services.config_service.encryption import ConfigEncryption
from services.config_service.hot_update import HotUpdateManager
from services.config_service.namespace import NamespaceManager
from services.config_service.repository import ConfigRepository
from services.config_service.rollback import RollbackManager
from services.config_service.saga import ConfigSagaOrchestrator
from services.config_service.schemas import (
    ConfigSnapshot,
    ConfigUpdateEvent,
    ConfigValue,
    ConfigVersion,
    SagaTransaction,
)
from services.config_service.version_control import ConfigVersionControl


class ConfigOrchestrator:
    """Coordinates config microservice operations."""

    def __init__(self, repo: ConfigRepository, encryption_key: str = "") -> None:
        self.repo = repo
        self.configs = ConfigManager(repo)
        self.versions = ConfigVersionControl(repo)
        self.snapshots = RollbackManager(repo)
        self.namespaces = NamespaceManager(repo)
        self.hot_updates = HotUpdateManager()
        self.audit = ConfigAuditLogger(repo)
        self.encryption = ConfigEncryption(encryption_key) if encryption_key else None

    async def create_config(self, config: ConfigValue) -> ConfigValue:
        if self.encryption and config.encrypted:
            config.value = self.encryption.encrypt(config.value)
        await self.configs.create(config)
        await self.audit.log(config.config_id, "created", {"namespace": config.namespace})
        return config

    async def update_config(
        self, config_id: str, value: str, updated_by: str = "system"
    ) -> Optional[ConfigValue]:
        config = await self.configs.get(config_id)
        if not config:
            return None
        old = config.value
        updated = await self.configs.update(config_id, value, updated_by)
        if updated:
            event = ConfigUpdateEvent(
                event_id=f"evt-{config_id}",
                config_id=config_id,
                namespace=updated.namespace,
                old_value=old,
                new_value=updated.value,
            )
            await self.hot_updates.publish(event)
            await self.audit.log(config_id, "updated", {"namespace": updated.namespace})
        return updated

    async def snapshot(self, namespace: str) -> ConfigSnapshot:
        return await self.snapshots.snapshot(namespace)

    async def restore(self, snapshot_id: str) -> List[str]:
        return await self.snapshots.restore(snapshot_id)

    async def commit_version(
        self, namespace: str, message: str, author: str = "system"
    ) -> ConfigVersion:
        version = await self.versions.commit(namespace, message, author)
        await self.audit.log(namespace, "committed", {"version": version.version_id})
        return version

    async def run_saga(self, saga: SagaTransaction) -> SagaTransaction:
        orchestrator = ConfigSagaOrchestrator(self.repo)
        return await orchestrator.execute(saga)
