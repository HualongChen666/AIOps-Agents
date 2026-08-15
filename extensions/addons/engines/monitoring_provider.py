# -*- coding: utf-8 -*-
"""Monitoring provider engine and observability addon base service.

The ``MonitoringProvider`` class implements real (but guarded) observability
operations against Prometheus, CloudWatch, Datadog, ELK, Loki, Jaeger/Zipkin
and generic HTTP/CLI targets.  When ``dry_run`` is ``True`` (the default unless
``INFRA_EXECUTE_ENABLED=true``) it returns realistic synthetic data without
performing any network or CLI calls.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover - minimal installs without requests
    requests = None  # type: ignore[assignment]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_operation(name: str) -> str:
    """Map an addon operation name to a ``MonitoringProvider`` engine method."""
    normalized = name.lower().replace("_", " ")
    if any(
        keyword in normalized
        for keyword in (
            "alert",
            "rule",
            "silence",
            "suppress",
            "escalate",
            "notify",
            "pagerduty",
        )
    ):
        return "push_alert"
    if any(
        keyword in normalized
        for keyword in ("topology", "discovery", "cmdb", "dependency", "service discovery")
    ):
        return "get_topology"
    if any(
        keyword in normalized
        for keyword in ("log", "loki", "elk", "fluentd", "audit_log")
    ):
        return "logs"
    if any(
        keyword in normalized
        for keyword in ("trace", "tracing", "jaeger", "zipkin", "skywalking", "otel")
    ):
        return "traces"
    if any(
        keyword in normalized
        for keyword in ("health", "status", "probe", "ping")
    ):
        return "health"
    return "query"


class _URLLibResponse:
    """Minimal adapter so the urllib fallback can be consumed like requests."""

    def __init__(self, response: urllib.request.addinfourl, data: bytes) -> None:
        self._response = response
        self._data = data
        self.status_code = response.getcode()

    def raise_for_status(self) -> None:
        if self.status_code is not None and self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return json.loads(self._data.decode("utf-8"))

    @property
    def text(self) -> str:
        return self._data.decode("utf-8")


class MonitoringProvider:
    """Real monitoring provider with dry-run safety."""

    def __init__(self, dry_run: Optional[bool] = None) -> None:
        if dry_run is None:
            dry_run = os.environ.get("INFRA_EXECUTE_ENABLED") != "true"
        self.dry_run = dry_run

    def _should_run(self) -> bool:
        return not self.dry_run

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Make an HTTP request using ``requests`` when available, urllib otherwise."""
        if requests is not None:
            return requests.request(method, url, **kwargs)
        data = kwargs.get("json")
        headers = kwargs.get("headers", {})
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8") if data is not None else None,
            headers=headers,
            method=method,
        )
        if kwargs.get("params"):
            query = urllib.parse.urlencode(kwargs["params"])
            url = url + "?" + query
            req = urllib.request.Request(
                url,
                data=req.data,
                headers=headers,
                method=method,
            )
        with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 30)) as resp:
            return _URLLibResponse(resp, resp.read())

    def _run_cli(self, cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, **kwargs)

    def query(
        self,
        target: Optional[str] = None,
        metric: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        step: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Query Prometheus/CloudWatch/Datadog/ELK metrics."""
        if self.dry_run or not target:
            return {
                "status": "ok",
                "data": [
                    {
                        "timestamp": _now(),
                        "value": 0.42,
                        "metric": metric or "unknown",
                    }
                ],
            }
        backend = target.lower()
        try:
            if "datadog" in backend or "api." in backend:
                return self._query_datadog(target, metric, start, end, step, **kwargs)
            if "elasticsearch" in backend or "es." in backend or ":9200" in backend:
                return self._query_elasticsearch(target, metric, start, end, step, **kwargs)
            if "cloudwatch" in backend:
                return self._query_cloudwatch(target, metric, start, end, step, **kwargs)
            return self._query_prometheus(target, metric, start, end, step, **kwargs)
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": []}

    def _query_prometheus(
        self,
        target: str,
        metric: Optional[str],
        start: Optional[str],
        end: Optional[str],
        step: Optional[str],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        url = target.rstrip("/") + "/api/v1/query_range"
        params: Dict[str, Any] = {}
        if metric:
            params["query"] = metric
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if step:
            params["step"] = step
        resp = self._request("GET", url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {"status": "ok", "data": data.get("data", {}).get("result", [])}

    def _query_datadog(
        self,
        target: str,
        metric: Optional[str],
        start: Optional[str],
        end: Optional[str],
        step: Optional[str],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        api_key = kwargs.get("api_key", "")
        app_key = kwargs.get("app_key", "")
        url = target.rstrip("/") + "/api/v1/query"
        params: Dict[str, Any] = {
            "from": start,
            "to": end,
        }
        if metric:
            params["query"] = metric
        headers = {
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
            "Accept": "application/json",
        }
        resp = self._request("GET", url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return {"status": "ok", "data": resp.json()}

    def _query_elasticsearch(
        self,
        target: str,
        metric: Optional[str],
        start: Optional[str],
        end: Optional[str],
        step: Optional[str],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        url = target.rstrip("/") + "/_search"
        body = {
            "query": {"query_string": {"query": metric or "*"}},
            "size": 100,
        }
        headers = {"Content-Type": "application/json"}
        resp = self._request("POST", url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": "ok",
            "data": data.get("hits", {}).get("hits", []),
        }

    def _query_cloudwatch(
        self,
        target: str,
        metric: Optional[str],
        start: Optional[str],
        end: Optional[str],
        step: Optional[str],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        namespace = kwargs.get("namespace", "AWS/EC2")
        cmd = [
            "aws",
            "cloudwatch",
            "get-metric-statistics",
            "--namespace",
            namespace,
            "--metric-name",
            metric or "CPUUtilization",
            "--start-time",
            start or _now(),
            "--end-time",
            end or _now(),
            "--period",
            step or "60",
            "--statistics",
            "Average",
        ]
        result = self._run_cli(cmd, timeout=30)
        if result.returncode != 0:
            return {"status": "error", "message": result.stderr, "data": []}
        return {"status": "ok", "data": json.loads(result.stdout or "{}")}

    def push_alert(
        self,
        rule_name: Optional[str] = None,
        expr: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
        annotations: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build and POST a Prometheus/Alertmanager alert rule or Datadog monitor."""
        if not self._should_run():
            return {
                "status": "ok",
                "data": {
                    "rule": rule_name or "rule",
                    "expr": expr or "up == 1",
                    "fired": False,
                },
            }

        # Reuse modules.observability.smart_alerting for rule generation/evaluation.
        smart_alerts: List[Dict[str, Any]] = []
        try:
            from modules.observability.smart_alerting import (
                AlertRule,
                AlertSeverity,
                SmartAlertingEngine,
            )

            engine = SmartAlertingEngine()
            sev_label = str((labels or {}).get("severity", "warning"))
            try:
                severity = AlertSeverity(sev_label)
            except ValueError:
                severity = AlertSeverity.WARNING
            rule = AlertRule(
                id=rule_name or "rule",
                name=rule_name or "rule",
                condition=expr or "up == 1",
                severity=severity,
                labels=(labels or {}),
                annotations=(annotations or {}),
            )
            engine.add_rule(rule)
            metrics = kwargs.get("metrics", {})
            if not isinstance(metrics, dict):
                metrics = {}
            smart_alerts = [
                alert.to_dict() for alert in engine.evaluate_metrics(metrics)
            ]
        except Exception:
            pass

        target = (
            kwargs.get("target")
            or kwargs.get("alertmanager_url")
            or os.environ.get("ALERTMANAGER_URL", "http://alertmanager:9093")
        )
        try:
            url = target.rstrip("/") + "/api/v1/alerts"
            alerts = [
                {
                    "labels": {**(labels or {}), "alertname": rule_name or "rule"},
                    "annotations": annotations or {},
                    "startsAt": _now(),
                }
            ]
            resp = self._request("POST", url, json=alerts, timeout=30)
            resp.raise_for_status()
            return {
                "status": "ok",
                "data": {"posted": resp.json() if hasattr(resp, "json") else resp.text},
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    def get_topology(
        self,
        source: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Pull topology from a CMDB or Prometheus service discovery."""
        if not self._should_run() or not source:
            return {
                "status": "ok",
                "data": {
                    "nodes": [
                        {"id": "svc-1", "name": "service-a"},
                        {"id": "svc-2", "name": "service-b"},
                    ],
                    "edges": [{"source": "svc-1", "target": "svc-2"}],
                },
            }
        # Reuse modules.apm.dependency_analyzer for topology discovery.
        try:
            from modules.apm.dependency_analyzer import DependencyAnalyzer

            analyzer = DependencyAnalyzer()
            if "method" in kwargs or any(
                k in kwargs for k in ("trace_data", "config_data", "metrics_data")
            ):
                method = kwargs.get("method", "trace")
                if method == "trace":
                    topology = analyzer.discover_topology(
                        method="trace",
                        trace_data=kwargs.get("trace_data", []),
                    )
                elif method == "config":
                    topology = analyzer.discover_topology(
                        method="config",
                        config_data=kwargs.get("config_data", {}),
                    )
                elif method == "metrics":
                    topology = analyzer.discover_topology(
                        method="metrics",
                        metrics_data=kwargs.get("metrics_data", {}),
                    )
                else:
                    topology = analyzer.discover_topology(method=method, **kwargs)
                return {
                    "status": "ok",
                    "data": {**topology.to_dict(), "source": source},
                }
        except Exception:
            pass

        if source.lower().startswith("http"):
            try:
                url = source.rstrip("/") + "/api/v1/targets"
                resp = self._request("GET", url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                targets = (
                    data.get("data", {}).get("activeTargets", [])
                    if isinstance(data, dict) and "data" in data
                    else data
                )
                nodes = [
                    {
                        "id": t.get("labels", {}).get("instance", f"target-{i}"),
                        "name": t.get("labels", {}).get("job", "unknown"),
                    }
                    for i, t in enumerate(targets)
                ]
                return {
                    "status": "ok",
                    "data": {"nodes": nodes, "edges": [], "source": source},
                }
            except Exception as exc:
                return {
                    "status": "error",
                    "message": str(exc),
                    "data": {"nodes": [], "edges": []},
                }
        try:
            cmd = ["kubectl", "get", "svc", "-o", "json"]
            if filters and "namespace" in filters:
                cmd.extend(["-n", str(filters["namespace"])])
            result = self._run_cli(cmd, timeout=30)
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": result.stderr,
                    "data": {"nodes": [], "edges": []},
                }
            data = json.loads(result.stdout)
            items = data.get("items", [])
            nodes = [
                {"id": item["metadata"]["name"], "name": item["metadata"]["name"]}
                for item in items
            ]
            return {
                "status": "ok",
                "data": {"nodes": nodes, "edges": [], "source": source},
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": str(exc),
                "data": {"nodes": [], "edges": []},
            }

    def logs(
        self,
        query: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
        target: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Query Loki/ELK logs."""
        if self.dry_run or not (target or query):
            return {
                "status": "ok",
                "data": [
                    {"timestamp": _now(), "line": "synthetic log line"}
                ],
            }
        target = target or os.environ.get("LOKI_URL", "http://loki:3100")
        if "elasticsearch" in target.lower() or ":9200" in target:
            try:
                url = target.rstrip("/") + "/_search"
                body = {
                    "query": {"query_string": {"query": query or "*"}},
                    "size": limit,
                }
                resp = self._request(
                    "POST",
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "status": "ok",
                    "data": data.get("hits", {}).get("hits", []),
                }
            except Exception as exc:
                return {"status": "error", "message": str(exc), "data": []}
        try:
            url = target.rstrip("/") + "/loki/api/v1/query_range"
            params: Dict[str, Any] = {
                "query": query or '{job="default"}',
                "start": start,
                "end": end,
                "limit": limit,
            }
            resp = self._request("GET", url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "ok",
                "data": data.get("data", {}).get("result", []) if isinstance(data, dict) else data,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": []}

    def traces(
        self,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
        target: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Query Jaeger/Zipkin/OTel collector traces."""
        if self.dry_run:
            return {
                "status": "ok",
                "data": [
                    {
                        "traceID": "abc123",
                        "spans": [
                            {
                                "serviceName": service or "unknown",
                                "operationName": operation or "op",
                            }
                        ],
                    }
                ],
            }
        target = target or os.environ.get("JAEGER_URL", "http://jaeger:16686")
        if "jaeger" in target.lower():
            try:
                url = target.rstrip("/") + "/api/traces"
                params: Dict[str, Any] = {
                    "service": service or "",
                    "operation": operation or "",
                    "start": start,
                    "end": end,
                    "limit": limit,
                }
                resp = self._request("GET", url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "status": "ok",
                    "data": data.get("data", []) if isinstance(data, dict) else data,
                }
            except Exception as exc:
                return {"status": "error", "message": str(exc), "data": []}
        try:
            url = target.rstrip("/") + "/api/v2/traces"
            params = {"serviceName": service, "spanName": operation, "limit": limit}
            resp = self._request("GET", url, params=params, timeout=30)
            resp.raise_for_status()
            return {
                "status": "ok",
                "data": resp.json() if hasattr(resp, "json") else resp.read(),
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": []}

    def health(self, target: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Simple HTTP/CLI health probe."""
        if self.dry_run or not target:
            return {
                "status": "ok",
                "data": {"healthy": True, "target": target or "unknown"},
            }
        if target.lower().startswith("http"):
            try:
                resp = self._request("GET", target, timeout=10)
                if requests is not None:
                    code = resp.status_code
                else:
                    code = getattr(resp, "status_code", 200)
                return {
                    "status": "ok" if code < 400 else "error",
                    "data": {"status_code": code, "target": target},
                }
            except Exception as exc:
                return {
                    "status": "error",
                    "message": str(exc),
                    "data": {"target": target},
                }
        try:
            cmd = target.split() if isinstance(target, str) else ["kubectl", "version"]
            result = self._run_cli(cmd, timeout=10)
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "data": {
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                    "target": target,
                },
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": str(exc),
                "data": {"target": target},
            }


class _NoOpMetrics:
    """Minimal metrics collector used when an addon has no real metrics module."""

    def __init__(self) -> None:
        self.request_count = 0
        self.cache_hits_count = 0
        self.cache_misses_count = 0

    def inc_request(self, operation: str) -> None:
        self.request_count += 1

    def inc_operation(self, operation: str) -> None:
        pass

    def inc_cache_hit(self) -> None:
        self.cache_hits_count += 1

    def inc_cache_miss(self) -> None:
        self.cache_misses_count += 1


class BaseObservabilityService:
    """Thin wrapper base for all observability/monitoring addon services."""

    OPERATIONS: List[str] = []
    BASE_METHODS: List[str] = [
        "get_state",
        "backup_state",
        "restore_state",
        "get_stats",
        "list_methods",
    ]

    def __init__(
        self,
        metrics: Optional[Any] = None,
        cache: Optional[Any] = None,
        settings: Optional[Any] = None,
    ) -> None:
        self.metrics = metrics or _NoOpMetrics()
        self.cache = cache
        self.settings = settings
        self._state: Dict[str, Any] = {}
        self._backups: Dict[str, Any] = {}
        self._operations: Dict[str, int] = {}
        self._feature_count = len(getattr(self, "OPERATIONS", []))

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
                "cache_hits": getattr(self.metrics, "cache_hits_count", 0),
                "cache_misses": getattr(self.metrics, "cache_misses_count", 0),
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
            "result": {
                "methods": list(getattr(self, "OPERATIONS", [])) + list(self.BASE_METHODS),
            },
            "message": "Methods listed",
        }

    def execute_operation(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Instantiate ``MonitoringProvider`` and dispatch to the engine."""
        self.metrics.inc_request(name)
        method = resolve_operation(name)
        dry_run = os.environ.get("INFRA_EXECUTE_ENABLED") != "true"
        provider = MonitoringProvider(dry_run=dry_run)
        result = getattr(provider, method)(**params)
        self._operations[name] = self._operations.get(name, 0) + 1
        self.metrics.inc_operation(name)
        return {
            "feature": name,
            "success": result.get("status") == "ok",
            "status": result.get("status", "ok"),
            "config": params,
            "result": result,
            "message": f"{name} completed",
        }

    def __getattr__(self, name: str) -> Any:
        if name in getattr(self, "OPERATIONS", []):
            async def _handler(request: Any = None):
                return self.execute_operation(name, self._get_config(request))
            return _handler
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    async def call(self, method: str, **kwargs: Any) -> Any:
        self.metrics.inc_request("call")
        if method in self.BASE_METHODS:
            return await getattr(self, method)(kwargs.get("request"))
        if method in getattr(self, "OPERATIONS", []):
            return self.execute_operation(method, self._get_config(kwargs.get("request")))
        raise ValueError(f"Unknown method: {method}")
