# -*- coding: utf-8 -*-
"""
Cost Advanced Router Module
============================

Provides advanced API endpoints for cost management.
Supports overview, analytics, optimization, budgets, forecasts, reports,
anomalies, and alerts.

Endpoints:
- /api/v1/cost/overview - Cost overview dashboard
- /api/v1/cost/analytics - Cost analytics and insights
- /api/v1/cost/optimization - Cost optimization suggestions
- /api/v1/cost/budgets - Budget management (CRUD)
- /api/v1/cost/forecasts - Cost forecasting
- /api/v1/cost/reports - Cost reports generation
- /api/v1/cost/anomalies - Cost anomaly detection
- /api/v1/cost/alerts - Cost alerts management
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.cost_monitor import collect_costs, forecast_costs, budget_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cost", tags=["成本管理高级功能"])

# ============================================================================
# In-Memory Data Storage (Simulating database)
# ============================================================================

# Budgets storage
_budgets: Dict[str, Dict] = {
    "budget-1": {
        "id": "budget-1",
        "name": "EC2 Monthly Budget",
        "service": "Amazon EC2",
        "amount": 2000.0,
        "spent": 1450.50,
        "remaining": 549.50,
        "period": "monthly",
        "status": "on_track",
        "alerts_enabled": True,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-15T00:00:00",
    },
    "budget-2": {
        "id": "budget-2",
        "name": "S3 Storage Budget",
        "service": "Amazon S3",
        "amount": 500.0,
        "spent": 480.0,
        "remaining": 20.0,
        "period": "monthly",
        "status": "warning",
        "alerts_enabled": True,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-15T00:00:00",
    },
}

# Optimization suggestions storage
_optimization_suggestions: Dict[str, Dict] = {
    "opt-1": {
        "id": "opt-1",
        "resource": "i-0123456789abcdef0 (EC2 Instance)",
        "type": "resize",
        "current_cost": 150.0,
        "projected_savings": 45.0,
        "effort": "low",
        "impact": "medium",
        "description": "Resize instance from m5.large to m5.medium based on utilization",
        "status": "pending",
        "created_at": "2026-01-15T00:00:00",
    },
    "opt-2": {
        "id": "opt-2",
        "resource": "prod-db-cluster (RDS)",
        "type": "reserved",
        "current_cost": 300.0,
        "projected_savings": 90.0,
        "effort": "medium",
        "impact": "high",
        "description": "Purchase reserved instances for production database",
        "status": "pending",
        "created_at": "2026-01-15T00:00:00",
    },
}

# Cost anomalies storage
_anomalies: List[Dict] = [
    {
        "id": "anom-1",
        "detected_at": "2026-01-15T10:30:00",
        "service": "Amazon EC2",
        "expected_cost": 100.0,
        "actual_cost": 250.0,
        "deviation_percent": 150.0,
        "severity": "high",
        "description": "Unusual spike in EC2 costs",
        "status": "open",
    },
    {
        "id": "anom-2",
        "detected_at": "2026-01-14T14:20:00",
        "service": "Amazon S3",
        "expected_cost": 50.0,
        "actual_cost": 85.0,
        "deviation_percent": 70.0,
        "severity": "medium",
        "description": "Higher than expected S3 storage costs",
        "status": "investigating",
    },
]

# Cost alerts storage
_alerts: Dict[str, Dict] = {
    "alert-1": {
        "id": "alert-1",
        "name": "Budget Exceeded Alert",
        "type": "budget_exceeded",
        "threshold": 90.0,
        "current_value": 95.0,
        "severity": "critical",
        "enabled": True,
        "notification_channels": ["email", "slack"],
        "created_at": "2026-01-01T00:00:00",
    },
    "alert-2": {
        "id": "alert-2",
        "name": "Cost Anomaly Alert",
        "type": "anomaly_detected",
        "threshold": 50.0,
        "current_value": 0.0,
        "severity": "high",
        "enabled": True,
        "notification_channels": ["email"],
        "created_at": "2026-01-01T00:00:00",
    },
}

# Reports storage
_reports: Dict[str, Dict] = {}

# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================


class BudgetCreate(BaseModel):
    """Model for creating a new budget"""
    name: str = Field(..., description="Budget name")
    service: str = Field(..., description="Service name")
    amount: float = Field(..., gt=0, description="Budget amount")
    period: str = Field(default="monthly", description="Budget period")
    alerts_enabled: bool = Field(default=True, description="Enable alerts")


class BudgetUpdate(BaseModel):
    """Model for updating a budget"""
    name: Optional[str] = Field(None, description="Budget name")
    amount: Optional[float] = Field(None, gt=0, description="Budget amount")
    period: Optional[str] = Field(None, description="Budget period")
    alerts_enabled: Optional[bool] = Field(None, description="Enable alerts")


class AnalyticsRequest(BaseModel):
    """Model for analytics request"""
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    group_by: Optional[str] = Field(default="service", description="Group by field")
    granularity: Optional[str] = Field(default="daily", description="Time granularity")


class OptimizationRequest(BaseModel):
    """Model for optimization request"""
    resource_id: Optional[str] = Field(None, description="Resource ID")
    action: str = Field(..., description="Action: apply or dismiss")


class ReportRequest(BaseModel):
    """Model for report generation request"""
    period: str = Field(default="30d", description="Report period (e.g., 30d, 90d)")
    format: str = Field(default="json", description="Report format")
    include_forecast: bool = Field(default=False, description="Include forecast data")


class AlertCreate(BaseModel):
    """Model for creating an alert"""
    name: str = Field(..., description="Alert name")
    type: str = Field(..., description="Alert type")
    threshold: float = Field(..., gt=0, description="Alert threshold")
    severity: str = Field(default="medium", description="Alert severity")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")


class AlertUpdate(BaseModel):
    """Model for updating an alert"""
    name: Optional[str] = Field(None, description="Alert name")
    threshold: Optional[float] = Field(None, gt=0, description="Alert threshold")
    severity: Optional[str] = Field(None, description="Alert severity")
    enabled: Optional[bool] = Field(None, description="Alert enabled status")
    notification_channels: Optional[List[str]] = Field(None, description="Notification channels")


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/overview",
    summary="Get cost overview",
    responses={
        200: {"description": "Cost overview data"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_cost_overview() -> Dict[str, Any]:
    """
    Get comprehensive cost overview including total costs, budget status,
    forecasts, and key metrics.
    """
    try:
        # Collect cost data
        cost_data = collect_costs()
        
        # Get budget status
        budget_info = budget_status()
        
        # Calculate totals
        total_cost = sum(record.get("cost", 0) for record in cost_data)
        
        # Get forecast
        forecast_data = forecast_costs(30)
        total_forecast = sum(record.get("forecasted_cost", 0) for record in forecast_data)
        
        # Calculate trends
        if len(cost_data) >= 2:
            recent_cost = cost_data[-1].get("cost", 0)
            previous_cost = cost_data[-2].get("cost", 0)
            trend = "up" if recent_cost > previous_cost else "down" if recent_cost < previous_cost else "stable"
            trend_percent = ((recent_cost - previous_cost) / previous_cost * 100) if previous_cost > 0 else 0
        else:
            trend = "stable"
            trend_percent = 0
        
        # Count active budgets
        active_budgets = len([b for b in _budgets.values() if b.get("alerts_enabled", False)])
        
        # Count pending optimizations
        pending_optimizations = len([o for o in _optimization_suggestions.values() if o.get("status") == "pending"])
        
        # Count open anomalies
        open_anomalies = len([a for a in _anomalies if a.get("status") in ["open", "investigating"]])
        
        return {
            "total_cost": total_cost,
            "budget_status": budget_info,
            "forecast": {
                "period_days": 30,
                "total_forecast": total_forecast,
                "forecast_data": forecast_data,
            },
            "trends": {
                "direction": trend,
                "percent_change": round(trend_percent, 2),
            },
            "metrics": {
                "active_budgets": active_budgets,
                "pending_optimizations": pending_optimizations,
                "open_anomalies": open_anomalies,
                "total_alerts": len(_alerts),
            },
            "cost_by_service": _group_costs_by_service(cost_data),
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting cost overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost overview: {str(e)}")


@router.get(
    "/analytics",
    summary="Get cost analytics",
    responses={
        200: {"description": "Cost analytics data"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_cost_analytics(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    group_by: str = Query("service", description="Group by field"),
    granularity: str = Query("daily", description="Time granularity"),
) -> Dict[str, Any]:
    """
    Get detailed cost analytics with grouping and filtering options.
    """
    try:
        # Collect cost data
        cost_data = collect_costs()
        
        # Filter by date range if provided
        if start_date or end_date:
            filtered_data = []
            for record in cost_data:
                record_date = record.get("timestamp", "")
                if start_date and record_date < start_date:
                    continue
                if end_date and record_date > end_date:
                    continue
                filtered_data.append(record)
            cost_data = filtered_data
        
        # Group costs
        if group_by == "service":
            grouped = _group_costs_by_service(cost_data)
        elif group_by == "region":
            grouped = _group_costs_by_region(cost_data)
        elif group_by == "category":
            grouped = _group_costs_by_category(cost_data)
        else:
            grouped = _group_costs_by_service(cost_data)
        
        # Calculate statistics
        total_cost = sum(record.get("cost", 0) for record in cost_data)
        avg_cost = total_cost / len(cost_data) if cost_data else 0
        
        # Find max and min
        if cost_data:
            max_cost = max(record.get("cost", 0) for record in cost_data)
            min_cost = min(record.get("cost", 0) for record in cost_data)
        else:
            max_cost = 0
            min_cost = 0
        
        # Calculate cost trends over time
        time_series = _calculate_cost_trends(cost_data, granularity)
        
        return {
            "summary": {
                "total_cost": total_cost,
                "average_cost": round(avg_cost, 2),
                "max_cost": max_cost,
                "min_cost": min_cost,
                "record_count": len(cost_data),
            },
            "grouped_data": grouped,
            "time_series": time_series,
            "insights": _generate_cost_insights(cost_data, grouped),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "group_by": group_by,
                "granularity": granularity,
            },
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting cost analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost analytics: {str(e)}")


@router.post(
    "/analytics",
    summary="Run custom cost analytics",
    responses={
        200: {"description": "Custom analytics results"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def run_custom_analytics(request: AnalyticsRequest) -> Dict[str, Any]:
    """
    Run custom cost analytics with specific parameters.
    """
    try:
        return await get_cost_analytics(
            start_date=request.start_date,
            end_date=request.end_date,
            group_by=request.group_by,
            granularity=request.granularity,
        )
    except Exception as e:
        logger.error(f"Error running custom analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run custom analytics: {str(e)}")


@router.get(
    "/optimization",
    summary="Get cost optimization suggestions",
    responses={
        200: {"description": "Optimization suggestions"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_optimization_suggestions() -> Dict[str, Any]:
    """
    Get list of cost optimization suggestions with potential savings.
    """
    try:
        suggestions = list(_optimization_suggestions.values())
        
        # Calculate total potential savings
        total_savings = sum(
            s.get("projected_savings", 0) 
            for s in suggestions 
            if s.get("status") == "pending"
        )
        
        # Group by type
        by_type = {}
        for suggestion in suggestions:
            opt_type = suggestion.get("type", "unknown")
            if opt_type not in by_type:
                by_type[opt_type] = []
            by_type[opt_type].append(suggestion)
        
        # Group by effort
        by_effort = {"low": [], "medium": [], "high": []}
        for suggestion in suggestions:
            effort = suggestion.get("effort", "medium")
            by_effort[effort].append(suggestion)
        
        return {
            "suggestions": suggestions,
            "summary": {
                "total_suggestions": len(suggestions),
                "pending_count": len([s for s in suggestions if s.get("status") == "pending"]),
                "applied_count": len([s for s in suggestions if s.get("status") == "applied"]),
                "dismissed_count": len([s for s in suggestions if s.get("status") == "dismissed"]),
                "total_potential_savings": round(total_savings, 2),
            },
            "by_type": by_type,
            "by_effort": by_effort,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimization suggestions: {str(e)}")


@router.post(
    "/optimization",
    summary="Apply or dismiss optimization suggestion",
    responses={
        200: {"description": "Operation result"},
        401: {"description": "Unauthorized"},
        404: {"description": "Suggestion not found"},
        500: {"description": "Internal server error"},
    },
)
async def handle_optimization(request: OptimizationRequest) -> Dict[str, Any]:
    """
    Apply or dismiss a specific optimization suggestion.
    """
    try:
        if not request.resource_id:
            raise HTTPException(status_code=400, detail="resource_id is required")
        
        if request.resource_id not in _optimization_suggestions:
            raise HTTPException(status_code=404, detail="Optimization suggestion not found")
        
        suggestion = _optimization_suggestions[request.resource_id]
        
        if request.action == "apply":
            suggestion["status"] = "applied"
            suggestion["updated_at"] = datetime.now().isoformat()
            message = f"Successfully applied optimization for {suggestion.get('resource')}"
        elif request.action == "dismiss":
            suggestion["status"] = "dismissed"
            suggestion["updated_at"] = datetime.now().isoformat()
            message = f"Successfully dismissed optimization for {suggestion.get('resource')}"
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Must be 'apply' or 'dismiss'")
        
        return {
            "success": True,
            "message": message,
            "suggestion": suggestion,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to handle optimization: {str(e)}")


@router.get(
    "/budgets",
    summary="Get all budgets",
    responses={
        200: {"description": "List of budgets"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_budgets() -> Dict[str, Any]:
    """
    Get all budgets with their current status.
    """
    try:
        budgets = list(_budgets.values())
        
        # Calculate summary
        total_budget = sum(b.get("amount", 0) for b in budgets)
        total_spent = sum(b.get("spent", 0) for b in budgets)
        total_remaining = sum(b.get("remaining", 0) for b in budgets)
        
        # Count by status
        status_counts = {
            "on_track": len([b for b in budgets if b.get("status") == "on_track"]),
            "warning": len([b for b in budgets if b.get("status") == "warning"]),
            "exceeded": len([b for b in budgets if b.get("status") == "exceeded"]),
        }
        
        return {
            "budgets": budgets,
            "summary": {
                "total_budgets": len(budgets),
                "total_budget_amount": total_budget,
                "total_spent": total_spent,
                "total_remaining": total_remaining,
                "utilization_percent": round((total_spent / total_budget * 100) if total_budget > 0 else 0, 2),
                "status_counts": status_counts,
            },
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting budgets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get budgets: {str(e)}")


@router.post(
    "/budgets",
    summary="Create a new budget",
    responses={
        200: {"description": "Created budget"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def create_budget(budget: BudgetCreate) -> Dict[str, Any]:
    """
    Create a new budget.
    """
    try:
        budget_id = f"budget-{uuid.uuid4().hex[:8]}"
        
        new_budget = {
            "id": budget_id,
            "name": budget.name,
            "service": budget.service,
            "amount": budget.amount,
            "spent": 0.0,
            "remaining": budget.amount,
            "period": budget.period,
            "status": "on_track",
            "alerts_enabled": budget.alerts_enabled,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        _budgets[budget_id] = new_budget
        
        return {
            "success": True,
            "message": "Budget created successfully",
            "budget": new_budget,
        }
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create budget: {str(e)}")


@router.patch(
    "/budgets/{budget_id}",
    summary="Update a budget",
    responses={
        200: {"description": "Updated budget"},
        404: {"description": "Budget not found"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def update_budget(budget_id: str, budget: BudgetUpdate) -> Dict[str, Any]:
    """
    Update an existing budget.
    """
    try:
        if budget_id not in _budgets:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        existing_budget = _budgets[budget_id]
        
        # Update fields if provided
        if budget.name is not None:
            existing_budget["name"] = budget.name
        if budget.amount is not None:
            existing_budget["amount"] = budget.amount
            existing_budget["remaining"] = budget.amount - existing_budget.get("spent", 0)
        if budget.period is not None:
            existing_budget["period"] = budget.period
        if budget.alerts_enabled is not None:
            existing_budget["alerts_enabled"] = budget.alerts_enabled
        
        # Recalculate status
        utilization = existing_budget.get("spent", 0) / existing_budget.get("amount", 1)
        if utilization >= 0.9:
            existing_budget["status"] = "exceeded"
        elif utilization >= 0.8:
            existing_budget["status"] = "warning"
        else:
            existing_budget["status"] = "on_track"
        
        existing_budget["updated_at"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": "Budget updated successfully",
            "budget": existing_budget,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")


@router.delete(
    "/budgets/{budget_id}",
    summary="Delete a budget",
    responses={
        200: {"description": "Deleted budget"},
        404: {"description": "Budget not found"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def delete_budget(budget_id: str) -> Dict[str, Any]:
    """
    Delete a budget.
    """
    try:
        if budget_id not in _budgets:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        deleted_budget = _budgets.pop(budget_id)
        
        return {
            "success": True,
            "message": "Budget deleted successfully",
            "deleted_budget": deleted_budget,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete budget: {str(e)}")


@router.get(
    "/forecasts",
    summary="Get cost forecasts",
    responses={
        200: {"description": "Cost forecast data"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_forecasts(
    days: int = Query(30, ge=1, le=365, description="Number of days to forecast"),
    service: Optional[str] = Query(None, description="Filter by service"),
) -> Dict[str, Any]:
    """
    Get cost forecasts for the specified period.
    """
    try:
        # Get forecast data
        forecast_data = forecast_costs(days)
        
        # Filter by service if specified
        if service:
            # In a real implementation, this would filter by service
            # For now, we'll just return all data
            pass
        
        # Calculate totals
        total_forecast = sum(record.get("forecasted_cost", 0) for record in forecast_data)
        avg_daily_forecast = total_forecast / days if days > 0 else 0
        
        # Get historical data for comparison
        historical_costs = collect_costs()
        total_historical = sum(record.get("cost", 0) for record in historical_costs)
        avg_historical = total_historical / len(historical_costs) if historical_costs else 0
        
        # Calculate growth rate
        growth_rate = ((avg_daily_forecast - avg_historical) / avg_historical * 100) if avg_historical > 0 else 0
        
        return {
            "forecast_period": {
                "days": days,
                "start_date": datetime.now().isoformat(),
                "end_date": (datetime.now() + timedelta(days=days)).isoformat(),
            },
            "forecast_data": forecast_data,
            "summary": {
                "total_forecast": round(total_forecast, 2),
                "average_daily_forecast": round(avg_daily_forecast, 2),
                "historical_average": round(avg_historical, 2),
                "growth_rate_percent": round(growth_rate, 2),
            },
            "confidence": "medium",
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting forecasts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get forecasts: {str(e)}")


@router.get(
    "/reports",
    summary="Get cost reports",
    responses={
        200: {"description": "Cost reports"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_reports() -> Dict[str, Any]:
    """
    Get list of available cost reports.
    """
    try:
        reports = list(_reports.values())
        
        return {
            "reports": reports,
            "total_count": len(reports),
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get reports: {str(e)}")


@router.post(
    "/reports",
    summary="Generate a cost report",
    responses={
        200: {"description": "Generated report"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def generate_report(request: ReportRequest) -> Dict[str, Any]:
    """
    Generate a cost report for the specified period.
    """
    try:
        # Parse period
        period_days = int(request.period.rstrip("d")) if request.period.endswith("d") else 30
        
        # Collect cost data
        cost_data = collect_costs()
        
        # Filter by period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        period_costs = [
            record for record in cost_data
            if datetime.fromisoformat(record.get("timestamp", "")) >= start_date
        ]
        
        # Calculate totals
        total_cost = sum(record.get("cost", 0) for record in period_costs)
        
        # Get budget info
        budget_info = budget_status()
        budget_amount = budget_info.get("budget", {}).get("monthly_budget", 0)
        
        # Calculate variance
        variance = total_cost - budget_amount
        
        # Group by service
        by_service = _group_costs_by_service(period_costs)
        
        # Group by category
        by_category = _group_costs_by_category(period_costs)
        
        # Calculate trends
        trends = _calculate_cost_trends(period_costs, "daily")
        
        # Create report
        report_id = f"report-{uuid.uuid4().hex[:8]}"
        report = {
            "id": report_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "period_days": period_days,
            "total_cost": round(total_cost, 2),
            "budget": budget_amount,
            "variance": round(variance, 2),
            "variance_percent": round((variance / budget_amount * 100) if budget_amount > 0 else 0, 2),
            "by_service": by_service,
            "by_category": by_category,
            "trends": trends,
            "format": request.format,
            "include_forecast": request.include_forecast,
            "created_at": datetime.now().isoformat(),
        }
        
        # Add forecast if requested
        if request.include_forecast:
            forecast_data = forecast_costs(30)
            report["forecast"] = {
                "period_days": 30,
                "total_forecast": sum(r.get("forecasted_cost", 0) for r in forecast_data),
                "forecast_data": forecast_data,
            }
        
        # Store report
        _reports[report_id] = report
        
        return {
            "success": True,
            "message": "Report generated successfully",
            "report": report,
        }
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get(
    "/anomalies",
    summary="Get cost anomalies",
    responses={
        200: {"description": "Cost anomalies"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_anomalies(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """
    Get detected cost anomalies with filtering options.
    """
    try:
        anomalies = _anomalies.copy()
        
        # Filter by severity
        if severity:
            anomalies = [a for a in anomalies if a.get("severity") == severity]
        
        # Filter by status
        if status:
            anomalies = [a for a in anomalies if a.get("status") == status]
        
        # Count by severity
        severity_counts = {
            "high": len([a for a in _anomalies if a.get("severity") == "high"]),
            "medium": len([a for a in _anomalies if a.get("severity") == "medium"]),
            "low": len([a for a in _anomalies if a.get("severity") == "low"]),
        }
        
        # Count by status
        status_counts = {
            "open": len([a for a in _anomalies if a.get("status") == "open"]),
            "investigating": len([a for a in _anomalies if a.get("status") == "investigating"]),
            "resolved": len([a for a in _anomalies if a.get("status") == "resolved"]),
        }
        
        # Calculate total impact
        total_impact = sum(
            a.get("actual_cost", 0) - a.get("expected_cost", 0)
            for a in anomalies
        )
        
        return {
            "anomalies": anomalies,
            "summary": {
                "total_count": len(anomalies),
                "filtered_count": len(anomalies),
                "severity_counts": severity_counts,
                "status_counts": status_counts,
                "total_impact": round(total_impact, 2),
            },
            "filters": {
                "severity": severity,
                "status": status,
            },
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get anomalies: {str(e)}")


@router.get(
    "/alerts",
    summary="Get cost alerts",
    responses={
        200: {"description": "Cost alerts"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_alerts(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
) -> Dict[str, Any]:
    """
    Get cost alerts with filtering options.
    """
    try:
        alerts = list(_alerts.values())
        
        # Filter by enabled status
        if enabled is not None:
            alerts = [a for a in alerts if a.get("enabled") == enabled]
        
        # Count by severity
        severity_counts = {
            "critical": len([a for a in alerts if a.get("severity") == "critical"]),
            "high": len([a for a in alerts if a.get("severity") == "high"]),
            "medium": len([a for a in alerts if a.get("severity") == "medium"]),
            "low": len([a for a in alerts if a.get("severity") == "low"]),
        }
        
        # Count by type
        type_counts = {}
        for alert in alerts:
            alert_type = alert.get("type", "unknown")
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        
        return {
            "alerts": alerts,
            "summary": {
                "total_count": len(alerts),
                "enabled_count": len([a for a in alerts if a.get("enabled")]),
                "disabled_count": len([a for a in alerts if not a.get("enabled")]),
                "severity_counts": severity_counts,
                "type_counts": type_counts,
            },
            "filters": {
                "enabled": enabled,
            },
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post(
    "/alerts",
    summary="Create a cost alert",
    responses={
        200: {"description": "Created alert"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def create_alert(alert: AlertCreate) -> Dict[str, Any]:
    """
    Create a new cost alert.
    """
    try:
        alert_id = f"alert-{uuid.uuid4().hex[:8]}"
        
        new_alert = {
            "id": alert_id,
            "name": alert.name,
            "type": alert.type,
            "threshold": alert.threshold,
            "current_value": 0.0,
            "severity": alert.severity,
            "enabled": True,
            "notification_channels": alert.notification_channels,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        _alerts[alert_id] = new_alert
        
        return {
            "success": True,
            "message": "Alert created successfully",
            "alert": new_alert,
        }
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")


# ============================================================================
# Helper Functions
# ============================================================================


def _group_costs_by_service(cost_data: List[Dict]) -> Dict[str, float]:
    """Group costs by service"""
    grouped = {}
    for record in cost_data:
        service = record.get("service", "unknown")
        cost = record.get("cost", 0)
        grouped[service] = grouped.get(service, 0) + cost
    return grouped


def _group_costs_by_region(cost_data: List[Dict]) -> Dict[str, float]:
    """Group costs by region"""
    grouped = {}
    for record in cost_data:
        region = record.get("region", "unknown")
        cost = record.get("cost", 0)
        grouped[region] = grouped.get(region, 0) + cost
    return grouped


def _group_costs_by_category(cost_data: List[Dict]) -> Dict[str, float]:
    """Group costs by category"""
    grouped = {}
    for record in cost_data:
        category = record.get("category", "compute")
        cost = record.get("cost", 0)
        grouped[category] = grouped.get(category, 0) + cost
    return grouped


def _calculate_cost_trends(cost_data: List[Dict], granularity: str) -> List[Dict]:
    """Calculate cost trends over time"""
    trends = []
    
    if not cost_data:
        return trends
    
    # Sort by timestamp
    sorted_data = sorted(cost_data, key=lambda x: x.get("timestamp", ""))
    
    for record in sorted_data:
        trends.append({
            "date": record.get("timestamp", ""),
            "cost": record.get("cost", 0),
        })
    
    return trends


def _generate_cost_insights(cost_data: List[Dict], grouped_data: Dict) -> List[str]:
    """Generate insights from cost data"""
    insights = []
    
    if not cost_data:
        insights.append("No cost data available for analysis")
        return insights
    
    # Find highest cost service
    if grouped_data:
        top_service = max(grouped_data.items(), key=lambda x: x[1])
        insights.append(f"Highest cost service: {top_service[0]} (${top_service[1]:.2f})")
    
    # Calculate trend
    if len(cost_data) >= 2:
        recent = cost_data[-1].get("cost", 0)
        previous = cost_data[-2].get("cost", 0)
        if recent > previous:
            insights.append(f"Costs are trending up ({((recent - previous) / previous * 100):.1f}%)")
        elif recent < previous:
            insights.append(f"Costs are trending down ({((previous - recent) / previous * 100):.1f}%)")
        else:
            insights.append("Costs are stable")
    
    return insights
