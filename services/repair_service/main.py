"""AIOps Repair Service.

Creates repair tasks and executes them after human approval.
"""

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from core.auto_heal import approve_repair as core_approve_repair
from core.heal_graph import HealState, run_heal

app = FastAPI(title="AIOps Repair Service", version="0.1.0")

repairs: Dict[str, Dict[str, Any]] = {}


class RepairPayload(BaseModel):
    alert_id: str
    host: str = "unknown"
    platform: str = "windows"
    metric: str = ""
    metric_value: Any = None
    description: str = ""
    params: Dict[str, Any] = {}
    requested_by: str = "gateway"
    auto_approve: bool = False


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/repairs")
async def create_repair(payload: RepairPayload) -> Dict[str, Any]:
    repair_id = f"repair-{payload.alert_id}-{len(repairs)}"
    repairs[repair_id] = payload.model_dump()
    repairs[repair_id]["status"] = "pending"
    return {"task_id": repair_id, "status": "pending"}


@app.post("/repairs/{repair_id}/approve")
async def approve_repair(repair_id: str) -> Dict[str, Any]:
    if repair_id not in repairs:
        raise HTTPException(status_code=404, detail="repair not found")

    data = repairs[repair_id]
    alert_id = data["alert_id"]
    alert = {
        "id": alert_id,
        "title": data.get("description") or "repair",
        "host": data.get("host", "unknown"),
        "platform": data.get("platform", "windows"),
        "metric": data.get("metric", ""),
        "metric_value": data.get("metric_value"),
        "description": data.get("description", ""),
        "params": data.get("params", {}),
    }

    # Persist the explicit human/machine approval before executing so that
    # heal_graph.apply_fix sees an approved record instead of stopping at HITL.
    approval_result = await core_approve_repair(alert_id, approver="repair_service")
    if not approval_result.get("success"):
        _logger = __import__("logging").getLogger(__name__)
        _logger.warning("Failed to persist approval: %s", approval_result)

    final_state = await run_heal(HealState(alert=alert))
    success = bool(final_state.fix_applied and not final_state.error)
    output = final_state.runbook or final_state.analysis or str(final_state)

    repairs[repair_id]["status"] = "completed" if success else "failed"
    return {
        "task_id": repair_id,
        "alert_id": alert_id,
        "success": success,
        "status": repairs[repair_id]["status"],
        "output": output,
    }


if __name__ == "__main__":
    uvicorn.run(
        "services.repair_service.main:app",
        host="0.0.0.0",  # nosec B104
        port=int(sys.argv[1]) if len(sys.argv) > 1 else 8002,
    )
