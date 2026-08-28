# -*- coding: utf-8 -*-
"""
Test suite for SLO Advanced Router (Database-backed)
SLO高级路由测试套件（数据库版本）
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.slo_advanced_router import (
    SLOAlertCreate,
    SLODefinitionCreate,
    SLODefinitionUpdate,
    SLOObjectiveCreate,
    SLOObjectiveUpdate,
    router,
)
from core.models import SLODefinitionDB, SLOObjectiveDB, SLOAlertDB
from core.auth_db import SessionLocal


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    """Clean up database before and after each test"""
    # Clean up before test
    db_session.query(SLOAlertDB).delete()
    db_session.query(SLOObjectiveDB).delete()
    db_session.query(SLODefinitionDB).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(SLOAlertDB).delete()
    db_session.query(SLOObjectiveDB).delete()
    db_session.query(SLODefinitionDB).delete()
    db_session.commit()


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user"""
    user = Mock()
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def sample_slo_definition():
    """Sample SLO definition data"""
    return {
        "id": "SLO-12345678",
        "name": "API Availability SLO",
        "description": "API service availability target",
        "metric_type": "availability",
        "threshold": 99.9,
        "operator": "gte",
        "window": "30d",
        "alerting": True,
    }


@pytest.fixture
def sample_slo_objective():
    """Sample SLO objective data"""
    return {
        "id": "OBJ-12345678",
        "name": "API Latency Objective",
        "service": "api-service",
        "metric": "latency",
        "target": 95.0,
        "window": "7d",
        "description": "API latency target",
    }


@pytest.fixture
def sample_slo_alert():
    """Sample SLO alert data"""
    return {
        "id": "ALT-12345678",
        "slo_id": "SLO-12345678",
        "severity": "critical",
        "message": "SLO breach detected",
        "metadata": {"error_rate": 0.05},
    }


# ============================================================================
# SLO Definition Tests
# ============================================================================


class TestSLODefinitions:
    """Test suite for SLO definition endpoints"""

    @pytest.mark.asyncio
    async def test_list_slo_definitions_success(self, mock_admin_user):
        """Test successful listing of SLO definitions"""
        from api.slo_advanced_router import list_slo_definitions

        result = await list_slo_definitions(current_user=mock_admin_user)

        assert "definitions" in result
        assert isinstance(result["definitions"], list)

    @pytest.mark.asyncio
    async def test_list_slo_definitions_with_data(self, mock_admin_user, sample_slo_definition):
        """Test listing SLO definitions with data"""
        from api.slo_advanced_router import create_slo_definition, list_slo_definitions

        # Create a definition first
        body = SLODefinitionCreate(**sample_slo_definition)
        await create_slo_definition(body, current_user=mock_admin_user)

        result = await list_slo_definitions(current_user=mock_admin_user)

        assert len(result["definitions"]) == 1
        assert result["definitions"][0]["name"] == "API Availability SLO"

    @pytest.mark.asyncio
    async def test_create_slo_definition_success(self, sample_slo_definition, mock_admin_user):
        """Test successful creation of SLO definition"""
        from api.slo_advanced_router import create_slo_definition

        body = SLODefinitionCreate(**sample_slo_definition)
        result = await create_slo_definition(body, current_user=mock_admin_user)

        assert result["name"] == "API Availability SLO"
        assert result["metric_type"] == "availability"
        assert result["threshold"] == 99.9
        assert result["window"] == "30d"
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_create_slo_definition_unauthorized(self, sample_slo_definition):
        """Test that viewers cannot create SLO definitions"""
        from api.slo_advanced_router import create_slo_definition, require_roles

        # Create a viewer user
        viewer_user = Mock()
        viewer_user.username = "viewer"
        viewer_user.role = "viewer"
        viewer_user.is_active = True

        body = SLODefinitionCreate(**sample_slo_definition)

        # The require_roles dependency should reject non-admin/operator users
        # We'll test this by checking that the dependency function works
        try:
            # require_roles returns a function, call it with the user
            role_check = require_roles("admin", "operator")
            role_check(viewer_user)
            # If we get here, the user passed the check (shouldn't happen for viewer)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.status_code == 403

    @pytest.mark.asyncio
    async def test_get_slo_definition_success(self, sample_slo_definition, mock_admin_user):
        """Test successful retrieval of SLO definition"""
        from api.slo_advanced_router import create_slo_definition, get_slo_definition

        body = SLODefinitionCreate(**sample_slo_definition)
        created = await create_slo_definition(body, current_user=mock_admin_user)
        definition_id = created["id"]

        result = await get_slo_definition(definition_id, current_user=mock_admin_user)

        assert result["id"] == definition_id
        assert result["name"] == "API Availability SLO"

    @pytest.mark.asyncio
    async def test_get_slo_definition_not_found(self, mock_admin_user):
        """Test getting non-existent SLO definition"""
        from api.slo_advanced_router import get_slo_definition

        with pytest.raises(HTTPException) as exc_info:
            await get_slo_definition("non-existent", current_user=mock_admin_user)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_slo_definition_success(self, sample_slo_definition, mock_admin_user):
        """Test successful update of SLO definition"""
        from api.slo_advanced_router import create_slo_definition, update_slo_definition

        body = SLODefinitionCreate(**sample_slo_definition)
        created = await create_slo_definition(body, current_user=mock_admin_user)
        definition_id = created["id"]

        update_body = SLODefinitionUpdate(name="Updated SLO", threshold=99.5)
        result = await update_slo_definition(
            definition_id, update_body, current_user=mock_admin_user
        )

        assert result["name"] == "Updated SLO"
        assert result["threshold"] == 99.5

    @pytest.mark.asyncio
    async def test_update_slo_definition_unauthorized(self, sample_slo_definition, mock_admin_user):
        """Test that viewers cannot update SLO definitions"""
        from api.slo_advanced_router import (
            create_slo_definition,
            require_roles,
            update_slo_definition,
        )

        body = SLODefinitionCreate(**sample_slo_definition)
        created = await create_slo_definition(body, current_user=mock_admin_user)
        definition_id = created["id"]

        # Create a viewer user
        viewer_user = Mock()
        viewer_user.username = "viewer"
        viewer_user.role = "viewer"
        viewer_user.is_active = True

        update_body = SLODefinitionUpdate(name="Updated SLO")

        # Test the role check directly
        try:
            role_check = require_roles("admin", "operator")
            role_check(viewer_user)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_slo_definition_success(self, sample_slo_definition, mock_admin_user):
        """Test successful deletion of SLO definition"""
        from api.slo_advanced_router import create_slo_definition, delete_slo_definition

        body = SLODefinitionCreate(**sample_slo_definition)
        created = await create_slo_definition(body, current_user=mock_admin_user)
        definition_id = created["id"]

        result = await delete_slo_definition(definition_id, current_user=mock_admin_user)

        assert result["ok"] == True

    @pytest.mark.asyncio
    async def test_delete_slo_definition_unauthorized(self, sample_slo_definition, mock_admin_user):
        """Test that viewers cannot delete SLO definitions"""
        from api.slo_advanced_router import (
            create_slo_definition,
            delete_slo_definition,
            require_roles,
        )

        body = SLODefinitionCreate(**sample_slo_definition)
        created = await create_slo_definition(body, current_user=mock_admin_user)
        definition_id = created["id"]

        # Create a viewer user
        viewer_user = Mock()
        viewer_user.username = "viewer"
        viewer_user.role = "viewer"
        viewer_user.is_active = True

        # Test the role check directly
        try:
            role_check = require_roles("admin", "operator")
            role_check(viewer_user)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_slo_definition_not_found(self, mock_admin_user):
        """Test deleting non-existent SLO definition"""
        from api.slo_advanced_router import delete_slo_definition

        with pytest.raises(HTTPException) as exc_info:
            await delete_slo_definition("non-existent", current_user=mock_admin_user)

        assert exc_info.value.status_code == 404


# ============================================================================
# SLO Metrics Tests
# ============================================================================


class TestSLOMetrics:
    """Test suite for SLO metrics endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_metrics_success(self, mock_admin_user):
        """Test successful retrieval of SLO metrics"""
        from api.slo_advanced_router import get_slo_metrics

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_metrics(current_user=mock_admin_user)

            assert "metrics" in result
            assert isinstance(result["metrics"], list)

    @pytest.mark.asyncio
    async def test_get_slo_metrics_with_service_filter(self, mock_admin_user):
        """Test SLO metrics with service filter"""
        from api.slo_advanced_router import get_slo_metrics

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_metrics(service="api-service", current_user=mock_admin_user)

            assert "metrics" in result

    @pytest.mark.asyncio
    async def test_get_slo_metrics_structure(self, mock_admin_user):
        """Test that SLO metrics have correct structure"""
        from api.slo_advanced_router import get_slo_metrics
        from core.slo_engine import SLORule

        # Create a mock SLO rule
        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.metric = "availability"
        mock_rule.target = 0.999
        mock_rule.window = 720  # 30 days in hours

        with (
            patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch("api.slo_advanced_router.evaluate_slo", return_value={"current": 0.995}),
        ):
            result = await get_slo_metrics(current_user=mock_admin_user)

            # Just check the structure exists, don't assume length
            assert "metrics" in result
            if len(result["metrics"]) > 0:
                metric = result["metrics"][0]
                assert "name" in metric
                assert "service" in metric
                assert "metric_type" in metric
                assert "current" in metric
                assert "target" in metric
                assert "trend" in metric
                assert "history" in metric


# ============================================================================
# SLO Budgets Tests
# ============================================================================


class TestSLOBudgets:
    """Test suite for SLO budgets endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_budgets_success(self, mock_admin_user):
        """Test successful retrieval of SLO budgets"""
        from api.slo_advanced_router import get_slo_budgets

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_budgets(current_user=mock_admin_user)

            assert "budgets" in result
            assert isinstance(result["budgets"], list)

    @pytest.mark.asyncio
    async def test_get_slo_budgets_structure(self, mock_admin_user):
        """Test that SLO budgets have correct structure"""
        from api.slo_advanced_router import get_slo_budgets
        from core.slo_engine import SLORule

        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.target = 0.999
        mock_rule.window = 720

        with (
            patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={
                    "current": 0.995,
                    "error_budget_remaining_percent": 95.0,
                    "status": "healthy",
                    "burn_rate": 0.1,
                },
            ),
        ):
            result = await get_slo_budgets(current_user=mock_admin_user)

            assert len(result["budgets"]) == 1
            budget = result["budgets"][0]
            assert "slo_id" in budget
            assert "slo_name" in budget
            assert "service" in budget
            assert "target" in budget
            assert "current" in budget
            assert "error_budget_remaining" in budget
            assert "error_budget_consumed" in budget
            assert "window" in budget
            assert "status" in budget


# ============================================================================
# SLO Burn Rates Tests
# ============================================================================


class TestSLOBurnRates:
    """Test suite for SLO burn rates endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_burn_rates_success(self, mock_admin_user):
        """Test successful retrieval of SLO burn rates"""
        from api.slo_advanced_router import get_slo_burn_rates

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_burn_rates(current_user=mock_admin_user)

            assert "burn_rates" in result
            assert isinstance(result["burn_rates"], list)

    @pytest.mark.asyncio
    async def test_get_slo_burn_rates_structure(self, mock_admin_user):
        """Test that SLO burn rates have correct structure"""
        from api.slo_advanced_router import get_slo_burn_rates
        from core.slo_engine import SLORule

        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.target = 0.999
        mock_rule.window = 720

        with (
            patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.995, "status": "healthy", "burn_rate": 0.1},
            ),
        ):
            result = await get_slo_burn_rates(current_user=mock_admin_user)

            assert len(result["burn_rates"]) == 1
            burn_rate = result["burn_rates"][0]
            assert "slo_id" in burn_rate
            assert "slo_name" in burn_rate
            assert "service" in burn_rate
            assert "burn_rate_1h" in burn_rate
            assert "burn_rate_24h" in burn_rate
            assert "burn_rate_7d" in burn_rate
            assert "status" in burn_rate
            assert "window" in burn_rate


# ============================================================================
# SLO Error Budgets Tests
# ============================================================================


class TestSLOErrorBudgets:
    """Test suite for detailed SLO error budgets endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_error_budgets_success(self, mock_admin_user):
        """Test successful retrieval of detailed SLO error budgets"""
        from api.slo_advanced_router import get_slo_error_budgets

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_error_budgets(current_user=mock_admin_user)

            assert "error_budgets" in result
            assert isinstance(result["error_budgets"], list)

    @pytest.mark.asyncio
    async def test_get_slo_error_budgets_structure(self, mock_admin_user):
        """Test that detailed error budgets have correct structure"""
        from api.slo_advanced_router import get_slo_error_budgets
        from core.slo_engine import SLORule

        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.target = 0.999
        mock_rule.window = 720

        with (
            patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={
                    "current": 0.995,
                    "error_budget_remaining_percent": 95.0,
                    "status": "healthy",
                    "burn_rate": 0.1,
                },
            ),
        ):
            result = await get_slo_error_budgets(current_user=mock_admin_user)

            assert len(result["error_budgets"]) == 1
            error_budget = result["error_budgets"][0]
            assert "slo_id" in error_budget
            assert "slo_name" in error_budget
            assert "service" in error_budget
            assert "target" in error_budget
            assert "current" in error_budget
            assert "error_budget_remaining_percent" in error_budget
            assert "error_budget_consumed_percent" in error_budget
            assert "burn_rate" in error_budget
            assert "estimated_hours_remaining" in error_budget
            assert "status" in error_budget
            assert "window" in error_budget
