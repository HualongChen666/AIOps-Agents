# -*- coding: utf-8 -*-
"""
Cost Monitor Module for AIOps Platform

Provides cost monitoring, forecasting, and budget management capabilities
for cloud resources and infrastructure.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _fit_linear_trend(values: List[float]) -> Tuple[float, float]:
    """最小二乘拟合 ``y = intercept + slope * x``（x 为序号）。

    Returns:
        (intercept, slope)；数据不足时退化为均值 / 0 斜率。
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return values[0], 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return mean_y, 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom
    intercept = mean_y - slope * mean_x
    return intercept, slope


def _forecast_daily_growth_rate() -> float:
    """日均增长率（样本不足时用于外推），来自配置项，可按部署覆盖。"""
    try:
        import config

        return float(getattr(config, "DEFAULT_COST_FORECAST_DAILY_GROWTH", 0.01))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Forecast growth-rate lookup from config failed: {e}")
        return 0.01


def _resolve_monthly_budget() -> Optional[float]:
    """从持久化预算 / 配置解析当月预算总额。

    优先级：
      1. ``cost_budgets`` 表中 period=monthly 的预算之和（运营真实配置）；
      2. 配置项 ``DEFAULT_MONTHLY_BUDGET``（可按部署通过环境变量覆盖）。

    Returns:
        预算金额；均未配置时返回 ``None``（由调用方按“未配置预算”处理）。
    """
    try:
        from core.database import SessionLocal
        from core.models import CostBudgetDB

        db = SessionLocal()
        try:
            rows = db.query(CostBudgetDB).filter(CostBudgetDB.period == "monthly").all()
            total = sum(float(row.amount or 0) for row in rows)
            if total > 0:
                return total
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001 - 预算表不可用则回退配置
        logger.debug(f"Monthly budget lookup from database failed: {e}")

    try:
        import config

        value = getattr(config, "DEFAULT_MONTHLY_BUDGET", None)
        if value:
            return float(value)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Monthly budget lookup from config failed: {e}")
    return None


def _budget_row_to_dict(row: Any) -> Dict[str, Any]:
    """Serialise a CostBudgetDB row to the API dictionary shape."""
    return {
        "id": row.id,
        "name": row.name,
        "service": row.service,
        "amount": row.amount,
        "spent": row.spent,
        "used": row.spent,
        "remaining": row.remaining,
        "period": row.period,
        "status": row.status,
        "alerts_enabled": row.alerts_enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


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

        # 按时间排序；样本充足时用最小二乘拟合真实趋势，样本过少时用（可配置的）
        # 日均增长率外推 —— 增长率来自 config，而非写死常量。
        ordered = sorted(historical_costs, key=lambda r: str(r.get("timestamp", "")))
        series = [float(record["cost"]) for record in ordered]
        n = len(series)
        avg_daily_cost = sum(series) / n

        if n >= 3:
            intercept, slope = _fit_linear_trend(series)
            last_x = n - 1
            confidence = "high" if n >= 30 else "medium" if n >= 7 else "low"

            def _predict(i: int) -> float:
                return max(0.0, intercept + slope * (last_x + i))
        else:
            growth = _forecast_daily_growth_rate()
            confidence = "medium"

            def _predict(i: int, _avg: float = avg_daily_cost, _g: float = growth) -> float:
                return max(0.0, _avg * (1 + _g * i))

        forecast_data = [
            {
                "timestamp": (current_time + timedelta(days=i)).isoformat(),
                "forecasted_cost": _predict(i),
                "confidence": confidence,
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

        # Budget configuration: resolved from persisted budgets / config per deployment
        monthly_budget = _resolve_monthly_budget()
        warning_threshold = 0.8  # 80% warning threshold
        critical_threshold = 0.9  # 90% critical threshold

        if not monthly_budget or monthly_budget <= 0:
            # 未配置预算时如实上报，而非用恒定常量伪造利用率
            return {
                "status": "unconfigured",
                "alert_level": "low",
                "message": "No monthly budget configured; set a budget via /api/v1/cost/budgets",
                "budget": {
                    "monthly_budget": None,
                    "current_spend": total_spend,
                    "utilization_percent": None,
                    "remaining_budget": None,
                },
                "period": {
                    "start": current_month.isoformat(),
                    "end": (current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                },
                "recommendations": [],
                "last_updated": current_time.isoformat(),
            }

        budget_utilization = total_spend / monthly_budget

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

        total_cost = sum(service_costs.values())
        mean_service_cost = total_cost / len(service_costs) if service_costs else 0.0

        for service, cost in sorted_services[:5]:
            if mean_service_cost <= 0:
                continue
            if cost > mean_service_cost:
                # 高于均值的部分视为可右移/缩容空间（数据驱动，非固定比例）
                potential_savings = (cost - mean_service_cost) * 0.5
                priority = "high" if cost > 2 * mean_service_cost else "medium"
            else:
                potential_savings = cost * 0.05
                priority = "low"
            if potential_savings <= 0:
                continue
            suggestions.append({
                "id": len(suggestions) + 1,
                "type": "resize",
                "resource": service,
                "current_cost": cost,
                "potential_savings": potential_savings,
                "priority": priority,
                "action": f"Review {service} instance sizes and consider right-sizing",
            })

        # Idle-resource 建议：以显著低于均值的服务作为闲置信号（真实数据驱动）
        if cost_data and service_costs and mean_service_cost > 0:
            idle_candidates = [
                s for s, c in service_costs.items() if c < mean_service_cost * 0.25
            ]
            if idle_candidates:
                idle_cost = sum(service_costs[s] for s in idle_candidates)
                suggestions.append({
                    "id": len(suggestions) + 1,
                    "type": "idle_resources",
                    "resource": ", ".join(idle_candidates[:5]),
                    "current_cost": idle_cost,
                    "potential_savings": idle_cost,
                    "priority": "medium",
                    "action": "Identify and remove idle or underutilized resources",
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


def _read_llm_usage_from_metrics() -> Tuple[Dict[str, float], Dict[str, float]]:
    """从 Prometheus 默认注册表读取真实 LLM token / 成本计数。

    ``core.prometheus_metrics`` 在 LLM 推理链路的单一收口处累加
    ``aiops_ai_tokens_total`` 与 ``aiops_ai_cost_usd_total``；这里读取实际
    样本值，而不是按固定比例拆分（旧实现 0.6/0.4 为凭空推算）。

    Returns:
        (tokens_by_model, cost_by_model)；无样本时返回两个空字典。
    """
    tokens: Dict[str, float] = {}
    cost: Dict[str, float] = {}
    try:
        from prometheus_client import REGISTRY

        for metric in REGISTRY.collect():
            # prometheus_client strips the ``_total`` suffix from Counter names,
            # so accept both spellings.
            if metric.name in ("aiops_ai_tokens_total", "aiops_ai_tokens"):
                for sample in metric.samples:
                    if not sample.name.endswith("_total"):
                        continue
                    model = sample.labels.get("model", "unknown")
                    tokens[model] = tokens.get(model, 0.0) + float(sample.value)
            elif metric.name in ("aiops_ai_cost_usd_total", "aiops_ai_cost_usd"):
                for sample in metric.samples:
                    if not sample.name.endswith("_total"):
                        continue
                    model = sample.labels.get("model", "unknown")
                    cost[model] = cost.get(model, 0.0) + float(sample.value)
    except Exception as e:  # noqa: BLE001 - 指标注册表不可用则如实返回空
        logger.debug(f"LLM usage metric read failed: {e}")
    return tokens, cost


def get_llm_costs() -> Dict[str, Any]:
    """
    Get LLM-related costs from the real process metric registry.

    Returns:
        LLM cost breakdown by model plus total tokens/cost actually recorded
        via ``core.prometheus_metrics``. Returns zeroed/empty structures when
        no inference has been recorded yet (no synthetic breakdown).
    """
    try:
        tokens_by_model, cost_by_model = _read_llm_usage_from_metrics()

        total_tokens = int(sum(tokens_by_model.values()))
        total_cost = sum(cost_by_model.values())

        models = {
            model: {
                "tokens": int(tokens_by_model.get(model, 0)),
                "cost": round(cost_by_model.get(model, 0.0), 6),
            }
            for model in sorted(set(tokens_by_model) | set(cost_by_model))
        }

        result = {
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "models": models,
            "cost_per_1k_tokens": (total_cost / total_tokens * 1000) if total_tokens else 0.0,
            "period": "process_lifetime",
            "source": "prometheus_metrics_registry",
        }

        logger.info(f"Retrieved LLM costs: ${total_cost:.4f} over {total_tokens} tokens")
        return result

    except Exception as e:
        logger.error(f"Error getting LLM costs: {e}")
        return {
            "total_tokens": 0,
            "total_cost": 0.0,
            "models": {},
            "cost_per_1k_tokens": 0.0,
            "period": "process_lifetime",
            "source": "prometheus_metrics_registry",
        }


def get_budget_management() -> List[Dict[str, Any]]:
    """
    Get all budget configurations persisted in the ``cost_budgets`` table.

    Returns:
        List of budget configurations (empty when none have been created).
    """
    from core.database import SessionLocal
    from core.models import CostBudgetDB

    db = SessionLocal()
    try:
        rows = db.query(CostBudgetDB).order_by(CostBudgetDB.created_at).all()
        budgets = [_budget_row_to_dict(row) for row in rows]
        logger.info(f"Retrieved {len(budgets)} budget configurations")
        return budgets
    except Exception as e:
        logger.error(f"Error getting budget management: {e}")
        return []
    finally:
        db.close()


def create_budget(budget_data: dict) -> Dict[str, Any]:
    """
    Create a new budget configuration and persist it in ``cost_budgets``.

    Args:
        budget_data: Budget configuration data

    Returns:
        Created budget configuration
    """
    from core.database import SessionLocal
    from core.models import CostBudgetDB

    try:
        amount = float(budget_data.get("amount", 0) or 0)
        spent = float(budget_data.get("spent", budget_data.get("used", 0.0)) or 0.0)
        budget_id = budget_data.get("id") or f"budget-{uuid.uuid4().hex[:8]}"

        db = SessionLocal()
        try:
            row = CostBudgetDB(
                id=budget_id,
                name=budget_data.get("name", "New Budget"),
                service=budget_data.get("service", "default"),
                amount=amount,
                spent=spent,
                remaining=amount - spent,
                period=budget_data.get("period", "monthly"),
                status=budget_data.get("status", "on_track"),
                alerts_enabled=bool(budget_data.get("alerts_enabled", True)),
                budget_metadata=budget_data.get("metadata"),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            new_budget = _budget_row_to_dict(row)
        finally:
            db.close()

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
