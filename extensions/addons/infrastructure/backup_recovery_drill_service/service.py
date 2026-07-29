# -*- coding: utf-8 -*-
"""Core service logic for the Backup Recovery Drill microservice."""

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
    "design_drill_plan",
    "run_database_backup_drill",
    "run_config_backup_drill",
    "run_log_backup_drill",
    "write_drill_report",
]


class BackupRecoveryDrillService:
    """Domain service for Backup Recovery Drill."""

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

    async def design_drill_plan(self, request: Any = None) -> Dict[str, Any]:
        """Design Drill Plan."""
        self.metrics.inc_request("design_drill_plan")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:design_drill_plan", config)
        self._state["design_drill_plan"] = config
        self._operations["design_drill_plan"] = self._operations.get("design_drill_plan", 0) + 1
        self.metrics.inc_operation("design_drill_plan")
        return {
            "feature": "design_drill_plan",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Backup Recovery Drill"},
            "message": "design_drill_plan completed",
        }

    async def run_database_backup_drill(self, request: Any = None) -> Dict[str, Any]:
        """Run Database Backup Drill."""
        self.metrics.inc_request("run_database_backup_drill")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_database_backup_drill", config)
        self._state["run_database_backup_drill"] = config
        self._operations["run_database_backup_drill"] = (
            self._operations.get("run_database_backup_drill", 0) + 1
        )
        self.metrics.inc_operation("run_database_backup_drill")
        return {
            "feature": "run_database_backup_drill",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Backup Recovery Drill"},
            "message": "run_database_backup_drill completed",
        }

    async def run_config_backup_drill(self, request: Any = None) -> Dict[str, Any]:
        """Run Config Backup Drill."""
        self.metrics.inc_request("run_config_backup_drill")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_config_backup_drill", config)
        self._state["run_config_backup_drill"] = config
        self._operations["run_config_backup_drill"] = (
            self._operations.get("run_config_backup_drill", 0) + 1
        )
        self.metrics.inc_operation("run_config_backup_drill")
        return {
            "feature": "run_config_backup_drill",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Backup Recovery Drill"},
            "message": "run_config_backup_drill completed",
        }

    async def run_log_backup_drill(self, request: Any = None) -> Dict[str, Any]:
        """Run Log Backup Drill."""
        self.metrics.inc_request("run_log_backup_drill")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_log_backup_drill", config)
        self._state["run_log_backup_drill"] = config
        self._operations["run_log_backup_drill"] = (
            self._operations.get("run_log_backup_drill", 0) + 1
        )
        self.metrics.inc_operation("run_log_backup_drill")
        return {
            "feature": "run_log_backup_drill",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Backup Recovery Drill"},
            "message": "run_log_backup_drill completed",
        }

    async def write_drill_report(self, request: Any = None) -> Dict[str, Any]:
        """Write Drill Report."""
        self.metrics.inc_request("write_drill_report")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_drill_report", config)
        self._state["write_drill_report"] = config
        self._operations["write_drill_report"] = self._operations.get("write_drill_report", 0) + 1
        self.metrics.inc_operation("write_drill_report")
        return {
            "feature": "write_drill_report",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Backup Recovery Drill"},
            "message": "write_drill_report completed",
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


Service = BackupRecoveryDrillService
