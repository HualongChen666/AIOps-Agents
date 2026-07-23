# -*- coding: utf-8 -*-
"""Core service logic for the FastAPI Security microservice."""

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
    "oauth2_password_auth",
    "jwt_token_auth",
    "api_key_auth",
    "dependency_injection",
    "cors_configuration",
    "security_headers",
    "https_enforcement",
    "rate_limiting",
    "integrate_api_gateway",
    "test_and_optimize_fastapi_security",
]


class FastAPISecurityService:
    """Domain service for FastAPI Security."""

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

    async def oauth2_password_auth(self, request: Any = None) -> Dict[str, Any]:
        """Oauth2 Password Auth."""
        self.metrics.inc_request("oauth2_password_auth")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:oauth2_password_auth", config)
        self._state["oauth2_password_auth"] = config
        self._operations["oauth2_password_auth"] = (
            self._operations.get("oauth2_password_auth", 0) + 1
        )
        self.metrics.inc_operation("oauth2_password_auth")
        return {
            "feature": "oauth2_password_auth",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "oauth2_password_auth completed",
        }

    async def jwt_token_auth(self, request: Any = None) -> Dict[str, Any]:
        """Jwt Token Auth."""
        self.metrics.inc_request("jwt_token_auth")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:jwt_token_auth", config)
        self._state["jwt_token_auth"] = config
        self._operations["jwt_token_auth"] = self._operations.get("jwt_token_auth", 0) + 1
        self.metrics.inc_operation("jwt_token_auth")
        return {
            "feature": "jwt_token_auth",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "jwt_token_auth completed",
        }

    async def api_key_auth(self, request: Any = None) -> Dict[str, Any]:
        """Api Key Auth."""
        self.metrics.inc_request("api_key_auth")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:api_key_auth", config)
        self._state["api_key_auth"] = config
        self._operations["api_key_auth"] = self._operations.get("api_key_auth", 0) + 1
        self.metrics.inc_operation("api_key_auth")
        return {
            "feature": "api_key_auth",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "api_key_auth completed",
        }

    async def dependency_injection(self, request: Any = None) -> Dict[str, Any]:
        """Dependency Injection."""
        self.metrics.inc_request("dependency_injection")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:dependency_injection", config)
        self._state["dependency_injection"] = config
        self._operations["dependency_injection"] = (
            self._operations.get("dependency_injection", 0) + 1
        )
        self.metrics.inc_operation("dependency_injection")
        return {
            "feature": "dependency_injection",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "dependency_injection completed",
        }

    async def cors_configuration(self, request: Any = None) -> Dict[str, Any]:
        """Cors Configuration."""
        self.metrics.inc_request("cors_configuration")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:cors_configuration", config)
        self._state["cors_configuration"] = config
        self._operations["cors_configuration"] = self._operations.get("cors_configuration", 0) + 1
        self.metrics.inc_operation("cors_configuration")
        return {
            "feature": "cors_configuration",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "cors_configuration completed",
        }

    async def security_headers(self, request: Any = None) -> Dict[str, Any]:
        """Security Headers."""
        self.metrics.inc_request("security_headers")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:security_headers", config)
        self._state["security_headers"] = config
        self._operations["security_headers"] = self._operations.get("security_headers", 0) + 1
        self.metrics.inc_operation("security_headers")
        return {
            "feature": "security_headers",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "security_headers completed",
        }

    async def https_enforcement(self, request: Any = None) -> Dict[str, Any]:
        """Https Enforcement."""
        self.metrics.inc_request("https_enforcement")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:https_enforcement", config)
        self._state["https_enforcement"] = config
        self._operations["https_enforcement"] = self._operations.get("https_enforcement", 0) + 1
        self.metrics.inc_operation("https_enforcement")
        return {
            "feature": "https_enforcement",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "https_enforcement completed",
        }

    async def rate_limiting(self, request: Any = None) -> Dict[str, Any]:
        """Rate Limiting."""
        self.metrics.inc_request("rate_limiting")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:rate_limiting", config)
        self._state["rate_limiting"] = config
        self._operations["rate_limiting"] = self._operations.get("rate_limiting", 0) + 1
        self.metrics.inc_operation("rate_limiting")
        return {
            "feature": "rate_limiting",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "rate_limiting completed",
        }

    async def integrate_api_gateway(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Api Gateway."""
        self.metrics.inc_request("integrate_api_gateway")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:integrate_api_gateway", config)
        self._state["integrate_api_gateway"] = config
        self._operations["integrate_api_gateway"] = (
            self._operations.get("integrate_api_gateway", 0) + 1
        )
        self.metrics.inc_operation("integrate_api_gateway")
        return {
            "feature": "integrate_api_gateway",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "integrate_api_gateway completed",
        }

    async def test_and_optimize_fastapi_security(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Fastapi Security."""
        self.metrics.inc_request("test_and_optimize_fastapi_security")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_fastapi_security", config)
        self._state["test_and_optimize_fastapi_security"] = config
        self._operations["test_and_optimize_fastapi_security"] = (
            self._operations.get("test_and_optimize_fastapi_security", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_fastapi_security")
        return {
            "feature": "test_and_optimize_fastapi_security",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "FastAPI Security"},
            "message": "test_and_optimize_fastapi_security completed",
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


Service = FastAPISecurityService
