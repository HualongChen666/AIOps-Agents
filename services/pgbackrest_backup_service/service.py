# -*- coding: utf-8 -*-
"""Core service logic for the pgBackRest Backup microservice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .config import settings
from .metrics import MetricsCollector
from .retry import RetryEngine

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "postgresql_full_backup",
    "postgresql_incremental_backup",
    "backup_compression",
    "backup_encryption",
    "backup_retention_policy",
    "backup_transfer_s3",
    "backup_validation",
    "point_in_time_recovery",
    "integrate_ops_service",
    "test_and_optimize_pgbackrest_backup",
]


class pgBackRestBackupService:
    """Domain service for pgBackRest Backup."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector(settings.service_name)
        self.cache = cache or CacheManager(redis_url or settings.redis_url, self.metrics)
        self.retry_engine = RetryEngine("exponential_fast", self.metrics)
        self._state: Dict[str, Any] = {}
        self._backups: Dict[str, Any] = {}
        self._operations: Dict[str, int] = {}
        self._feature_count = len(OPERATIONS)

    @staticmethod
    def _get_config(request: Any) -> Dict[str, Any]:
        if request is None:
            return {}
        if hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            return {}
        if not isinstance(data, dict):
            return {}
        return data.get("config", data) if "config" in data else data

    async def get_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_state")
        config = self._get_config(request)
        feature = config.get("feature") if isinstance(config, dict) else None
        if feature and feature in self._state:
            return {
                "feature": "get_state",
                "success": True,
                "status": "found",
                "config": {"feature": feature},
                "result": {"state": self._state[feature]},
                "message": f"State for {feature}",
            }
        return {
            "feature": "get_state",
            "success": False,
            "status": "not_found",
            "config": config,
            "result": {},
            "message": "State not found",
        }

    async def backup_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("backup_state")
        config = self._get_config(request)
        name = config.get("name", "default") if isinstance(config, dict) else "default"
        self._backups[name] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self._state.copy(),
        }
        self.metrics.inc_operation("backup_state")
        return {
            "feature": "backup_state",
            "success": True,
            "status": "backed_up",
            "config": {"name": name},
            "result": {"snapshot": name},
            "message": f"Backup {name} created",
        }

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("restore_state")
        config = self._get_config(request)
        name = config.get("name", "default") if isinstance(config, dict) else "default"
        data = self._backups.get(name)
        if not data:
            return {
                "feature": "restore_state",
                "success": False,
                "status": "not_found",
                "config": {"name": name},
                "result": {},
                "message": f"Backup {name} not found",
            }
        self._state = data["state"].copy()
        self.metrics.inc_operation("restore_state")
        return {
            "feature": "restore_state",
            "success": True,
            "status": "restored",
            "config": {"name": name},
            "result": {"snapshot": name},
            "message": f"Backup {name} restored",
        }

    async def get_stats(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_stats")
        return {
            "feature": "get_stats",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {
                "total_requests": self.metrics.request_count,
                "cache_hits": self.metrics.cache_hits_count,
                "cache_misses": self.metrics.cache_misses_count,
                "operations": self._operations.copy(),
                "index_size": len(self._state),
                "feature_count": self._feature_count,
            },
            "message": "Statistics",
        }

    async def list_methods(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("list_methods")
        return {
            "feature": "list_methods",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {"methods": OPERATIONS + BASE_METHODS},
            "message": "Methods listed",
        }

    async def postgresql_full_backup(self, request: Any = None) -> Dict[str, Any]:
        """Postgresql Full Backup."""
        self.metrics.inc_request("postgresql_full_backup")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:postgresql_full_backup", config)
        self._state["postgresql_full_backup"] = config
        self._operations["postgresql_full_backup"] = (
            self._operations.get("postgresql_full_backup", 0) + 1
        )
        self.metrics.inc_operation("postgresql_full_backup")
        return {
            "feature": "postgresql_full_backup",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "postgresql_full_backup completed",
        }

    async def postgresql_incremental_backup(self, request: Any = None) -> Dict[str, Any]:
        """Postgresql Incremental Backup."""
        self.metrics.inc_request("postgresql_incremental_backup")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:postgresql_incremental_backup", config)
        self._state["postgresql_incremental_backup"] = config
        self._operations["postgresql_incremental_backup"] = (
            self._operations.get("postgresql_incremental_backup", 0) + 1
        )
        self.metrics.inc_operation("postgresql_incremental_backup")
        return {
            "feature": "postgresql_incremental_backup",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "postgresql_incremental_backup completed",
        }

    async def backup_compression(self, request: Any = None) -> Dict[str, Any]:
        """Backup Compression."""
        self.metrics.inc_request("backup_compression")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:backup_compression", config)
        self._state["backup_compression"] = config
        self._operations["backup_compression"] = self._operations.get("backup_compression", 0) + 1
        self.metrics.inc_operation("backup_compression")
        return {
            "feature": "backup_compression",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "backup_compression completed",
        }

    async def backup_encryption(self, request: Any = None) -> Dict[str, Any]:
        """Backup Encryption."""
        self.metrics.inc_request("backup_encryption")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:backup_encryption", config)
        self._state["backup_encryption"] = config
        self._operations["backup_encryption"] = self._operations.get("backup_encryption", 0) + 1
        self.metrics.inc_operation("backup_encryption")
        return {
            "feature": "backup_encryption",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "backup_encryption completed",
        }

    async def backup_retention_policy(self, request: Any = None) -> Dict[str, Any]:
        """Backup Retention Policy."""
        self.metrics.inc_request("backup_retention_policy")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:backup_retention_policy", config)
        self._state["backup_retention_policy"] = config
        self._operations["backup_retention_policy"] = (
            self._operations.get("backup_retention_policy", 0) + 1
        )
        self.metrics.inc_operation("backup_retention_policy")
        return {
            "feature": "backup_retention_policy",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "backup_retention_policy completed",
        }

    async def backup_transfer_s3(self, request: Any = None) -> Dict[str, Any]:
        """Backup Transfer S3."""
        self.metrics.inc_request("backup_transfer_s3")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:backup_transfer_s3", config)
        self._state["backup_transfer_s3"] = config
        self._operations["backup_transfer_s3"] = self._operations.get("backup_transfer_s3", 0) + 1
        self.metrics.inc_operation("backup_transfer_s3")
        return {
            "feature": "backup_transfer_s3",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "backup_transfer_s3 completed",
        }

    async def backup_validation(self, request: Any = None) -> Dict[str, Any]:
        """Backup Validation."""
        self.metrics.inc_request("backup_validation")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:backup_validation", config)
        self._state["backup_validation"] = config
        self._operations["backup_validation"] = self._operations.get("backup_validation", 0) + 1
        self.metrics.inc_operation("backup_validation")
        return {
            "feature": "backup_validation",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "backup_validation completed",
        }

    async def point_in_time_recovery(self, request: Any = None) -> Dict[str, Any]:
        """Point In Time Recovery."""
        self.metrics.inc_request("point_in_time_recovery")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:point_in_time_recovery", config)
        self._state["point_in_time_recovery"] = config
        self._operations["point_in_time_recovery"] = (
            self._operations.get("point_in_time_recovery", 0) + 1
        )
        self.metrics.inc_operation("point_in_time_recovery")
        return {
            "feature": "point_in_time_recovery",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "point_in_time_recovery completed",
        }

    async def integrate_ops_service(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Ops Service."""
        self.metrics.inc_request("integrate_ops_service")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:integrate_ops_service", config)
        self._state["integrate_ops_service"] = config
        self._operations["integrate_ops_service"] = (
            self._operations.get("integrate_ops_service", 0) + 1
        )
        self.metrics.inc_operation("integrate_ops_service")
        return {
            "feature": "integrate_ops_service",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "integrate_ops_service completed",
        }

    async def test_and_optimize_pgbackrest_backup(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Pgbackrest Backup."""
        self.metrics.inc_request("test_and_optimize_pgbackrest_backup")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_pgbackrest_backup", config)
        self._state["test_and_optimize_pgbackrest_backup"] = config
        self._operations["test_and_optimize_pgbackrest_backup"] = (
            self._operations.get("test_and_optimize_pgbackrest_backup", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_pgbackrest_backup")
        return {
            "feature": "test_and_optimize_pgbackrest_backup",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "pgBackRest Backup"},
            "message": "test_and_optimize_pgbackrest_backup completed",
        }

    async def call(self, method: str, **kwargs: Any) -> Any:
        self.metrics.inc_request("call")
        if method == "list_methods":
            return await self.list_methods(**kwargs)
        if method == "get_stats":
            return await self.get_stats(**kwargs)
        if method == "get_state":
            return await self.get_state(**kwargs)
        if method == "backup_state":
            return await self.backup_state(**kwargs)
        if method == "restore_state":
            return await self.restore_state(**kwargs)
        if method in OPERATIONS:
            fn = getattr(self, method, None)
            if fn is None:
                raise ValueError(f"Unknown method: {method}")
            return await fn(**kwargs)
        raise ValueError(f"Unknown method: {method}")


Service = pgBackRestBackupService
