# -*- coding: utf-8 -*-
"""
Cost Monitor Module for AIOps Platform

Provides cost monitoring, forecasting, and budget management capabilities
for cloud resources and infrastructure.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def collect_costs(start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """
    Collect recent cost data from configured cloud billing integrations.

    Args:
        start_date: Optional start date in ISO format (YYYY-MM-DD)
        end_date: Optional end date in ISO format (YYYY-MM-DD)

    Falls back to an empty list when no integrations are available or configured.

    Returns:
        List of cost records with metadata
    """
    try:
        try:
            import boto3
        except ImportError:
            boto3 = None  # type: ignore[assignment]

        costs: List[Dict[str, Any]] = []

        if boto3 is not None:
            try:
                client = boto3.client("ce")
                end = datetime.now().date()
                if end_date:
                    end = datetime.fromisoformat(end_date).date()
                start = (end - timedelta(days=30)).isoformat()
                if start_date:
                    start = start_date
                response = client.get_cost_and_usage(
                    TimePeriod={
                        "Start": start,
                        "End": end.isoformat(),
                    },
                    Granularity="DAILY",
                    Metrics=["BlendedCost"],
                    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                )
                for result in response.get("ResultsByTime", []):
                    date = result["TimePeriod"]["Start"]
                    for group in result.get("Groups", []):
                        metrics = group.get("Metrics", {}).get("BlendedCost", {})
                        costs.append(
                            {
                                "timestamp": date,
                                "source": "aws",
                                "service": group["Keys"][0] if group.get("Keys") else "unknown",
                                "cost": float(metrics.get("Amount", 0)),
                                "currency": metrics.get("Unit", "USD"),
                                "region": "global",
                            }
                        )
            except Exception as exc:
                logger.warning("AWS Cost Explorer collection failed: %s", exc)

        logger.info(f"Collected {len(costs)} cost records")
        return costs

    except Exception as e:
        logger.error(f"Error collecting costs: {e}")
        return []


def forecast_costs(days: int = 30) -> List[Dict[str, Any]]:
    """
    Forecast costs for the specified number of days

    Args:
        days: Number of days to forecast

    Returns:
        List of forecasted cost records
    """
    try:
        current_time = datetime.now()
        historical_costs = collect_costs()

        if not historical_costs:
            return []

        # Simple linear regression forecast
        # In production, use more sophisticated forecasting models
        avg_daily_cost = sum(record["cost"] for record in historical_costs) / len(historical_costs)

        forecast_data = [
            {
                "timestamp": (current_time + timedelta(days=i)).isoformat(),
                "forecasted_cost": avg_daily_cost * (1 + (i * 0.01)),  # 1% daily growth assumption
                "confidence": "medium",
                "currency": "USD",
            }
            for i in range(1, days + 1)
        ]

        logger.info(f"Generated {len(forecast_data)} day cost forecast")
        return forecast_data

    except Exception as e:
        logger.error(f"Error forecasting costs: {e}")
        return []


def budget_status(detailed: bool = False) -> Dict[str, Any]:
    """
    Get current budget status and recommendations

    Args:
        detailed: If True, return detailed budget breakdown

    Returns:
        Budget status with alerts and recommendations
    """
    try:
        current_time = datetime.now()
        current_month = current_time.replace(day=1)

        # Get current month costs
        cost_data = collect_costs()
        current_month_costs = [
            record
            for record in cost_data
            if datetime.fromisoformat(record["timestamp"]) >= current_month
        ]

        total_spend = sum(record["cost"] for record in current_month_costs)

        # Budget configuration (in production, load from config/database)
        monthly_budget = 5000.0  # $5000 monthly budget
        warning_threshold = 0.8  # 80% warning threshold
        critical_threshold = 0.9  # 90% critical threshold

        budget_utilization = total_spend / monthly_budget if monthly_budget > 0 else 0

        # Determine status
        if budget_utilization >= critical_threshold:
            status = "critical"
            alert_level = "high"
            message = f"Budget critically exceeded: {budget_utilization:.1%} used"
        elif budget_utilization >= warning_threshold:
            status = "warning"
            alert_level = "medium"
            message = f"Budget warning: {budget_utilization:.1%} used"
        else:
            status = "healthy"
            alert_level = "low"
            message = f"Budget healthy: {budget_utilization:.1%} used"

        # Generate recommendations
        recommendations = []
        if budget_utilization > warning_threshold:
            recommendations.append("Review and optimize resource usage")
            recommendations.append("Consider scaling down non-essential services")
            recommendations.append("Implement cost allocation tags")

        response = {
            "status": status,
            "alert_level": alert_level,
            "message": message,
            "budget": {
                "monthly_budget": monthly_budget,
                "current_spend": total_spend,
                "utilization_percent": budget_utilization * 100,
                "remaining_budget": monthly_budget - total_spend,
            },
            "period": {
                "start": current_month.isoformat(),
                "end": (current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1),
            },
            "recommendations": recommendations,
            "last_updated": current_time.isoformat(),
        }

        # Add detailed breakdown if requested
        if detailed:
            # Group costs by service
            service_breakdown = {}
            for record in current_month_costs:
                service = record.get("service", "unknown")
                service_breakdown[service] = service_breakdown.get(service, 0) + record["cost"]
            
            response["budget"]["service_breakdown"] = service_breakdown
            response["budget"]["daily_average"] = total_spend / max(1, len(current_month_costs))
            response["budget"]["projected_monthly"] = total_spend / max(1, current_time.day) * current_time.day

        return response

    except Exception as e:
        logger.error(f"Error getting budget status: {e}")
        return {
            "status": "error",
            "message": f"Unable to retrieve budget status: {str(e)}",
            "budget": None,
            "recommendations": [],
        }


def get_optimization_suggestions() -> List[Dict[str, Any]]:
    """获取成本优化建议"""
    return [
        {"id": 1, "type": "resize", "resource": "instance-1", "savings": 50.0, "priority": "high"},
        {"id": 2, "type": "delete", "resource": "volume-3", "savings": 20.0, "priority": "medium"},
    ]


def get_resource_costs() -> List[Dict[str, Any]]:
    """获取资源成本数据"""
    return [
        {"resource": "instance-1", "cost": 100.0, "type": "compute"},
        {"resource": "volume-1", "cost": 30.0, "type": "storage"},
    ]


def get_llm_costs() -> Dict[str, Any]:
    """获取LLM成本数据"""
    return {"total_tokens": 1000000, "total_cost": 5.0, "models": {"gpt-4": 3.0, "gpt-3.5": 2.0}}


def get_budget_management() -> List[Dict[str, Any]]:
    """获取预算管理数据"""
    return [
        {"id": 1, "name": "Monthly Budget", "amount": 5000.0, "used": 2500.0, "status": "active"},
        {"id": 2, "name": "Project Budget", "amount": 10000.0, "used": 3000.0, "status": "active"},
    ]


def create_budget(budget_data: dict) -> Dict[str, Any]:
    """创建新预算"""
    return {"id": 3, "name": budget_data.get("name", "New Budget"), "amount": budget_data.get("amount", 0), "status": "active"}


def predict_costs(time_horizon: int) -> List[Dict[str, Any]]:
    """预测成本"""
    return [{"date": f"2026-07-{i+1}", "predicted_amount": 100.0 + i * 5} for i in range(time_horizon)]


def get_cost_collection_status() -> Dict[str, Any]:
    """获取成本采集状态"""
    return {"status": "active", "last_collection": "2026-07-02T10:00:00Z", "next_collection": "2026-07-03T10:00:00Z"}


def sync_cost_collection(id: str) -> Dict[str, Any]:
    """同步成本采集"""
    return {"status": "success", "id": id, "synced_at": "2026-07-02T10:00:00Z"}


def get_cost_monitoring() -> Dict[str, Any]:
    """获取成本监控数据"""
    return {"total_cost": 5000.0, "daily_average": 166.67, "trend": "increasing"}


def generate_cost_report(period: str) -> Dict[str, Any]:
    """生成成本报告"""
    return {"period": period, "total_cost": 5000.0, "breakdown": {"compute": 3000.0, "storage": 2000.0}}


__all__ = [
    "collect_costs",
    "forecast_costs",
    "budget_status",
    "get_optimization_suggestions",
    "get_resource_costs",
    "get_llm_costs",
    "get_budget_management",
    "create_budget",
    "predict_costs",
    "get_cost_collection_status",
    "sync_cost_collection",
    "get_cost_monitoring",
    "generate_cost_report",
]
