# -*- coding: utf-8 -*-
"""Core service logic for the Alert Rule microservice."""

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
    "design_alert_rule_system",
    "configure_system_resource_alerts",
    "configure_application_performance_alerts",
    "configure_business_metric_alerts",
    "configure_prometheus_alert_rules",
    "configure_alertmanager_routing",
    "configure_alert_suppression",
    "configure_alert_aggregation",
    "configure_slack_notifications",
    "configure_email_notifications",
    "configure_pagerduty_notifications",
    "configure_alert_escalation",
    "configure_alert_silencing",
    "validate_alert_rules",
    "test_alert_rules",
]


class AlertRuleService:
    """Domain service for Alert Rule."""

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

    async def design_alert_rule_system(self, request: Any = None) -> Dict[str, Any]:
        """Design Alert Rule System."""
        self.metrics.inc_request("design_alert_rule_system")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:design_alert_rule_system", config)
        self._state["design_alert_rule_system"] = config
        self._operations["design_alert_rule_system"] = (
            self._operations.get("design_alert_rule_system", 0) + 1
        )
        self.metrics.inc_operation("design_alert_rule_system")
        return {
            "feature": "design_alert_rule_system",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "design_alert_rule_system completed",
        }

    async def configure_system_resource_alerts(self, request: Any = None) -> Dict[str, Any]:
        """Configure System Resource Alerts."""
        self.metrics.inc_request("configure_system_resource_alerts")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_system_resource_alerts", config)
        self._state["configure_system_resource_alerts"] = config
        self._operations["configure_system_resource_alerts"] = (
            self._operations.get("configure_system_resource_alerts", 0) + 1
        )
        self.metrics.inc_operation("configure_system_resource_alerts")
        return {
            "feature": "configure_system_resource_alerts",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_system_resource_alerts completed",
        }

    async def configure_application_performance_alerts(self, request: Any = None) -> Dict[str, Any]:
        """Configure Application Performance Alerts."""
        self.metrics.inc_request("configure_application_performance_alerts")
        config = self._get_config(request)
        await self.cache.set(
            f"{settings.service_name}:configure_application_performance_alerts", config
        )
        self._state["configure_application_performance_alerts"] = config
        self._operations["configure_application_performance_alerts"] = (
            self._operations.get("configure_application_performance_alerts", 0) + 1
        )
        self.metrics.inc_operation("configure_application_performance_alerts")
        return {
            "feature": "configure_application_performance_alerts",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_application_performance_alerts completed",
        }

    async def configure_business_metric_alerts(self, request: Any = None) -> Dict[str, Any]:
        """Configure Business Metric Alerts."""
        self.metrics.inc_request("configure_business_metric_alerts")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_business_metric_alerts", config)
        self._state["configure_business_metric_alerts"] = config
        self._operations["configure_business_metric_alerts"] = (
            self._operations.get("configure_business_metric_alerts", 0) + 1
        )
        self.metrics.inc_operation("configure_business_metric_alerts")
        return {
            "feature": "configure_business_metric_alerts",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_business_metric_alerts completed",
        }

    async def configure_prometheus_alert_rules(self, request: Any = None) -> Dict[str, Any]:
        """Configure Prometheus Alert Rules."""
        self.metrics.inc_request("configure_prometheus_alert_rules")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_prometheus_alert_rules", config)
        self._state["configure_prometheus_alert_rules"] = config
        self._operations["configure_prometheus_alert_rules"] = (
            self._operations.get("configure_prometheus_alert_rules", 0) + 1
        )
        self.metrics.inc_operation("configure_prometheus_alert_rules")
        return {
            "feature": "configure_prometheus_alert_rules",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_prometheus_alert_rules completed",
        }

    async def configure_alertmanager_routing(self, request: Any = None) -> Dict[str, Any]:
        """Configure Alertmanager Routing."""
        self.metrics.inc_request("configure_alertmanager_routing")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_alertmanager_routing", config)
        self._state["configure_alertmanager_routing"] = config
        self._operations["configure_alertmanager_routing"] = (
            self._operations.get("configure_alertmanager_routing", 0) + 1
        )
        self.metrics.inc_operation("configure_alertmanager_routing")
        return {
            "feature": "configure_alertmanager_routing",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_alertmanager_routing completed",
        }

    async def configure_alert_suppression(self, request: Any = None) -> Dict[str, Any]:
        """Configure Alert Suppression."""
        self.metrics.inc_request("configure_alert_suppression")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_alert_suppression", config)
        self._state["configure_alert_suppression"] = config
        self._operations["configure_alert_suppression"] = (
            self._operations.get("configure_alert_suppression", 0) + 1
        )
        self.metrics.inc_operation("configure_alert_suppression")
        return {
            "feature": "configure_alert_suppression",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_alert_suppression completed",
        }

    async def configure_alert_aggregation(self, request: Any = None) -> Dict[str, Any]:
        """Configure Alert Aggregation."""
        self.metrics.inc_request("configure_alert_aggregation")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_alert_aggregation", config)
        self._state["configure_alert_aggregation"] = config
        self._operations["configure_alert_aggregation"] = (
            self._operations.get("configure_alert_aggregation", 0) + 1
        )
        self.metrics.inc_operation("configure_alert_aggregation")
        return {
            "feature": "configure_alert_aggregation",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_alert_aggregation completed",
        }

    async def configure_slack_notifications(self, request: Any = None) -> Dict[str, Any]:
        """Configure Slack Notifications."""
        self.metrics.inc_request("configure_slack_notifications")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_slack_notifications", config)
        self._state["configure_slack_notifications"] = config
        self._operations["configure_slack_notifications"] = (
            self._operations.get("configure_slack_notifications", 0) + 1
        )
        self.metrics.inc_operation("configure_slack_notifications")
        return {
            "feature": "configure_slack_notifications",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_slack_notifications completed",
        }

    async def configure_email_notifications(self, request: Any = None) -> Dict[str, Any]:
        """Configure Email Notifications."""
        self.metrics.inc_request("configure_email_notifications")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_email_notifications", config)
        self._state["configure_email_notifications"] = config
        self._operations["configure_email_notifications"] = (
            self._operations.get("configure_email_notifications", 0) + 1
        )
        self.metrics.inc_operation("configure_email_notifications")
        return {
            "feature": "configure_email_notifications",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_email_notifications completed",
        }

    async def configure_pagerduty_notifications(self, request: Any = None) -> Dict[str, Any]:
        """Configure Pagerduty Notifications."""
        self.metrics.inc_request("configure_pagerduty_notifications")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_pagerduty_notifications", config)
        self._state["configure_pagerduty_notifications"] = config
        self._operations["configure_pagerduty_notifications"] = (
            self._operations.get("configure_pagerduty_notifications", 0) + 1
        )
        self.metrics.inc_operation("configure_pagerduty_notifications")
        return {
            "feature": "configure_pagerduty_notifications",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_pagerduty_notifications completed",
        }

    async def configure_alert_escalation(self, request: Any = None) -> Dict[str, Any]:
        """Configure Alert Escalation."""
        self.metrics.inc_request("configure_alert_escalation")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_alert_escalation", config)
        self._state["configure_alert_escalation"] = config
        self._operations["configure_alert_escalation"] = (
            self._operations.get("configure_alert_escalation", 0) + 1
        )
        self.metrics.inc_operation("configure_alert_escalation")
        return {
            "feature": "configure_alert_escalation",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_alert_escalation completed",
        }

    async def configure_alert_silencing(self, request: Any = None) -> Dict[str, Any]:
        """Configure Alert Silencing."""
        self.metrics.inc_request("configure_alert_silencing")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_alert_silencing", config)
        self._state["configure_alert_silencing"] = config
        self._operations["configure_alert_silencing"] = (
            self._operations.get("configure_alert_silencing", 0) + 1
        )
        self.metrics.inc_operation("configure_alert_silencing")
        return {
            "feature": "configure_alert_silencing",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "configure_alert_silencing completed",
        }

    async def validate_alert_rules(self, request: Any = None) -> Dict[str, Any]:
        """Validate Alert Rules."""
        self.metrics.inc_request("validate_alert_rules")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:validate_alert_rules", config)
        self._state["validate_alert_rules"] = config
        self._operations["validate_alert_rules"] = (
            self._operations.get("validate_alert_rules", 0) + 1
        )
        self.metrics.inc_operation("validate_alert_rules")
        return {
            "feature": "validate_alert_rules",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "validate_alert_rules completed",
        }

    async def test_alert_rules(self, request: Any = None) -> Dict[str, Any]:
        """Test Alert Rules."""
        self.metrics.inc_request("test_alert_rules")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_alert_rules", config)
        self._state["test_alert_rules"] = config
        self._operations["test_alert_rules"] = self._operations.get("test_alert_rules", 0) + 1
        self.metrics.inc_operation("test_alert_rules")
        return {
            "feature": "test_alert_rules",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Alert Rule"},
            "message": "test_alert_rules completed",
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


Service = AlertRuleService
