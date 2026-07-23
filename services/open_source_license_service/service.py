# -*- coding: utf-8 -*-
"""Core service logic for the Open Source License microservice."""

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
    "select_osi_license",
    "add_license_file",
    "add_source_headers",
    "write_license_usage_docs",
    "configure_dependency_license_check",
    "generate_license_inventory",
    "write_compliance_docs",
    "review_license_compliance",
    "handle_license_changes",
    "test_and_optimize_licenses",
]


class OpenSourceLicenseService:
    """Domain service for Open Source License."""

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

    async def select_osi_license(self, request: Any = None) -> Dict[str, Any]:
        """Select Osi License."""
        self.metrics.inc_request("select_osi_license")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:select_osi_license", config)
        self._state["select_osi_license"] = config
        self._operations["select_osi_license"] = self._operations.get("select_osi_license", 0) + 1
        self.metrics.inc_operation("select_osi_license")
        return {
            "feature": "select_osi_license",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "select_osi_license completed",
        }

    async def add_license_file(self, request: Any = None) -> Dict[str, Any]:
        """Add License File."""
        self.metrics.inc_request("add_license_file")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:add_license_file", config)
        self._state["add_license_file"] = config
        self._operations["add_license_file"] = self._operations.get("add_license_file", 0) + 1
        self.metrics.inc_operation("add_license_file")
        return {
            "feature": "add_license_file",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "add_license_file completed",
        }

    async def add_source_headers(self, request: Any = None) -> Dict[str, Any]:
        """Add Source Headers."""
        self.metrics.inc_request("add_source_headers")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:add_source_headers", config)
        self._state["add_source_headers"] = config
        self._operations["add_source_headers"] = self._operations.get("add_source_headers", 0) + 1
        self.metrics.inc_operation("add_source_headers")
        return {
            "feature": "add_source_headers",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "add_source_headers completed",
        }

    async def write_license_usage_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write License Usage Docs."""
        self.metrics.inc_request("write_license_usage_docs")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_license_usage_docs", config)
        self._state["write_license_usage_docs"] = config
        self._operations["write_license_usage_docs"] = (
            self._operations.get("write_license_usage_docs", 0) + 1
        )
        self.metrics.inc_operation("write_license_usage_docs")
        return {
            "feature": "write_license_usage_docs",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "write_license_usage_docs completed",
        }

    async def configure_dependency_license_check(self, request: Any = None) -> Dict[str, Any]:
        """Configure Dependency License Check."""
        self.metrics.inc_request("configure_dependency_license_check")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_dependency_license_check", config)
        self._state["configure_dependency_license_check"] = config
        self._operations["configure_dependency_license_check"] = (
            self._operations.get("configure_dependency_license_check", 0) + 1
        )
        self.metrics.inc_operation("configure_dependency_license_check")
        return {
            "feature": "configure_dependency_license_check",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "configure_dependency_license_check completed",
        }

    async def generate_license_inventory(self, request: Any = None) -> Dict[str, Any]:
        """Generate License Inventory."""
        self.metrics.inc_request("generate_license_inventory")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:generate_license_inventory", config)
        self._state["generate_license_inventory"] = config
        self._operations["generate_license_inventory"] = (
            self._operations.get("generate_license_inventory", 0) + 1
        )
        self.metrics.inc_operation("generate_license_inventory")
        return {
            "feature": "generate_license_inventory",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "generate_license_inventory completed",
        }

    async def write_compliance_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write Compliance Docs."""
        self.metrics.inc_request("write_compliance_docs")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_compliance_docs", config)
        self._state["write_compliance_docs"] = config
        self._operations["write_compliance_docs"] = (
            self._operations.get("write_compliance_docs", 0) + 1
        )
        self.metrics.inc_operation("write_compliance_docs")
        return {
            "feature": "write_compliance_docs",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "write_compliance_docs completed",
        }

    async def review_license_compliance(self, request: Any = None) -> Dict[str, Any]:
        """Review License Compliance."""
        self.metrics.inc_request("review_license_compliance")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:review_license_compliance", config)
        self._state["review_license_compliance"] = config
        self._operations["review_license_compliance"] = (
            self._operations.get("review_license_compliance", 0) + 1
        )
        self.metrics.inc_operation("review_license_compliance")
        return {
            "feature": "review_license_compliance",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "review_license_compliance completed",
        }

    async def handle_license_changes(self, request: Any = None) -> Dict[str, Any]:
        """Handle License Changes."""
        self.metrics.inc_request("handle_license_changes")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:handle_license_changes", config)
        self._state["handle_license_changes"] = config
        self._operations["handle_license_changes"] = (
            self._operations.get("handle_license_changes", 0) + 1
        )
        self.metrics.inc_operation("handle_license_changes")
        return {
            "feature": "handle_license_changes",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "handle_license_changes completed",
        }

    async def test_and_optimize_licenses(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Licenses."""
        self.metrics.inc_request("test_and_optimize_licenses")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_licenses", config)
        self._state["test_and_optimize_licenses"] = config
        self._operations["test_and_optimize_licenses"] = (
            self._operations.get("test_and_optimize_licenses", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_licenses")
        return {
            "feature": "test_and_optimize_licenses",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Open Source License"},
            "message": "test_and_optimize_licenses completed",
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


Service = OpenSourceLicenseService
