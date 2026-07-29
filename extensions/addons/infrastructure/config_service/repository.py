# -*- coding: utf-8 -*-
"""Configuration repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from services.config_service.schemas import (
    AuditLogEntry,
    ConfigSnapshot,
    ConfigValue,
    ConfigVersion,
    SagaTransaction,
)


class ConfigRepository(ABC):
    """Abstract config repository."""

    @abstractmethod
    async def save_config(self, config: ConfigValue) -> str: ...

    @abstractmethod
    async def get_config(self, config_id: str) -> Optional[ConfigValue]: ...

    @abstractmethod
    async def list_configs(self, namespace: str, limit: int = 100) -> List[ConfigValue]: ...

    @abstractmethod
    async def delete_config(self, config_id: str) -> bool: ...

    @abstractmethod
    async def save_version(self, version: ConfigVersion) -> str: ...

    @abstractmethod
    async def list_versions(self, namespace: str, limit: int = 100) -> List[ConfigVersion]: ...

    @abstractmethod
    async def save_snapshot(self, snapshot: ConfigSnapshot) -> str: ...

    @abstractmethod
    async def get_snapshot(self, snapshot_id: str) -> Optional[ConfigSnapshot]: ...

    @abstractmethod
    async def save_audit_log(self, entry: AuditLogEntry) -> str: ...

    @abstractmethod
    async def list_audit_logs(self, config_id: str) -> List[AuditLogEntry]: ...

    @abstractmethod
    async def save_saga(self, saga: SagaTransaction) -> str: ...

    @abstractmethod
    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]: ...


class InMemoryConfigRepository(ConfigRepository):
    """In-memory config repository."""

    def __init__(self) -> None:
        self._configs: Dict[str, ConfigValue] = {}
        self._versions: Dict[str, List[ConfigVersion]] = {}
        self._snapshots: Dict[str, ConfigSnapshot] = {}
        self._audit_logs: Dict[str, List[AuditLogEntry]] = {}
        self._sagas: Dict[str, SagaTransaction] = {}

    async def save_config(self, config: ConfigValue) -> str:
        self._configs[config.config_id] = config
        return config.config_id

    async def get_config(self, config_id: str) -> Optional[ConfigValue]:
        return self._configs.get(config_id)

    async def list_configs(self, namespace: str, limit: int = 100) -> List[ConfigValue]:
        configs = [c for c in self._configs.values() if c.namespace == namespace]
        configs.sort(key=lambda c: c.updated_at, reverse=True)
        return configs[:limit]

    async def delete_config(self, config_id: str) -> bool:
        if config_id in self._configs:
            del self._configs[config_id]
            return True
        return False

    async def save_version(self, version: ConfigVersion) -> str:
        self._versions.setdefault(version.namespace, []).append(version)
        return version.version_id

    async def list_versions(self, namespace: str, limit: int = 100) -> List[ConfigVersion]:
        versions = self._versions.get(namespace, [])
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions[:limit]

    async def save_snapshot(self, snapshot: ConfigSnapshot) -> str:
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot.snapshot_id

    async def get_snapshot(self, snapshot_id: str) -> Optional[ConfigSnapshot]:
        return self._snapshots.get(snapshot_id)

    async def save_audit_log(self, entry: AuditLogEntry) -> str:
        self._audit_logs.setdefault(entry.config_id, []).append(entry)
        return entry.log_id

    async def list_audit_logs(self, config_id: str) -> List[AuditLogEntry]:
        return self._audit_logs.get(config_id, [])

    async def save_saga(self, saga: SagaTransaction) -> str:
        self._sagas[saga.saga_id] = saga
        return saga.saga_id

    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]:
        return self._sagas.get(saga_id)


async def get_repository(use_in_memory: bool = True) -> ConfigRepository:
    """Return repository instance."""
    return InMemoryConfigRepository()
