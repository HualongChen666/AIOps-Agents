# -*- coding: utf-8 -*-
"""
Test suite for Change Advanced Router
======================================

Comprehensive tests for change management endpoints including requests,
approvals, schedules, impact analysis, and rollback plans.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException, status

from api.change_advanced_router import (
    router,
    ChangeStatus,
    ApprovalStatus,
    ScheduleStatus,
    ImpactLevel,
    ChangeRequestCreate,
    ChangeRequestUpdate,
    ApprovalRequest,
    ApprovalResponse,
    ScheduleRequest,
    ScheduleResponse,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    RollbackPlanRequest,
    RollbackPlanResponse,
    _approvals,
    _schedules,
    _rollback_plans,
    _generate_approval_id,
    _generate_schedule_id,
    _generate_rollback_plan_id,
)
from core.change_management_engine import ChangeRequest, RiskLevel
from core.auth_db import User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = Mock(spec=User)
    user.id = 1
    user.username = "admin"
    user.tenant_id = "default"
    user.roles = ["admin"]
    return user


@pytest.fixture
def mock_operator_user():
    """Mock operator user."""
    user = Mock(spec=User)
    user.id = 2
    user.username = "operator"
    user.tenant_id = "default"
    user.roles = ["operator"]
    return user


@pytest.fixture
def mock_business_user():
    """Mock business user."""
    user = Mock(spec=User)
    user.id = 3
    user.username = "business"
    user.tenant_id = "default"
    user.roles = ["business"]
    return user


@pytest.fixture
def sample_change_request():
    """Sample change request."""
    request = Mock(spec=ChangeRequest)
    request.id = "CR-12345678"
    request.title = "Test Change"
    request.description = "Test change description"
    request.requester = "admin"
    request.approver = "manager"
    request.risk_level = RiskLevel.LOW
    request.schedule = ""
    request.affected_services = ["compute-service"]
    request.implementation_plan = "Step 1, Step 2"
    request.rollback_plan = "Rollback step 1"
    request.status = ChangeStatus.DRAFT
    request.audit_log = []
    return request


@pytest.fixture
def sample_request_create():
    """Sample change request creation data."""
    return ChangeRequestCreate(
        title="Test Change",
        description="Test change description",
        requester="admin",
        approver="manager",
        risk_level=RiskLevel.LOW,
        schedule="",
        affected_services=["compute-service"],
        implementation_plan="Step 1, Step 2",
        rollback_plan="Rollback step 1",
        priority="medium",
        estimated_duration=60,
        change_type="standard",
        test_plan="Test step 1",
        validation_criteria=["criterion1"],
        notification_recipients=["team@example.com"],
        metadata={"key": "value"},
    )


@pytest.fixture
def sample_request_update():
    """Sample change request update data."""
    return ChangeRequestUpdate(
        title="Updated Change",
        description="Updated description",
        approver="new-manager",
        risk_level=RiskLevel.MEDIUM,
        priority="high",
    )


@pytest.fixture
def sample_approval_request():
    """Sample approval request."""
    return ApprovalRequest(
        change_request_id="CR-12345678",
        approver="manager",
        decision=ApprovalStatus.APPROVED,
        comments="Approved for implementation",
        conditions=["condition1"],
    )


@pytest.fixture
def sample_schedule_request():
    """Sample schedule request."""
    return ScheduleRequest(
        change_request_id="CR-12345678",
        scheduled_start=datetime.utcnow() + timedelta(days=1),
        scheduled_end=datetime.utcnow() + timedelta(days=1, hours=2),
        maintenance_window="MW-001",
        timezone="UTC",
        assigned_team=["admin", "operator"],
        prerequisites=["prereq1"],
        dependencies=["CR-DEP-001"],
    )


@pytest.fixture
def sample_impact_analysis_request():
    """Sample impact analysis request."""
    return ImpactAnalysisRequest(
        change_request_id="CR-12345678",
        affected_services=["compute-service", "database"],
        change_description="Update server configuration",
        risk_level=RiskLevel.MEDIUM,
        analysis_depth="standard",
    )


@pytest.fixture
def sample_rollback_plan_request():
    """Sample rollback plan request."""
    return RollbackPlanRequest(
        change_request_id="CR-12345678",
        rollback_steps=["Step 1", "Step 2", "Step 3"],
        estimated_rollback_time=30,
        data_consistency_checks=["check1", "check2"],
        rollback_triggers=["trigger1"],
        validation_after_rollback=["validation1"],
    )


@pytest.fixture
def clear_in_memory_data():
    """Clear in-memory data before each test."""
    yield
    _approvals.clear()
    _schedules.clear()
    _rollback_plans.clear()


# ============================================================================
# Test Change Requests Endpoints
# ============================================================================

class TestListChangeRequests:
    """Tests for GET /api/v1/change/requests"""

    @pytest.mark.asyncio
    async def test_list_requests_success(self, sample_change_request, mock_admin_user):
        """Test successful listing of change requests."""
        # Setup
        with patch('api.change_advanced_router.list_requests', return_value=[sample_change_request]):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[0].endpoint(
                    status=None,
                    risk_level=None,
                    requester=None,
                    priority=None,
                    current_user=mock_admin_user,
                )

        # Assert
        assert len(result) == 1
        assert result[0].id == "CR-12345678"

    @pytest.mark.asyncio
    async def test_list_requests_with_filters(self, sample_change_request, mock_admin_user):
        """Test listing requests with filters."""
        # Setup
        with patch('api.change_advanced_router.list_requests', return_value=[sample_change_request]):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[0].endpoint(
                    status="draft",
                    risk_level=RiskLevel.LOW,
                    requester="admin",
                    priority="medium",
                    current_user=mock_admin_user,
                )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_requests_empty_result(self, mock_admin_user):
        """Test listing requests with no results."""
        # Setup
        with patch('api.change_advanced_router.list_requests', return_value=[]):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[0].endpoint(
                    status=None,
                    risk_level=None,
                    requester=None,
                    priority=None,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_list_requests_permission_denied(self):
        """Test listing requests without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[0].endpoint(
                    status=None,
                    risk_level=None,
                    requester=None,
                    priority=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_requests_error_handling(self, mock_admin_user):
        """Test listing requests with error."""
        # Setup
        with patch('api.change_advanced_router.list_requests', side_effect=Exception("Database error")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[0].endpoint(
                        status=None,
                        risk_level=None,
                        requester=None,
                        priority=None,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 500


class TestCreateChangeRequest:
    """Tests for POST /api/v1/change/requests"""

    @pytest.mark.asyncio
    async def test_create_request_success(self, sample_request_create, sample_change_request, mock_admin_user):
        """Test successful creation of change request."""
        # Setup
        with patch('api.change_advanced_router.create_request', return_value=sample_change_request):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[1].endpoint(
                    request=sample_request_create,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.id == "CR-12345678"
        assert result.title == "Test Change"

    @pytest.mark.asyncio
    async def test_create_request_validation_error(self, mock_admin_user):
        """Test creating request with invalid data."""
        # Setup
        invalid_data = ChangeRequestCreate(
            title="",  # Invalid: empty title
            requester="admin",
        )

        # Execute & Assert
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(Exception):  # Pydantic validation error
                await router.routes[1].endpoint(
                    request=invalid_data,
                    current_user=mock_admin_user,
                )

    @pytest.mark.asyncio
    async def test_create_request_permission_denied(self, sample_request_create, mock_business_user):
        """Test creating request without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[1].endpoint(
                    request=sample_request_create,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_request_engine_error(self, sample_request_create, mock_admin_user):
        """Test creating request with engine error."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.create_request', side_effect=ChangeManagementError("Engine error")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[1].endpoint(
                        request=sample_request_create,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 400


class TestGetChangeRequest:
    """Tests for GET /api/v1/change/requests/{id}"""

    @pytest.mark.asyncio
    async def test_get_request_success(self, sample_change_request, mock_admin_user):
        """Test successful retrieval of change request."""
        # Setup
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[2].endpoint(
                    request_id="CR-12345678",
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.id == "CR-12345678"

    @pytest.mark.asyncio
    async def test_get_request_not_found(self, mock_admin_user):
        """Test retrieving non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[2].endpoint(
                        request_id="CR-NOTFOUND",
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_request_permission_denied(self):
        """Test retrieving request without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[2].endpoint(
                    request_id="CR-12345678",
                    current_user=None,
                )
            assert exc_info.value.status_code == 403


class TestUpdateChangeRequest:
    """Tests for PATCH /api/v1/change/requests/{id}"""

    @pytest.mark.asyncio
    async def test_update_request_success(self, sample_change_request, sample_request_update, mock_admin_user):
        """Test successful update of change request."""
        # Setup
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[3].endpoint(
                        request_id="CR-12345678",
                        update=sample_request_update,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result.title == "Updated Change"

    @pytest.mark.asyncio
    async def test_update_request_not_found(self, sample_request_update, mock_admin_user):
        """Test updating non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[3].endpoint(
                        request_id="CR-NOTFOUND",
                        update=sample_request_update,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_request_permission_denied(self, sample_request_update, mock_business_user):
        """Test updating request without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[3].endpoint(
                    request_id="CR-12345678",
                    update=sample_request_update,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_request_partial_update(self, sample_change_request, mock_admin_user):
        """Test partial update of change request."""
        # Setup
        partial_update = ChangeRequestUpdate(title="Updated Title Only")
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[3].endpoint(
                        request_id="CR-12345678",
                        update=partial_update,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result.title == "Updated Title Only"


class TestDeleteChangeRequest:
    """Tests for DELETE /api/v1/change/requests/{id}"""

    @pytest.mark.asyncio
    async def test_delete_request_success(self, sample_change_request, mock_admin_user):
        """Test successful deletion of change request."""
        # Setup
        sample_change_request.status = ChangeStatus.DRAFT
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[4].endpoint(
                        request_id="CR-12345678",
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_request_not_found(self, mock_admin_user):
        """Test deleting non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[4].endpoint(
                        request_id="CR-NOTFOUND",
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_request_invalid_status(self, sample_change_request, mock_admin_user):
        """Test deleting request with invalid status."""
        # Setup
        sample_change_request.status = ChangeStatus.APPROVED
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[4].endpoint(
                        request_id="CR-12345678",
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_request_permission_denied(self, mock_operator_user):
        """Test deleting request without admin permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[4].endpoint(
                    request_id="CR-12345678",
                    current_user=mock_operator_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Approvals Endpoints
# ============================================================================

class TestListApprovals:
    """Tests for GET /api/v1/change/approvals"""

    @pytest.mark.asyncio
    async def test_list_approvals_success(self, sample_approval_request, mock_admin_user, clear_in_memory_data):
        """Test successful listing of approvals."""
        # Setup
        approval = ApprovalResponse(
            id="APR-12345678",
            change_request_id="CR-12345678",
            approver="manager",
            decision=ApprovalStatus.APPROVED,
            comments="Approved",
            conditions=[],
            approved_at=datetime.utcnow(),
        )
        _approvals["APR-12345678"] = approval

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[5].endpoint(
                change_request_id=None,
                decision=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].id == "APR-12345678"

    @pytest.mark.asyncio
    async def test_list_approvals_with_filters(self, mock_admin_user, clear_in_memory_data):
        """Test listing approvals with filters."""
        # Setup
        approval = ApprovalResponse(
            id="APR-12345678",
            change_request_id="CR-12345678",
            approver="manager",
            decision=ApprovalStatus.APPROVED,
            comments="Approved",
            conditions=[],
            approved_at=datetime.utcnow(),
        )
        _approvals["APR-12345678"] = approval

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[5].endpoint(
                change_request_id="CR-12345678",
                decision=ApprovalStatus.APPROVED,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_approvals_permission_denied(self):
        """Test listing approvals without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[5].endpoint(
                    change_request_id=None,
                    decision=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403


class TestCreateApproval:
    """Tests for POST /api/v1/change/approvals"""

    @pytest.mark.asyncio
    async def test_create_approval_success(self, sample_approval_request, sample_change_request, mock_admin_user, clear_in_memory_data):
        """Test successful creation of approval."""
        # Setup
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router.approve_request', return_value=None):
                with patch('api.change_advanced_router.record_audit', return_value=None):
                    # Execute
                    with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                        result = await router.routes[6].endpoint(
                            request=sample_approval_request,
                            current_user=mock_admin_user,
                        )

        # Assert
        assert result.change_request_id == "CR-12345678"
        assert result.decision == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_create_approval_rejected(self, sample_approval_request, sample_change_request, mock_admin_user, clear_in_memory_data):
        """Test creating approval with rejection."""
        # Setup
        sample_approval_request.decision = ApprovalStatus.REJECTED
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router.reject_request', return_value=None):
                with patch('api.change_advanced_router.record_audit', return_value=None):
                    # Execute
                    with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                        result = await router.routes[6].endpoint(
                            request=sample_approval_request,
                            current_user=mock_admin_user,
                        )

        # Assert
        assert result.decision == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_create_approval_request_not_found(self, sample_approval_request, mock_admin_user):
        """Test creating approval for non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[6].endpoint(
                        request=sample_approval_request,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_approval_permission_denied(self, sample_approval_request, mock_operator_user):
        """Test creating approval without admin permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[6].endpoint(
                    request=sample_approval_request,
                    current_user=mock_operator_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Schedules Endpoints
# ============================================================================

class TestListSchedules:
    """Tests for GET /api/v1/change/schedules"""

    @pytest.mark.asyncio
    async def test_list_schedules_success(self, mock_admin_user, clear_in_memory_data):
        """Test successful listing of schedules."""
        # Setup
        schedule = ScheduleResponse(
            id="SCH-12345678",
            change_request_id="CR-12345678",
            scheduled_start=datetime.utcnow() + timedelta(days=1),
            scheduled_end=datetime.utcnow() + timedelta(days=1, hours=2),
            maintenance_window="MW-001",
            timezone="UTC",
            status=ScheduleStatus.SCHEDULED,
            assigned_team=[],
            prerequisites=[],
            dependencies=[],
        )
        _schedules["SCH-12345678"] = schedule

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[7].endpoint(
                change_request_id=None,
                status=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].id == "SCH-12345678"

    @pytest.mark.asyncio
    async def test_list_schedules_with_filters(self, mock_admin_user, clear_in_memory_data):
        """Test listing schedules with filters."""
        # Setup
        schedule = ScheduleResponse(
            id="SCH-12345678",
            change_request_id="CR-12345678",
            scheduled_start=datetime.utcnow() + timedelta(days=1),
            scheduled_end=datetime.utcnow() + timedelta(days=1, hours=2),
            maintenance_window="MW-001",
            timezone="UTC",
            status=ScheduleStatus.SCHEDULED,
            assigned_team=[],
            prerequisites=[],
            dependencies=[],
        )
        _schedules["SCH-12345678"] = schedule

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[7].endpoint(
                change_request_id="CR-12345678",
                status=ScheduleStatus.SCHEDULED,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_schedules_permission_denied(self):
        """Test listing schedules without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[7].endpoint(
                    change_request_id=None,
                    status=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403


class TestCreateSchedule:
    """Tests for POST /api/v1/change/schedules"""

    @pytest.mark.asyncio
    async def test_create_schedule_success(self, sample_schedule_request, sample_change_request, mock_admin_user, clear_in_memory_data):
        """Test successful creation of schedule."""
        # Setup
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[8].endpoint(
                        request=sample_schedule_request,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result.change_request_id == "CR-12345678"
        assert result.status == ScheduleStatus.SCHEDULED

    @pytest.mark.asyncio
    async def test_create_schedule_invalid_time(self, sample_schedule_request, sample_change_request, mock_admin_user):
        """Test creating schedule with invalid time range."""
        # Setup
        sample_schedule_request.scheduled_end = sample_schedule_request.scheduled_start - timedelta(hours=1)
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[8].endpoint(
                        request=sample_schedule_request,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_schedule_request_not_found(self, sample_schedule_request, mock_admin_user):
        """Test creating schedule for non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[8].endpoint(
                        request=sample_schedule_request,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_schedule_permission_denied(self, sample_schedule_request, mock_business_user):
        """Test creating schedule without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[8].endpoint(
                    request=sample_schedule_request,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403


class TestUpdateSchedule:
    """Tests for PATCH /api/v1/change/schedules/{id}"""

    @pytest.mark.asyncio
    async def test_update_schedule_success(self, mock_admin_user, clear_in_memory_data):
        """Test successful update of schedule."""
        # Setup
        schedule = ScheduleResponse(
            id="SCH-12345678",
            change_request_id="CR-12345678",
            scheduled_start=datetime.utcnow() + timedelta(days=1),
            scheduled_end=datetime.utcnow() + timedelta(days=1, hours=2),
            maintenance_window="MW-001",
            timezone="UTC",
            status=ScheduleStatus.SCHEDULED,
            assigned_team=[],
            prerequisites=[],
            dependencies=[],
        )
        _schedules["SCH-12345678"] = schedule

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[9].endpoint(
                schedule_id="SCH-12345678",
                status=ScheduleStatus.IN_PROGRESS,
                actual_start=datetime.utcnow(),
                actual_end=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert result.status == ScheduleStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self, mock_admin_user):
        """Test updating non-existent schedule."""
        # Execute & Assert
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[9].endpoint(
                    schedule_id="SCH-NOTFOUND",
                    status=ScheduleStatus.IN_PROGRESS,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_schedule_permission_denied(self, mock_business_user):
        """Test updating schedule without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[9].endpoint(
                    schedule_id="SCH-12345678",
                    status=ScheduleStatus.IN_PROGRESS,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Impact Analysis Endpoints
# ============================================================================

class TestPerformImpactAnalysis:
    """Tests for POST /api/v1/change/impact-analysis"""

    @pytest.mark.asyncio
    async def test_impact_analysis_success(self, sample_impact_analysis_request, sample_change_request, mock_admin_user):
        """Test successful impact analysis."""
        # Setup
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[10].endpoint(
                    request=sample_impact_analysis_request,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.change_request_id == "CR-12345678"
        assert result.overall_impact == ImpactLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_impact_analysis_high_risk(self, sample_change_request, mock_admin_user):
        """Test impact analysis with high risk."""
        # Setup
        request = ImpactAnalysisRequest(
            change_request_id="CR-12345678",
            affected_services=["database"],
            change_description="Critical database update",
            risk_level=RiskLevel.HIGH,
        )
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[10].endpoint(
                    request=request,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.overall_impact == ImpactLevel.HIGH

    @pytest.mark.asyncio
    async def test_impact_analysis_low_risk(self, sample_change_request, mock_admin_user):
        """Test impact analysis with low risk."""
        # Setup
        request = ImpactAnalysisRequest(
            change_request_id="CR-12345678",
            affected_services=["frontend"],
            change_description="Minor UI update",
            risk_level=RiskLevel.LOW,
        )
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            # Execute
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                result = await router.routes[10].endpoint(
                    request=request,
                    current_user=mock_admin_user,
                )

        # Assert
        assert result.overall_impact == ImpactLevel.LOW

    @pytest.mark.asyncio
    async def test_impact_analysis_request_not_found(self, sample_impact_analysis_request, mock_admin_user):
        """Test impact analysis for non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[10].endpoint(
                        request=sample_impact_analysis_request,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_impact_analysis_permission_denied(self, sample_impact_analysis_request, mock_business_user):
        """Test impact analysis without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[10].endpoint(
                    request=sample_impact_analysis_request,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Rollback Plans Endpoints
# ============================================================================

class TestListRollbackPlans:
    """Tests for GET /api/v1/change/rollback-plans"""

    @pytest.mark.asyncio
    async def test_list_rollback_plans_success(self, mock_admin_user, clear_in_memory_data):
        """Test successful listing of rollback plans."""
        # Setup
        plan = RollbackPlanResponse(
            id="RBP-12345678",
            change_request_id="CR-12345678",
            rollback_steps=["Step 1", "Step 2"],
            estimated_rollback_time=30,
            data_consistency_checks=[],
            rollback_triggers=[],
            validation_after_rollback=[],
            complexity="low",
            success_probability=0.95,
        )
        _rollback_plans["RBP-12345678"] = plan

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[11].endpoint(
                change_request_id=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].id == "RBP-12345678"

    @pytest.mark.asyncio
    async def test_list_rollback_plans_with_filter(self, mock_admin_user, clear_in_memory_data):
        """Test listing rollback plans with filter."""
        # Setup
        plan = RollbackPlanResponse(
            id="RBP-12345678",
            change_request_id="CR-12345678",
            rollback_steps=["Step 1", "Step 2"],
            estimated_rollback_time=30,
            data_consistency_checks=[],
            rollback_triggers=[],
            validation_after_rollback=[],
            complexity="low",
            success_probability=0.95,
        )
        _rollback_plans["RBP-12345678"] = plan

        # Execute
        with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[11].endpoint(
                change_request_id="CR-12345678",
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_rollback_plans_permission_denied(self):
        """Test listing rollback plans without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[11].endpoint(
                    change_request_id=None,
                    current_user=None,
                )
            assert exc_info.value.status_code == 403


class TestCreateRollbackPlan:
    """Tests for POST /api/v1/change/rollback-plans"""

    @pytest.mark.asyncio
    async def test_create_rollback_plan_success(self, sample_rollback_plan_request, sample_change_request, mock_admin_user, clear_in_memory_data):
        """Test successful creation of rollback plan."""
        # Setup
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[12].endpoint(
                        request=sample_rollback_plan_request,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result.change_request_id == "CR-12345678"
        assert result.complexity == "medium"  # 3 steps = medium complexity

    @pytest.mark.asyncio
    async def test_create_rollback_plan_low_complexity(self, sample_change_request, mock_admin_user, clear_in_memory_data):
        """Test creating rollback plan with low complexity."""
        # Setup
        request = RollbackPlanRequest(
            change_request_id="CR-12345678",
            rollback_steps=["Step 1", "Step 2"],
            estimated_rollback_time=15,
            data_consistency_checks=[],
            rollback_triggers=[],
            validation_after_rollback=[],
        )
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[12].endpoint(
                        request=request,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result.complexity == "low"
        assert result.success_probability == 0.95

    @pytest.mark.asyncio
    async def test_create_rollback_plan_high_complexity(self, sample_change_request, mock_admin_user, clear_in_memory_data):
        """Test creating rollback plan with high complexity."""
        # Setup
        request = RollbackPlanRequest(
            change_request_id="CR-12345678",
            rollback_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6", "Step 7", "Step 8"],
            estimated_rollback_time=60,
            data_consistency_checks=[],
            rollback_triggers=[],
            validation_after_rollback=[],
        )
        with patch('api.change_advanced_router.get_request', return_value=sample_change_request):
            with patch('api.change_advanced_router._persist', return_value=None):
                # Execute
                with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                    result = await router.routes[12].endpoint(
                        request=request,
                        current_user=mock_admin_user,
                    )

        # Assert
        assert result.complexity == "high"
        assert result.success_probability == 0.75

    @pytest.mark.asyncio
    async def test_create_rollback_plan_request_not_found(self, sample_rollback_plan_request, mock_admin_user):
        """Test creating rollback plan for non-existent request."""
        # Setup
        from core.change_management_engine import ChangeManagementError
        with patch('api.change_advanced_router.get_request', side_effect=ChangeManagementError("Not found")):
            # Execute & Assert
            with patch('api.change_advanced_router.require_roles', return_value=mock_admin_user):
                with pytest.raises(HTTPException) as exc_info:
                    await router.routes[12].endpoint(
                        request=sample_rollback_plan_request,
                        current_user=mock_admin_user,
                    )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_rollback_plan_permission_denied(self, sample_rollback_plan_request, mock_business_user):
        """Test creating rollback plan without proper permissions."""
        # Setup
        with patch('api.change_advanced_router.require_roles', side_effect=HTTPException(status_code=403, detail="Forbidden")):
            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[12].endpoint(
                    request=sample_rollback_plan_request,
                    current_user=mock_business_user,
                )
            assert exc_info.value.status_code == 403


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions"""

    def test_generate_approval_id(self):
        """Test approval ID generation."""
        # Execute
        approval_id = _generate_approval_id()

        # Assert
        assert approval_id.startswith("APR-")
        assert len(approval_id) == 12  # APR- + 8 characters

    def test_generate_schedule_id(self):
        """Test schedule ID generation."""
        # Execute
        schedule_id = _generate_schedule_id()

        # Assert
        assert schedule_id.startswith("SCH-")
        assert len(schedule_id) == 12  # SCH- + 8 characters

    def test_generate_rollback_plan_id(self):
        """Test rollback plan ID generation."""
        # Execute
        plan_id = _generate_rollback_plan_id()

        # Assert
        assert plan_id.startswith("RBP-")
        assert len(plan_id) == 12  # RBP- + 8 characters
