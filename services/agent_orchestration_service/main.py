"""AIOps Agent Orchestration Service.

Provides a single endpoint to run the full heal workflow for a given alert.
"""

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from core.heal_graph import HealState, run_heal

app = FastAPI(title="AIOps Agent Orchestration Service", version="0.1.0")


class OrchestratePayload(BaseModel):
    alert: Dict[str, Any]


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/orchestrate")
async def orchestrate(payload: OrchestratePayload) -> Dict[str, Any]:
    final_state = await run_heal(HealState(alert=payload.alert))
    return {
        "alert_id": (payload.alert or {}).get("id"),
        "success": bool(final_state.fix_applied and not final_state.error),
        "fix_applied": final_state.fix_applied,
        "error": final_state.error,
        "analysis": final_state.analysis,
        "runbook": final_state.runbook,
        "verification": final_state.verification,
    }


if __name__ == "__main__":
    uvicorn.run(
        "services.agent_orchestration_service.main:app",
        host="0.0.0.0",  # nosec B104
        port=int(sys.argv[1]) if len(sys.argv) > 1 else 8003,
    )
