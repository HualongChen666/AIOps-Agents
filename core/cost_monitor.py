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
    """
    Get cost optimization suggestions based on current usage patterns
    
    Returns:
        List of optimization suggestions with potential savings
    """
    try:
        cost_data = collect_costs()
        
        # Analyze cost patterns and generate optimization suggestions
        suggestions = []
        
        # Group by service to identify high-cost services
        service_costs = {}
        for record in cost_data:
            service = record.get("service", "unknown")
            service_costs[service] = service_costs.get(service, 0) + record["cost"]
        
        # Identify top cost contributors
        sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
        
        for service, cost in sorted_services[:5]:
            if cost > 100:  # Threshold for significant costs
                suggestions.append({
                    "id": len(suggestions) + 1,
                    "type": "resize",
                    "resource": service,
                    "current_cost": cost,
                    "potential_savings": cost * 0.2,  # Assume 20% savings potential
                    "priority": "high" if cost > 500 else "medium",
                    "action": f"Review {service} instance sizes and consider right-sizing"
                })
        
        # Check for idle resources
        if len(cost_data) > 0:
            avg_cost = sum(r["cost"] for r in cost_data) / len(cost_data)
            suggestions.append({
                "id": len(suggestions) + 1,
                "type": "idle_resources",
                "resource": "various",
                "current_cost": avg_cost * 0.1,
                "potential_savings": avg_cost * 0.1,
                "priority": "medium",
                "action": "Identify and remove idle or underutilized resources"
            })
        
        logger.info(f"Generated {len(suggestions)} cost optimization suggestions")
        return suggestions
        
    except Exception as e:
        logger.error(f"Error generating optimization suggestions: {e}")
        return []


def get_resource_costs() -> List[Dict[str, Any]]:
    """
    Get cost breakdown by resource type
    
    Returns:
        List of resource costs with type information
    """
    try:
        cost_data = collect_costs()
        
        # Group costs by resource type based on service names
        resource_type_mapping = {
            "EC2": "compute",
            "Lambda": "compute",
            "ECS": "compute",
            "EBS": "storage",
            "S3": "storage",
            "RDS": "database",
            "DynamoDB": "database",
            "ElastiCache": "database",
            "CloudFront": "network",
            "VPC": "network",
        }
        
        resource_costs = {}
        for record in cost_data:
            service = record.get("service", "unknown")
            resource_type = resource_type_mapping.get(service, "other")
            resource_costs[resource_type] = resource_costs.get(resource_type, 0) + record["cost"]
        
        result = [
            {
                "resource_type": rtype,
                "cost": cost,
                "percentage": (cost / sum(resource_costs.values()) * 100) if resource_costs else 0
            }
            for rtype, cost in resource_costs.items()
        ]
        
        logger.info(f"Retrieved resource costs for {len(result)} resource types")
        return result
        
    except Exception as e:
        logger.error(f"Error getting resource costs: {e}")
        return []


def get_llm_costs() -> Dict[str, Any]:
    """
    Get LLM-related costs from usage data
    
    Returns:
        LLM cost breakdown by model and usage
    """
    try:
        # In production, this would query actual LLM usage metrics
        # For now, return a structured response based on available cost data
        cost_data = collect_costs()
        
        # Filter for AI/ML related services
        ai_services = ["SageMaker", "Bedrock", "Lambda"]
        ai_costs = sum(r["cost"] for r in cost_data if r.get("service") in ai_services)
        
        result = {
            "total_tokens": 0,  # Would be populated from actual usage metrics
            "total_cost": ai_costs,
            "models": {
                "gpt-4": ai_costs * 0.6 if ai_costs > 0 else 0,
                "gpt-3.5": ai_costs * 0.4 if ai_costs > 0 else 0,
            },
            "cost_per_1k_tokens": ai_costs / 1000 if ai_costs > 0 else 0,
            "period": "current_month"
        }
        
        logger.info(f"Retrieved LLM costs: ${ai_costs:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting LLM costs: {e}")
        return {"total_tokens": 0, "total_cost": 0, "models": {}, "cost_per_1k_tokens": 0}


def get_budget_management() -> List[Dict[str, Any]]:
    """
    Get all budget configurations
    
    Returns:
        List of budget configurations
    """
    try:
        # In production, load from database
        # For now, return default budget configuration
        budgets = [
            {
                "id": 1,
                "name": "Monthly Budget",
                "amount": 5000.0,
                "used": sum(r["cost"] for r in collect_costs()),
                "status": "active",
                "period": "monthly",
                "alert_threshold": 0.8
            },
            {
                "id": 2,
                "name": "Project Budget",
                "amount": 10000.0,
                "used": sum(r["cost"] for r in collect_costs()) * 2,
                "status": "active",
                "period": "quarterly",
                "alert_threshold": 0.75
            }
        ]
        
        logger.info(f"Retrieved {len(budgets)} budget configurations")
        return budgets
        
    except Exception as e:
        logger.error(f"Error getting budget management: {e}")
        return []


def create_budget(budget_data: dict) -> Dict[str, Any]:
    """
    Create a new budget configuration
    
    Args:
        budget_data: Budget configuration data
        
    Returns:
        Created budget configuration
    """
    try:
        # In production, save to database
        # For now, return a mock response
        new_budget = {
            "id": len(get_budget_management()) + 1,
            "name": budget_data.get("name", "New Budget"),
            "amount": budget_data.get("amount", 0),
            "used": 0,
            "status": "active",
            "period": budget_data.get("period", "monthly"),
            "alert_threshold": budget_data.get("alert_threshold", 0.8),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Created budget: {new_budget['name']} with amount ${new_budget['amount']}")
        return new_budget
        
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise


def predict_costs(time_horizon: int) -> List[Dict[str, Any]]:
    """
    Predict costs for a given time horizon
    
    Args:
        time_horizon: Number of days to predict
        
    Returns:
        List of predicted costs
    """
    try:
        forecast = forecast_costs(time_horizon)
        
        # Format as prediction response
        predictions = [
            {
                "date": f["timestamp"][:10],
                "predicted_amount": f["forecasted_cost"],
                "confidence": f["confidence"],
                "lower_bound": f["forecasted_cost"] * 0.9,
                "upper_bound": f["forecasted_cost"] * 1.1
            }
            for f in forecast
        ]
        
        logger.info(f"Generated cost predictions for {time_horizon} days")
        return predictions
        
    except Exception as e:
        logger.error(f"Error predicting costs: {e}")
        return []


def get_cost_collection_status() -> Dict[str, Any]:
    """
    Get the status of cost data collection
    
    Returns:
        Collection status information
    """
    try:
        cost_data = collect_costs()
        
        status = {
            "status": "active" if len(cost_data) > 0 else "inactive",
            "last_collection": cost_data[-1]["timestamp"] if cost_data else None,
            "next_collection": (datetime.now() + timedelta(hours=24)).isoformat(),
            "total_records": len(cost_data),
            "collection_frequency": "daily",
            "data_sources": ["aws_ce"] if cost_data else []
        }
        
        logger.info(f"Cost collection status: {status['status']}")
        return status
        
    except Exception as e:
        logger.error(f"Error getting cost collection status: {e}")
        return {"status": "error", "error": str(e)}


def sync_cost_collection(collection_id: str) -> Dict[str, Any]:
    """
    Trigger a manual sync of cost collection
    
    Args:
        collection_id: ID of the collection to sync
        
    Returns:
        Sync result
    """
    try:
        # Trigger cost collection
        cost_data = collect_costs()
        
        result = {
            "status": "success",
            "id": collection_id,
            "synced_at": datetime.now().isoformat(),
            "records_collected": len(cost_data),
            "message": f"Successfully synced {len(cost_data)} cost records"
        }
        
        logger.info(f"Synced cost collection {collection_id}: {len(cost_data)} records")
        return result
        
    except Exception as e:
        logger.error(f"Error syncing cost collection: {e}")
        return {"status": "error", "id": collection_id, "error": str(e)}


def get_cost_monitoring() -> Dict[str, Any]:
    """
    Get real-time cost monitoring data
    
    Returns:
        Current cost monitoring metrics
    """
    try:
        cost_data = collect_costs()
        
        if not cost_data:
            return {
                "total_cost": 0,
                "daily_average": 0,
                "trend": "stable",
                "anomalies": []
            }
        
        total_cost = sum(r["cost"] for r in cost_data)
        daily_average = total_cost / len(cost_data)
        
        # Calculate trend
        if len(cost_data) >= 2:
            recent_avg = sum(r["cost"] for r in cost_data[-7:]) / min(7, len(cost_data))
            earlier_avg = sum(r["cost"] for r in cost_data[:-7]) / max(1, len(cost_data) - 7)
            if recent_avg > earlier_avg * 1.1:
                trend = "increasing"
            elif recent_avg < earlier_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        monitoring = {
            "total_cost": total_cost,
            "daily_average": daily_average,
            "trend": trend,
            "anomalies": [],
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"Cost monitoring: total=${total_cost:.2f}, trend={trend}")
        return monitoring
        
    except Exception as e:
        logger.error(f"Error getting cost monitoring: {e}")
        return {"status": "error", "error": str(e)}


def generate_cost_report(period: str) -> Dict[str, Any]:
    """
    Generate a cost report for a given period
    
    Args:
        period: Report period (daily, weekly, monthly, quarterly)
        
    Returns:
        Cost report with breakdown
    """
    try:
        cost_data = collect_costs()
        
        # Filter data based on period
        if period == "daily":
            filtered = cost_data[-1:] if cost_data else []
        elif period == "weekly":
            filtered = cost_data[-7:] if len(cost_data) >= 7 else cost_data
        elif period == "monthly":
            filtered = cost_data[-30:] if len(cost_data) >= 30 else cost_data
        else:  # quarterly
            filtered = cost_data[-90:] if len(cost_data) >= 90 else cost_data
        
        total_cost = sum(r["cost"] for r in filtered)
        
        # Breakdown by service
        service_breakdown = {}
        for record in filtered:
            service = record.get("service", "unknown")
            service_breakdown[service] = service_breakdown.get(service, 0) + record["cost"]
        
        report = {
            "period": period,
            "total_cost": total_cost,
            "breakdown": service_breakdown,
            "record_count": len(filtered),
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated {period} cost report: ${total_cost:.2f}")
        return report
        
    except Exception as e:
        logger.error(f"Error generating cost report: {e}")
        return {"status": "error", "error": str(e)}


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
