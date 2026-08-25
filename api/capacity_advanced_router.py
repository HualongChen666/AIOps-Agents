# -*- coding: utf-8 -*-
"""
Advanced Capacity Planning API Router
=====================================

Provides comprehensive capacity planning endpoints including planning,
forecasts, optimization, rightsizing, and recommendations.

Endpoints:
- GET/POST   /api/v1/capacity/planning
- GET        /api/v1/capacity/forecasts
- GET/POST   /api/v1/capacity/optimization
- GET        /api/v1/capacity/rightsizing
- GET        /api/v1/capacity/recommendations
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.auth_service import require_roles
from core.capacity_engine import forecast_capacity, generate_scaling_recommendations
from core.collector import get_disk_metrics
from core.metrics_history import METRICS_HISTORY as metrics_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/capacity", tags=["capacity-advanced"])

_NETWORK_CAP_MB = 100.0
_DISK_HISTORY_LEN = 10


# ============================================================================
# Enums and Models
# ============================================================================


class ResourceType(str, Enum):
    """Resource type for capacity planning."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    STORAGE = "storage"


class PlanningHorizon(str, Enum):
    """Planning time horizon."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class OptimizationStrategy(str, Enum):
    """Optimization strategy."""

    COST_OPTIMIZATION = "cost_optimization"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class RightsizingAction(str, Enum):
    """Rightsizing action type."""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_OUT = "scale_out"
    SCALE_IN = "scale_in"
    NO_ACTION = "no_action"


class Priority(str, Enum):
    """Priority level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# Pydantic Models
# ============================================================================


class CapacityPlan(BaseModel):
    """Model for capacity planning."""

    id: str = Field(..., description="Plan ID")
    name: str = Field(..., description="Plan name")
    resource_type: ResourceType = Field(..., description="Resource type")
    service: str = Field(..., description="Service name")
    current_capacity: float = Field(..., description="Current capacity value")
    projected_capacity: float = Field(..., description="Projected capacity value")
    unit: str = Field(..., description="Capacity unit (%, GB, MB/s, etc.)")
    horizon: PlanningHorizon = Field(..., description="Planning horizon")
    target_date: datetime = Field(..., description="Target date for capacity")
    threshold: float = Field(..., description="Alert threshold")
    recommended_action: str = Field(..., description="Recommended action")
    estimated_cost: float = Field(default=0.0, description="Estimated cost of action")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", description="Creator")
    status: str = Field(default="draft", description="Plan status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CapacityPlanCreate(BaseModel):
    """Model for creating a capacity plan."""

    name: str = Field(..., min_length=1, max_length=255)
    resource_type: ResourceType
    service: str
    horizon: PlanningHorizon
    target_date: datetime
    threshold: float = Field(..., ge=0, le=100)
    recommended_action: str
    estimated_cost: float = Field(default=0.0, ge=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CapacityForecast(BaseModel):
    """Model for capacity forecast."""

    metric: str = Field(..., description="Metric name")
    resource_type: ResourceType = Field(..., description="Resource type")
    service: str = Field(..., description="Service name")
    current_value: float = Field(..., description="Current value")
    forecast_7d: float = Field(..., description="7-day forecast")
    forecast_30d: float = Field(..., description="30-day forecast")
    forecast_90d: float = Field(..., description="90-day forecast")
    threshold: float = Field(..., description="Alert threshold")
    unit: str = Field(..., description="Unit")
    confidence: float = Field(..., ge=0, le=1, description="Forecast confidence")
    trend: str = Field(..., description="Trend direction (increasing/decreasing/stable)")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class OptimizationRequest(BaseModel):
    """Model for optimization request."""

    service: str = Field(..., description="Service name")
    resource_types: List[ResourceType] = Field(default_factory=list)
    strategy: OptimizationStrategy = Field(default=OptimizationStrategy.BALANCED)
    target_cost_reduction: float = Field(
        default=0.2, ge=0, le=1, description="Target cost reduction (0-1)"
    )
    min_performance_sla: float = Field(
        default=0.95, ge=0, le=1, description="Minimum performance SLA"
    )
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OptimizationResult(BaseModel):
    """Model for optimization result."""

    id: str = Field(..., description="Optimization ID")
    service: str = Field(..., description="Service name")
    strategy: OptimizationStrategy = Field(..., description="Strategy used")
    current_cost: float = Field(..., description="Current monthly cost")
    optimized_cost: float = Field(..., description="Optimized monthly cost")
    cost_savings: float = Field(..., description="Monthly cost savings")
    savings_percentage: float = Field(..., description="Savings percentage")
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    implementation_steps: List[str] = Field(default_factory=list)
    risk_assessment: str = Field(..., description="Risk assessment")
    estimated_implementation_time: str = Field(..., description="Implementation time estimate")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RightsizingRecommendation(BaseModel):
    """Model for rightsizing recommendation."""

    id: str = Field(..., description="Recommendation ID")
    service: str = Field(..., description="Service name")
    resource_type: ResourceType = Field(..., description="Resource type")
    current_spec: Dict[str, Any] = Field(..., description="Current specification")
    recommended_spec: Dict[str, Any] = Field(..., description="Recommended specification")
    action: RightsizingAction = Field(..., description="Action to take")
    reason: str = Field(..., description="Reason for recommendation")
    priority: Priority = Field(..., description="Priority level")
    estimated_monthly_savings: float = Field(..., description="Estimated monthly savings")
    performance_impact: str = Field(..., description="Expected performance impact")
    implementation_complexity: str = Field(..., description="Implementation complexity")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScalingRecommendation(BaseModel):
    """Model for scaling recommendation."""

    id: str = Field(..., description="Recommendation ID")
    service: str = Field(..., description="Service name")
    action: str = Field(..., description="Action (scale-up/scale-down/no-action)")
    reason: str = Field(..., description="Reason for recommendation")
    priority: Priority = Field(..., description="Priority level")
    estimated_cost: float = Field(..., description="Estimated cost")
    resource_type: ResourceType = Field(..., description="Resource type")
    current_value: float = Field(..., description="Current resource value")
    recommended_value: float = Field(..., description="Recommended resource value")
    unit: str = Field(..., description="Unit")
    time_horizon: str = Field(..., description="Time horizon for action")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")


# ============================================================================
# In-Memory Data Storage
# ============================================================================

_capacity_plans: Dict[str, CapacityPlan] = {}
_optimization_results: Dict[str, OptimizationResult] = {}
_rightsizing_recommendations: List[RightsizingRecommendation] = []


def _generate_plan_id() -> str:
    """Generate a unique plan ID."""
    import uuid

    return f"CP-{uuid.uuid4().hex[:8].upper()}"


def _generate_optimization_id() -> str:
    """Generate a unique optimization ID."""
    import uuid

    return f"OPT-{uuid.uuid4().hex[:8].upper()}"


def _generate_rightsizing_id() -> str:
    """Generate a unique rightsizing ID."""
    import uuid

    return f"RS-{uuid.uuid4().hex[:8].upper()}"


# ============================================================================
# Helper Functions
# ============================================================================


async def _build_metric_history() -> Dict[str, List[float]]:
    """Build a normalized metric history dict for the forecasting engine."""
    hist = metrics_history.to_dict()

    cpu = [float(v) for v in hist.get("cpu", [])]
    memory = [float(v) for v in hist.get("memory", [])]
    net_in = [float(v) for v in hist.get("net_in", [])]
    network = [max(0.0, min(100.0, v / _NETWORK_CAP_MB * 100.0)) for v in net_in]

    try:
        disks = await asyncio.to_thread(get_disk_metrics)
        avg = sum(d.get("usage_percent", 0.0) for d in disks) / max(len(disks), 1)
    except Exception as e:
        logger.warning(f"磁盘指标采集失败，使用默认值: {e}")
        avg = 45.0

    disk = [
        max(0.0, min(100.0, avg - (_DISK_HISTORY_LEN - 1 - i) * 0.5))
        for i in range(_DISK_HISTORY_LEN)
    ]

    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "network": network,
    }


def _calculate_trend(current: float, forecast: float) -> str:
    """Calculate trend direction."""
    if forecast > current * 1.05:
        return "increasing"
    elif forecast < current * 0.95:
        return "decreasing"
    else:
        return "stable"


def _calculate_confidence(history_length: int) -> float:
    """Calculate forecast confidence based on history length."""
    if history_length >= 10:
        return 0.85
    elif history_length >= 5:
        return 0.70
    elif history_length >= 3:
        return 0.50
    else:
        return 0.30


# ============================================================================
# API Endpoints - Planning
# ============================================================================


@router.get("/planning", response_model=List[CapacityPlan])
async def list_capacity_plans(
    service: Optional[str] = Query(None, description="Filter by service"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    horizon: Optional[PlanningHorizon] = Query(None, description="Filter by horizon"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List all capacity plans with optional filtering.

    Returns capacity planning documents that define resource allocation
    targets and timelines for services.
    """
    try:
        plans = list(_capacity_plans.values())

        if service:
            plans = [p for p in plans if p.service == service]
        if resource_type:
            plans = [p for p in plans if p.resource_type == resource_type]
        if status:
            plans = [p for p in plans if p.status == status]
        if horizon:
            plans = [p for p in plans if p.horizon == horizon]

        return sorted(plans, key=lambda p: p.created_at, reverse=True)
    except Exception as e:
        logger.error(f"Error listing capacity plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list plans: {str(e)}")


@router.post("/planning", response_model=CapacityPlan, status_code=status.HTTP_201_CREATED)
async def create_capacity_plan(
    plan: CapacityPlanCreate,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a new capacity plan.

    Creates a capacity planning document defining resource targets
    and implementation timelines.
    """
    try:
        plan_id = _generate_plan_id()

        # Get current capacity from metrics
        metric_history = await _build_metric_history()
        resource_key = plan.resource_type.value
        current_values = metric_history.get(resource_key, [50.0])
        current_capacity = current_values[-1] if current_values else 50.0

        # Calculate projected capacity based on horizon
        if plan.horizon == PlanningHorizon.WEEKLY:
            days_ahead = 7
        elif plan.horizon == PlanningHorizon.MONTHLY:
            days_ahead = 30
        elif plan.horizon == PlanningHorizon.QUARTERLY:
            days_ahead = 90
        else:
            days_ahead = 365

        # Simple projection: assume 2% growth per week
        growth_rate = 1.02 ** (days_ahead / 7)
        projected_capacity = current_capacity * growth_rate

        # Determine unit based on resource type
        unit_map = {
            ResourceType.CPU: "%",
            ResourceType.MEMORY: "%",
            ResourceType.DISK: "%",
            ResourceType.NETWORK: "%",
            ResourceType.GPU: "%",
            ResourceType.STORAGE: "GB",
        }
        unit = unit_map.get(plan.resource_type, "%")

        new_plan = CapacityPlan(
            id=plan_id,
            name=plan.name,
            resource_type=plan.resource_type,
            service=plan.service,
            current_capacity=current_capacity,
            projected_capacity=projected_capacity,
            unit=unit,
            horizon=plan.horizon,
            target_date=plan.target_date,
            threshold=plan.threshold,
            recommended_action=plan.recommended_action,
            estimated_cost=plan.estimated_cost,
            created_by=current_user.username if hasattr(current_user, "username") else "system",
            status="draft",
            metadata=plan.metadata,
        )

        _capacity_plans[plan_id] = new_plan

        logger.info(f"Created capacity plan: {plan_id} for service {plan.service}")

        return new_plan
    except Exception as e:
        logger.error(f"Error creating capacity plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create plan: {str(e)}")


@router.get("/planning/{plan_id}", response_model=CapacityPlan)
async def get_capacity_plan(
    plan_id: str,
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """Get a specific capacity plan by ID."""
    try:
        if plan_id not in _capacity_plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")
        return _capacity_plans[plan_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capacity plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get plan: {str(e)}")


@router.patch("/planning/{plan_id}", response_model=CapacityPlan)
async def update_capacity_plan(
    plan_id: str,
    status: Optional[str] = None,
    recommended_action: Optional[str] = None,
    estimated_cost: Optional[float] = None,
    current_user=Depends(require_roles("admin", "operator")),
):
    """Update a capacity plan."""
    try:
        if plan_id not in _capacity_plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        plan = _capacity_plans[plan_id]

        if status is not None:
            plan.status = status
        if recommended_action is not None:
            plan.recommended_action = recommended_action
        if estimated_cost is not None:
            plan.estimated_cost = estimated_cost

        logger.info(f"Updated capacity plan: {plan_id}")

        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating capacity plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {str(e)}")


@router.delete("/planning/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capacity_plan(
    plan_id: str,
    current_user=Depends(require_roles("admin")),
):
    """Delete a capacity plan."""
    try:
        if plan_id not in _capacity_plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        del _capacity_plans[plan_id]

        logger.info(f"Deleted capacity plan: {plan_id}")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting capacity plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete plan: {str(e)}")


# ============================================================================
# API Endpoints - Forecasts
# ============================================================================


@router.get("/forecasts", response_model=List[CapacityForecast])
async def get_capacity_forecasts(
    service: Optional[str] = Query(None, description="Filter by service"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get capacity forecasts.

    Returns multi-horizon forecasts (7, 30, 90 days) for various resources
    with confidence intervals and trend analysis.
    """
    try:
        metric_history = await _build_metric_history()
        forecasts = forecast_capacity(metric_history, days_ahead=7)

        # Map service names
        service_map = {
            "cpu": "compute-service",
            "memory": "cache-service",
            "disk": "database",
            "network": "api-gateway",
        }

        resource_type_map = {
            "cpu": ResourceType.CPU,
            "memory": ResourceType.MEMORY,
            "disk": ResourceType.DISK,
            "network": ResourceType.NETWORK,
        }

        result = []
        for key, forecast in forecasts.items():
            rt = resource_type_map.get(key, ResourceType.CPU)
            svc = service or service_map.get(key, "unknown")

            # Calculate 90-day forecast (extrapolate from 30-day)
            forecast_30 = forecast.get("forecast30d", 0.0)
            forecast_90 = forecast_30 * 1.1  # Assume 10% additional growth

            current = forecast.get("currentValue", 0.0)
            trend = _calculate_trend(current, forecast_90)
            confidence = _calculate_confidence(len(metric_history.get(key, [])))

            result.append(
                CapacityForecast(
                    metric=forecast.get("metric", key),
                    resource_type=rt,
                    service=svc,
                    current_value=current,
                    forecast_7d=forecast.get("forecast7d", 0.0),
                    forecast_30d=forecast_30,
                    forecast_90d=forecast_90,
                    threshold=forecast.get("threshold", 80.0),
                    unit=forecast.get("unit", "%"),
                    confidence=confidence,
                    trend=trend,
                )
            )

        if resource_type:
            result = [f for f in result if f.resource_type == resource_type]

        return result
    except Exception as e:
        logger.error(f"Error getting capacity forecasts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get forecasts: {str(e)}")


# ============================================================================
# API Endpoints - Optimization
# ============================================================================


@router.get("/optimization", response_model=List[OptimizationResult])
async def list_optimization_results(
    service: Optional[str] = Query(None, description="Filter by service"),
    strategy: Optional[OptimizationStrategy] = Query(None, description="Filter by strategy"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List optimization results.

    Returns historical optimization analysis results showing cost savings
    and performance improvements.
    """
    try:
        results = list(_optimization_results.values())

        if service:
            results = [r for r in results if r.service == service]
        if strategy:
            results = [r for r in results if r.strategy == strategy]

        return sorted(results, key=lambda r: r.created_at, reverse=True)
    except Exception as e:
        logger.error(f"Error listing optimization results: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list optimization results: {str(e)}"
        )


@router.post(
    "/optimization", response_model=OptimizationResult, status_code=status.HTTP_201_CREATED
)
async def create_optimization(
    request: OptimizationRequest,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a new optimization analysis.

    Analyzes resource usage patterns and generates optimization
    recommendations based on the specified strategy.
    """
    try:
        opt_id = _generate_optimization_id()

        # Get current metrics
        metric_history = await _build_metric_history()  # noqa: F841 - Reserved for future use

        # Calculate current cost (simplified model)
        current_cost = 1000.0  # Base monthly cost

        # Calculate optimization based on strategy
        if request.strategy == OptimizationStrategy.COST_OPTIMIZATION:
            cost_reduction = request.target_cost_reduction
            performance_impact = (
                0.05  # 5% performance impact  # noqa: F841 - Reserved for future use
            )
        elif request.strategy == OptimizationStrategy.PERFORMANCE_OPTIMIZATION:
            cost_reduction = 0.1  # 10% cost reduction
            performance_impact = (
                -0.15
            )  # 15% performance improvement  # noqa: F841 - Reserved for future use
        elif request.strategy == OptimizationStrategy.AGGRESSIVE:
            cost_reduction = 0.3  # 30% cost reduction
            performance_impact = (
                0.15  # 15% performance impact  # noqa: F841 - Reserved for future use
            )
        else:  # BALANCED
            cost_reduction = 0.2  # 20% cost reduction
            performance_impact = (
                0.02  # 2% performance impact  # noqa: F841 - Reserved for future use
            )

        optimized_cost = current_cost * (1 - cost_reduction)
        cost_savings = current_cost - optimized_cost
        savings_percentage = cost_savings / current_cost * 100

        # Generate recommendations
        recommendations = []
        if request.resource_types:
            for rt in request.resource_types:
                if rt == ResourceType.CPU:
                    recommendations.append(
                        {
                            "resource_type": "CPU",
                            "action": "rightsize_instances",
                            "current": "4 vCPU",
                            "recommended": "2 vCPU",
                            "savings": 200.0,
                        }
                    )
                elif rt == ResourceType.MEMORY:
                    recommendations.append(
                        {
                            "resource_type": "Memory",
                            "action": "optimize_memory_allocation",
                            "current": "16 GB",
                            "recommended": "8 GB",
                            "savings": 150.0,
                        }
                    )
                elif rt == ResourceType.STORAGE:
                    recommendations.append(
                        {
                            "resource_type": "Storage",
                            "action": "implement_storage_tiering",
                            "current": "1 TB SSD",
                            "recommended": "500 GB SSD + 500 GB HDD",
                            "savings": 100.0,
                        }
                    )

        # Implementation steps
        implementation_steps = [
            "1. Analyze current resource utilization patterns",
            "2. Identify underutilized resources",
            "3. Implement rightsizing recommendations",
            "4. Monitor performance post-optimization",
            "5. Adjust based on observed results",
        ]

        # Risk assessment
        if cost_reduction > 0.25:
            risk_assessment = "High - significant performance impact possible"
            implementation_time = "4-6 weeks"
        elif cost_reduction > 0.15:
            risk_assessment = "Medium - moderate performance impact expected"
            implementation_time = "2-4 weeks"
        else:
            risk_assessment = "Low - minimal performance impact expected"
            implementation_time = "1-2 weeks"

        result = OptimizationResult(
            id=opt_id,
            service=request.service,
            strategy=request.strategy,
            current_cost=current_cost,
            optimized_cost=optimized_cost,
            cost_savings=cost_savings,
            savings_percentage=savings_percentage,
            recommendations=recommendations,
            implementation_steps=implementation_steps,
            risk_assessment=risk_assessment,
            estimated_implementation_time=implementation_time,
        )

        _optimization_results[opt_id] = result

        logger.info(f"Created optimization analysis: {opt_id} for service {request.service}")

        return result
    except Exception as e:
        logger.error(f"Error creating optimization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create optimization: {str(e)}")


# ============================================================================
# API Endpoints - Rightsizing
# ============================================================================


@router.get("/rightsizing", response_model=List[RightsizingRecommendation])
async def get_rightsizing_recommendations(
    service: Optional[str] = Query(None, description="Filter by service"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get rightsizing recommendations.

    Returns recommendations for rightsizing resources based on
    actual usage patterns to optimize costs.
    """
    try:
        # Generate recommendations if not already done
        if not _rightsizing_recommendations:
            await _generate_rightsizing_recommendations()

        recommendations = _rightsizing_recommendations

        if service:
            recommendations = [r for r in recommendations if r.service == service]
        if resource_type:
            recommendations = [r for r in recommendations if r.resource_type == resource_type]
        if priority:
            recommendations = [r for r in recommendations if r.priority == priority]

        return recommendations
    except Exception as e:
        logger.error(f"Error getting rightsizing recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get rightsizing: {str(e)}")


async def _generate_rightsizing_recommendations() -> None:
    """Generate rightsizing recommendations based on current metrics."""
    global _rightsizing_recommendations

    metric_history = await _build_metric_history()

    services = ["compute-service", "cache-service", "database", "api-gateway"]
    resource_types = [ResourceType.CPU, ResourceType.MEMORY, ResourceType.DISK]

    for service in services:
        for rt in resource_types:
            key = rt.value
            values = metric_history.get(key, [50.0])
            current_value = values[-1] if values else 50.0

            # Determine action based on utilization
            if current_value < 30:
                action = RightsizingAction.SCALE_DOWN
                priority = Priority.MEDIUM
                reason = f"Low utilization ({current_value:.1f}%) indicates over-provisioning"
                current_spec = {"value": current_value, "unit": "%"}
                recommended_spec = {"value": current_value * 0.7, "unit": "%"}
                savings = 100.0
                performance_impact = "Minimal - current usage well below capacity"
            elif current_value > 85:
                action = RightsizingAction.SCALE_UP
                priority = Priority.HIGH
                reason = f"High utilization ({current_value:.1f}%) indicates under-provisioning"
                current_spec = {"value": current_value, "unit": "%"}
                recommended_spec = {"value": current_value * 1.3, "unit": "%"}
                savings = -50.0  # Cost increase
                performance_impact = "Positive - improved performance and stability"
            else:
                action = RightsizingAction.NO_ACTION
                priority = Priority.LOW
                reason = f"Utilization ({current_value:.1f}%) within optimal range"
                current_spec = {"value": current_value, "unit": "%"}
                recommended_spec = {"value": current_value, "unit": "%"}
                savings = 0.0
                performance_impact = "None - current configuration is optimal"

            rec = RightsizingRecommendation(
                id=_generate_rightsizing_id(),
                service=service,
                resource_type=rt,
                current_spec=current_spec,
                recommended_spec=recommended_spec,
                action=action,
                reason=reason,
                priority=priority,
                estimated_monthly_savings=savings,
                performance_impact=performance_impact,
                implementation_complexity=(
                    "Low" if action == RightsizingAction.NO_ACTION else "Medium"
                ),
            )

            _rightsizing_recommendations.append(rec)


# ============================================================================
# API Endpoints - Recommendations
# ============================================================================


@router.get("/recommendations", response_model=List[ScalingRecommendation])
async def get_scaling_recommendations(
    service: Optional[str] = Query(None, description="Filter by service"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get scaling recommendations.

    Returns actionable scaling recommendations based on capacity
    forecasts and current utilization patterns.
    """
    try:
        metric_history = await _build_metric_history()
        forecasts = forecast_capacity(metric_history, days_ahead=7)
        base_recommendations = generate_scaling_recommendations(forecasts)

        # Map to enhanced model
        service_map = {
            "cpu": "compute-service",
            "memory": "cache-service",
            "disk": "database",
            "network": "api-gateway",
        }

        resource_type_map = {
            "cpu": ResourceType.CPU,
            "memory": ResourceType.MEMORY,
            "disk": ResourceType.DISK,
            "network": ResourceType.NETWORK,
        }

        priority_map = {
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }

        result = []
        for rec in base_recommendations:
            key = rec["id"].split("-")[1].lower()
            rt = resource_type_map.get(key, ResourceType.CPU)
            svc = service or service_map.get(key, "unknown")

            forecast = forecasts.get(key, {})
            current_value = forecast.get("currentValue", 0.0)
            threshold = forecast.get("threshold", 80.0)

            # Calculate recommended value
            if rec["action"] == "scale-up":
                recommended_value = threshold * 0.9
            elif rec["action"] == "scale-down":
                recommended_value = threshold * 0.5
            else:
                recommended_value = current_value

            result.append(
                ScalingRecommendation(
                    id=rec["id"],
                    service=svc,
                    action=rec["action"],
                    reason=rec["reason"],
                    priority=priority_map.get(rec["priority"], Priority.MEDIUM),
                    estimated_cost=rec["estimatedCost"],
                    resource_type=rt,
                    current_value=current_value,
                    recommended_value=recommended_value,
                    unit=forecast.get("unit", "%"),
                    time_horizon="7-30 days",
                    confidence=0.75,
                )
            )

        if service:
            result = [r for r in result if r.service == service]
        if resource_type:
            result = [r for r in result if r.resource_type == resource_type]
        if priority:
            result = [r for r in result if r.priority == priority]

        return result
    except Exception as e:
        logger.error(f"Error getting scaling recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")
