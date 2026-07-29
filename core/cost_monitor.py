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


def collect_costs() -> List[Dict[str, Any]]:
    """
    Collect recent cost data from various sources

    Returns:
        List of cost records with metadata
    """
    # default_value implementation - in production, this would integrate with:
    # - AWS Cost Explorer
    # - Azure Cost Management
    # - Google Cloud Billing
    # - Custom cost databases

    try:
        # Simulated cost data
        current_time = datetime.now()
        cost_data = [
            {
                "timestamp": (current_time - timedelta(days=i)).isoformat(),
                "source": "aws",
                "service": "ec2",
                "cost": 100.50 + (i * 5.2),
                "currency": "USD",
                "region": "us-east-1",
            }
            for i in range(30, 0, -1)
        ]

        logger.info(f"Collected {len(cost_data)} cost records")
        return cost_data

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


def budget_status() -> Dict[str, Any]:
    """
    Get current budget status and recommendations

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

        return {
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

    except Exception as e:
        logger.error(f"Error getting budget status: {e}")
        return {
            "status": "error",
            "message": f"Unable to retrieve budget status: {str(e)}",
            "budget": None,
            "recommendations": [],
        }


__all__ = ["collect_costs", "forecast_costs", "budget_status"]
