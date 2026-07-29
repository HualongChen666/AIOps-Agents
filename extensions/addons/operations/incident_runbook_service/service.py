# -*- coding: utf-8 -*-
"""Core service logic for the Incident Runbook microservice."""

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
    "incident_handbook",
    "diagnosis_process",
    "recovery_process",
    "preventive_measures",
    "training_materials",
]


class IncidentRunbookService:
    """Domain service for Incident Runbook."""

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

    async def incident_handbook(self, request: Any = None) -> Dict[str, Any]:
        """Incident Handbook."""
        self.metrics.inc_request("incident_handbook")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:incident_handbook", config)
        self._state["incident_handbook"] = config
        self._operations["incident_handbook"] = self._operations.get("incident_handbook", 0) + 1
        self.metrics.inc_operation("incident_handbook")
        return {
            "feature": "incident_handbook",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Incident Runbook"},
            "message": "incident_handbook completed",
        }

    async def diagnosis_process(self, request: Any = None) -> Dict[str, Any]:
        """Diagnosis Process."""
        self.metrics.inc_request("diagnosis_process")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:diagnosis_process", config)
        self._state["diagnosis_process"] = config
        self._operations["diagnosis_process"] = self._operations.get("diagnosis_process", 0) + 1
        self.metrics.inc_operation("diagnosis_process")
        return {
            "feature": "diagnosis_process",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Incident Runbook"},
            "message": "diagnosis_process completed",
        }

    async def recovery_process(self, request: Any = None) -> Dict[str, Any]:
        """Recovery Process."""
        self.metrics.inc_request("recovery_process")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:recovery_process", config)
        self._state["recovery_process"] = config
        self._operations["recovery_process"] = self._operations.get("recovery_process", 0) + 1
        self.metrics.inc_operation("recovery_process")
        return {
            "feature": "recovery_process",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Incident Runbook"},
            "message": "recovery_process completed",
        }

    async def preventive_measures(self, request: Any = None) -> Dict[str, Any]:
        """Preventive Measures."""
        self.metrics.inc_request("preventive_measures")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:preventive_measures", config)
        self._state["preventive_measures"] = config
        self._operations["preventive_measures"] = self._operations.get("preventive_measures", 0) + 1
        self.metrics.inc_operation("preventive_measures")
        return {
            "feature": "preventive_measures",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Incident Runbook"},
            "message": "preventive_measures completed",
        }

    async def training_materials(self, request: Any = None) -> Dict[str, Any]:
        """Training Materials."""
        self.metrics.inc_request("training_materials")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:training_materials", config)
        self._state["training_materials"] = config
        self._operations["training_materials"] = self._operations.get("training_materials", 0) + 1
        self.metrics.inc_operation("training_materials")
        return {
            "feature": "training_materials",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Incident Runbook"},
            "message": "training_materials completed",
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


Service = IncidentRunbookService
