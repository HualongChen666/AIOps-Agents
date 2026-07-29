import logging
"""AIOps Alert Service.

Receives normalized or raw alert payloads and routes them to the auto-heal
workflow. This service is the entry point for the remote microservice mode.
"""

import sys
from pathlib import Path
from typing import Any, Dict, cast

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os

import httpx
import uvicorn
from fastapi import FastAPI

from core.auto_heal import try_auto_heal

try:
    from core.db_engine import async_insert_alert
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    async_insert_alert = None  # type: ignore[assignment]

app = FastAPI(title="AIOps Alert Service", version="0.1.0")

_AGENT_ORCH_URL = os.getenv("AGENT_ORCHESTRATION_SERVICE_URL", "").rstrip("/")
_HTTP_TIMEOUT = float(os.getenv("ALERT_SERVICE_HTTP_TIMEOUT", "10.0"))


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


async def _persist_alert(alert: Dict[str, Any]) -> None:
    """Persist the alert to AlertHistory when storage is available."""
    if async_insert_alert is None:
        return
    try:
        await async_insert_alert(alert)
    except Exception as exc:  # pragma: no cover
        _logger = __import__("logging").getLogger(__name__)
        _logger.warning("Failed to persist alert history: %s", exc)


async def _call_agent_orchestration(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Forward the alert to the agent orchestration service."""
    if not _AGENT_ORCH_URL:
        raise RuntimeError("AGENT_ORCHESTRATION_SERVICE_URL not configured")
    url = f"{_AGENT_ORCH_URL}/orchestrate"
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json={"alert": alert})
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())


@app.post("/process")
async def process_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single alert through the auto-heal workflow.

    In remote/microservice mode this forwards the alert to the
    agent_orchestration_service. In local mode it falls back to the in-process
    core.try_auto_heal.
    """
    await _persist_alert(alert)

    if _AGENT_ORCH_URL:
        try:
            result = await _call_agent_orchestration(alert)
            return {"processed": 1, "result": result, "source": "agent_orchestration"}
        except Exception as exc:  # pragma: no cover
            _logger = __import__("logging").getLogger(__name__)
            _logger.warning(
                "agent_orchestration call failed, falling back to local try_auto_heal: %s",
                exc,
            )

    result = await try_auto_heal(alert)
    return {"processed": 1, "result": result, "source": "local"}


if __name__ == "__main__":
    uvicorn.run(
        "services.alert_service.main:app",
        host="0.0.0.0",  # nosec B104
        port=int(sys.argv[1]) if len(sys.argv) > 1 else 8001,
    )