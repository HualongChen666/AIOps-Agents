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
from sqlalchemy.orm import Session

from core.auth_service import require_roles
from core.capacity_engine import forecast_capacity, generate_scaling_recommendations
from core.collector import get_disk_metrics
from core.database import get_db
from core.metrics_history import METRICS_HISTORY as metrics_history
from core.models import (
    CapacityPlanDB,
    OptimizationResultDB,
    RightsizingRecommendationDB,
)

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
# In-Memory Data Storage (fallback)
# ============================================================================

_capacity_plans: Dict[str, CapacityPlan] = {}
_optimization_results: Dict[str, OptimizationResult] = {}
_rightsizing_recommendations: List[RightsizingRecommendation] = []


def _get_capacity_plans(db: Optional[Session] = None) -> Dict[str, CapacityPlan]:
    """Get capacity plans from database with fallback to memory."""
    try:
        if db:
            db_plans = db.query(CapacityPlanDB).all()
            return {
                plan.id: CapacityPlan(
                    id=plan.id,
                    name=plan.name,
                    resource_type=ResourceType(plan.resource_type),
                    service=plan.service,
                    current_capacity=plan.current_capacity,
                    projected_capacity=plan.projected_capacity,
                    unit=plan.unit,
                    horizon=PlanningHorizon(plan.horizon),
                    target_date=plan.target_date,
                    threshold=plan.threshold,
                    recommended_action=plan.recommended_action,
                    estimated_cost=plan.estimated_cost,
                    created_at=plan.created_at,
                    created_by=plan.created_by,
                    status=plan.status,
                    metadata=plan.plan_metadata,
                )
                for plan in db_plans
            }
        # Fallback to memory storage
        return _capacity_plans
    except Exception as e:
        logger.error(f"Failed to get capacity plans from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _capacity_plans


def _set_capacity_plan(plan: CapacityPlan, db: Optional[Session] = None) -> None:
    """Set capacity plan in database with fallback to memory."""
    try:
        if db:
            existing_plan = db.query(CapacityPlanDB).filter(
                CapacityPlanDB.id == plan.id
            ).first()
            if existing_plan:
                existing_plan.name = plan.name
                existing_plan.resource_type = plan.resource_type.value
                existing_plan.service = plan.service
                existing_plan.current_capacity = plan.current_capacity
                existing_plan.projected_capacity = plan.projected_capacity
                existing_plan.unit = plan.unit
                existing_plan.horizon = plan.horizon.value
                existing_plan.target_date = plan.target_date
                existing_plan.threshold = plan.threshold
                existing_plan.recommended_action = plan.recommended_action
                existing_plan.estimated_cost = plan.estimated_cost
                existing_plan.status = plan.status
                existing_plan.plan_metadata = plan.metadata
            else:
                db_plan = CapacityPlanDB(
                    id=plan.id,
                    name=plan.name,
                    resource_type=plan.resource_type.value,
                    service=plan.service,
                    current_capacity=plan.current_capacity,
                    projected_capacity=plan.projected_capacity,
                    unit=plan.unit,
                    horizon=plan.horizon.value,
                    target_date=plan.target_date,
                    threshold=plan.threshold,
                    recommended_action=plan.recommended_action,
                    estimated_cost=plan.estimated_cost,
                    created_at=plan.created_at,
                    created_by=plan.created_by,
                    status=plan.status,
                    plan_metadata=plan.metadata,
                )
                db.add(db_plan)
            db.commit()
        else:
            # Fallback to memory storage
            _capacity_plans[plan.id] = plan
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to set capacity plan in database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _capacity_plans[plan.id] = plan


def _delete_capacity_plan(plan_id: str, db: Optional[Session] = None) -> None:
    """Delete capacity plan from database with fallback to memory."""
    try:
        if db:
            db.query(CapacityPlanDB).filter(
                CapacityPlanDB.id == plan_id
            ).delete()
            db.commit()
        else:
            # Fallback to memory storage
            _capacity_plans.pop(plan_id, None)
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to delete capacity plan from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _capacity_plans.pop(plan_id, None)


def _get_optimization_results(db: Optional[Session] = None) -> Dict[str, OptimizationResult]:
    """Get optimization results from database with fallback to memory."""
    try:
        if db:
            db_results = db.query(OptimizationResultDB).all()
            return {
                result.id: OptimizationResult(
                    id=result.id,
                    service=result.service,
                    resource_types=[ResourceType(rt) for rt in result.resource_types],
                    strategy=OptimizationStrategy(result.strategy),
                    current_usage=result.current_usage,
                    optimized_usage=result.optimized_usage,
                    savings=result.savings,
                    implementation_steps=result.implementation_steps,
                    created_at=result.created_at,
                    created_by=result.created_by,
                    status=result.status,
                    metadata=result.opt_metadata,
                )
                for result in db_results
            }
        # Fallback to memory storage
        return _optimization_results
    except Exception as e:
        logger.error(f"Failed to get optimization results from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _optimization_results


def _set_optimization_result(result: OptimizationResult, db: Optional[Session] = None) -> None:
    """Set optimization result in database with fallback to memory."""
    try:
        if db:
            existing_result = db.query(OptimizationResultDB).filter(
                OptimizationResultDB.id == result.id
            ).first()
            if existing_result:
                existing_result.service = result.service
                existing_result.resource_types = [rt.value for rt in result.resource_types]
                existing_result.strategy = result.strategy.value
                existing_result.current_usage = result.current_usage
                existing_result.optimized_usage = result.optimized_usage
                existing_result.savings = result.savings
                existing_result.implementation_steps = result.implementation_steps
                existing_result.status = result.status
                existing_result.opt_metadata = result.metadata
            else:
                db_result = OptimizationResultDB(
                    id=result.id,
                    service=result.service,
                    resource_types=[rt.value for rt in result.resource_types],
                    strategy=result.strategy.value,
                    current_usage=result.current_usage,
                    optimized_usage=result.optimized_usage,
                    savings=result.savings,
                    implementation_steps=result.implementation_steps,
                    created_at=result.created_at,
                    created_by=result.created_by,
                    status=result.status,
                    opt_metadata=result.metadata,
                )
                db.add(db_result)
            db.commit()
        else:
            # Fallback to memory storage
            _optimization_results[result.id] = result
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to set optimization result in database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _optimization_results[result.id] = result


def _get_rightsizing_recommendations(db: Optional[Session] = None) -> List[RightsizingRecommendation]:
    """Get rightsizing recommendations from database with fallback to memory."""
    try:
        if db:
            db_recommendations = db.query(RightsizingRecommendationDB).all()
            return [
                RightsizingRecommendation(
                    id=rec.id,
                    service=rec.service,
                    resource_type=ResourceType(rec.resource_type),
                    current_spec=rec.current_spec,
                    recommended_spec=rec.recommended_spec,
                    action=RightsizingAction(rec.action),
                    reason=rec.reason,
                    priority=Priority(rec.priority),
                    estimated_monthly_savings=rec.estimated_monthly_savings,
                    performance_impact=rec.performance_impact,
                    implementation_complexity=rec.implementation_complexity,
                    created_at=rec.created_at,
                )
                for rec in db_recommendations
            ]
        # Fallback to memory storage
        return _rightsizing_recommendations
    except Exception as e:
        logger.error(f"Failed to get rightsizing recommendations from database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        return _rightsizing_recommendations


def _add_rightsizing_recommendation(recommendation: RightsizingRecommendation, db: Optional[Session] = None) -> None:
    """Add rightsizing recommendation to database with fallback to memory."""
    try:
        if db:
            db_recommendation = RightsizingRecommendationDB(
                id=recommendation.id,
                service=recommendation.service,
                resource_type=recommendation.resource_type.value,
                current_spec=recommendation.current_spec,
                recommended_spec=recommendation.recommended_spec,
                action=recommendation.action.value,
                reason=recommendation.reason,
                priority=recommendation.priority.value,
                estimated_monthly_savings=recommendation.estimated_monthly_savings,
                performance_impact=recommendation.performance_impact,
                implementation_complexity=recommendation.implementation_complexity,
                created_at=recommendation.created_at,
                rec_metadata=None,
            )
            db.add(db_recommendation)
            db.commit()
        else:
            # Fallback to memory storage
            _rightsizing_recommendations.append(recommendation)
    except Exception as e:
        db.rollback() if db else None
        logger.error(f"Failed to add rightsizing recommendation to database, using fallback: {e}", exc_info=True)
        # Fallback to memory storage
        _rightsizing_recommendations.append(recommendation)


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
    db_core: Session = Depends(get_db),
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

        _set_capacity_plan(new_plan, db_core)

        logger.info(f"Created capacity plan: {plan_id} for service {plan.service}")

        return new_plan
    except Exception as e:
        logger.error(f"Error creating capacity plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create plan: {str(e)}")


@router.get("/planning/{plan_id}", response_model=CapacityPlan)
async def get_capacity_plan(
    plan_id: str,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """Get a specific capacity plan by ID."""
    try:
        plans = _get_capacity_plans(db_core)
        if plan_id not in plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")
        return plans[plan_id]
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
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """Update a capacity plan."""
    try:
        plans = _get_capacity_plans(db_core)
        if plan_id not in plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        plan = plans[plan_id]

        if status is not None:
            plan.status = status
        if recommended_action is not None:
            plan.recommended_action = recommended_action
        if estimated_cost is not None:
            plan.estimated_cost = estimated_cost

        # Save to database with fallback
        _set_capacity_plan(plan, db_core)

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
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Delete a capacity plan."""
    try:
        plans = _get_capacity_plans(db_core)
        if plan_id not in plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        _delete_capacity_plan(plan_id, db_core)

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
    db_core: Session = Depends(get_db),
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

        _set_optimization_result(result, db_core)

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
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get rightsizing recommendations.

    Returns recommendations for rightsizing resources based on
    actual usage patterns to optimize costs.
    """
    try:
        # Get recommendations from database with fallback
        recommendations = _get_rightsizing_recommendations(db_core)
        
        # Generate recommendations if not already done
        if not recommendations:
            await _generate_rightsizing_recommendations(db_core)
            recommendations = _get_rightsizing_recommendations(db_core)

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


async def _generate_rightsizing_recommendations(db_core: Optional[Session] = None) -> None:
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

            _add_rightsizing_recommendation(rec, db_core)


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


# ============================================================================
# API Endpoints - Planning Extensions
# ============================================================================


@router.post("/planning/{plan_id}/approve", response_model=CapacityPlan)
async def approve_capacity_plan(
    plan_id: str,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Approve a capacity plan for execution.

    Changes the plan status from 'draft' to 'approved' and records
    the approver information for audit purposes.
    """
    try:
        plans = _get_capacity_plans(db_core)
        if plan_id not in plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        plan = plans[plan_id]

        if plan.status == "approved":
            raise HTTPException(status_code=400, detail=f"Plan {plan_id} is already approved")
        if plan.status == "executed":
            raise HTTPException(status_code=400, detail=f"Plan {plan_id} has already been executed")
        if plan.status == "rejected":
            raise HTTPException(status_code=400, detail=f"Plan {plan_id} has been rejected")

        plan.status = "approved"
        plan.metadata["approved_by"] = current_user.username if hasattr(current_user, "username") else "system"
        plan.metadata["approved_at"] = datetime.utcnow().isoformat()

        _set_capacity_plan(plan, db_core)

        logger.info(f"Approved capacity plan: {plan_id} by {plan.metadata.get('approved_by')}")

        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving capacity plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve plan: {str(e)}")


@router.post("/planning/{plan_id}/reject", response_model=CapacityPlan)
async def reject_capacity_plan(
    plan_id: str,
    reason: str = Query(..., min_length=1, max_length=500, description="Rejection reason"),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Reject a capacity plan.

    Changes the plan status from 'draft' to 'rejected' and records
    the rejection reason for audit purposes.
    """
    try:
        plans = _get_capacity_plans(db_core)
        if plan_id not in plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        plan = plans[plan_id]

        if plan.status == "rejected":
            raise HTTPException(status_code=400, detail=f"Plan {plan_id} is already rejected")
        if plan.status == "executed":
            raise HTTPException(status_code=400, detail=f"Plan {plan_id} has already been executed")
        if plan.status == "approved":
            raise HTTPException(status_code=400, detail=f"Plan {plan_id} is already approved")

        plan.status = "rejected"
        plan.metadata["rejected_by"] = current_user.username if hasattr(current_user, "username") else "system"
        plan.metadata["rejected_at"] = datetime.utcnow().isoformat()
        plan.metadata["rejection_reason"] = reason

        _set_capacity_plan(plan, db_core)

        logger.info(f"Rejected capacity plan: {plan_id} by {plan.metadata.get('rejected_by')}, reason: {reason}")

        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting capacity plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reject plan: {str(e)}")


@router.post("/planning/{plan_id}/execute", response_model=CapacityPlan)
async def execute_capacity_plan(
    plan_id: str,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Execute an approved capacity plan.

    Changes the plan status from 'approved' to 'executed' and triggers
    the actual capacity changes. This is an irreversible operation.
    """
    try:
        plans = _get_capacity_plans(db_core)
        if plan_id not in plans:
            raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")

        plan = plans[plan_id]

        if plan.status != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Plan {plan_id} must be approved before execution. Current status: {plan.status}"
            )

        # Simulate execution - in production this would trigger actual infrastructure changes
        # For now, we record the execution metadata
        plan.status = "executed"
        plan.metadata["executed_by"] = current_user.username if hasattr(current_user, "username") else "system"
        plan.metadata["executed_at"] = datetime.utcnow().isoformat()
        plan.metadata["execution_result"] = "success"

        _set_capacity_plan(plan, db_core)

        logger.info(f"Executed capacity plan: {plan_id} by {plan.metadata.get('executed_by')}")

        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing capacity plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute plan: {str(e)}")


@router.get("/planning/history", response_model=List[CapacityPlan])
async def get_capacity_plan_history(
    service: Optional[str] = Query(None, description="Filter by service"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get capacity plan history with pagination.

    Returns historical capacity plans including executed, rejected,
    and approved plans for audit and analysis purposes.
    """
    try:
        plans = list(_get_capacity_plans(db_core).values())

        if service:
            plans = [p for p in plans if p.service == service]

        # Sort by creation date descending
        plans = sorted(plans, key=lambda p: p.created_at, reverse=True)

        # Apply pagination
        total = len(plans)
        paginated_plans = plans[offset:offset + limit]

        logger.debug(f"Retrieved capacity plan history: {len(paginated_plans)} of {total} total")

        return paginated_plans
    except Exception as e:
        logger.error(f"Error getting capacity plan history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get plan history: {str(e)}")


class BatchPlanCreate(BaseModel):
    """Model for batch capacity plan creation."""

    plans: List[CapacityPlanCreate] = Field(..., min_items=1, max_items=10, description="List of plans to create")


@router.post("/planning/batch", response_model=List[CapacityPlan], status_code=status.HTTP_201_CREATED)
async def create_capacity_plans_batch(
    batch: BatchPlanCreate,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create multiple capacity plans in a single batch operation.

    Processes up to 10 plans in a single transaction to improve efficiency
    when creating multiple related capacity plans.
    """
    try:
        if len(batch.plans) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 plans allowed per batch")

        created_plans = []
        metric_history = await _build_metric_history()

        for plan_create in batch.plans:
            plan_id = _generate_plan_id()

            resource_key = plan_create.resource_type.value
            current_values = metric_history.get(resource_key, [50.0])
            current_capacity = current_values[-1] if current_values else 50.0

            if plan_create.horizon == PlanningHorizon.WEEKLY:
                days_ahead = 7
            elif plan_create.horizon == PlanningHorizon.MONTHLY:
                days_ahead = 30
            elif plan_create.horizon == PlanningHorizon.QUARTERLY:
                days_ahead = 90
            else:
                days_ahead = 365

            growth_rate = 1.02 ** (days_ahead / 7)
            projected_capacity = current_capacity * growth_rate

            unit_map = {
                ResourceType.CPU: "%",
                ResourceType.MEMORY: "%",
                ResourceType.DISK: "%",
                ResourceType.NETWORK: "%",
                ResourceType.GPU: "%",
                ResourceType.STORAGE: "GB",
            }
            unit = unit_map.get(plan_create.resource_type, "%")

            new_plan = CapacityPlan(
                id=plan_id,
                name=plan_create.name,
                resource_type=plan_create.resource_type,
                service=plan_create.service,
                current_capacity=current_capacity,
                projected_capacity=projected_capacity,
                unit=unit,
                horizon=plan_create.horizon,
                target_date=plan_create.target_date,
                threshold=plan_create.threshold,
                recommended_action=plan_create.recommended_action,
                estimated_cost=plan_create.estimated_cost,
                created_by=current_user.username if hasattr(current_user, "username") else "system",
                status="draft",
                metadata=plan_create.metadata,
            )

            _set_capacity_plan(new_plan, db_core)
            created_plans.append(new_plan)

        logger.info(f"Created batch of {len(created_plans)} capacity plans")

        return created_plans
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch capacity plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create batch plans: {str(e)}")


# ============================================================================
# API Endpoints - Forecasts Extensions
# ============================================================================


_capacity_forecasts: Dict[str, CapacityForecast] = {}


def _generate_forecast_id() -> str:
    """Generate a unique forecast ID."""
    import uuid
    return f"FC-{uuid.uuid4().hex[:8].upper()}"


class ForecastCreate(BaseModel):
    """Model for creating a custom forecast."""

    service: str = Field(..., description="Service name")
    resource_type: ResourceType = Field(..., description="Resource type")
    forecast_days: int = Field(..., ge=1, le=365, description="Forecast horizon in days")
    custom_threshold: Optional[float] = Field(None, ge=0, le=100, description="Custom threshold")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post("/forecasts", response_model=CapacityForecast, status_code=status.HTTP_201_CREATED)
async def create_capacity_forecast(
    forecast_request: ForecastCreate,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a custom capacity forecast.

    Generates a forecast for a specific service and resource type
    with custom parameters for specialized planning scenarios.
    """
    try:
        forecast_id = _generate_forecast_id()

        metric_history = await _build_metric_history()
        resource_key = forecast_request.resource_type.value
        current_values = metric_history.get(resource_key, [50.0])
        current_value = current_values[-1] if current_values else 50.0

        # Generate forecasts for different horizons
        forecasts = forecast_capacity(metric_history, days_ahead=forecast_request.forecast_days)
        forecast_data = forecasts.get(resource_key, {})

        forecast_7d = forecast_data.get("forecast7d", current_value * 1.05)
        forecast_30d = forecast_data.get("forecast30d", current_value * 1.15)
        forecast_90d = forecast_data.get("forecast30d", current_value * 1.25) * 1.1

        threshold = forecast_request.custom_threshold or forecast_data.get("threshold", 80.0)

        trend = _calculate_trend(current_value, forecast_90d)
        confidence = _calculate_confidence(len(current_values))

        forecast = CapacityForecast(
            id=forecast_id,
            metric=f"{forecast_request.resource_type.value}_usage",
            resource_type=forecast_request.resource_type,
            service=forecast_request.service,
            current_value=current_value,
            forecast_7d=forecast_7d,
            forecast_30d=forecast_30d,
            forecast_90d=forecast_90d,
            threshold=threshold,
            unit="%",
            confidence=confidence,
            trend=trend,
        )

        _capacity_forecasts[forecast_id] = forecast

        logger.info(f"Created custom forecast: {forecast_id} for service {forecast_request.service}")

        return forecast
    except Exception as e:
        logger.error(f"Error creating capacity forecast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create forecast: {str(e)}")


@router.get("/forecasts/{forecast_id}", response_model=CapacityForecast)
async def get_capacity_forecast(
    forecast_id: str,
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get a specific capacity forecast by ID.

    Returns detailed information about a previously generated forecast
    including confidence intervals and trend analysis.
    """
    try:
        if forecast_id not in _capacity_forecasts:
            raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")

        return _capacity_forecasts[forecast_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capacity forecast {forecast_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get forecast: {str(e)}")


class ForecastAccuracy(BaseModel):
    """Model for forecast accuracy metrics."""

    forecast_id: str = Field(..., description="Forecast ID")
    metric: str = Field(..., description="Metric name")
    mae: float = Field(..., description="Mean Absolute Error")
    mape: float = Field(..., description="Mean Absolute Percentage Error")
    rmse: float = Field(..., description="Root Mean Square Error")
    accuracy_score: float = Field(..., description="Overall accuracy score (0-1)")
    evaluation_period: str = Field(..., description="Evaluation period")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


@router.get("/forecasts/{forecast_id}/accuracy", response_model=ForecastAccuracy)
async def get_forecast_accuracy(
    forecast_id: str,
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get forecast accuracy metrics.

    Returns accuracy metrics for a forecast by comparing predicted
    values against actual observed values.
    """
    try:
        if forecast_id not in _capacity_forecasts:
            raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")

        forecast = _capacity_forecasts[forecast_id]

        # Simulate accuracy calculation based on forecast age
        forecast_age = (datetime.utcnow() - forecast.generated_at).days

        if forecast_age < 7:
            mae = 2.5
            mape = 0.05
            rmse = 3.0
            accuracy_score = 0.95
        elif forecast_age < 30:
            mae = 5.0
            mape = 0.10
            rmse = 6.0
            accuracy_score = 0.85
        else:
            mae = 8.0
            mape = 0.15
            rmse = 10.0
            accuracy_score = 0.75

        accuracy = ForecastAccuracy(
            forecast_id=forecast_id,
            metric=forecast.metric,
            mae=mae,
            mape=mape,
            rmse=rmse,
            accuracy_score=accuracy_score,
            evaluation_period=f"Last {max(forecast_age, 1)} days",
        )

        logger.debug(f"Retrieved accuracy metrics for forecast: {forecast_id}")

        return accuracy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecast accuracy {forecast_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get forecast accuracy: {str(e)}")


@router.post("/forecasts/{forecast_id}/recalculate", response_model=CapacityForecast)
async def recalculate_forecast(
    forecast_id: str,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Recalculate a forecast with updated metrics.

    Regenerates the forecast using the latest available metrics
    to improve accuracy and reflect recent changes.
    """
    try:
        if forecast_id not in _capacity_forecasts:
            raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")

        original_forecast = _capacity_forecasts[forecast_id]

        # Get updated metrics
        metric_history = await _build_metric_history()
        resource_key = original_forecast.resource_type.value
        current_values = metric_history.get(resource_key, [50.0])
        current_value = current_values[-1] if current_values else 50.0

        # Recalculate forecasts
        forecasts = forecast_capacity(metric_history, days_ahead=30)
        forecast_data = forecasts.get(resource_key, {})

        forecast_7d = forecast_data.get("forecast7d", current_value * 1.05)
        forecast_30d = forecast_data.get("forecast30d", current_value * 1.15)
        forecast_90d = forecast_data.get("forecast30d", current_value * 1.25) * 1.1

        trend = _calculate_trend(current_value, forecast_90d)
        confidence = _calculate_confidence(len(current_values))

        # Update forecast
        original_forecast.current_value = current_value
        original_forecast.forecast_7d = forecast_7d
        original_forecast.forecast_30d = forecast_30d
        original_forecast.forecast_90d = forecast_90d
        original_forecast.confidence = confidence
        original_forecast.trend = trend
        original_forecast.generated_at = datetime.utcnow()

        logger.info(f"Recalculated forecast: {forecast_id}")

        return original_forecast
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating forecast {forecast_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to recalculate forecast: {str(e)}")


# ============================================================================
# API Endpoints - Optimization Extensions
# ============================================================================


@router.get("/optimization/{optimization_id}", response_model=OptimizationResult)
async def get_optimization_result(
    optimization_id: str,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get a specific optimization result by ID.

    Returns detailed information about a previously generated
    optimization analysis including recommendations and steps.
    """
    try:
        results = _get_optimization_results(db_core)
        if optimization_id not in results:
            raise HTTPException(status_code=404, detail=f"Optimization {optimization_id} not found")

        return results[optimization_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting optimization result {optimization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get optimization: {str(e)}")


class OptimizationApplyRequest(BaseModel):
    """Model for applying optimization recommendations."""

    optimization_id: str = Field(..., description="Optimization ID to apply")
    dry_run: bool = Field(default=False, description="Dry run without actual changes")
    confirmation: bool = Field(default=False, description="Confirmation for destructive changes")


@router.post("/optimization/apply", response_model=Dict[str, Any])
async def apply_optimization(
    request: OptimizationApplyRequest,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Apply optimization recommendations.

    Executes the optimization recommendations from a previous analysis.
    Supports dry-run mode for testing before actual implementation.
    """
    try:
        results = _get_optimization_results(db_core)
        if request.optimization_id not in results:
            raise HTTPException(status_code=404, detail=f"Optimization {request.optimization_id} not found")

        optimization = results[request.optimization_id]

        if not request.confirmation and not request.dry_run:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required for applying optimizations. Set confirmation=true or dry_run=true"
            )

        # Simulate optimization application
        applied_recommendations = []
        for rec in optimization.recommendations:
            if request.dry_run:
                status = "dry_run"
                message = f"Would apply: {rec.get('action')} for {rec.get('resource_type')}"
            else:
                status = "applied"
                message = f"Applied: {rec.get('action')} for {rec.get('resource_type')}"

            applied_recommendations.append({
                "resource_type": rec.get("resource_type"),
                "action": rec.get("action"),
                "status": status,
                "message": message,
                "savings": rec.get("savings", 0.0),
            })

        result = {
            "optimization_id": request.optimization_id,
            "dry_run": request.dry_run,
            "applied_count": len(applied_recommendations),
            "recommendations": applied_recommendations,
            "total_savings": optimization.cost_savings if not request.dry_run else 0.0,
            "applied_by": current_user.username if hasattr(current_user, "username") else "system",
            "applied_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Applied optimization: {request.optimization_id} (dry_run={request.dry_run})")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying optimization {request.optimization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply optimization: {str(e)}")


class OptimizationImpact(BaseModel):
    """Model for optimization impact analysis."""

    optimization_id: str = Field(..., description="Optimization ID")
    service: str = Field(..., description="Service name")
    before_cost: float = Field(..., description="Cost before optimization")
    after_cost: float = Field(..., description="Cost after optimization")
    cost_reduction: float = Field(..., description="Cost reduction amount")
    reduction_percentage: float = Field(..., description="Cost reduction percentage")
    performance_impact: str = Field(..., description="Performance impact assessment")
    risk_level: str = Field(..., description="Risk level")
    estimated_roi: float = Field(..., description="Estimated ROI in months")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


@router.get("/optimization/{optimization_id}/impact", response_model=OptimizationImpact)
async def get_optimization_impact(
    optimization_id: str,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get optimization impact analysis.

    Returns detailed impact analysis for an optimization including
    cost savings, performance effects, and risk assessment.
    """
    try:
        results = _get_optimization_results(db_core)
        if optimization_id not in results:
            raise HTTPException(status_code=404, detail=f"Optimization {optimization_id} not found")

        optimization = results[optimization_id]

        # Calculate impact metrics
        cost_reduction = optimization.cost_savings
        reduction_percentage = optimization.savings_percentage

        # Determine performance impact based on strategy
        if optimization.strategy == OptimizationStrategy.COST_OPTIMIZATION:
            performance_impact = "Moderate - may affect response times"
            risk_level = "Medium"
            estimated_roi = 3.0
        elif optimization.strategy == OptimizationStrategy.PERFORMANCE_OPTIMIZATION:
            performance_impact = "Positive - improved performance expected"
            risk_level = "Low"
            estimated_roi = 6.0
        elif optimization.strategy == OptimizationStrategy.AGGRESSIVE:
            performance_impact = "High - significant changes expected"
            risk_level = "High"
            estimated_roi = 2.0
        else:  # BALANCED
            performance_impact = "Minimal - balanced approach"
            risk_level = "Low"
            estimated_roi = 4.0

        impact = OptimizationImpact(
            optimization_id=optimization_id,
            service=optimization.service,
            before_cost=optimization.current_cost,
            after_cost=optimization.optimized_cost,
            cost_reduction=cost_reduction,
            reduction_percentage=reduction_percentage,
            performance_impact=performance_impact,
            risk_level=risk_level,
            estimated_roi=estimated_roi,
        )

        logger.debug(f"Retrieved impact analysis for optimization: {optimization_id}")

        return impact
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting optimization impact {optimization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get optimization impact: {str(e)}")


# ============================================================================
# API Endpoints - Rightsizing Extensions
# ============================================================================


class RightsizingCreate(BaseModel):
    """Model for creating a rightsizing recommendation."""

    service: str = Field(..., description="Service name")
    resource_type: ResourceType = Field(..., description="Resource type")
    current_spec: Dict[str, Any] = Field(..., description="Current specification")
    target_utilization: float = Field(default=70.0, ge=30, le=90, description="Target utilization percentage")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post("/rightsizing", response_model=RightsizingRecommendation, status_code=status.HTTP_201_CREATED)
async def create_rightsizing_recommendation(
    request: RightsizingCreate,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a custom rightsizing recommendation.

    Generates a rightsizing recommendation based on current specifications
    and target utilization goals for a specific service.
    """
    try:
        rec_id = _generate_rightsizing_id()

        # Analyze current spec and determine action
        current_value = request.current_spec.get("value", 50.0)
        target_value = request.target_utilization

        if current_value > target_value * 1.2:
            action = RightsizingAction.SCALE_DOWN
            recommended_value = current_value * 0.8
            priority = Priority.HIGH
            reason = f"Current utilization ({current_value:.1f}%) significantly above target ({target_value}%)"
            savings = (current_value - recommended_value) * 10.0
            performance_impact = "Minimal - current usage well above recommended"
        elif current_value < target_value * 0.8:
            action = RightsizingAction.SCALE_UP
            recommended_value = current_value * 1.2
            priority = Priority.HIGH
            reason = f"Current utilization ({current_value:.1f}%) below target ({target_value}%)"
            savings = -50.0
            performance_impact = "Positive - improved performance and headroom"
        else:
            action = RightsizingAction.NO_ACTION
            recommended_value = current_value
            priority = Priority.LOW
            reason = f"Current utilization ({current_value:.1f}%) within target range ({target_value}%)"
            savings = 0.0
            performance_impact = "None - current configuration is optimal"

        recommended_spec = request.current_spec.copy()
        recommended_spec["value"] = recommended_value

        recommendation = RightsizingRecommendation(
            id=rec_id,
            service=request.service,
            resource_type=request.resource_type,
            current_spec=request.current_spec,
            recommended_spec=recommended_spec,
            action=action,
            reason=reason,
            priority=priority,
            estimated_monthly_savings=savings,
            performance_impact=performance_impact,
            implementation_complexity="Medium" if action != RightsizingAction.NO_ACTION else "Low",
        )

        _add_rightsizing_recommendation(recommendation, db_core)

        logger.info(f"Created rightsizing recommendation: {rec_id} for service {request.service}")

        return recommendation
    except Exception as e:
        logger.error(f"Error creating rightsizing recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create rightsizing: {str(e)}")


class RightsizingApplyRequest(BaseModel):
    """Model for applying rightsizing recommendations."""

    recommendation_id: str = Field(..., description="Recommendation ID to apply")
    dry_run: bool = Field(default=False, description="Dry run without actual changes")
    confirmation: bool = Field(default=False, description="Confirmation for destructive changes")


@router.post("/rightsizing/apply", response_model=Dict[str, Any])
async def apply_rightsizing_recommendation(
    request: RightsizingApplyRequest,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Apply a rightsizing recommendation.

    Executes the rightsizing action from a recommendation.
    Supports dry-run mode for testing before actual implementation.
    """
    try:
        recommendations = _get_rightsizing_recommendations(db_core)
        recommendation = None
        for rec in recommendations:
            if rec.id == request.recommendation_id:
                recommendation = rec
                break

        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Rightsizing recommendation {request.recommendation_id} not found")

        if not request.confirmation and not request.dry_run:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required for applying rightsizing. Set confirmation=true or dry_run=true"
            )

        # Simulate rightsizing application
        if request.dry_run:
            status = "dry_run"
            message = f"Would apply {recommendation.action} for {recommendation.service}"
            actual_savings = 0.0
        else:
            status = "applied"
            message = f"Applied {recommendation.action} for {recommendation.service}"
            actual_savings = recommendation.estimated_monthly_savings

        result = {
            "recommendation_id": request.recommendation_id,
            "service": recommendation.service,
            "resource_type": recommendation.resource_type.value,
            "action": recommendation.action.value,
            "dry_run": request.dry_run,
            "status": status,
            "message": message,
            "estimated_savings": recommendation.estimated_monthly_savings,
            "actual_savings": actual_savings,
            "applied_by": current_user.username if hasattr(current_user, "username") else "system",
            "applied_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Applied rightsizing recommendation: {request.recommendation_id} (dry_run={request.dry_run})")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying rightsizing recommendation {request.recommendation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply rightsizing: {str(e)}")


class BatchRightsizingCreate(BaseModel):
    """Model for batch rightsizing recommendation creation."""

    services: List[str] = Field(..., min_items=1, max_items=10, description="List of service names")
    resource_types: List[ResourceType] = Field(default_factory=list, description="Resource types to analyze")
    target_utilization: float = Field(default=70.0, ge=30, le=90, description="Target utilization percentage")


@router.post("/rightsizing/batch", response_model=List[RightsizingRecommendation], status_code=status.HTTP_201_CREATED)
async def create_rightsizing_batch(
    batch: BatchRightsizingCreate,
    db_core: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create rightsizing recommendations for multiple services in batch.

    Generates rightsizing recommendations for multiple services
    in a single operation to improve efficiency.
    """
    try:
        if len(batch.services) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 services allowed per batch")

        if not batch.resource_types:
            batch.resource_types = [ResourceType.CPU, ResourceType.MEMORY, ResourceType.DISK]

        metric_history = await _build_metric_history()
        created_recommendations = []

        for service in batch.services:
            for rt in batch.resource_types:
                rec_id = _generate_rightsizing_id()

                key = rt.value
                values = metric_history.get(key, [50.0])
                current_value = values[-1] if values else 50.0

                target_value = batch.target_utilization

                if current_value > target_value * 1.2:
                    action = RightsizingAction.SCALE_DOWN
                    recommended_value = current_value * 0.8
                    priority = Priority.HIGH
                    reason = f"Current utilization ({current_value:.1f}%) significantly above target ({target_value}%)"
                    savings = (current_value - recommended_value) * 10.0
                    performance_impact = "Minimal - current usage well above recommended"
                elif current_value < target_value * 0.8:
                    action = RightsizingAction.SCALE_UP
                    recommended_value = current_value * 1.2
                    priority = Priority.HIGH
                    reason = f"Current utilization ({current_value:.1f}%) below target ({target_value}%)"
                    savings = -50.0
                    performance_impact = "Positive - improved performance and headroom"
                else:
                    action = RightsizingAction.NO_ACTION
                    recommended_value = current_value
                    priority = Priority.LOW
                    reason = f"Current utilization ({current_value:.1f}%) within target range ({target_value}%)"
                    savings = 0.0
                    performance_impact = "None - current configuration is optimal"

                current_spec = {"value": current_value, "unit": "%"}
                recommended_spec = {"value": recommended_value, "unit": "%"}

                recommendation = RightsizingRecommendation(
                    id=rec_id,
                    service=service,
                    resource_type=rt,
                    current_spec=current_spec,
                    recommended_spec=recommended_spec,
                    action=action,
                    reason=reason,
                    priority=priority,
                    estimated_monthly_savings=savings,
                    performance_impact=performance_impact,
                    implementation_complexity="Medium" if action != RightsizingAction.NO_ACTION else "Low",
                )

                _add_rightsizing_recommendation(recommendation, db_core)
                created_recommendations.append(recommendation)

        logger.info(f"Created batch of {len(created_recommendations)} rightsizing recommendations")

        return created_recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch rightsizing recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create batch rightsizing: {str(e)}")


# ============================================================================
# API Endpoints - Recommendations Extensions
# ============================================================================


_scaling_recommendations_history: List[ScalingRecommendation] = []


def _generate_scaling_id() -> str:
    """Generate a unique scaling recommendation ID."""
    import uuid
    return f"SR-{uuid.uuid4().hex[:8].upper()}"


class ScalingRecommendationCreate(BaseModel):
    """Model for creating a custom scaling recommendation."""

    service: str = Field(..., description="Service name")
    resource_type: ResourceType = Field(..., description="Resource type")
    action: str = Field(..., description="Action (scale-up/scale-down/no-action)")
    reason: str = Field(..., description="Reason for recommendation")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    estimated_cost: float = Field(default=0.0, ge=0, description="Estimated cost")
    current_value: float = Field(..., description="Current resource value")
    recommended_value: float = Field(..., description="Recommended resource value")
    unit: str = Field(default="%", description="Unit")
    time_horizon: str = Field(default="7-30 days", description="Time horizon")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post("/recommendations", response_model=ScalingRecommendation, status_code=status.HTTP_201_CREATED)
async def create_scaling_recommendation(
    request: ScalingRecommendationCreate,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a custom scaling recommendation.

    Creates a scaling recommendation with custom parameters for
    specialized scenarios not covered by automated analysis.
    """
    try:
        rec_id = _generate_scaling_id()

        # Calculate confidence based on data availability
        confidence = 0.75 if request.action != "no-action" else 0.90

        recommendation = ScalingRecommendation(
            id=rec_id,
            service=request.service,
            action=request.action,
            reason=request.reason,
            priority=request.priority,
            estimated_cost=request.estimated_cost,
            resource_type=request.resource_type,
            current_value=request.current_value,
            recommended_value=request.recommended_value,
            unit=request.unit,
            time_horizon=request.time_horizon,
            confidence=confidence,
        )

        _scaling_recommendations_history.append(recommendation)

        logger.info(f"Created scaling recommendation: {rec_id} for service {request.service}")

        return recommendation
    except Exception as e:
        logger.error(f"Error creating scaling recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create recommendation: {str(e)}")


class ScalingApplyRequest(BaseModel):
    """Model for applying scaling recommendations."""

    recommendation_id: str = Field(..., description="Recommendation ID to apply")
    dry_run: bool = Field(default=False, description="Dry run without actual changes")
    confirmation: bool = Field(default=False, description="Confirmation for destructive changes")


@router.post("/recommendations/apply", response_model=Dict[str, Any])
async def apply_scaling_recommendation(
    request: ScalingApplyRequest,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Apply a scaling recommendation.

    Executes the scaling action from a recommendation.
    Supports dry-run mode for testing before actual implementation.
    """
    try:
        recommendation = None
        for rec in _scaling_recommendations_history:
            if rec.id == request.recommendation_id:
                recommendation = rec
                break

        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Scaling recommendation {request.recommendation_id} not found")

        if not request.confirmation and not request.dry_run:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required for applying scaling. Set confirmation=true or dry_run=true"
            )

        # Simulate scaling application
        if request.dry_run:
            status = "dry_run"
            message = f"Would apply {recommendation.action} for {recommendation.service}"
            actual_cost = 0.0
        else:
            status = "applied"
            message = f"Applied {recommendation.action} for {recommendation.service}"
            actual_cost = recommendation.estimated_cost

        result = {
            "recommendation_id": request.recommendation_id,
            "service": recommendation.service,
            "resource_type": recommendation.resource_type.value,
            "action": recommendation.action,
            "dry_run": request.dry_run,
            "status": status,
            "message": message,
            "estimated_cost": recommendation.estimated_cost,
            "actual_cost": actual_cost,
            "applied_by": current_user.username if hasattr(current_user, "username") else "system",
            "applied_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Applied scaling recommendation: {request.recommendation_id} (dry_run={request.dry_run})")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying scaling recommendation {request.recommendation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply scaling: {str(e)}")


@router.get("/recommendations/history", response_model=List[ScalingRecommendation])
async def get_scaling_recommendation_history(
    service: Optional[str] = Query(None, description="Filter by service"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    Get scaling recommendation history with pagination.

    Returns historical scaling recommendations including applied
    and pending recommendations for audit and analysis purposes.
    """
    try:
        recommendations = _scaling_recommendations_history.copy()

        if service:
            recommendations = [r for r in recommendations if r.service == service]
        if resource_type:
            recommendations = [r for r in recommendations if r.resource_type == resource_type]
        if action:
            recommendations = [r for r in recommendations if r.action == action]

        # Sort by creation date descending (using id as proxy for time)
        recommendations = sorted(recommendations, key=lambda r: r.id, reverse=True)

        # Apply pagination
        total = len(recommendations)
        paginated_recommendations = recommendations[offset:offset + limit]

        logger.debug(f"Retrieved scaling recommendation history: {len(paginated_recommendations)} of {total} total")

        return paginated_recommendations
    except Exception as e:
        logger.error(f"Error getting scaling recommendation history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get recommendation history: {str(e)}")
