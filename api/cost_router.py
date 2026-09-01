# -*- coding: utf-8 -*-
"""成本监控与费用预测 API（占位实现）

提供三条 GET 接口：
- /api/cost/collect   → 返回最近费用记录（list）
- /api/cost/forecast?days=30  → 返回未来 `days` 天的费用预测（list）
- /api/cost/budget    → 返回预算使用情况与建议（dict）

全部受 `admin` 角色保护（调用 `core.rbac.role_required`).
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

try:
    from core.authentication import get_current_active_user
except ImportError:
    # Fallback for testing
    async def get_current_active_user():
        return None

try:
    from core.rbac import role_required
except ImportError:
    # Fallback for testing
    def role_required(role):
        def decorator(func):
            return func
        return decorator
from core.cost_monitor import (
    budget_status,
    collect_costs,
    forecast_costs,
    get_optimization_suggestions,
    get_resource_costs,
    get_llm_costs,
    get_budget_management,
    create_budget,
    predict_costs,
    get_cost_collection_status,
    sync_cost_collection,
    get_cost_monitoring,
    generate_cost_report,
)

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
    end_date: str = Query(default=None, description="End date in ISO format (YYYY-MM-DD)"),
    user=Depends(get_current_active_user) if get_current_active_user else None,
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
async def get_forecast(days: int = Query(default=None, description="Forecast horizon days"), user=Depends(get_current_active_user) if get_current_active_user else None):
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
    detailed: bool = Query(default=False, description="Return detailed budget breakdown"),
    user=Depends(get_current_active_user) if get_current_active_user else None,
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
async def get_cost_optimization(user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取成本优化建议"""
    suggestions = get_optimization_suggestions()
    return {"status": "success", "suggestions": suggestions}


@router.get(
    "/resource-cost",
    summary="资源成本",
    responses={
        200: {"description": "资源成本数据"},
        401: {"description": "未授权"},
    },
)
async def get_resource_cost(user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取资源成本数据"""
    costs = get_resource_costs()
    return {"status": "success", "resources": costs}


@router.get(
    "/llm-cost",
    summary="LLM成本",
    responses={
        200: {"description": "LLM成本数据"},
        401: {"description": "未授权"},
    },
)
async def get_llm_cost(user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取LLM成本数据"""
    llm_costs = get_llm_costs()
    return {"status": "success", "llm_costs": llm_costs}


@router.get(
    "/budget-management",
    summary="预算管理",
    responses={
        200: {"description": "预算管理数据"},
        401: {"description": "未授权"},
    },
)
async def get_budget_management(user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取预算管理数据"""
    budgets = get_budget_management()
    return {"status": "success", "budgets": budgets}


@router.post(
    "/budget-management",
    summary="创建预算",
    responses={
        200: {"description": "预算创建成功"},
        401: {"description": "未授权"},
    },
)
async def create_budget_endpoint(budget_data: dict, user=Depends(role_required("admin")) if role_required else None):
    """创建新预算"""
    budget = create_budget(budget_data)
    return {"status": "success", "budget": budget}


@router.post(
    "/cost-prediction",
    summary="成本预测",
    responses={
        200: {"description": "成本预测结果"},
        401: {"description": "未授权"},
    },
)
async def get_cost_prediction(data: dict, user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取成本预测"""
    time_horizon = data.get("time_horizon", 30)
    prediction = predict_costs(time_horizon)
    return {"status": "success", "prediction": prediction}


@router.get(
    "/cost-collection",
    summary="成本采集",
    responses={
        200: {"description": "成本采集状态"},
        401: {"description": "未授权"},
    },
)
async def get_cost_collection(user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取成本采集状态"""
    status = get_cost_collection_status()
    return {"status": "success", "collection": status}


@router.post(
    "/cost-collection/{id}/sync",
    summary="同步成本采集",
    responses={
        200: {"description": "同步成功"},
        401: {"description": "未授权"},
    },
)
async def sync_cost_collection_endpoint(id: str, user=Depends(role_required("admin")) if role_required else None):
    """同步成本采集"""
    result = sync_cost_collection(id)
    return {"status": "success", "result": result}


@router.get(
    "/cost-monitoring",
    summary="成本监控",
    responses={
        200: {"description": "成本监控数据"},
        401: {"description": "未授权"},
    },
)
async def get_cost_monitoring(user=Depends(get_current_active_user) if get_current_active_user else None):
    """获取成本监控数据"""
    monitoring = get_cost_monitoring()
    return {"status": "success", "monitoring": monitoring}


@router.post(
    "/cost-report",
    summary="成本报告",
    responses={
        200: {"description": "成本报告"},
        401: {"description": "未授权"},
    },
)
async def get_cost_report(data: dict, user=Depends(get_current_active_user) if get_current_active_user else None):
    """生成成本报告"""
    period = data.get("period", "monthly")
    report = generate_cost_report(period)
    return {"status": "success", "report": report}
