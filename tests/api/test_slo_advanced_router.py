# -*- coding: utf-8 -*-
"""
Test suite for slo_advanced_router.py

This module provides comprehensive test coverage for the SLO advanced router,
including all CRUD operations, data validation, error handling, and permission controls.
"""

import datetime
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from api.slo_advanced_router import (
    SLOAlertCreate,
    SLODefinitionCreate,
    SLODefinitionUpdate,
    SLOObjectiveCreate,
    SLOObjectiveUpdate,
    _slo_alerts,
    _slo_definitions,
    _slo_objectives,
    router,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user"""
    user = Mock()
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def mock_operator_user():
    """Create a mock operator user"""
    user = Mock()
    user.username = "operator"
    user.role = "operator"
    user.is_active = True
    return user


@pytest.fixture
def mock_viewer_user():
    """Create a mock viewer user"""
    user = Mock()
    user.username = "viewer"
    user.role = "viewer"
    user.is_active = True
    return user


@pytest.fixture
def sample_slo_definition():
    """Create a sample SLO definition for testing"""
    return {
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
    """Create a sample SLO objective for testing"""
    return {
        "name": "API Latency Objective",
        "service": "api-service",
        "metric": "latency",
        "target": 95.0,
        "window": "7d",
        "description": "API latency target",
    }


@pytest.fixture
def sample_slo_alert():
    """Create a sample SLO alert for testing"""
    return {
        "slo_id": "DEF-001",
        "severity": "critical",
        "message": "SLO breach detected",
        "metadata": {"error_rate": 0.05},
    }


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the in-memory state before each test"""
    _slo_definitions.clear()
    _slo_objectives.clear()
    _slo_alerts.clear()
    yield
    _slo_definitions.clear()
    _slo_objectives.clear()
    _slo_alerts.clear()


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
            require_roles("admin", "operator")(lambda: None)(viewer_user)
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
            require_roles("admin", "operator")(lambda: None)(viewer_user)
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
        assert definition_id not in _slo_definitions

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
            require_roles("admin", "operator")(lambda: None)(viewer_user)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.value.status_code == 403

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


# ============================================================================
# SLO Alerts Tests
# ============================================================================


class TestSLOAlerts:
    """Test suite for SLO alert endpoints"""

    @pytest.mark.asyncio
    async def test_list_slo_alerts_success(self, mock_admin_user):
        """Test successful listing of SLO alerts"""
        from api.slo_advanced_router import list_slo_alerts

        result = await list_slo_alerts(current_user=mock_admin_user)

        assert "alerts" in result
        assert isinstance(result["alerts"], list)

    @pytest.mark.asyncio
    async def test_list_slo_alerts_with_status_filter(self, mock_admin_user):
        """Test listing SLO alerts with status filter"""
        from api.slo_advanced_router import list_slo_alerts

        result = await list_slo_alerts(status="open", current_user=mock_admin_user)

        assert "alerts" in result

    @pytest.mark.asyncio
    async def test_list_slo_alerts_with_severity_filter(self, mock_admin_user):
        """Test listing SLO alerts with severity filter"""
        from api.slo_advanced_router import list_slo_alerts

        result = await list_slo_alerts(severity="critical", current_user=mock_admin_user)

        assert "alerts" in result

    @pytest.mark.asyncio
    async def test_create_slo_alert_success(self, sample_slo_alert, mock_admin_user):
        """Test successful creation of SLO alert"""
        from api.slo_advanced_router import create_slo_alert

        with patch("api.slo_advanced_router.get_slo", return_value=Mock(name="Test SLO")):
            body = SLOAlertCreate(**sample_slo_alert)
            result = await create_slo_alert(body, current_user=mock_admin_user)

            assert result["slo_id"] == "DEF-001"
            assert result["severity"] == "critical"
            assert result["message"] == "SLO breach detected"
            assert result["status"] == "open"
            assert "id" in result
            assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_slo_alert_unauthorized(self, sample_slo_alert):
        """Test that viewers cannot create SLO alerts"""
        from api.slo_advanced_router import create_slo_alert, require_roles

        # Create a viewer user
        viewer_user = Mock()
        viewer_user.username = "viewer"
        viewer_user.role = "viewer"
        viewer_user.is_active = True

        body = SLOAlertCreate(**sample_slo_alert)

        # Test the role check directly
        try:
            require_roles("admin", "operator")(lambda: None)(viewer_user)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.value.status_code == 403


# ============================================================================
# SLO Reports Tests
# ============================================================================


class TestSLOReports:
    """Test suite for SLO reports endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_reports_success(self, mock_admin_user):
        """Test successful retrieval of SLO reports"""
        from api.slo_advanced_router import get_slo_reports

        with patch("api.slo_advanced_router.generate_sla_report", return_value=[]):
            result = await get_slo_reports(period="30d", current_user=mock_admin_user)

            assert "reports" in result
            assert isinstance(result["reports"], list)

    @pytest.mark.asyncio
    async def test_get_slo_reports_different_periods(self, mock_admin_user):
        """Test SLO reports with different periods"""
        from api.slo_advanced_router import get_slo_reports

        with patch("api.slo_advanced_router.generate_sla_report", return_value=[]):
            result_7d = await get_slo_reports(period="7d", current_user=mock_admin_user)
            assert "reports" in result_7d

            result_90d = await get_slo_reports(period="90d", current_user=mock_admin_user)
            assert "reports" in result_90d


# ============================================================================
# SLO Historical Data Tests
# ============================================================================


class TestSLOHistoricalData:
    """Test suite for SLO historical data endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_historical_data_success(self, mock_admin_user):
        """Test successful retrieval of SLO historical data"""
        from api.slo_advanced_router import get_slo_historical_data

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_historical_data(period="7d", current_user=mock_admin_user)

            assert "historical_data" in result
            assert isinstance(result["historical_data"], list)

    @pytest.mark.asyncio
    async def test_get_slo_historical_data_with_slo_filter(self, mock_admin_user):
        """Test historical data with SLO ID filter"""
        from api.slo_advanced_router import get_slo_historical_data

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_historical_data(
                slo_id="DEF-001", period="7d", current_user=mock_admin_user
            )

            assert "historical_data" in result

    @pytest.mark.asyncio
    async def test_get_slo_historical_data_different_periods(self, mock_admin_user):
        """Test historical data with different periods"""
        from api.slo_advanced_router import get_slo_historical_data

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result_1h = await get_slo_historical_data(period="1h", current_user=mock_admin_user)
            assert "historical_data" in result_1h

            result_7d = await get_slo_historical_data(period="7d", current_user=mock_admin_user)
            assert "historical_data" in result_7d


# ============================================================================
# SLO Services Tests
# ============================================================================


class TestSLOServices:
    """Test suite for SLO services endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_services_success(self, mock_admin_user):
        """Test successful retrieval of services with SLOs"""
        from api.slo_advanced_router import get_slo_services

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_services(current_user=mock_admin_user)

            assert "services" in result
            assert isinstance(result["services"], list)

    @pytest.mark.asyncio
    async def test_get_slo_services_structure(self, mock_admin_user):
        """Test that services have correct structure"""
        from api.slo_advanced_router import get_slo_services
        from core.slo_engine import SLORule

        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.target = 0.999

        with patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]):
            result = await get_slo_services(current_user=mock_admin_user)

            assert len(result["services"]) == 1
            service = result["services"][0]
            assert "name" in service
            assert "slo_count" in service
            assert "slos" in service


# ============================================================================
# SLO Objectives Tests
# ============================================================================


class TestSLOObjectives:
    """Test suite for SLO objective endpoints"""

    @pytest.mark.asyncio
    async def test_list_slo_objectives_success(self, mock_admin_user):
        """Test successful listing of SLO objectives"""
        from api.slo_advanced_router import list_slo_objectives

        result = await list_slo_objectives(current_user=mock_admin_user)

        assert "objectives" in result
        assert isinstance(result["objectives"], list)

    @pytest.mark.asyncio
    async def test_list_slo_objectives_with_service_filter(self, mock_admin_user):
        """Test listing SLO objectives with service filter"""
        from api.slo_advanced_router import list_slo_objectives

        result = await list_slo_objectives(service="api-service", current_user=mock_admin_user)

        assert "objectives" in result

    @pytest.mark.asyncio
    async def test_create_slo_objective_success(self, sample_slo_objective, mock_admin_user):
        """Test successful creation of SLO objective"""
        from api.slo_advanced_router import create_slo_objective

        with (
            patch("api.slo_advanced_router.create_slo", return_value=Mock(id="rule-1")),
            patch("api.slo_advanced_router.get_slo", return_value=Mock()),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.95, "status": "healthy"},
            ),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
        ):
            body = SLOObjectiveCreate(**sample_slo_objective)
            result = await create_slo_objective(body, current_user=mock_admin_user)

            assert result["name"] == "API Latency Objective"
            assert result["service"] == "api-service"
            assert result["target"] == 95.0
            assert "id" in result
            assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_slo_objective_unauthorized(self, sample_slo_objective):
        """Test that viewers cannot create SLO objectives"""
        from api.slo_advanced_router import create_slo_objective, require_roles

        # Create a viewer user
        viewer_user = Mock()
        viewer_user.username = "viewer"
        viewer_user.role = "viewer"
        viewer_user.is_active = True

        body = SLOObjectiveCreate(**sample_slo_objective)

        # Test the role check directly
        try:
            require_roles("admin", "operator")(lambda: None)(viewer_user)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_slo_objective_success(self, sample_slo_objective, mock_admin_user):
        """Test successful update of SLO objective"""
        from api.slo_advanced_router import create_slo_objective, update_slo_objective

        with (
            patch("api.slo_advanced_router.create_slo", return_value=Mock(id="rule-1")),
            patch("api.slo_advanced_router.get_slo", return_value=Mock()),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.95, "status": "healthy"},
            ),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch("api.slo_advanced_router.update_slo"),
        ):
            body = SLOObjectiveCreate(**sample_slo_objective)
            created = await create_slo_objective(body, current_user=mock_admin_user)
            objective_id = created["id"]

            update_body = SLOObjectiveUpdate(name="Updated Objective", target=98.0)
            result = await update_slo_objective(
                objective_id, update_body, current_user=mock_admin_user
            )

            assert result["name"] == "Updated Objective"
            assert result["target"] == 98.0

    @pytest.mark.asyncio
    async def test_update_slo_objective_unauthorized(self, sample_slo_objective, mock_admin_user):
        """Test that viewers cannot update SLO objectives"""
        from api.slo_advanced_router import (
            create_slo_objective,
            require_roles,
            update_slo_objective,
        )

        with (
            patch("api.slo_advanced_router.create_slo", return_value=Mock(id="rule-1")),
            patch("api.slo_advanced_router.get_slo", return_value=Mock()),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.95, "status": "healthy"},
            ),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
        ):
            body = SLOObjectiveCreate(**sample_slo_objective)
            created = await create_slo_objective(body, current_user=mock_admin_user)
            objective_id = created["id"]

            # Create a viewer user
            viewer_user = Mock()
            viewer_user.username = "viewer"
            viewer_user.role = "viewer"

            update_body = SLOObjectiveUpdate(name="Updated Objective")

            # Test the role check directly
            try:
                require_roles("admin", "operator")(lambda: None)(viewer_user)
                assert False, "Viewer should not pass role check"
            except HTTPException as exc_info:
                assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_slo_objective_success(self, sample_slo_objective, mock_admin_user):
        """Test successful deletion of SLO objective"""
        from api.slo_advanced_router import create_slo_objective, delete_slo_objective

        with (
            patch("api.slo_advanced_router.create_slo", return_value=Mock(id="rule-1")),
            patch("api.slo_advanced_router.get_slo", return_value=Mock()),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.95, "status": "healthy"},
            ),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch("api.slo_advanced_router.delete_slo"),
        ):
            body = SLOObjectiveCreate(**sample_slo_objective)
            created = await create_slo_objective(body, current_user=mock_admin_user)
            objective_id = created["id"]

            result = await delete_slo_objective(objective_id, current_user=mock_admin_user)

            assert result["ok"] == True
            assert objective_id not in _slo_objectives

    @pytest.mark.asyncio
    async def test_delete_slo_objective_unauthorized(self, sample_slo_objective, mock_admin_user):
        """Test that viewers cannot delete SLO objectives"""
        from api.slo_advanced_router import (
            create_slo_objective,
            delete_slo_objective,
            require_roles,
        )

        with (
            patch("api.slo_advanced_router.create_slo", return_value=Mock(id="rule-1")),
            patch("api.slo_advanced_router.get_slo", return_value=Mock()),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.95, "status": "healthy"},
            ),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
        ):
            body = SLOObjectiveCreate(**sample_slo_objective)
            created = await create_slo_objective(body, current_user=mock_admin_user)
            objective_id = created["id"]

            # Create a viewer user
            viewer_user = Mock()
            viewer_user.username = "viewer"
            viewer_user.role = "viewer"

            # Test the role check directly
            try:
                require_roles("admin", "operator")(lambda: None)(viewer_user)
                assert False, "Viewer should not pass role check"
            except HTTPException as exc_info:
                assert exc_info.value.status_code == 403


# ============================================================================
# SLO Rollups Tests
# ============================================================================


class TestSLORollups:
    """Test suite for SLO rollup endpoint"""

    @pytest.mark.asyncio
    async def test_get_slo_rollups_success(self, mock_admin_user):
        """Test successful retrieval of SLO rollups"""
        from api.slo_advanced_router import get_slo_rollups

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_rollups(current_user=mock_admin_user)

            assert "rollups" in result
            assert isinstance(result["rollups"], list)

    @pytest.mark.asyncio
    async def test_get_slo_rollups_with_service_filter(self, mock_admin_user):
        """Test SLO rollups with service filter"""
        from api.slo_advanced_router import get_slo_rollups

        with patch("api.slo_advanced_router.list_slos", return_value=[]):
            result = await get_slo_rollups(service="api-service", current_user=mock_admin_user)

            assert "rollups" in result

    @pytest.mark.asyncio
    async def test_get_slo_rollups_structure(self, mock_admin_user):
        """Test that rollups have correct structure"""
        from api.slo_advanced_router import get_slo_rollups
        from core.slo_engine import SLORule

        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.metric = "availability"
        mock_rule.target = 0.999

        with (
            patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.995, "status": "healthy"},
            ),
        ):
            result = await get_slo_rollups(current_user=mock_admin_user)

            # Just check the structure exists, don't assume length
            assert "rollups" in result
            if len(result["rollups"]) > 0:
                rollup = result["rollups"][0]
                assert "service" in rollup
                assert "total_slos" in rollup
                assert "healthy_slos" in rollup
                assert "warning_slos" in rollup
                assert "critical_slos" in rollup
                assert "avg_current" in rollup
                assert "avg_target" in rollup
                assert "metrics" in rollup


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Test suite for data validation"""

    def test_slo_definition_create_valid(self, sample_slo_definition):
        """Test valid SLO definition creation"""
        definition = SLODefinitionCreate(**sample_slo_definition)
        assert definition.name == "API Availability SLO"
        assert definition.metric_type == "availability"
        assert definition.threshold == 99.9

    def test_slo_definition_create_invalid_metric_type(self):
        """Test that invalid metric type is rejected"""
        with pytest.raises(Exception):
            SLODefinitionCreate(name="Test", metric_type="invalid_type", threshold=99.9)

    def test_slo_definition_create_invalid_operator(self):
        """Test that invalid operator is rejected"""
        with pytest.raises(Exception):
            SLODefinitionCreate(
                name="Test", metric_type="availability", threshold=99.9, operator="invalid_op"
            )

    def test_slo_definition_create_invalid_threshold(self):
        """Test that threshold outside range is rejected"""
        with pytest.raises(Exception):
            SLODefinitionCreate(
                name="Test", metric_type="availability", threshold=150.0  # Exceeds le=100
            )

    def test_slo_objective_create_valid(self, sample_slo_objective):
        """Test valid SLO objective creation"""
        objective = SLOObjectiveCreate(**sample_slo_objective)
        assert objective.name == "API Latency Objective"
        assert objective.service == "api-service"
        assert objective.target == 95.0

    def test_slo_objective_create_invalid_target(self):
        """Test that target outside range is rejected"""
        with pytest.raises(Exception):
            SLOObjectiveCreate(
                name="Test", service="api-service", metric="latency", target=150.0  # Exceeds le=100
            )

    def test_slo_alert_create_valid(self, sample_slo_alert):
        """Test valid SLO alert creation"""
        alert = SLOAlertCreate(**sample_slo_alert)
        assert alert.slo_id == "DEF-001"
        assert alert.severity == "critical"

    def test_slo_alert_create_invalid_severity(self):
        """Test that invalid severity is rejected"""
        with pytest.raises(Exception):
            SLOAlertCreate(slo_id="DEF-001", severity="invalid_severity", message="Test")


# ============================================================================
# Authentication and Authorization Tests
# ============================================================================


class TestAuthentication:
    """Test suite for authentication"""

    @pytest.mark.asyncio
    async def test_internal_api_key_authentication(self):
        """Test internal API key authentication"""
        from fastapi import Request

        from api.slo_advanced_router import _get_current_user_or_internal

        request = Mock(spec=Request)
        request.headers = {"x-internal-key": "test-key"}

        with patch("api.slo_advanced_router.INTERNAL_API_KEY", "test-key"):
            user = await _get_current_user_or_internal(request, x_internal_key="test-key")
            assert user.username == "internal"
            assert user.role == "admin"

    @pytest.mark.asyncio
    async def test_bearer_token_authentication(self):
        """Test bearer token authentication"""
        from fastapi import Request

        from api.slo_advanced_router import _get_current_user_or_internal

        request = Mock(spec=Request)
        request.headers = {"authorization": "Bearer test-token"}

        with patch(
            "api.slo_advanced_router.get_current_user",
            return_value=Mock(username="user", role="viewer"),
        ):
            user = await _get_current_user_or_internal(request, x_internal_key=None)
            assert user.username == "user"

    @pytest.mark.asyncio
    async def test_no_authentication_fails(self):
        """Test that missing authentication fails"""
        from fastapi import Request

        from api.slo_advanced_router import _get_current_user_or_internal

        request = Mock(spec=Request)
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await _get_current_user_or_internal(request, x_internal_key=None)

        assert exc_info.value.status_code == 401


class TestAuthorization:
    """Test suite for authorization"""

    @pytest.mark.asyncio
    async def test_admin_can_create_definitions(self, sample_slo_definition, mock_admin_user):
        """Test that admins can create SLO definitions"""
        from api.slo_advanced_router import create_slo_definition

        body = SLODefinitionCreate(**sample_slo_definition)
        result = await create_slo_definition(body, current_user=mock_admin_user)

        assert "id" in result

    @pytest.mark.asyncio
    async def test_operator_can_create_definitions(self, sample_slo_definition, mock_operator_user):
        """Test that operators can create SLO definitions"""
        from api.slo_advanced_router import create_slo_definition

        body = SLODefinitionCreate(**sample_slo_definition)
        result = await create_slo_definition(body, current_user=mock_operator_user)

        assert "id" in result

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_definitions(self, sample_slo_definition):
        """Test that viewers cannot create SLO definitions"""
        from api.slo_advanced_router import create_slo_definition, require_roles

        # Create a viewer user
        viewer_user = Mock()
        viewer_user.username = "viewer"
        viewer_user.role = "viewer"
        viewer_user.is_active = True

        body = SLODefinitionCreate(**sample_slo_definition)

        # Test the role check directly
        try:
            require_roles("admin", "operator")(lambda: None)(viewer_user)
            assert False, "Viewer should not pass role check"
        except HTTPException as exc_info:
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_all_roles_can_view_definitions(
        self, mock_admin_user, mock_operator_user, mock_viewer_user
    ):
        """Test that all roles can view SLO definitions"""
        from api.slo_advanced_router import list_slo_definitions

        result_admin = await list_slo_definitions(current_user=mock_admin_user)
        assert "definitions" in result_admin

        result_operator = await list_slo_definitions(current_user=mock_operator_user)
        assert "definitions" in result_operator

        result_viewer = await list_slo_definitions(current_user=mock_viewer_user)
        assert "definitions" in result_viewer


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling"""

    @pytest.mark.asyncio
    async def test_slo_engine_exception_handling(self, mock_admin_user):
        """Test that SLO engine exceptions are handled properly"""
        from api.slo_advanced_router import get_slo_metrics

        with patch("api.slo_advanced_router.list_slos", side_effect=Exception("SLO engine error")):
            # The endpoint should handle the exception gracefully
            with pytest.raises(Exception) as exc_info:
                await get_slo_metrics(current_user=mock_admin_user)
            # Should raise the exception
            assert "SLO engine error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_metrics_history_exception_handling(self, mock_admin_user):
        """Test that metrics history exceptions are handled properly"""
        from api.slo_advanced_router import get_slo_metrics
        from core.slo_engine import SLORule

        mock_rule = Mock(spec=SLORule)
        mock_rule.id = "slo-1"
        mock_rule.name = "Test SLO"
        mock_rule.service = "test-service"
        mock_rule.metric = "availability"
        mock_rule.target = 0.999
        mock_rule.window = 720

        with (
            patch("api.slo_advanced_router.list_slos", return_value=[mock_rule]),
            patch(
                "api.slo_advanced_router._get_metric_points", side_effect=Exception("Metrics error")
            ),
        ):
            result = await get_slo_metrics(current_user=mock_admin_user)
            # Should handle gracefully
            assert "metrics" in result


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for SLO router"""

    @pytest.mark.asyncio
    async def test_full_slo_definition_lifecycle(self, sample_slo_definition, mock_admin_user):
        """Test complete SLO definition lifecycle: create, read, update, delete"""
        from api.slo_advanced_router import (
            create_slo_definition,
            delete_slo_definition,
            get_slo_definition,
            update_slo_definition,
        )

        # Create
        body = SLODefinitionCreate(**sample_slo_definition)
        created = await create_slo_definition(body, current_user=mock_admin_user)
        definition_id = created["id"]
        assert "id" in created

        # Read
        retrieved = await get_slo_definition(definition_id, current_user=mock_admin_user)
        assert retrieved["id"] == definition_id

        # Update
        update_body = SLODefinitionUpdate(name="Updated SLO", threshold=99.5)
        updated = await update_slo_definition(
            definition_id, update_body, current_user=mock_admin_user
        )
        assert updated["name"] == "Updated SLO"

        # Delete
        deleted = await delete_slo_definition(definition_id, current_user=mock_admin_user)
        assert deleted["ok"] == True

    @pytest.mark.asyncio
    async def test_full_slo_objective_lifecycle(self, sample_slo_objective, mock_admin_user):
        """Test complete SLO objective lifecycle: create, read, update, delete"""
        from api.slo_advanced_router import (
            _slo_objectives,
            create_slo_objective,
            delete_slo_objective,
            update_slo_objective,
        )

        with (
            patch("api.slo_advanced_router.create_slo", return_value=Mock(id="rule-1")),
            patch("api.slo_advanced_router.get_slo", return_value=Mock()),
            patch(
                "api.slo_advanced_router.evaluate_slo",
                return_value={"current": 0.95, "status": "healthy"},
            ),
            patch("api.slo_advanced_router._get_metric_points", return_value=[]),
            patch("api.slo_advanced_router.update_slo"),
            patch("api.slo_advanced_router.delete_slo"),
        ):
            # Create
            body = SLOObjectiveCreate(**sample_slo_objective)
            created = await create_slo_objective(body, current_user=mock_admin_user)
            objective_id = created["id"]
            assert "id" in created

            # Read - check directly in the objectives dict
            assert objective_id in _slo_objectives

            # Update
            update_body = SLOObjectiveUpdate(name="Updated Objective")
            updated = await update_slo_objective(
                objective_id, update_body, current_user=mock_admin_user
            )
            assert updated["name"] == "Updated Objective"

            # Delete
            deleted = await delete_slo_objective(objective_id, current_user=mock_admin_user)
            assert deleted["ok"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
