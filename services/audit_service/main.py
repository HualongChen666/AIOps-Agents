"""AIOps Audit Service.

Exposes audit logs and allows recording new audit events.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from fastapi import FastAPI, Query

from core.command_guard import get_audit_log

app = FastAPI(title="AIOps Audit Service", version="0.1.0")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.get("/logs")
async def list_logs(limit: Optional[int] = Query(100, ge=1, le=5000)) -> List[Dict[str, Any]]:
    """Return recent audit logs."""
    if limit is None:
        limit = 100
    logs = await asyncio.to_thread(get_audit_log, limit)
    return logs if isinstance(logs, list) else []


if __name__ == "__main__":
    uvicorn.run(
        "services.audit_service.main:app",
        host="0.0.0.0",  # nosec B104
        port=int(sys.argv[1]) if len(sys.argv) > 1 else 8004,
    )
