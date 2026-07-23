# -*- coding: utf-8 -*-
"""Core service logic for the Security Scanning microservice."""

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
    "run_sast_sonarqube",
    "run_dast_zap",
    "run_dependency_snyk",
    "run_container_trivy",
    "manage_vulnerabilities",
    "generate_scan_reports",
    "check_compliance",
    "generate_fix_suggestions",
    "schedule_security_scans",
    "test_and_optimize_security_scanning",
]


class SecurityScanningService:
    """Domain service for Security Scanning."""

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

    async def run_sast_sonarqube(self, request: Any = None) -> Dict[str, Any]:
        """Run Sast Sonarqube."""
        self.metrics.inc_request("run_sast_sonarqube")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_sast_sonarqube", config)
        self._state["run_sast_sonarqube"] = config
        self._operations["run_sast_sonarqube"] = self._operations.get("run_sast_sonarqube", 0) + 1
        self.metrics.inc_operation("run_sast_sonarqube")
        return {
            "feature": "run_sast_sonarqube",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "run_sast_sonarqube completed",
        }

    async def run_dast_zap(self, request: Any = None) -> Dict[str, Any]:
        """Run Dast Zap."""
        self.metrics.inc_request("run_dast_zap")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_dast_zap", config)
        self._state["run_dast_zap"] = config
        self._operations["run_dast_zap"] = self._operations.get("run_dast_zap", 0) + 1
        self.metrics.inc_operation("run_dast_zap")
        return {
            "feature": "run_dast_zap",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "run_dast_zap completed",
        }

    async def run_dependency_snyk(self, request: Any = None) -> Dict[str, Any]:
        """Run Dependency Snyk."""
        self.metrics.inc_request("run_dependency_snyk")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_dependency_snyk", config)
        self._state["run_dependency_snyk"] = config
        self._operations["run_dependency_snyk"] = self._operations.get("run_dependency_snyk", 0) + 1
        self.metrics.inc_operation("run_dependency_snyk")
        return {
            "feature": "run_dependency_snyk",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "run_dependency_snyk completed",
        }

    async def run_container_trivy(self, request: Any = None) -> Dict[str, Any]:
        """Run Container Trivy."""
        self.metrics.inc_request("run_container_trivy")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_container_trivy", config)
        self._state["run_container_trivy"] = config
        self._operations["run_container_trivy"] = self._operations.get("run_container_trivy", 0) + 1
        self.metrics.inc_operation("run_container_trivy")
        return {
            "feature": "run_container_trivy",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "run_container_trivy completed",
        }

    async def manage_vulnerabilities(self, request: Any = None) -> Dict[str, Any]:
        """Manage Vulnerabilities."""
        self.metrics.inc_request("manage_vulnerabilities")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:manage_vulnerabilities", config)
        self._state["manage_vulnerabilities"] = config
        self._operations["manage_vulnerabilities"] = (
            self._operations.get("manage_vulnerabilities", 0) + 1
        )
        self.metrics.inc_operation("manage_vulnerabilities")
        return {
            "feature": "manage_vulnerabilities",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "manage_vulnerabilities completed",
        }

    async def generate_scan_reports(self, request: Any = None) -> Dict[str, Any]:
        """Generate Scan Reports."""
        self.metrics.inc_request("generate_scan_reports")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:generate_scan_reports", config)
        self._state["generate_scan_reports"] = config
        self._operations["generate_scan_reports"] = (
            self._operations.get("generate_scan_reports", 0) + 1
        )
        self.metrics.inc_operation("generate_scan_reports")
        return {
            "feature": "generate_scan_reports",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "generate_scan_reports completed",
        }

    async def check_compliance(self, request: Any = None) -> Dict[str, Any]:
        """Check Compliance."""
        self.metrics.inc_request("check_compliance")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:check_compliance", config)
        self._state["check_compliance"] = config
        self._operations["check_compliance"] = self._operations.get("check_compliance", 0) + 1
        self.metrics.inc_operation("check_compliance")
        return {
            "feature": "check_compliance",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "check_compliance completed",
        }

    async def generate_fix_suggestions(self, request: Any = None) -> Dict[str, Any]:
        """Generate Fix Suggestions."""
        self.metrics.inc_request("generate_fix_suggestions")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:generate_fix_suggestions", config)
        self._state["generate_fix_suggestions"] = config
        self._operations["generate_fix_suggestions"] = (
            self._operations.get("generate_fix_suggestions", 0) + 1
        )
        self.metrics.inc_operation("generate_fix_suggestions")
        return {
            "feature": "generate_fix_suggestions",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "generate_fix_suggestions completed",
        }

    async def schedule_security_scans(self, request: Any = None) -> Dict[str, Any]:
        """Schedule Security Scans."""
        self.metrics.inc_request("schedule_security_scans")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:schedule_security_scans", config)
        self._state["schedule_security_scans"] = config
        self._operations["schedule_security_scans"] = (
            self._operations.get("schedule_security_scans", 0) + 1
        )
        self.metrics.inc_operation("schedule_security_scans")
        return {
            "feature": "schedule_security_scans",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "schedule_security_scans completed",
        }

    async def test_and_optimize_security_scanning(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Security Scanning."""
        self.metrics.inc_request("test_and_optimize_security_scanning")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_security_scanning", config)
        self._state["test_and_optimize_security_scanning"] = config
        self._operations["test_and_optimize_security_scanning"] = (
            self._operations.get("test_and_optimize_security_scanning", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_security_scanning")
        return {
            "feature": "test_and_optimize_security_scanning",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Security Scanning"},
            "message": "test_and_optimize_security_scanning completed",
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


Service = SecurityScanningService
