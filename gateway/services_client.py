"""Microservice gateway client with in-process fallback.

When ``MICROSERVICE_MODE`` is set to ``remote`` the client forwards calls to the
standalone ``services/`` FastAPI endpoints. In any other case it falls back to
calling ``core.*`` functions in-process, which is what the converged ``main.py"
gateway uses for local/e2e runs.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, cast

import httpx

import config

logger = logging.getLogger(__name__)

_http_client: Optional[httpx.AsyncClient] = None

# Default add-on service URLs are centralized in config.py so that
# `MICROSERVICE_MODE=remote` automatically has usable endpoints.
_DEFAULT_SERVICE_URLS: Dict[str, str] = config.ADDON_SERVICE_URLS


def _get_http_client() -> httpx.AsyncClient:
    """Return a lazily-created async HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=float(os.getenv("MICROSERVICE_TIMEOUT", "15.0")))
    return _http_client


def _is_remote() -> bool:
    return config.MICROSERVICE_MODE == "remote"


async def _close_http_client() -> None:
    """Close the shared HTTP client (called by main.py lifespan)."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None


async def _remote_alert_process(alert: Dict[str, Any]) -> Any:
    """POST a raw alert to the alert_service /process endpoint."""
    base = os.environ["ALERT_SERVICE_URL"].rstrip("/")
    client = _get_http_client()
    resp = await client.post(f"{base}/process", json=alert)
    resp.raise_for_status()
    return resp.json()


try:
    from core.auto_heal import try_auto_heal as _try_auto_heal

    _AUTO_HEAL_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _AUTO_HEAL_AVAILABLE = False
    _try_auto_heal = None  # type: ignore[assignment]

try:
    from core.heal_graph import HealState
    from core.heal_graph import run_heal as _run_heal

    _HEAL_GRAPH_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _HEAL_GRAPH_AVAILABLE = False
    _run_heal = None  # type: ignore[assignment]
    HealState = None  # type: ignore[assignment, misc]

try:
    from core.rag_engine import search_similar as _rag_search

    _RAG_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _RAG_AVAILABLE = False
    _rag_search = None  # type: ignore[assignment]

try:
    from core.ai.llm_router import get_llm_router as _get_llm_router

    _LLM_ROUTER_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _LLM_ROUTER_AVAILABLE = False
    _get_llm_router = None  # type: ignore[assignment]

try:
    from core.topology_engine import get_full_link_topology as _get_full_link_topology

    _TOPOLOGY_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _TOPOLOGY_AVAILABLE = False
    _get_full_link_topology = None  # type: ignore[assignment]


async def process_alert(alert: Dict[str, Any]) -> Any:
    """Process an alert through the alert_service (remote) or core.try_auto_heal (local)."""
    if _is_remote() and os.getenv("ALERT_SERVICE_URL"):
        try:
            return await _remote_alert_process(alert)
        except Exception as exc:
            logger.warning(f"remote alert_service call failed, falling back: {exc}")

    if not _AUTO_HEAL_AVAILABLE or _try_auto_heal is None:
        raise RuntimeError("Auto-heal engine is not available")
    return await _try_auto_heal(alert)


async def approve_and_execute(
    alert_id: str, alert: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Approve and run the repair workflow via repair_service or core.heal_graph."""
    if _is_remote() and os.getenv("REPAIR_SERVICE_URL"):
        try:
            base = os.environ["REPAIR_SERVICE_URL"].rstrip("/")
            client = _get_http_client()
            payload = {
                "alert_id": alert_id,
                "host": (alert or {}).get("host", (alert or {}).get("instance", "unknown")),
                "platform": (alert or {}).get("platform", "linux").lower(),
                "metric": (alert or {}).get("metric", ""),
                "metric_value": (alert or {}).get("metric_value"),
                "description": (alert or {}).get("desc", ""),
                "params": (alert or {}).get("params", {}),
                "requested_by": "gateway",
                "auto_approve": True,
            }
            created = await client.post(f"{base}/repairs", json=payload)
            created.raise_for_status()
            task = created.json()
            task_id = task.get("task_id") or task.get("id")
            if not task_id:
                return {"success": False, "error": "repair_service did not return a task_id"}
            approved = await client.post(f"{base}/repairs/{task_id}/approve")
            approved.raise_for_status()
            return cast(dict[str, Any], approved.json())
        except Exception as exc:
            logger.warning(f"remote repair_service call failed, falling back: {exc}")

    if not _HEAL_GRAPH_AVAILABLE or _run_heal is None or HealState is None:
        raise RuntimeError("Heal graph engine is not available")

    target_alert = alert or {"id": alert_id, "title": "Auto-heal approval", "platform": "windows"}
    final_state = await _run_heal(HealState(alert=target_alert))
    success = bool(final_state.fix_applied and not final_state.error)
    result: Dict[str, Any] = {
        "alert_id": alert_id,
        "success": success,
        "status": "completed" if success else "pending",
        "message": "修复工作流已完成" if success else "修复工作流尚未完成",
        "fix_applied": final_state.fix_applied,
        "verification": final_state.verification,
    }
    if final_state.runbook:
        if isinstance(final_state.runbook, (str, dict, list, int, float, bool)):
            result["output"] = final_state.runbook
        else:
            result["output"] = str(final_state.runbook)
    elif final_state.analysis:
        result["output"] = final_state.analysis
    else:
        result["output"] = ""
    return result


async def _remote_call(
    service_url_env: str,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    """Generic remote microservice call."""
    url_value = _DEFAULT_SERVICE_URLS.get(service_url_env)
    if not url_value:
        raise RuntimeError(f"{service_url_env} is not configured and no default URL is available")
    base = url_value.rstrip("/")
    client = _get_http_client()
    url = f"{base}{path}"
    method = method.upper()
    if method == "GET":
        resp = await client.get(url)
    elif method == "POST":
        resp = await client.post(url, json=payload or {})
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    resp.raise_for_status()
    return resp.json()


async def remote_rag_query(query: str, top_k: int = 5) -> Any:
    """Query the RAG add-on service, falling back to the in-process RAG engine."""
    if _is_remote() and os.getenv("RAG_SERVICE_URL"):
        try:
            return await _remote_call(
                "RAG_SERVICE_URL", "POST", "/search", {"query": query, "top_k": top_k}
            )
        except Exception as exc:
            logger.warning(f"remote RAG service call failed, falling back: {exc}")

    if not _RAG_AVAILABLE or _rag_search is None:
        raise RuntimeError("RAG engine is not available")
    return await asyncio.to_thread(_rag_search, query, top_k=top_k)


async def remote_llm_route(prompt: str, models: Optional[List[str]] = None) -> Any:
    """Route a prompt through the LLM router add-on service, falling back to the in-process LLM router."""
    if _is_remote() and os.getenv("LLM_ROUTER_SERVICE_URL"):
        payload: Dict[str, Any] = {"prompt": prompt}
        if models:
            payload["force_model"] = models[0]
        try:
            return await _remote_call("LLM_ROUTER_SERVICE_URL", "POST", "/route", payload)
        except Exception as exc:
            logger.warning(f"remote LLM router service call failed, falling back: {exc}")

    if not _LLM_ROUTER_AVAILABLE or _get_llm_router is None:
        raise RuntimeError("LLM router is not available")
    generate_kwargs: Dict[str, Any] = {"system": "", "temperature": 0.3, "max_new_tokens": 1500}
    if models:
        generate_kwargs["force_model"] = models[0]
    return await _get_llm_router().generate(prompt, **generate_kwargs)


async def remote_topology() -> Any:
    """Fetch topology nodes and edges from the observability add-on service, falling back to the in-process topology engine."""
    if _is_remote() and os.getenv("TOPOLOGY_SERVICE_URL"):
        try:
            nodes = await _remote_call("TOPOLOGY_SERVICE_URL", "GET", "/nodes")
            edges = await _remote_call("TOPOLOGY_SERVICE_URL", "GET", "/edges")
            return {
                "nodes": nodes.get("nodes", []),
                "edges": edges.get("edges", []),
            }
        except Exception as exc:
            logger.warning(f"remote topology service call failed, falling back: {exc}")

    if not _TOPOLOGY_AVAILABLE or _get_full_link_topology is None:
        raise RuntimeError("Topology engine is not available")
    return await _get_full_link_topology()


async def remote_incident_list() -> Any:
    """List methods available on the incident response add-on service."""
    return await _remote_call(
        "INCIDENT_RESPONSE_SERVICE_URL", "POST", "/incident-response/list_methods", {}
    )


async def remote_datadog_query(config: Dict[str, Any]) -> Any:
    """Query a Datadog metric through the Datadog integration add-on."""
    return await _remote_call(
        "DATADOG_INTEGRATION_SERVICE_URL",
        "POST",
        "/datadog-integration/query-metrics",
        {"config": config},
    )


async def remote_grafana_query(config: Dict[str, Any]) -> Any:
    """Query Grafana dashboards through the Grafana integration add-on."""
    return await _remote_call(
        "GRAFANA_INTEGRATION_SERVICE_URL",
        "POST",
        "/grafana-integration/query-data",
        {"config": config},
    )


async def remote_elk_search(config: Dict[str, Any]) -> Any:
    """Search an Elasticsearch index through the ELK stack add-on."""
    return await _remote_call(
        "ELK_STACK_SERVICE_URL",
        "POST",
        "/elk-stack/search-query",
        {"config": config},
    )
