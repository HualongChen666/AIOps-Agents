# -*- coding: utf-8 -*-
"""Direct end-to-end test of the backend heal_graph business loop."""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Local SQLite, no AI key, simulated repair execution
os.environ["POSTGRES_URL"] = "sqlite+aiosqlite:///e2e_direct.db"
os.environ["AI_ENABLED"] = "false"
os.environ["HEAL_EXECUTE_ENABLED"] = "false"
os.environ["HARDWARE_EXECUTE_ENABLED"] = "false"

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
import core.models  # noqa: F401
from core.heal_graph import HealState, run_heal
from core.db_engine import async_update_approval_status_by_alert
from core.command_guard import get_audit_log


def _pydantic_safe(obj):
    """Dump state / DB objects to JSON-safe primitives."""
    return json.loads(json.dumps(obj, default=str, ensure_ascii=False))


async def main():
    # 1. Create tables (sync engine, same file as the async app engine)
    sync_engine = create_engine("sqlite:///e2e_direct.db")
    Base.metadata.create_all(sync_engine)

    alert_id = f"CPU-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:-3]}"
    alert = {
        "id": alert_id,
        "metric": "cpu_percent",
        "title": "CPU high on host-01",
        "desc": "CPU usage is above 90%",
        "platform": "windows",
        "value": 95,
        "host": "host-01",
    }

    # 2. First pass: generate runbook, create pending approval
    print("=== First run_heal (should create pending approval) ===")
    state1 = HealState(alert=alert)
    state1 = await run_heal(state1)
    print(
        json.dumps(
            {
                "approval_status": state1.approval_status,
                "error": state1.error,
                "runbook_source": (
                    state1.runbook.get("source") if isinstance(state1.runbook, dict) else None
                ),
                "runbook_worst_risk": (
                    state1.runbook.get("worst_risk") if isinstance(state1.runbook, dict) else None
                ),
                "runbook_commands": (
                    state1.runbook.get("runbook", {}).get("commands")
                    if isinstance(state1.runbook, dict)
                    else None
                ),
            },
            default=str,
            ensure_ascii=False,
            indent=2,
        )
    )

    # 3. Approve via DB
    approved = await async_update_approval_status_by_alert(alert["id"], "approved")
    print("\n=== Approval persisted ===", approved)

    # 4. Second pass: approved -> simulated execution -> verify -> audit
    print("\n=== Second run_heal (should simulate and complete) ===")
    state2 = HealState(alert=alert)
    state2 = await run_heal(state2)
    print(
        json.dumps(
            {
                "approval_status": state2.approval_status,
                "error": state2.error,
                "fix_applied": state2.fix_applied,
                "executed_commands": state2.executed_commands,
                "repair_result": state2.repair_result,
            },
            default=str,
            ensure_ascii=False,
            indent=2,
        )
    )

    # 5. Audit trail
    print("\n=== Audit log ===")
    logs = get_audit_log(limit=50)
    for log in logs:
        print(json.dumps(_pydantic_safe(log), ensure_ascii=False, default=str))

    # 6. Persisted repair record
    print("\n=== RepairRecord rows in DB ===")
    async_engine = create_async_engine("sqlite+aiosqlite:///e2e_direct.db", echo=False)
    AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        from core.models import RepairRecord

        result = await session.execute(select(RepairRecord))
        rows = result.scalars().all()
        for row in rows:
            print(
                json.dumps(
                    {
                        "id": row.id,
                        "alert_id": row.alert_id,
                        "status": row.status,
                        "success": row.success,
                        "script_key": row.script_key,
                        "platform": row.platform,
                    },
                    default=str,
                    ensure_ascii=False,
                )
            )
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
