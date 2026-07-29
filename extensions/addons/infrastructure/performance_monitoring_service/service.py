# -*- coding: utf-8 -*-
"""Core service logic for the Performance Monitoring microservice."""

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
    "design_apm_framework",
    "integrate_skywalking",
    "collect_performance_metrics",
    "analyze_performance",
    "identify_bottlenecks",
    "generate_optimization_suggestions",
    "run_benchmark_tests",
    "detect_regressions",
    "write_performance_reports",
    "test_and_optimize_performance_monitoring",
]


class PerformanceMonitoringService:
    """Domain service for Performance Monitoring."""

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

    async def design_apm_framework(self, request: Any = None) -> Dict[str, Any]:
        """Design Apm Framework."""
        self.metrics.inc_request("design_apm_framework")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:design_apm_framework", config)
        self._state["design_apm_framework"] = config
        self._operations["design_apm_framework"] = (
            self._operations.get("design_apm_framework", 0) + 1
        )
        self.metrics.inc_operation("design_apm_framework")
        return {
            "feature": "design_apm_framework",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "design_apm_framework completed",
        }

    async def integrate_skywalking(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Skywalking."""
        self.metrics.inc_request("integrate_skywalking")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:integrate_skywalking", config)
        self._state["integrate_skywalking"] = config
        self._operations["integrate_skywalking"] = (
            self._operations.get("integrate_skywalking", 0) + 1
        )
        self.metrics.inc_operation("integrate_skywalking")
        return {
            "feature": "integrate_skywalking",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "integrate_skywalking completed",
        }

    async def collect_performance_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Collect Performance Metrics."""
        self.metrics.inc_request("collect_performance_metrics")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:collect_performance_metrics", config)
        self._state["collect_performance_metrics"] = config
        self._operations["collect_performance_metrics"] = (
            self._operations.get("collect_performance_metrics", 0) + 1
        )
        self.metrics.inc_operation("collect_performance_metrics")
        return {
            "feature": "collect_performance_metrics",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "collect_performance_metrics completed",
        }

    async def analyze_performance(self, request: Any = None) -> Dict[str, Any]:
        """Analyze Performance."""
        self.metrics.inc_request("analyze_performance")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:analyze_performance", config)
        self._state["analyze_performance"] = config
        self._operations["analyze_performance"] = self._operations.get("analyze_performance", 0) + 1
        self.metrics.inc_operation("analyze_performance")
        return {
            "feature": "analyze_performance",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "analyze_performance completed",
        }

    async def identify_bottlenecks(self, request: Any = None) -> Dict[str, Any]:
        """Identify Bottlenecks."""
        self.metrics.inc_request("identify_bottlenecks")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:identify_bottlenecks", config)
        self._state["identify_bottlenecks"] = config
        self._operations["identify_bottlenecks"] = (
            self._operations.get("identify_bottlenecks", 0) + 1
        )
        self.metrics.inc_operation("identify_bottlenecks")
        return {
            "feature": "identify_bottlenecks",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "identify_bottlenecks completed",
        }

    async def generate_optimization_suggestions(self, request: Any = None) -> Dict[str, Any]:
        """Generate Optimization Suggestions."""
        self.metrics.inc_request("generate_optimization_suggestions")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:generate_optimization_suggestions", config)
        self._state["generate_optimization_suggestions"] = config
        self._operations["generate_optimization_suggestions"] = (
            self._operations.get("generate_optimization_suggestions", 0) + 1
        )
        self.metrics.inc_operation("generate_optimization_suggestions")
        return {
            "feature": "generate_optimization_suggestions",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "generate_optimization_suggestions completed",
        }

    async def run_benchmark_tests(self, request: Any = None) -> Dict[str, Any]:
        """Run Benchmark Tests."""
        self.metrics.inc_request("run_benchmark_tests")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:run_benchmark_tests", config)
        self._state["run_benchmark_tests"] = config
        self._operations["run_benchmark_tests"] = self._operations.get("run_benchmark_tests", 0) + 1
        self.metrics.inc_operation("run_benchmark_tests")
        return {
            "feature": "run_benchmark_tests",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "run_benchmark_tests completed",
        }

    async def detect_regressions(self, request: Any = None) -> Dict[str, Any]:
        """Detect Regressions."""
        self.metrics.inc_request("detect_regressions")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:detect_regressions", config)
        self._state["detect_regressions"] = config
        self._operations["detect_regressions"] = self._operations.get("detect_regressions", 0) + 1
        self.metrics.inc_operation("detect_regressions")
        return {
            "feature": "detect_regressions",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "detect_regressions completed",
        }

    async def write_performance_reports(self, request: Any = None) -> Dict[str, Any]:
        """Write Performance Reports."""
        self.metrics.inc_request("write_performance_reports")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_performance_reports", config)
        self._state["write_performance_reports"] = config
        self._operations["write_performance_reports"] = (
            self._operations.get("write_performance_reports", 0) + 1
        )
        self.metrics.inc_operation("write_performance_reports")
        return {
            "feature": "write_performance_reports",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "write_performance_reports completed",
        }

    async def test_and_optimize_performance_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Performance Monitoring."""
        self.metrics.inc_request("test_and_optimize_performance_monitoring")
        config = self._get_config(request)
        await self.cache.set(
            f"{settings.service_name}:test_and_optimize_performance_monitoring", config
        )
        self._state["test_and_optimize_performance_monitoring"] = config
        self._operations["test_and_optimize_performance_monitoring"] = (
            self._operations.get("test_and_optimize_performance_monitoring", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_performance_monitoring")
        return {
            "feature": "test_and_optimize_performance_monitoring",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Performance Monitoring"},
            "message": "test_and_optimize_performance_monitoring completed",
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


Service = PerformanceMonitoringService
