# -*- coding: utf-8 -*-
"""
Tracing Visualization Router

Provides API endpoints for trace data visualization and analysis.
When no external tracing backend (Jaeger/Tempo) is configured,
endpoints fall back to deterministic synthetic traces so the UI
always has something to render.
"""

import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

router = APIRouter(prefix="/api/tracing", tags=["Tracing"])


def _parse_duration_ms(duration_str: Optional[str]) -> Optional[float]:
    if not duration_str:
        return None
    duration_str = duration_str.strip().lower()
    try:
        if duration_str.endswith("ms"):
            return float(duration_str[:-2])
        if duration_str.endswith("s"):
            return float(duration_str[:-1]) * 1000
        if duration_str.endswith("m"):
            return float(duration_str[:-1]) * 60_000
        return float(duration_str)
    except ValueError:
        return None


def _services() -> List[str]:
    from config import LINUX_HOSTS

    default = ["aiops-agent"]
    if LINUX_HOSTS:
        return [f"host-{i}" for i in range(min(len(LINUX_HOSTS), 5))] or default
    return default


def _generate_synthetic_trace(trace_id: str, seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate a deterministic synthetic trace from the trace_id."""
    digest = int(hashlib.md5(trace_id.encode()).hexdigest(), 16)
    rand = digest % 1000
    services = _services()
    span_count = 3 + (rand % 8)
    base_time = time.time() - (rand % 3600)

    spans: List[Dict[str, Any]] = []
    parent_id = ""
    for i in range(span_count):
        service = services[(rand + i) % len(services)]
        duration_ms = 10 + (rand * (i + 1)) % 450
        span_id = f"{trace_id[:16]}-{i:04x}"
        spans.append(
            {
                "span_id": span_id,
                "parent_id": parent_id if parent_id else None,
                "service": service,
                "operation": f"/api/v1/{service.replace('host-', '')}/{'health' if i % 2 == 0 else 'process'}",
                "start_time": datetime.fromtimestamp(base_time + i * 0.01, tz=timezone.utc).isoformat(),
                "duration_ms": duration_ms,
                "status": "error" if (rand + i) % 13 == 0 else "ok",
                "tags": {"synthetic": True, "index": i},
            }
        )
        parent_id = span_id

    return {
        "trace_id": trace_id,
        "spans": spans,
        "services": sorted({s["service"] for s in spans}),
        "total_duration_ms": sum(s["duration_ms"] for s in spans),
        "error_count": sum(1 for s in spans if s["status"] == "error"),
    }


def _recent_synthetic_traces(limit: int) -> List[Dict[str, Any]]:
    now = int(time.time())
    traces = []
    for i in range(limit):
        trace_id = hashlib.md5(f"synthetic-{now - i * 60}".encode()).hexdigest()[:16]
        trace = _generate_synthetic_trace(trace_id, seed=i)
        traces.append(
            {
                "trace_id": trace_id,
                "root_service": trace["services"][0] if trace["services"] else "aiops-agent",
                "operation": "/api/v1/status",
                "start_time": trace["spans"][0]["start_time"],
                "duration_ms": trace["total_duration_ms"],
                "error_count": trace["error_count"],
            }
        )
    return traces


def _try_real_backend(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    if not url:
        return None
    try:
        import httpx

        resp = httpx.get(url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug(f"Real tracing backend query failed: {exc}")
        return None


@router.get(
    "/dashboard",
    summary="获取追踪仪表板",
    responses={200: {"description": "仪表板数据"}, 500: {"description": "获取失败"}},
)
async def get_tracing_dashboard():
    """Get tracing dashboard overview."""
    try:
        jaeger_url = os.getenv("JAEGER_QUERY_URL")
        real = _try_real_backend(f"{jaeger_url}/api/services") if jaeger_url else None
        if real:
            services = real.get("data", [])
            return {
                "status": "success",
                "data": {
                    "total_traces": real.get("total", 0),
                    "error_rate": 0.0,
                    "avg_latency": 0.0,
                    "services": services,
                    "time_range": "last_24h",
                    "source": "jaeger",
                },
            }

        from core.alert_engine import alert_history

        services = _services()
        total = max(len(alert_history), 24)
        errors = sum(1 for a in alert_history if a.get(
            "level", "").lower() in ("error", "critical"))
        error_rate = round(errors / max(total, 1), 4)
        return {
            "status": "success",
            "data": {
                "total_traces": total,
                "error_rate": error_rate,
                "avg_latency": 42.0,
                "services": services,
                "time_range": "last_24h",
                "source": "synthetic",
                "message": "Connect to Jaeger/Tempo for live visualization",
            },
        }
    except Exception as e:
        logger.error(f"Error getting tracing dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/traces",
    summary="列出追踪记录",
    responses={200: {"description": "追踪记录列表"}, 500: {"description": "获取失败"}},
)
async def list_traces(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    limit: int = Query(20, ge=1, le=100, description="Number of traces to return"),
    min_duration: Optional[str] = Query(None, description="Minimum duration (e.g., '100ms')"),
    max_duration: Optional[str] = Query(None, description="Maximum duration (e.g., '1s')"),
):
    """List traces with optional filters."""
    try:
        jaeger_url = os.getenv("JAEGER_QUERY_URL")
        if jaeger_url:
            real = _try_real_backend(
                f"{jaeger_url}/api/traces",
                {"service": service_name, "limit": limit} if service_name else {"limit": limit},
            )
            if real:
                return {"status": "success", "data": real.get(
                    "data", []), "total": real.get("total", 0)}

        min_ms = _parse_duration_ms(min_duration) if min_duration else None
        max_ms = _parse_duration_ms(max_duration) if max_duration else None
        traces = _recent_synthetic_traces(limit * 3)
        filtered = [
            t
            for t in traces
            if (not service_name or t["root_service"] == service_name)
            and (min_ms is None or t["duration_ms"] >= min_ms)
            and (max_ms is None or t["duration_ms"] <= max_ms)
        ][:limit]
        return {
            "status": "success",
            "data": filtered,
            "total": len(filtered),
            "source": "synthetic" if not jaeger_url else "jaeger",
        }
    except Exception as e:
        logger.error(f"Error listing traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/traces/{trace_id}",
    summary="获取追踪详情",
    responses={200: {"description": "追踪详情"}, 500: {"description": "获取失败"}},
)
async def get_trace_details(trace_id: str):
    """Get detailed information about a specific trace."""
    try:
        jaeger_url = os.getenv("JAEGER_QUERY_URL")
        if jaeger_url:
            real = _try_real_backend(f"{jaeger_url}/api/traces/{trace_id}")
            if real:
                return {"status": "success", "data": real, "source": "jaeger"}

        trace = _generate_synthetic_trace(trace_id)
        return {
            "status": "success",
            "data": trace,
            "source": "synthetic",
            "message": "Connect to Jaeger/Tempo for live trace details",
        }
    except Exception as e:
        logger.error(f"Error getting trace details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/topology",
    summary="获取服务调用拓扑",
    responses={200: {"description": "服务拓扑数据"}, 500: {"description": "获取失败"}},
)
async def get_service_topology():
    """Get service call topology graph."""
    try:
        services = _services()
        nodes = [{"id": s, "type": "service", "name": s} for s in services]
        nodes.append({"id": "aiops-agent", "type": "gateway", "name": "AIOps Agent"})
        edges = []
        for i, s in enumerate(services):
            edges.append({"source": "aiops-agent", "target": s, "calls_per_sec": 10 + i})
            if i > 0:
                edges.append({"source": services[i - 1], "target": s, "calls_per_sec": 5 + i})
        return {
            "status": "success",
            "data": {"nodes": nodes, "edges": edges},
            "source": "synthetic",
            "message": "Connect to Jaeger/Tempo for live topology",
        }
    except Exception as e:
        logger.error(f"Error getting service topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/performance/hotspots",
    summary="获取性能热点分析",
    responses={200: {"description": "性能热点数据"}, 500: {"description": "获取失败"}},
)
async def get_performance_hotspots(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    time_range: str = Query("1h", description="Time range (e.g., '1h', '24h')"),
):
    """Get performance hotspots analysis."""
    try:
        services = _services()
        if service_name and service_name in services:
            services = [service_name]
        slow = []
        bottlenecks = []
        for s in services:
            slow.append(
                {
                    "service": s,
                    "operation": "/api/v1/process",
                    "avg_duration_ms": 120 + (hash(s) % 200),
                    "p99_duration_ms": 450 + (hash(s) % 300),
                }
            )
            bottlenecks.append(
                {
                    "resource": "cpu" if hash(s) % 2 == 0 else "memory",
                    "service": s,
                    "utilization": 0.5 + (hash(s) % 50) / 100.0,
                }
            )
        return {
            "status": "success",
            "data": {
                "slow_operations": sorted(slow, key=lambda x: x["avg_duration_ms"], reverse=True)[:5],
                "high_latency_endpoints": slow[:3],
                "resource_bottlenecks": bottlenecks,
                "time_range": time_range,
            },
            "source": "synthetic",
        }
    except Exception as e:
        logger.error(f"Error getting performance hotspots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/errors/analysis",
    summary="获取错误分析",
    responses={200: {"description": "错误分析数据"}, 500: {"description": "获取失败"}},
)
async def get_error_analysis(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    time_range: str = Query("1h", description="Time range (e.g., '1h', '24h')"),
):
    """Get error analysis from traces."""
    try:
        from core.alert_engine import alert_history

        services = _services()
        if service_name:
            services = [service_name]
        error_alerts = [a for a in alert_history if a.get(
            "level", "").lower() in ("error", "critical")]
        error_count = len(error_alerts) or sum(hash(s) % 5 for s in services)
        error_types = list({a.get("title", "unknown")
                           for a in error_alerts}) or ["Timeout", "ConnectionError"]
        affected = list({a.get("source_service") or a.get("source", s)
                        for a in error_alerts for s in services}) or services
        return {
            "status": "success",
            "data": {
                "error_count": error_count,
                "error_rate": round(error_count / max(100, error_count + 50), 4),
                "error_types": error_types,
                "affected_operations": [{"service": s, "operation": "/api/v1/process"} for s in affected[:5]],
                "time_range": time_range,
            },
            "source": "synthetic",
        }
    except Exception as e:
        logger.error(f"Error getting error analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/export/trace-config",
    summary="导出追踪配置",
    responses={200: {"description": "追踪配置"}, 500: {"description": "导出失败"}},
)
async def export_trace_config():
    """Export tracing configuration for dashboard setup."""
    try:
        from config import OTEL_COLLECTOR_ENDPOINT

        return {
            "status": "success",
            "data": {
                "otlp_endpoint": OTEL_COLLECTOR_ENDPOINT,
                "jaeger_ui": os.getenv("JAEGER_UI_URL", "http://localhost:1668"),
                "grafana_datasource": os.getenv("GRAFANA_DATASOURCE_URL", "http://localhost:3000"),
                "tempo_ui": os.getenv("TEMPO_UI_URL", "http://localhost:3200"),
            },
        }
    except Exception as e:
        logger.error(f"Error exporting trace config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
