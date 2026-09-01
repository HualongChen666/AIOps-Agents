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


@router.get(
    "/cost-optimization",
    summary="成本优化建议",
    responses={
        200: {"description": "成本优化建议"},
        401: {"description": "未授权"},
    },
)
async def get_cost_optimization():
    """获取成本优化建议"""
    from core.cost_monitor import get_optimization_suggestions
    return {"status": "success", "suggestions": get_optimization_suggestions()}


@router.get(
    "/resource-cost",
    summary="资源成本",
    responses={
        200: {"description": "资源成本数据"},
        401: {"description": "未授权"},
    },
)
async def get_resource_cost():
    """获取资源成本数据"""
    from core.cost_monitor import get_resource_costs
    return {"status": "success", "resources": get_resource_costs()}


@router.get(
    "/llm-cost",
    summary="LLM成本",
    responses={
        200: {"description": "LLM成本数据"},
        401: {"description": "未授权"},
    },
)
async def get_llm_cost():
    """获取LLM成本数据"""
    from core.cost_monitor import get_llm_costs
    return {"status": "success", "llm_costs": get_llm_costs()}


@router.get(
    "/budget-management",
    summary="预算管理",
    responses={
        200: {"description": "预算管理数据"},
        401: {"description": "未授权"},
    },
)
async def get_budget_management():
    """获取预算管理数据"""
    from core.cost_monitor import get_budget_management
    return {"status": "success", "budgets": get_budget_management()}


@router.post(
    "/budget-management",
    summary="创建预算",
    responses={
        200: {"description": "预算创建成功"},
        401: {"description": "未授权"},
    },
)
async def create_budget(budget_data: dict):
    """创建新预算"""
    from core.cost_monitor import create_budget
    return {"status": "success", "budget": create_budget(budget_data)}


@router.post(
    "/cost-prediction",
    summary="成本预测",
    responses={
        200: {"description": "成本预测结果"},
        401: {"description": "未授权"},
    },
)
async def get_cost_prediction(data: dict):
    """获取成本预测"""
    from core.cost_monitor import predict_costs
    time_horizon = data.get("time_horizon", 30)
    return {"status": "success", "prediction": predict_costs(time_horizon)}


@router.get(
    "/cost-collection",
    summary="成本采集",
    responses={
        200: {"description": "成本采集状态"},
        401: {"description": "未授权"},
    },
)
async def get_cost_collection():
    """获取成本采集状态"""
    from core.cost_monitor import get_cost_collection_status
    return {"status": "success", "collection": get_cost_collection_status()}


@router.post(
    "/cost-collection/{id}/sync",
    summary="同步成本采集",
    responses={
        200: {"description": "同步成功"},
        401: {"description": "未授权"},
    },
)
async def sync_cost_collection(id: str):
    """同步成本采集"""
    from core.cost_monitor import sync_cost_collection
    return {"status": "success", "result": sync_cost_collection(id)}


@router.get(
    "/cost-monitoring",
    summary="成本监控",
    responses={
        200: {"description": "成本监控数据"},
        401: {"description": "未授权"},
    },
)
async def get_cost_monitoring():
    """获取成本监控数据"""
    from core.cost_monitor import get_cost_monitoring
    return {"status": "success", "monitoring": get_cost_monitoring()}


@router.post(
    "/cost-report",
    summary="成本报告",
    responses={
        200: {"description": "成本报告"},
        401: {"description": "未授权"},
    },
)
async def get_cost_report(data: dict):
    """生成成本报告"""
    from core.cost_monitor import generate_cost_report
    period = data.get("period", "monthly")
    return {"status": "success", "report": generate_cost_report(period)}
