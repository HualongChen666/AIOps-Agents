# -*- coding: utf-8 -*-
"""Core service logic for the Cloud Monitoring microservice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .config import settings
from .lock import IdempotencyManager, LockManager
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
    "integrate_aws_cloudwatch",
    "integrate_azure_monitor",
    "integrate_gcp_cloud_monitoring",
    "integrate_aliyun_monitoring",
    "integrate_tencent_cloud_monitoring",
    "unify_metric_collection",
    "unify_log_collection",
    "unify_alert_processing",
    "integrate_cloud_platform",
    "test_and_optimize_cloud_monitoring",
]


class CloudMonitoringService:
    """Domain service for Cloud Monitoring."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector(settings.service_name)
        self.cache = cache or CacheManager(redis_url or settings.redis_url, self.metrics)
        self.retry_engine = RetryEngine("exponential_fast", self.metrics)
        self.lock_manager = LockManager(redis_url or settings.redis_url)
        self.idempotency = IdempotencyManager(self.cache)
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
        request_id = self.idempotency.get_key(request, "backup_state")
        async with self.lock_manager.acquire("backup_state", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "backup_state",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "snapshot": (
                            config.get("name", "default") if isinstance(config, dict) else "default"
                        )
                    },
                    "message": "backup_state already processed",
                }
            name = config.get("name", "default") if isinstance(config, dict) else "default"
            self._backups[name] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "state": self._state.copy(),
            }
            self.metrics.inc_operation("backup_state")
            result = {
                "feature": "backup_state",
                "success": True,
                "status": "backed_up",
                "config": {"name": name},
                "result": {"snapshot": name},
                "message": f"Backup {name} created",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("restore_state")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "restore_state")
        async with self.lock_manager.acquire("restore_state", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "restore_state",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "snapshot": (
                            config.get("name", "default") if isinstance(config, dict) else "default"
                        )
                    },
                    "message": "restore_state already processed",
                }
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
            result = {
                "feature": "restore_state",
                "success": True,
                "status": "restored",
                "config": {"name": name},
                "result": {"snapshot": name},
                "message": f"Backup {name} restored",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

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

    async def integrate_aws_cloudwatch(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Aws Cloudwatch."""
        self.metrics.inc_request("integrate_aws_cloudwatch")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_aws_cloudwatch")
        async with self.lock_manager.acquire("integrate_aws_cloudwatch", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_aws_cloudwatch",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "integrate_aws_cloudwatch already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_aws_cloudwatch", config)
            self._state["integrate_aws_cloudwatch"] = config
            self._operations["integrate_aws_cloudwatch"] = (
                self._operations.get("integrate_aws_cloudwatch", 0) + 1
            )
            self.metrics.inc_operation("integrate_aws_cloudwatch")
            result = {
                "feature": "integrate_aws_cloudwatch",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "integrate_aws_cloudwatch completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_azure_monitor(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Azure Monitor."""
        self.metrics.inc_request("integrate_azure_monitor")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_azure_monitor")
        async with self.lock_manager.acquire("integrate_azure_monitor", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_azure_monitor",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "integrate_azure_monitor already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_azure_monitor", config)
            self._state["integrate_azure_monitor"] = config
            self._operations["integrate_azure_monitor"] = (
                self._operations.get("integrate_azure_monitor", 0) + 1
            )
            self.metrics.inc_operation("integrate_azure_monitor")
            result = {
                "feature": "integrate_azure_monitor",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "integrate_azure_monitor completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_gcp_cloud_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Gcp Cloud Monitoring."""
        self.metrics.inc_request("integrate_gcp_cloud_monitoring")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_gcp_cloud_monitoring")
        async with self.lock_manager.acquire("integrate_gcp_cloud_monitoring", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_gcp_cloud_monitoring",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "integrate_gcp_cloud_monitoring already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_gcp_cloud_monitoring", config)
            self._state["integrate_gcp_cloud_monitoring"] = config
            self._operations["integrate_gcp_cloud_monitoring"] = (
                self._operations.get("integrate_gcp_cloud_monitoring", 0) + 1
            )
            self.metrics.inc_operation("integrate_gcp_cloud_monitoring")
            result = {
                "feature": "integrate_gcp_cloud_monitoring",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "integrate_gcp_cloud_monitoring completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_aliyun_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Aliyun Monitoring."""
        self.metrics.inc_request("integrate_aliyun_monitoring")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_aliyun_monitoring")
        async with self.lock_manager.acquire("integrate_aliyun_monitoring", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_aliyun_monitoring",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "integrate_aliyun_monitoring already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_aliyun_monitoring", config)
            self._state["integrate_aliyun_monitoring"] = config
            self._operations["integrate_aliyun_monitoring"] = (
                self._operations.get("integrate_aliyun_monitoring", 0) + 1
            )
            self.metrics.inc_operation("integrate_aliyun_monitoring")
            result = {
                "feature": "integrate_aliyun_monitoring",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "integrate_aliyun_monitoring completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_tencent_cloud_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Tencent Cloud Monitoring."""
        self.metrics.inc_request("integrate_tencent_cloud_monitoring")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_tencent_cloud_monitoring")
        async with self.lock_manager.acquire("integrate_tencent_cloud_monitoring", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_tencent_cloud_monitoring",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "integrate_tencent_cloud_monitoring already processed",
                }
            await self.cache.set(
                f"{settings.service_name}:integrate_tencent_cloud_monitoring", config
            )
            self._state["integrate_tencent_cloud_monitoring"] = config
            self._operations["integrate_tencent_cloud_monitoring"] = (
                self._operations.get("integrate_tencent_cloud_monitoring", 0) + 1
            )
            self.metrics.inc_operation("integrate_tencent_cloud_monitoring")
            result = {
                "feature": "integrate_tencent_cloud_monitoring",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "integrate_tencent_cloud_monitoring completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def unify_metric_collection(self, request: Any = None) -> Dict[str, Any]:
        """Unify Metric Collection."""
        self.metrics.inc_request("unify_metric_collection")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "unify_metric_collection")
        async with self.lock_manager.acquire("unify_metric_collection", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "unify_metric_collection",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "unify_metric_collection already processed",
                }
            await self.cache.set(f"{settings.service_name}:unify_metric_collection", config)
            self._state["unify_metric_collection"] = config
            self._operations["unify_metric_collection"] = (
                self._operations.get("unify_metric_collection", 0) + 1
            )
            self.metrics.inc_operation("unify_metric_collection")
            result = {
                "feature": "unify_metric_collection",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "unify_metric_collection completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def unify_log_collection(self, request: Any = None) -> Dict[str, Any]:
        """Unify Log Collection."""
        self.metrics.inc_request("unify_log_collection")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "unify_log_collection")
        async with self.lock_manager.acquire("unify_log_collection", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "unify_log_collection",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "unify_log_collection already processed",
                }
            await self.cache.set(f"{settings.service_name}:unify_log_collection", config)
            self._state["unify_log_collection"] = config
            self._operations["unify_log_collection"] = (
                self._operations.get("unify_log_collection", 0) + 1
            )
            self.metrics.inc_operation("unify_log_collection")
            result = {
                "feature": "unify_log_collection",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "unify_log_collection completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def unify_alert_processing(self, request: Any = None) -> Dict[str, Any]:
        """Unify Alert Processing."""
        self.metrics.inc_request("unify_alert_processing")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "unify_alert_processing")
        async with self.lock_manager.acquire("unify_alert_processing", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "unify_alert_processing",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "unify_alert_processing already processed",
                }
            await self.cache.set(f"{settings.service_name}:unify_alert_processing", config)
            self._state["unify_alert_processing"] = config
            self._operations["unify_alert_processing"] = (
                self._operations.get("unify_alert_processing", 0) + 1
            )
            self.metrics.inc_operation("unify_alert_processing")
            result = {
                "feature": "unify_alert_processing",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "unify_alert_processing completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_cloud_platform(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Cloud Platform."""
        self.metrics.inc_request("integrate_cloud_platform")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_cloud_platform")
        async with self.lock_manager.acquire("integrate_cloud_platform", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_cloud_platform",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "integrate_cloud_platform already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_cloud_platform", config)
            self._state["integrate_cloud_platform"] = config
            self._operations["integrate_cloud_platform"] = (
                self._operations.get("integrate_cloud_platform", 0) + 1
            )
            self.metrics.inc_operation("integrate_cloud_platform")
            result = {
                "feature": "integrate_cloud_platform",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "integrate_cloud_platform completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def test_and_optimize_cloud_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Cloud Monitoring."""
        self.metrics.inc_request("test_and_optimize_cloud_monitoring")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "test_and_optimize_cloud_monitoring")
        async with self.lock_manager.acquire("test_and_optimize_cloud_monitoring", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "test_and_optimize_cloud_monitoring",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                    "message": "test_and_optimize_cloud_monitoring already processed",
                }
            await self.cache.set(
                f"{settings.service_name}:test_and_optimize_cloud_monitoring", config
            )
            self._state["test_and_optimize_cloud_monitoring"] = config
            self._operations["test_and_optimize_cloud_monitoring"] = (
                self._operations.get("test_and_optimize_cloud_monitoring", 0) + 1
            )
            self.metrics.inc_operation("test_and_optimize_cloud_monitoring")
            result = {
                "feature": "test_and_optimize_cloud_monitoring",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Cloud Monitoring"},
                "message": "test_and_optimize_cloud_monitoring completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

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


Service = CloudMonitoringService
