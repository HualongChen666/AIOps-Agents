# -*- coding: utf-8 -*-
"""成本监控与费用预测 API（占位实现）

提供三条 GET 接口：
- /api/cost/collect   → 返回最近费用记录（list）
- /api/cost/forecast?days=30  → 返回未来 `days` 天的费用预测（list）
- /api/cost/budget    → 返回预算使用情况与建议（dict）

全部受 `admin` 角色保护（调用 `core.rbac.role_required`).
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from core.cost_monitor import budget_status, collect_costs, forecast_costs

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get(
    "/collect",
    summary="获取成本数据",
    responses={
        200: {
            "description": "成本数据",
            "content": {
                "application/json": {
                    "example": {"costs": [{"date": "2026-07-01", "amount": 100.0}]}
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足(需要管理员)"},
        404: {"description": "无成本数据"},
    },
)
async def get_collect(
    start_date: str = Query(default=None, description="Start date in ISO format (YYYY-MM-DD)"),
    end_date: str = Query(default=None, description="End date in ISO format (YYYY-MM-DD)")
):
    # Validate date format if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    cost_data = collect_costs(start_date=start_date, end_date=end_date)
    if not cost_data:
        raise HTTPException(status_code=404, detail="No cost data found")
    return {"costs": cost_data}


@router.get(
    "/forecast",
    summary="费用预测",
    responses={
        200: {
            "description": "费用预测数据",
            "content": {
                "application/json": {
                    "example": {
                        "days": 30,
                        "forecast": [{"date": "2026-07-02", "predicted_amount": 105.0}],
                    }
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足(需要管理员)"},
        404: {"description": "预测数据不可用"},
    },
)
async def get_forecast(days: int = Query(default=None, description="Forecast horizon days")):
    days = days or 30
    
    # Validate days parameter
    if days <= 0:
        raise HTTPException(status_code=422, detail="Days must be a positive integer")
    
    cost_data = forecast_costs(days)
    if not cost_data:
        raise HTTPException(status_code=404, detail="Forecast data unavailable")
    return {"days": days, "forecast": cost_data}


@router.get(
    "/budget",
    summary="预算状态",
    responses={
        200: {
            "description": "预算状态",
            "content": {
                "application/json": {
                    "example": {
                        "budget": 1000.0,
                        "used": 500.0,
                        "remaining": 500.0,
                        "status": "normal",
                    }
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足(需要管理员)"},
    },
)
async def get_budget(
    detailed: bool = Query(default=False, description="Return detailed budget breakdown")
):
    return budget_status(detailed=detailed)
