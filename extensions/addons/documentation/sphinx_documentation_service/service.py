# -*- coding: utf-8 -*-
"""Core service logic for the Sphinx Documentation microservice."""

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
    "configure_sphinx",
    "write_api_docs",
    "write_architecture_docs",
    "write_user_manual",
    "write_developer_guide",
    "configure_readthedocs_theme",
    "implement_doc_search",
    "implement_doc_versioning",
    "deploy_doc_site",
    "test_and_optimize_sphinx",
]


class SphinxDocumentationService:
    """Domain service for Sphinx Documentation."""

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

    async def configure_sphinx(self, request: Any = None) -> Dict[str, Any]:
        """Configure Sphinx."""
        self.metrics.inc_request("configure_sphinx")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_sphinx", config)
        self._state["configure_sphinx"] = config
        self._operations["configure_sphinx"] = self._operations.get("configure_sphinx", 0) + 1
        self.metrics.inc_operation("configure_sphinx")
        return {
            "feature": "configure_sphinx",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "configure_sphinx completed",
        }

    async def write_api_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write Api Docs."""
        self.metrics.inc_request("write_api_docs")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_api_docs", config)
        self._state["write_api_docs"] = config
        self._operations["write_api_docs"] = self._operations.get("write_api_docs", 0) + 1
        self.metrics.inc_operation("write_api_docs")
        return {
            "feature": "write_api_docs",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "write_api_docs completed",
        }

    async def write_architecture_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write Architecture Docs."""
        self.metrics.inc_request("write_architecture_docs")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_architecture_docs", config)
        self._state["write_architecture_docs"] = config
        self._operations["write_architecture_docs"] = (
            self._operations.get("write_architecture_docs", 0) + 1
        )
        self.metrics.inc_operation("write_architecture_docs")
        return {
            "feature": "write_architecture_docs",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "write_architecture_docs completed",
        }

    async def write_user_manual(self, request: Any = None) -> Dict[str, Any]:
        """Write User Manual."""
        self.metrics.inc_request("write_user_manual")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_user_manual", config)
        self._state["write_user_manual"] = config
        self._operations["write_user_manual"] = self._operations.get("write_user_manual", 0) + 1
        self.metrics.inc_operation("write_user_manual")
        return {
            "feature": "write_user_manual",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "write_user_manual completed",
        }

    async def write_developer_guide(self, request: Any = None) -> Dict[str, Any]:
        """Write Developer Guide."""
        self.metrics.inc_request("write_developer_guide")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_developer_guide", config)
        self._state["write_developer_guide"] = config
        self._operations["write_developer_guide"] = (
            self._operations.get("write_developer_guide", 0) + 1
        )
        self.metrics.inc_operation("write_developer_guide")
        return {
            "feature": "write_developer_guide",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "write_developer_guide completed",
        }

    async def configure_readthedocs_theme(self, request: Any = None) -> Dict[str, Any]:
        """Configure Readthedocs Theme."""
        self.metrics.inc_request("configure_readthedocs_theme")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_readthedocs_theme", config)
        self._state["configure_readthedocs_theme"] = config
        self._operations["configure_readthedocs_theme"] = (
            self._operations.get("configure_readthedocs_theme", 0) + 1
        )
        self.metrics.inc_operation("configure_readthedocs_theme")
        return {
            "feature": "configure_readthedocs_theme",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "configure_readthedocs_theme completed",
        }

    async def implement_doc_search(self, request: Any = None) -> Dict[str, Any]:
        """Implement Doc Search."""
        self.metrics.inc_request("implement_doc_search")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:implement_doc_search", config)
        self._state["implement_doc_search"] = config
        self._operations["implement_doc_search"] = (
            self._operations.get("implement_doc_search", 0) + 1
        )
        self.metrics.inc_operation("implement_doc_search")
        return {
            "feature": "implement_doc_search",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "implement_doc_search completed",
        }

    async def implement_doc_versioning(self, request: Any = None) -> Dict[str, Any]:
        """Implement Doc Versioning."""
        self.metrics.inc_request("implement_doc_versioning")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:implement_doc_versioning", config)
        self._state["implement_doc_versioning"] = config
        self._operations["implement_doc_versioning"] = (
            self._operations.get("implement_doc_versioning", 0) + 1
        )
        self.metrics.inc_operation("implement_doc_versioning")
        return {
            "feature": "implement_doc_versioning",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "implement_doc_versioning completed",
        }

    async def deploy_doc_site(self, request: Any = None) -> Dict[str, Any]:
        """Deploy Doc Site."""
        self.metrics.inc_request("deploy_doc_site")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:deploy_doc_site", config)
        self._state["deploy_doc_site"] = config
        self._operations["deploy_doc_site"] = self._operations.get("deploy_doc_site", 0) + 1
        self.metrics.inc_operation("deploy_doc_site")
        return {
            "feature": "deploy_doc_site",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "deploy_doc_site completed",
        }

    async def test_and_optimize_sphinx(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Sphinx."""
        self.metrics.inc_request("test_and_optimize_sphinx")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_sphinx", config)
        self._state["test_and_optimize_sphinx"] = config
        self._operations["test_and_optimize_sphinx"] = (
            self._operations.get("test_and_optimize_sphinx", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_sphinx")
        return {
            "feature": "test_and_optimize_sphinx",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Sphinx Documentation"},
            "message": "test_and_optimize_sphinx completed",
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


Service = SphinxDocumentationService
