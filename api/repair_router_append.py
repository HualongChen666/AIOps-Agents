# -*- coding: utf-8 -*-
"""
Repair Router Append
修复路由补充；全部数据来自真实的修复引擎与 auto_heal 脚本库，
不再返回硬编码示例记录 / 指标。
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from core.authentication import get_current_active_user
from core.auto_heal import get_pending_approvals, repair_script_library
from core.rbac import role_required
from core.repair_engine import (
    get_repair_history as _engine_get_repair_history,
    get_repair_scripts,
)

router = APIRouter(prefix="/api/repair", tags=["修复"])


def _history_records(limit: int = 50) -> List[Dict[str, Any]]:
    return _engine_get_repair_history(limit)


def _success_rate(records: List[Dict[str, Any]]) -> float:
    if not records:
        return 0.0
    success = sum(1 for r in records if r.get("success"))
    return success / len(records)


@router.get("/repair-history")
async def get_repair_history_endpoint(user=Depends(get_current_active_user)):
    """获取修复历史（真实修复引擎历史）"""
    records = _history_records(50)
    return {"status": "success", "history": records, "total": len(records)}


@router.get("/repair-templates")
async def get_repair_templates(user=Depends(get_current_active_user)):
    """获取修复模板（来自真实修复脚本库）"""
    scripts = get_repair_scripts()
    templates = [
        {
            "id": script["key"],
            "name": script["name"],
            "description": script["description"],
            "risk": script["risk"],
            "params": script["params"],
        }
        for script in scripts
    ]
    return {"status": "success", "templates": templates}


@router.get("/repair-metrics")
async def get_repair_metrics(user=Depends(get_current_active_user)):
    """获取修复指标（由真实历史计算）"""
    records = _engine_get_repair_history(500)
    total = len(records)
    successful = sum(1 for r in records if r.get("success"))
    failed = total - successful
    return {
        "status": "success",
        "metrics": {
            "total_repairs": total,
            "successful_repairs": successful,
            "failed_repairs": failed,
            "success_rate": _success_rate(records),
            "template_count": len(get_repair_scripts()),
        },
    }


@router.get("/repair-policies")
async def get_repair_policies(user=Depends(get_current_active_user)):
    """获取修复策略（来自真实脚本库的审批要求）"""
    policies = [
        {
            "id": key,
            "name": script.name,
            "platforms": [p.value for p in script.platforms],
            "risk_level": str(getattr(script.risk_level, "value", script.risk_level)),
            "requires_approval": script.requires_approval,
            "enabled": True,
        }
        for key, script in repair_script_library.scripts.items()
    ]
    return {"status": "success", "policies": policies}


@router.post("/repair-policies")
async def update_repair_policies(policy: dict, user=Depends(role_required("admin"))):
    """更新修复策略（调整真实脚本库的审批要求）"""
    policy_id = policy.get("id")
    script = repair_script_library.get_script(policy_id) if policy_id else None
    if script is None:
        raise HTTPException(status_code=404, detail=f"Unknown repair policy: {policy_id}")
    if "requires_approval" in policy:
        script.requires_approval = bool(policy["requires_approval"])
    return {
        "status": "success",
        "policy": {
            "id": script.script_key,
            "name": script.name,
            "requires_approval": script.requires_approval,
        },
        "message": "Policy updated successfully",
    }


@router.get("/repair-status")
async def get_repair_status(user=Depends(get_current_active_user)):
    """获取修复状态（真实待审批 / 最近修复）"""
    try:
        approvals = await get_pending_approvals()
    except Exception:
        approvals = []
    records = _engine_get_repair_history(1)
    return {
        "status": "success",
        "status": {
            "pending_repairs": len(approvals),
            "last_repair": records[0].get("time") if records else None,
            "registered_scripts": len(repair_script_library.scripts),
        },
    }


@router.get("/repair-recommendations")
async def get_repair_recommendations(user=Depends(get_current_active_user)):
    """获取修复建议（基于真实历史中的失败记录）"""
    records = _engine_get_repair_history(100)
    recommendations = [
        {
            "id": record.get("id"),
            "type": "retry",
            "priority": "high" if record.get("risk") in ("high", "critical") else "medium",
            "description": f"Retry failed repair: {record.get('script_name') or record.get('script_key')}",
            "script_key": record.get("script_key"),
            "error": record.get("error", ""),
        }
        for record in records
        if not record.get("success")
    ]
    return {"status": "success", "recommendations": recommendations}


@router.get("/repair-automation")
async def get_repair_automation(user=Depends(get_current_active_user)):
    """获取修复自动化（真实脚本库 / 历史成功率）"""
    records = _engine_get_repair_history(500)
    auto_scripts = [s for s in repair_script_library.scripts.values() if not s.requires_approval]
    return {
        "status": "success",
        "automation": {
            "enabled": len(auto_scripts) > 0,
            "auto_repair_rules": len(auto_scripts),
            "total_scripts": len(repair_script_library.scripts),
            "success_rate": _success_rate(records),
        },
    }
