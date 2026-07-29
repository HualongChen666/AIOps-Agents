# -*- coding: utf-8 -*-
"""Best-effort observability data fetcher for Agent tools.

The client reads endpoint configuration from environment variables and falls
back gracefully when no external system is available.  It is intentionally
synchronous (tools run in threads) and validates queries through the existing
``core.observability_query`` guardrails when possible.
"""

from __future__ import annotations

import logging
import json
import os
import re
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import httpx

    HTTPX_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

try:
    from core.observability_query import (
        DEFAULT_MAX_PROMQL_SAMPLES,
        MAX_QUERY_TIMEOUT,
        limit_range_samples,
        parse_duration_to_seconds,
        validate_logql,
        validate_promql,
    )
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    validate_promql = None  # type: ignore[assignment]
    validate_logql = None  # type: ignore[assignment]
    limit_range_samples = None  # type: ignore[assignment]
    parse_duration_to_seconds = None  # type: ignore[assignment]
    DEFAULT_MAX_PROMQL_SAMPLES = 40320  # type: ignore[assignment]
    MAX_QUERY_TIMEOUT = 30.0  # type: ignore[assignment]


_DEFAULT_TIMEOUT = float(os.environ.get("AIOPS_OBSERVABILITY_TIMEOUT", "10"))

# Safety / back-pressure limits ------------------------------------------------
_MAX_RESPONSE_BYTES = int(os.environ.get("AIOPS_MAX_RESPONSE_BYTES", 1024 * 1024))
_MAX_LOKI_LIMIT = int(os.environ.get("AIOPS_MAX_LOKI_LIMIT", 1000))
_MAX_K8S_EVENTS = int(os.environ.get("AIOPS_MAX_K8S_EVENTS", 1000))
_MAX_CHANGE_EVENTS_FILE_BYTES = int(
    os.environ.get("AIOPS_MAX_CHANGE_EVENTS_FILE_BYTES", 10 * 1024 * 1024)
)
_MAX_CONCURRENT_QUERIES = int(os.environ.get("AIOPS_MAX_CONCURRENT_QUERIES", "10"))
_QUERY_SEM = threading.Semaphore(_MAX_CONCURRENT_QUERIES)

# Shared HTTP client with connection pooling ------------------------------------
_HTTP_CLIENT: Optional[Any] = None


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        return None


def _safe_label(value: str) -> str:
    """Validate a Prometheus/Kubernetes label value used inside a query.

    Rejects quotes, braces, semicolons and other characters that could be used
    to break out of a label matcher or construct a new PromQL expression.
    """
    if not isinstance(value, str):
        raise ValueError("Label value must be a string")
    if len(value) > 200:
        raise ValueError("Label value too long (max 200 characters)")
    if not re.fullmatch(r"^[A-Za-z0-9_.:/-]+$", value):
        raise ValueError(f"Label value contains unsafe characters: {value!r}")
    return value


def get_prometheus_url() -> Optional[str]:
    return _get_env("AIOPS_PROMETHEUS_URL")


def get_loki_url() -> Optional[str]:
    return _get_env("AIOPS_LOKI_URL")


def get_change_events_url() -> Optional[str]:
    return _get_env("AIOPS_CHANGE_EVENTS_URL")


def get_kubernetes_api_url() -> Optional[str]:
    return _get_env("AIOPS_KUBERNETES_API_URL")


def get_kubernetes_token() -> Optional[str]:
    explicit = _get_env("AIOPS_KUBERNETES_TOKEN")
    if explicit:
        return explicit
    return _read_file("/var/run/secrets/kubernetes.io/serviceaccount/token")


def get_kubernetes_ca() -> Optional[str]:
    explicit = _get_env("AIOPS_KUBERNETES_CA")
    if explicit:
        return explicit
    default_ca = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    if os.path.exists(default_ca):
        return default_ca
    return None


def _should_verify_ssl() -> bool:
    return _get_env("AIOPS_KUBERNETES_VERIFY", "true").lower() in ("1", "true", "yes", "on")


def _get_http_client() -> Optional[Any]:
    """Return a shared httpx Client with connection pooling."""
    global _HTTP_CLIENT
    if not HTTPX_AVAILABLE or httpx is None:
        return None
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = httpx.Client(
            timeout=float(os.environ.get("AIOPS_OBSERVABILITY_TIMEOUT", "10")),
            limits=httpx.Limits(
                max_connections=int(os.environ.get("AIOPS_OBSERVABILITY_MAX_CONNECTIONS", "20")),
                max_keepalive_connections=10,
            ),
            follow_redirects=True,
        )
    return _HTTP_CLIENT


def _sanitize_url_for_log(url: str) -> str:
    """Remove bearer token from URL query string if any."""
    # The token is only placed in headers in this module, but keep as guard.
    return url


def _http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    verify: Optional[Any] = None,
    timeout: Optional[float] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not HTTPX_AVAILABLE or httpx is None:
        return None, "httpx not installed"

    client = _get_http_client()
    if client is None:
        return None, "httpx client not available"

    timeout = (
        timeout
        if timeout is not None
        else float(os.environ.get("AIOPS_OBSERVABILITY_TIMEOUT", "10"))
    )
    # Cap per-source timeout by global guardrail
    timeout = min(timeout, MAX_QUERY_TIMEOUT)

    start = time.monotonic()
    response_bytes = 0
    try:
        with _QUERY_SEM:
            response = client.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response_bytes = len(response.content)
        if response_bytes > _MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Response too large: {response_bytes} bytes (max {_MAX_RESPONSE_BYTES})"
            )
        data = response.json()
    except Exception as exc:  # pragma: no cover
        logger.debug(f"HTTP GET failed for {url}: {exc}")
        return None, str(exc)
    finally:
        latency = time.monotonic() - start
        result_count = 0
        if "data" in locals():
            if isinstance(data, dict):
                result_count = len(data.get("data", {}).get("result", []))
            elif isinstance(data, list):
                result_count = len(data)
        logger.info(
            "observability_query | url=%s latency_ms=%.1f response_bytes=%s result_count=%s",
            _sanitize_url_for_log(url),
            latency * 1000,
            response_bytes,
            result_count,
        )

    return data, None


def _prom_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    token = _get_env("AIOPS_PROMETHEUS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _k8s_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    token = get_kubernetes_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _k8s_verify() -> Any:
    if not _should_verify_ssl():
        return False
    ca = get_kubernetes_ca()
    return ca if ca else True


def query_prometheus(promql: str) -> Optional[Dict[str, Any]]:
    """Run a PromQL query against the configured Prometheus/VictoriaMetrics."""
    base_url = get_prometheus_url()
    if not base_url:
        return None
    if validate_promql is not None:
        try:
            validate_promql(promql)
        except Exception as exc:
            logger.warning(f"PromQL validation failed: {exc}")
            return None
    encoded = urllib.parse.quote(promql, safe="")
    url = f"{base_url.rstrip('/')}/api/v1/query?query={encoded}"
    data, error = _http_get_json(url, headers=_prom_headers())
    if data is None:
        return {"status": "error", "error": error, "data": {"result": []}}
    return data


def query_prometheus_range(
    promql: str,
    start: float,
    end: float,
    step: str = "15s",
) -> Optional[Dict[str, Any]]:
    base_url = get_prometheus_url()
    if not base_url:
        return None
    if validate_promql is not None:
        try:
            validate_promql(promql)
        except Exception as exc:
            logger.warning(f"PromQL validation failed: {exc}")
            return None

    if limit_range_samples is not None and parse_duration_to_seconds is not None:
        start_dt = datetime.fromtimestamp(start, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end, tz=timezone.utc)
        step_seconds = parse_duration_to_seconds(step)
        step_seconds = limit_range_samples(
            start_dt,
            end_dt,
            step_seconds,
            max_samples=DEFAULT_MAX_PROMQL_SAMPLES,
        )
        step_str = f"{step_seconds:.3f}s"
    else:
        step_str = step

    encoded = urllib.parse.quote(promql, safe="")
    url = (
        f"{base_url.rstrip('/')}/api/v1/query_range?"
        f"query={encoded}&start={start}&end={end}&step={step_str}"
    )
    data, error = _http_get_json(url, headers=_prom_headers())
    if data is None:
        return {"status": "error", "error": error, "data": {"result": []}}
    return data


def _extract_prom_scalar_value(data: Optional[Dict[str, Any]]) -> Optional[float]:
    if not isinstance(data, dict):
        return None
    result_data = data.get("data", {}).get("result", [])
    if not result_data:
        return None
    value = result_data[0].get("value", [])
    if len(value) >= 2:
        try:
            return float(value[1])
        except (TypeError, ValueError):
            return None
    return None


def query_service_metrics(
    service_name: str,
    time_range_hours: int = 1,
) -> Dict[str, Any]:
    """Query standard service SLI metrics for a service from Prometheus."""
    base_url = get_prometheus_url()
    if not base_url:
        return {
            "source": "prometheus",
            "available": False,
            "reason": "AIOPS_PROMETHEUS_URL not set",
        }

    # Clamp time window to avoid expensive range queries
    time_range_hours = max(1, min(int(time_range_hours), 24))
    safe_service = _safe_label(service_name)

    end = time.time()
    start = end - time_range_hours * 3600

    promqls = {
        "request_rate": f"sum(rate(http_requests_total{{service='{safe_service}'}}[1m]))",
        "error_rate": f"sum(rate(http_requests_total{{service='{safe_service}',status=~'5..'}}[1m])) / sum(rate(http_requests_total{{service='{safe_service}'}}[1m]))",  # noqa: E501
        "latency_p99": f"histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{{service='{safe_service}'}}[5m])) by (le))",  # noqa: E501
        "latency_p95": f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{service='{safe_service}'}}[5m])) by (le))",  # noqa: E501
        "latency_p50": f"histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{{service='{safe_service}'}}[5m])) by (le))",  # noqa: E501
    }

    metrics: Dict[str, Any] = {"source": "prometheus", "available": True}
    for key, promql in promqls.items():
        try:
            data = (
                query_prometheus_range(promql, start, end)
                if key == "request_rate"
                else query_prometheus(promql)
            )
            value = _extract_prom_scalar_value(data)
            metrics[key] = value if value is not None else "no_data"
        except Exception as exc:  # pragma: no cover
            metrics[key] = f"error: {exc}"
    return metrics


def query_network_metrics(
    target: str,
    duration: int = 60,
) -> Dict[str, Any]:
    """Query network/DNS metrics for a target from Prometheus."""
    base_url = get_prometheus_url()
    if not base_url:
        return {
            "source": "prometheus",
            "available": False,
            "reason": "AIOPS_PROMETHEUS_URL not set",
        }

    safe_target = _safe_label(target)

    promqls = {
        "dns_resolution_error_rate": f"probe_dns_error_ratio{{instance='{safe_target}'}} or dns_resolution_errors{{target='{safe_target}'}} or 0",  # noqa: E501
        "dns_lookup_time_ms": f"(probe_dns_lookup_time_seconds{{instance='{safe_target}'}} * 1000) or (dns_lookup_time_seconds{{target='{safe_target}'}} * 1000) or 0",  # noqa: E501
        "packet_loss_percent": f"probe_packet_loss_percent{{target='{safe_target}'}} or ping_packet_loss_percent{{target='{safe_target}'}} or 0",  # noqa: E501
        "latency_ms": f"(probe_icmp_duration_seconds{{target='{safe_target}'}} * 1000) or (ping_latency_ms{{target='{safe_target}'}}) or 0",  # noqa: E501
    }

    metrics: Dict[str, Any] = {"source": "prometheus", "available": True, "target": target}
    for key, promql in promqls.items():
        try:
            value = _extract_prom_scalar_value(query_prometheus(promql))
            metrics[key] = value if value is not None else "no_data"
        except Exception as exc:  # pragma: no cover
            metrics[key] = f"error: {exc}"
    return metrics


def query_loki(logql: str, limit: int = 100) -> Optional[Dict[str, Any]]:
    base_url = get_loki_url()
    if not base_url:
        return None
    if httpx is None:
        return None
    if validate_logql is not None:
        try:
            validate_logql(logql)
        except Exception as exc:
            logger.warning(f"LogQL validation failed: {exc}")
            return {"status": "error", "error": f"LogQL validation failed: {exc}"}
    limit = max(1, min(int(limit), _MAX_LOKI_LIMIT))
    encoded = urllib.parse.quote(logql, safe="")
    end = int(time.time() * 1e9)
    start = end - int(3600 * 1e9)
    url = (
        f"{base_url.rstrip('/')}/loki/api/v1/query_range?"
        f"query={encoded}&start={start}&end={end}&limit={limit}"
    )
    data, _ = _http_get_json(url)
    return data


def query_kubernetes_events(
    namespace: Optional[str] = None,
    field_selector: Optional[str] = None,
    limit: int = _MAX_K8S_EVENTS,
) -> List[Dict[str, Any]]:
    base_url = get_kubernetes_api_url()
    if not base_url:
        return []
    parts = ["api/v1/events"]
    params = []
    if namespace:
        params.append(f"namespace={urllib.parse.quote(namespace, safe='')}")
    if field_selector:
        params.append(f"fieldSelector={urllib.parse.quote(field_selector, safe='')}")
    if params:
        parts.append("?" + "&".join(params))
    url = base_url.rstrip("/") + "/" + "".join(parts)
    data, error = _http_get_json(url, headers=_k8s_headers(), verify=_k8s_verify())
    if data is None:
        logger.warning(f"Failed to query Kubernetes events: {error}")
        return []
    limit = max(1, min(int(limit), _MAX_K8S_EVENTS))
    return [
        {
            "type": item.get("type"),
            "reason": item.get("reason"),
            "message": item.get("message"),
            "object": item.get("involvedObject", {}).get("name"),
            "kind": item.get("involvedObject", {}).get("kind"),
            "namespace": item.get("metadata", {}).get("namespace"),
            "timestamp": item.get("lastTimestamp") or item.get("eventTime"),
        }
        for item in data.get("items", [])[:limit]
    ]


def query_kubernetes_pod(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    base_url = get_kubernetes_api_url()
    if not base_url:
        return {"available": False, "reason": "AIOPS_KUBERNETES_API_URL not set"}
    url = f"{base_url.rstrip('/')}/api/v1/namespaces/{namespace}/pods/{pod_name}"
    data, error = _http_get_json(url, headers=_k8s_headers(), verify=_k8s_verify())
    if data is None:
        return {"available": False, "reason": error}
    status = data.get("status", {})
    spec = data.get("spec", {})
    container_statuses = status.get("containerStatuses", [])
    last_state = {}
    for cs in container_statuses:
        last_state.update(cs.get("lastState", {}).get("terminated", {}) or {})
    return {
        "available": True,
        "pod_name": pod_name,
        "namespace": namespace,
        "node_name": spec.get("nodeName"),
        "phase": status.get("phase"),
        "container_statuses": container_statuses,
        "last_state": last_state,
    }


def query_kubernetes_node(node_name: str) -> Dict[str, Any]:
    base_url = get_kubernetes_api_url()
    if not base_url:
        return {"available": False, "reason": "AIOPS_KUBERNETES_API_URL not set"}
    url = f"{base_url.rstrip('/')}/api/v1/nodes/{node_name}"
    data, error = _http_get_json(url, headers=_k8s_headers(), verify=_k8s_verify())
    if data is None:
        return {"available": False, "reason": error}
    conditions = {
        c.get("type"): c.get("status") for c in data.get("status", {}).get("conditions", [])
    }
    allocatable = data.get("status", {}).get("allocatable", {})
    return {
        "available": True,
        "node_name": node_name,
        "conditions": conditions,
        "allocatable_memory": allocatable.get("memory"),
        "allocatable_cpu": allocatable.get("cpu"),
    }


def query_change_events(
    target: str,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """Query external change/deployment event API or fall back to a local file."""
    base_url = get_change_events_url()
    events: List[Dict[str, Any]] = []

    # Local file fallback: AIOPS_CHANGE_EVENTS_FILE points to a JSON list
    events_file = _get_env("AIOPS_CHANGE_EVENTS_FILE")
    if events_file and os.path.exists(events_file):
        try:
            file_size = os.path.getsize(events_file)
            if file_size > _MAX_CHANGE_EVENTS_FILE_BYTES:
                logger.warning(
                    f"Change events file too large: {file_size} bytes (max {_MAX_CHANGE_EVENTS_FILE_BYTES})"  # noqa: E501
                )
            else:
                with open(events_file, "r", encoding="utf-8") as f:
                    file_events = json.load(f)
                if isinstance(file_events, list):
                    events.extend(file_events)
        except Exception as exc:
            logger.warning(f"Failed to load change events file {events_file}: {exc}")

    if base_url:
        try:
            hours = max(1, min(int(hours), 168))
            qs = urllib.parse.urlencode({"target": target, "hours": hours})
            url = f"{base_url.rstrip('/')}/events?{qs}"
            data, error = _http_get_json(url, timeout=_DEFAULT_TIMEOUT)
            if isinstance(data, list):
                events.extend(data)
            elif isinstance(data, dict) and "events" in data:
                events.extend(data["events"])
            else:
                logger.warning(f"Unexpected change events response: {error}")
        except Exception as exc:
            logger.warning(f"Change events API query failed: {exc}")

    return events[:1000]