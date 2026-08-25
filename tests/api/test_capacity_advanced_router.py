# -*- coding: utf-8 -*-
"""
Test suite for Capacity Advanced Router
========================================

Comprehensive tests for capacity planning endpoints including planning,
forecasts, optimization, rightsizing, and recommendations.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from api.capacity_advanced_router import (
    CapacityForecast,
    CapacityPlan,
    CapacityPlanCreate,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStrategy,
    PlanningHorizon,
    Priority,
    ResourceType,
    RightsizingAction,
    RightsizingRecommendation,
    ScalingRecommendation,
    _build_metric_history,
    _calculate_confidence,
    _calculate_trend,
    _capacity_plans,
    _generate_optimization_id,
    _generate_plan_id,
    _generate_rightsizing_id,
    _optimization_results,
    _rightsizing_recommendations,
    router,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = Mock()
    user.id = 1
    user.username = "admin"
    user.tenant_id = "default"
    user.roles = ["admin"]
    return user


@pytest.fixture
def mock_operator_user():
    """Mock operator user."""
    user = Mock()
    user.id = 2
    user.username = "operator"
    user.tenant_id = "default"
    user.roles = ["operator"]
    return user


@pytest.fixture
def mock_business_user():
    """Mock business user."""
    user = Mock()
    user.id = 3
    user.username = "business"
    user.tenant_id = "default"
    user.roles = ["business"]
    return user


@pytest.fixture
def sample_capacity_plan():
    """Sample capacity plan."""
    return CapacityPlan(
        id="CP-12345678",
        name="Test Plan",
        resource_type=ResourceType.CPU,
        service="compute-service",
        current_capacity=50.0,
        projected_capacity=75.0,
        unit="%",
        horizon=PlanningHorizon.MONTHLY,
        target_date=datetime.utcnow() + timedelta(days=30),
        threshold=80.0,
        recommended_action="scale-up",
        estimated_cost=1000.0,
        created_at=datetime.utcnow(),
        created_by="admin",
        status="draft",
    )


@pytest.fixture
def sample_plan_create():
    """Sample plan creation data."""
    return CapacityPlanCreate(
        name="Test Plan",
        resource_type=ResourceType.CPU,
        service="compute-service",
        horizon=PlanningHorizon.MONTHLY,
        target_date=datetime.utcnow() + timedelta(days=30),
        threshold=80.0,
        recommended_action="scale-up",
        estimated_cost=1000.0,
        metadata={"key": "value"},
    )


@pytest.fixture
def sample_optimization_request():
    """Sample optimization request."""
    return OptimizationRequest(
        service="compute-service",
        resource_types=[ResourceType.CPU, ResourceType.MEMORY],
        strategy=OptimizationStrategy.BALANCED,
        target_cost_reduction=0.2,
        min_performance_sla=0.95,
        constraints={"max_downtime": "5min"},
    )


@pytest.fixture
def clear_in_memory_data():
    """Clear in-memory data before each test."""
    yield
    _capacity_plans.clear()
    _optimization_results.clear()
    _rightsizing_recommendations.clear()


# ============================================================================
# Test Planning Endpoints
# ============================================================================


class TestListCapacityPlans:
    """Tests for GET /api/v1/capacity/planning"""

    @pytest.mark.asyncio
    async def test_list_plans_success(
        self, sample_capacity_plan, mock_admin_user, clear_in_memory_data
    ):
        """Test successful listing of capacity plans."""
        # Setup
        _capacity_plans["CP-12345678"] = sample_capacity_plan

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[0].endpoint(
                service=None,
                resource_type=None,
                status=None,
                horizon=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].id == "CP-12345678"

    @pytest.mark.asyncio
    async def test_list_plans_with_filters(
        self, sample_capacity_plan, mock_admin_user, clear_in_memory_data
    ):
        """Test listing plans with filters."""
        # Setup
        _capacity_plans["CP-12345678"] = sample_capacity_plan

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[0].endpoint(
                service="compute-service",
                resource_type=ResourceType.CPU,
                status="draft",
                horizon=PlanningHorizon.MONTHLY,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_plans_empty_result(self, mock_admin_user, clear_in_memory_data):
        """Test listing plans with no results."""
        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[0].endpoint(
                service=None,
                resource_type=None,
                status=None,
                horizon=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_list_plans_permission_denied(self):
        """Test listing plans without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[0].endpoint(
                    service=None,
                    resource_type=None,
                    status=None,
                    horizon=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_plans_error_handling(self, mock_admin_user, clear_in_memory_data):
        """Test listing plans with error."""
        # Setup
        _capacity_plans["CP-12345678"] = "invalid_data"  # Invalid data type

        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[0].endpoint(
                    service=None,
                    resource_type=None,
                    status=None,
                    horizon=None,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 500


class TestCreateCapacityPlan:
    """Tests for POST /api/v1/capacity/planning"""

    @pytest.mark.asyncio
    async def test_create_plan_success(
        self, sample_plan_create, mock_admin_user, clear_in_memory_data
    ):
        """Test successful creation of capacity plan."""
        # Setup
        with patch(
            "api.capacity_advanced_router._build_metric_history",
            return_value={"cpu": [50.0, 55.0, 60.0]},
        ):
            # Execute
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[1].endpoint(
                    plan=sample_plan_create,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.name == "Test Plan"
        assert result.resource_type == ResourceType.CPU
        assert result.status == "draft"

    @pytest.mark.asyncio
    async def test_create_plan_validation_error(self, mock_admin_user):
        """Test creating plan with invalid data."""
        # Setup
        invalid_data = CapacityPlanCreate(
            name="",  # Invalid: empty name
            resource_type=ResourceType.CPU,
            service="compute-service",
            horizon=PlanningHorizon.MONTHLY,
            target_date=datetime.utcnow() + timedelta(days=30),
            threshold=80.0,
            recommended_action="scale-up",
        )

        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(Exception):  # Pydantic validation error
                await router.routes[1].endpoint(
                    plan=invalid_data,
                    current_user=mock_admin_user,
                )

    @pytest.mark.asyncio
    async def test_create_plan_threshold_validation(self, mock_admin_user):
        """Test creating plan with invalid threshold."""
        # Setup
        invalid_data = CapacityPlanCreate(
            name="Test Plan",
            resource_type=ResourceType.CPU,
            service="compute-service",
            horizon=PlanningHorizon.MONTHLY,
            target_date=datetime.utcnow() + timedelta(days=30),
            threshold=150.0,  # Invalid: > 100
            recommended_action="scale-up",
        )

        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(Exception):  # Pydantic validation error
                await router.routes[1].endpoint(
                    plan=invalid_data,
                    current_user=mock_admin_user,
                )

    @pytest.mark.asyncio
    async def test_create_plan_permission_denied(self, sample_plan_create, mock_business_user):
        """Test creating plan without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[1].endpoint(
                    plan=sample_plan_create,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_plan_different_horizons(
        self, sample_plan_create, mock_admin_user, clear_in_memory_data
    ):
        """Test creating plans with different horizons."""
        # Test weekly
        sample_plan_create.horizon = PlanningHorizon.WEEKLY
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[1].endpoint(
                    plan=sample_plan_create,
                    current_user=mock_admin_user,
                )
        assert result.horizon == PlanningHorizon.WEEKLY

        # Test quarterly
        sample_plan_create.horizon = PlanningHorizon.QUARTERLY
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[1].endpoint(
                    plan=sample_plan_create,
                    current_user=mock_admin_user,
                )
        assert result.horizon == PlanningHorizon.QUARTERLY

        # Test yearly
        sample_plan_create.horizon = PlanningHorizon.YEARLY
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[1].endpoint(
                    plan=sample_plan_create,
                    current_user=mock_admin_user,
                )
        assert result.horizon == PlanningHorizon.YEARLY


class TestGetCapacityPlan:
    """Tests for GET /api/v1/capacity/planning/{id}"""

    @pytest.mark.asyncio
    async def test_get_plan_success(
        self, sample_capacity_plan, mock_admin_user, clear_in_memory_data
    ):
        """Test successful retrieval of capacity plan."""
        # Setup
        _capacity_plans["CP-12345678"] = sample_capacity_plan

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[2].endpoint(
                plan_id="CP-12345678",
                current_user=mock_admin_user,
            )

        # Assert
        assert result.id == "CP-12345678"
        assert result.name == "Test Plan"

    @pytest.mark.asyncio
    async def test_get_plan_not_found(self, mock_admin_user):
        """Test retrieving non-existent plan."""
        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[2].endpoint(
                    plan_id="CP-NOTFOUND",
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_plan_permission_denied(self):
        """Test retrieving plan without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[2].endpoint(
                    plan_id="CP-12345678",
                    current_user=None,
                )
            assert exc_info.value.status_code == 403


class TestUpdateCapacityPlan:
    """Tests for PATCH /api/v1/capacity/planning/{id}"""

    @pytest.mark.asyncio
    async def test_update_plan_success(
        self, sample_capacity_plan, mock_admin_user, clear_in_memory_data
    ):
        """Test successful update of capacity plan."""
        # Setup
        _capacity_plans["CP-12345678"] = sample_capacity_plan

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[3].endpoint(
                plan_id="CP-12345678",
                status="approved",
                recommended_action="scale-down",
                estimated_cost=500.0,
                current_user=mock_admin_user,
            )

        # Assert
        assert result.status == "approved"
        assert result.recommended_action == "scale-down"
        assert result.estimated_cost == 500.0

    @pytest.mark.asyncio
    async def test_update_plan_not_found(self, mock_admin_user):
        """Test updating non-existent plan."""
        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[3].endpoint(
                    plan_id="CP-NOTFOUND",
                    status="approved",
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_plan_partial_update(
        self, sample_capacity_plan, mock_admin_user, clear_in_memory_data
    ):
        """Test partial update of capacity plan."""
        # Setup
        _capacity_plans["CP-12345678"] = sample_capacity_plan

        # Execute - update only status
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[3].endpoint(
                plan_id="CP-12345678",
                status="approved",
                current_user=mock_admin_user,
            )

        # Assert
        assert result.status == "approved"
        assert result.recommended_action == "scale-up"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_plan_permission_denied(self, mock_business_user):
        """Test updating plan without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[3].endpoint(
                    plan_id="CP-12345678",
                    status="approved",
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403


class TestDeleteCapacityPlan:
    """Tests for DELETE /api/v1/capacity/planning/{id}"""

    @pytest.mark.asyncio
    async def test_delete_plan_success(
        self, sample_capacity_plan, mock_admin_user, clear_in_memory_data
    ):
        """Test successful deletion of capacity plan."""
        # Setup
        _capacity_plans["CP-12345678"] = sample_capacity_plan

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[4].endpoint(
                plan_id="CP-12345678",
                current_user=mock_admin_user,
            )

        # Assert
        assert result is None
        assert "CP-12345678" not in _capacity_plans

    @pytest.mark.asyncio
    async def test_delete_plan_not_found(self, mock_admin_user):
        """Test deleting non-existent plan."""
        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[4].endpoint(
                    plan_id="CP-NOTFOUND",
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_plan_permission_denied(self, mock_operator_user):
        """Test deleting plan without admin permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[4].endpoint(
                    plan_id="CP-12345678",
                    current_user=mock_operator_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Forecasts Endpoints
# ============================================================================


class TestGetCapacityForecasts:
    """Tests for GET /api/v1/capacity/forecasts"""

    @pytest.mark.asyncio
    async def test_get_forecasts_success(self, mock_admin_user):
        """Test successful retrieval of capacity forecasts."""
        # Setup
        mock_forecasts = {
            "cpu": {
                "metric": "cpu",
                "currentValue": 50.0,
                "forecast7d": 55.0,
                "forecast30d": 60.0,
                "threshold": 80.0,
                "unit": "%",
            }
        }
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch(
                "api.capacity_advanced_router.forecast_capacity", return_value=mock_forecasts
            ):
                # Execute
                with patch(
                    "api.capacity_advanced_router.require_roles", return_value=mock_admin_user
                ):
                    result = await router.routes[5].endpoint(
                        service=None,
                        resource_type=None,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_forecasts_with_filters(self, mock_admin_user):
        """Test retrieving forecasts with filters."""
        # Setup
        mock_forecasts = {
            "cpu": {
                "metric": "cpu",
                "currentValue": 50.0,
                "forecast7d": 55.0,
                "forecast30d": 60.0,
                "threshold": 80.0,
                "unit": "%",
            }
        }
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch(
                "api.capacity_advanced_router.forecast_capacity", return_value=mock_forecasts
            ):
                # Execute
                with patch(
                    "api.capacity_advanced_router.require_roles", return_value=mock_admin_user
                ):
                    result = await router.routes[5].endpoint(
                        service="compute-service",
                        resource_type=ResourceType.CPU,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_forecasts_permission_denied(self):
        """Test retrieving forecasts without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[5].endpoint(
                    service=None,
                    resource_type=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_forecasts_error_handling(self, mock_admin_user):
        """Test retrieving forecasts with error."""
        # Setup
        with patch(
            "api.capacity_advanced_router._build_metric_history",
            side_effect=Exception("Metric error"),
        ):
            # Execute & Assert
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[5].endpoint(
                        service=None,
                        resource_type=None,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 500


# ============================================================================
# Test Optimization Endpoints
# ============================================================================


class TestListOptimizationResults:
    """Tests for GET /api/v1/capacity/optimization"""

    @pytest.mark.asyncio
    async def test_list_optimizations_success(self, mock_admin_user, clear_in_memory_data):
        """Test successful listing of optimization results."""
        # Setup
        optimization = OptimizationResult(
            id="OPT-12345678",
            service="compute-service",
            strategy=OptimizationStrategy.BALANCED,
            current_cost=1000.0,
            optimized_cost=800.0,
            cost_savings=200.0,
            savings_percentage=20.0,
            recommendations=[],
            implementation_steps=[],
            risk_assessment="Low",
            estimated_implementation_time="1-2 weeks",
        )
        _optimization_results["OPT-12345678"] = optimization

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[6].endpoint(
                service=None,
                strategy=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].id == "OPT-12345678"

    @pytest.mark.asyncio
    async def test_list_optimizations_with_filters(self, mock_admin_user, clear_in_memory_data):
        """Test listing optimizations with filters."""
        # Setup
        optimization = OptimizationResult(
            id="OPT-12345678",
            service="compute-service",
            strategy=OptimizationStrategy.BALANCED,
            current_cost=1000.0,
            optimized_cost=800.0,
            cost_savings=200.0,
            savings_percentage=20.0,
            recommendations=[],
            implementation_steps=[],
            risk_assessment="Low",
            estimated_implementation_time="1-2 weeks",
        )
        _optimization_results["OPT-12345678"] = optimization

        # Execute
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            result = await router.routes[6].endpoint(
                service="compute-service",
                strategy=OptimizationStrategy.BALANCED,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_optimizations_permission_denied(self):
        """Test listing optimizations without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[6].endpoint(
                    service=None,
                    strategy=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403


class TestCreateOptimization:
    """Tests for POST /api/v1/capacity/optimization"""

    @pytest.mark.asyncio
    async def test_create_optimization_success(
        self, sample_optimization_request, mock_admin_user, clear_in_memory_data
    ):
        """Test successful creation of optimization analysis."""
        # Setup
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            # Execute
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[7].endpoint(
                    request=sample_optimization_request,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.service == "compute-service"
        assert result.strategy == OptimizationStrategy.BALANCED
        assert result.cost_savings > 0

    @pytest.mark.asyncio
    async def test_create_optimization_different_strategies(
        self, sample_optimization_request, mock_admin_user, clear_in_memory_data
    ):
        """Test creating optimizations with different strategies."""
        # Test cost optimization
        sample_optimization_request.strategy = OptimizationStrategy.COST_OPTIMIZATION
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[7].endpoint(
                    request=sample_optimization_request,
                    current_user=mock_admin_user,
                )
        assert result.strategy == OptimizationStrategy.COST_OPTIMIZATION

        # Test performance optimization
        sample_optimization_request.strategy = OptimizationStrategy.PERFORMANCE_OPTIMIZATION
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[7].endpoint(
                    request=sample_optimization_request,
                    current_user=mock_admin_user,
                )
        assert result.strategy == OptimizationStrategy.PERFORMANCE_OPTIMIZATION

        # Test aggressive
        sample_optimization_request.strategy = OptimizationStrategy.AGGRESSIVE
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[7].endpoint(
                    request=sample_optimization_request,
                    current_user=mock_admin_user,
                )
        assert result.strategy == OptimizationStrategy.AGGRESSIVE

    @pytest.mark.asyncio
    async def test_create_optimization_validation_error(self, mock_admin_user):
        """Test creating optimization with invalid data."""
        # Setup
        invalid_data = OptimizationRequest(
            service="",  # Invalid: empty service
            resource_types=[ResourceType.CPU],
        )

        # Execute & Assert
        with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
            with pytest.raises(Exception):  # Pydantic validation error
                await router.routes[7].endpoint(
                    request=invalid_data,
                    current_user=mock_admin_user,
                )

    @pytest.mark.asyncio
    async def test_create_optimization_permission_denied(
        self, sample_optimization_request, mock_business_user
    ):
        """Test creating optimization without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[7].endpoint(
                    request=sample_optimization_request,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Rightsizing Endpoints
# ============================================================================


class TestGetRightsizingRecommendations:
    """Tests for GET /api/v1/capacity/rightsizing"""

    @pytest.mark.asyncio
    async def test_get_rightsizing_success(self, mock_admin_user, clear_in_memory_data):
        """Test successful retrieval of rightsizing recommendations."""
        # Setup
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [25.0]}
        ):
            # Execute
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[8].endpoint(
                    service=None,
                    resource_type=None,
                    priority=None,
                    current_user=mock_admin_user,
                )

        # Assert
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_rightsizing_with_filters(self, mock_admin_user, clear_in_memory_data):
        """Test retrieving rightsizing with filters."""
        # Setup
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [25.0]}
        ):
            # Execute
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[8].endpoint(
                    service="compute-service",
                    resource_type=ResourceType.CPU,
                    priority=Priority.MEDIUM,
                    current_user=mock_admin_user,
                )

        # Assert
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_rightsizing_permission_denied(self):
        """Test retrieving rightsizing without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[8].endpoint(
                    service=None,
                    resource_type=None,
                    priority=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_rightsizing_scale_down(self, mock_admin_user, clear_in_memory_data):
        """Test rightsizing recommendation for scale down."""
        # Setup - low utilization
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [20.0]}
        ):
            # Execute
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[8].endpoint(
                    service=None,
                    resource_type=None,
                    priority=None,
                    current_user=mock_admin_user,
                )

        # Assert
        assert len(result) >= 1
        # Should have scale down recommendations

    @pytest.mark.asyncio
    async def test_get_rightsizing_scale_up(self, mock_admin_user, clear_in_memory_data):
        """Test rightsizing recommendation for scale up."""
        # Setup - high utilization
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [90.0]}
        ):
            # Execute
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                result = await router.routes[8].endpoint(
                    service=None,
                    resource_type=None,
                    priority=None,
                    current_user=mock_admin_user,
                )

        # Assert
        assert len(result) >= 1
        # Should have scale up recommendations


# ============================================================================
# Test Recommendations Endpoints
# ============================================================================


class TestGetScalingRecommendations:
    """Tests for GET /api/v1/capacity/recommendations"""

    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, mock_admin_user):
        """Test successful retrieval of scaling recommendations."""
        # Setup
        mock_forecasts = {
            "cpu": {
                "metric": "cpu",
                "currentValue": 50.0,
                "forecast7d": 55.0,
                "forecast30d": 60.0,
                "threshold": 80.0,
                "unit": "%",
            }
        }
        mock_recommendations = [
            {
                "id": "rec-cpu-001",
                "action": "no-action",
                "reason": "Utilization within normal range",
                "priority": "low",
                "estimatedCost": 0.0,
            }
        ]
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch(
                "api.capacity_advanced_router.forecast_capacity", return_value=mock_forecasts
            ):
                with patch(
                    "api.capacity_advanced_router.generate_scaling_recommendations",
                    return_value=mock_recommendations,
                ):
                    # Execute
                    with patch(
                        "api.capacity_advanced_router.require_roles", return_value=mock_admin_user
                    ):
                        result = await router.routes[9].endpoint(
                            service=None,
                            resource_type=None,
                            priority=None,
                            current_user=mock_admin_user,
                        )

        # Assert
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_recommendations_with_filters(self, mock_admin_user):
        """Test retrieving recommendations with filters."""
        # Setup
        mock_forecasts = {
            "cpu": {
                "metric": "cpu",
                "currentValue": 50.0,
                "forecast7d": 55.0,
                "forecast30d": 60.0,
                "threshold": 80.0,
                "unit": "%",
            }
        }
        mock_recommendations = [
            {
                "id": "rec-cpu-001",
                "action": "no-action",
                "reason": "Utilization within normal range",
                "priority": "low",
                "estimatedCost": 0.0,
            }
        ]
        with patch(
            "api.capacity_advanced_router._build_metric_history", return_value={"cpu": [50.0]}
        ):
            with patch(
                "api.capacity_advanced_router.forecast_capacity", return_value=mock_forecasts
            ):
                with patch(
                    "api.capacity_advanced_router.generate_scaling_recommendations",
                    return_value=mock_recommendations,
                ):
                    # Execute
                    with patch(
                        "api.capacity_advanced_router.require_roles", return_value=mock_admin_user
                    ):
                        result = await router.routes[9].endpoint(
                            service="compute-service",
                            resource_type=ResourceType.CPU,
                            priority=Priority.LOW,
                            current_user=mock_admin_user,
                        )

        # Assert
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_recommendations_permission_denied(self):
        """Test retrieving recommendations without proper permissions."""
        # Setup
        with patch(
            "api.capacity_advanced_router.require_roles",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[9].endpoint(
                    service=None,
                    resource_type=None,
                    priority=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_recommendations_error_handling(self, mock_admin_user):
        """Test retrieving recommendations with error."""
        # Setup
        with patch(
            "api.capacity_advanced_router._build_metric_history",
            side_effect=Exception("Metric error"),
        ):
            # Execute & Assert
            with patch("api.capacity_advanced_router.require_roles", return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[9].endpoint(
                        service=None,
                        resource_type=None,
                        priority=None,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 500


# ============================================================================
# Test Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_generate_plan_id(self):
        """Test plan ID generation."""
        # Execute
        plan_id = _generate_plan_id()

        # Assert
        assert plan_id.startswith("CP-")
        assert len(plan_id) == 11  # CP- + 8 characters

    def test_generate_optimization_id(self):
        """Test optimization ID generation."""
        # Execute
        opt_id = _generate_optimization_id()

        # Assert
        assert opt_id.startswith("OPT-")
        assert len(opt_id) == 12  # OPT- + 8 characters

    def test_generate_rightsizing_id(self):
        """Test rightsizing ID generation."""
        # Execute
        rs_id = _generate_rightsizing_id()

        # Assert
        assert rs_id.startswith("RS-")
        assert len(rs_id) == 11  # RS- + 8 characters

    def test_calculate_trend_increasing(self):
        """Test trend calculation for increasing values."""
        # Execute
        trend = _calculate_trend(50.0, 60.0)

        # Assert
        assert trend == "increasing"

    def test_calculate_trend_decreasing(self):
        """Test trend calculation for decreasing values."""
        # Execute
        trend = _calculate_trend(60.0, 50.0)

        # Assert
        assert trend == "decreasing"

    def test_calculate_trend_stable(self):
        """Test trend calculation for stable values."""
        # Execute
        trend = _calculate_trend(50.0, 51.0)

        # Assert
        assert trend == "stable"

    def test_calculate_confidence_high(self):
        """Test confidence calculation with high history length."""
        # Execute
        confidence = _calculate_confidence(10)

        # Assert
        assert confidence == 0.85

    def test_calculate_confidence_medium(self):
        """Test confidence calculation with medium history length."""
        # Execute
        confidence = _calculate_confidence(5)

        # Assert
        assert confidence == 0.70

    def test_calculate_confidence_low(self):
        """Test confidence calculation with low history length."""
        # Execute
        confidence = _calculate_confidence(3)

        # Assert
        assert confidence == 0.50

    def test_calculate_confidence_very_low(self):
        """Test confidence calculation with very low history length."""
        # Execute
        confidence = _calculate_confidence(1)

        # Assert
        assert confidence == 0.30
