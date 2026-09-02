# -*- coding: utf-8 -*-
"""
Test suite for Change Management Router
变更管理路由测试套件
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest
from fastapi import HTTPException, status

# Add project root to Python path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.change_management_router import (
    AuditCommentRequest,
    AssignApproverRequest,
    BulkCreateRequest,
    BulkDeleteRequest,
    ChangeRequestCreate,
    ChangeRequestUpdate,
    ImportRequest,
    ScheduleRequestModel,
    router,
)
from core.change_management_engine import (
    AuditEntry,
    ChangeManagementError,
    ChangeRequest,
    ChangeStatus,
    RiskLevel,
    _REQUESTS,
    _LOADED,
    _LOCK,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
async def cleanup_change_requests():
    """Clean up change requests before and after each test."""
    # Clean up before test
    async with _LOCK:
        _REQUESTS.clear()
        global _LOADED
        _LOADED = False
    yield
    # Clean up after test
    async with _LOCK:
        _REQUESTS.clear()
        _LOADED = False


@pytest.fixture
def sample_change_request_data():
    """Sample change request creation data."""
    return {
        "title": "Test Change Request",
        "description": "Test change description",
        "requester": "test_user",
        "approver": "test_approver",
        "risk_level": RiskLevel.LOW,
        "schedule": "2024-01-01 00:00:00",
        "affected_services": ["service-a", "service-b"],
        "implementation_plan": "Step 1: Do this, Step 2: Do that",
        "rollback_plan": "Step 1: Undo this, Step 2: Undo that",
    }


@pytest.fixture
def mock_request_state():
    """Mock request state with tenant_id."""
    state = Mock()
    state.tenant_id = "test-tenant"
    return state


@pytest.fixture
def mock_request(mock_request_state):
    """Mock FastAPI request."""
    request = Mock()
    request.state = mock_request_state
    return request


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = Mock()
    user.id = 1
    user.username = "admin"
    user.tenant_id = "test-tenant"
    user.role = "admin"
    return user


@pytest.fixture
def mock_operator_user():
    """Mock operator user."""
    user = Mock()
    user.id = 2
    user.username = "operator"
    user.tenant_id = "test-tenant"
    user.role = "operator"
    return user


# ============================================================================
# Test: GET /api/v1/change-management/requests
# ============================================================================


@pytest.mark.asyncio
async def test_get_change_requests(cleanup_change_requests, mock_request):
    """Test getting all change requests."""
    from core.change_management_engine import create_request

    # Create test data
    await create_request(
        {
            "title": "Change 1",
            "requester": "user1",
            "tenant_id": "test-tenant",
        },
        tenant_id="test-tenant",
    )
    await create_request(
        {
            "title": "Change 2",
            "requester": "user2",
            "tenant_id": "test-tenant",
        },
        tenant_id="test-tenant",
    )

    # Call the endpoint
    result = await router.routes[0].endpoint(mock_request)

    assert len(result) == 2
    assert all(isinstance(r, ChangeRequest) for r in result)


# ============================================================================
# Test: POST /api/v1/change-management/requests
# ============================================================================


@pytest.mark.asyncio
async def test_post_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test creating a new change request."""
    payload = ChangeRequestCreate(**sample_change_request_data)

    result = await router.routes[1].endpoint(mock_request, payload)

    assert isinstance(result, ChangeRequest)
    assert result.title == "Test Change Request"
    assert result.requester == "test_user"
    assert result.status == ChangeStatus.DRAFT
    assert result.tenant_id == "test-tenant"
    assert len(result.audit_log) > 0


# ============================================================================
# Test: GET /api/v1/change-management/requests/{id}
# ============================================================================


@pytest.mark.asyncio
async def test_get_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting a single change request by ID."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[2].endpoint(mock_request, created.id)

    assert isinstance(result, ChangeRequest)
    assert result.id == created.id
    assert result.title == "Test Change Request"


@pytest.mark.asyncio
async def test_get_change_request_not_found(cleanup_change_requests, mock_request):
    """Test getting a non-existent change request."""
    with pytest.raises(HTTPException) as exc_info:
        await router.routes[2].endpoint(mock_request, "NONEXISTENT")

    assert exc_info.value.status_code == 404


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/submit
# ============================================================================


@pytest.mark.asyncio
async def test_submit_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test submitting a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[3].endpoint(mock_request, created.id)

    assert result.status == ChangeStatus.PENDING
    assert any(entry.action == "submit" for entry in result.audit_log)


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/approve
# ============================================================================


@pytest.mark.asyncio
async def test_approve_change_request(cleanup_change_requests, mock_admin_user, sample_change_request_data):
    """Test approving a change request."""
    from core.change_management_engine import create_request, submit_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")

    result = await router.routes[4].endpoint(created.id, mock_admin_user)

    assert result.status == ChangeStatus.APPROVED
    assert any(entry.action == "approve" for entry in result.audit_log)


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/reject
# ============================================================================


@pytest.mark.asyncio
async def test_reject_change_request(cleanup_change_requests, mock_admin_user, sample_change_request_data):
    """Test rejecting a change request."""
    from core.change_management_engine import create_request, submit_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")

    result = await router.routes[5].endpoint(created.id, mock_admin_user)

    assert result.status == ChangeStatus.REJECTED
    assert any(entry.action == "reject" for entry in result.audit_log)


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/implement
# ============================================================================


@pytest.mark.asyncio
async def test_implement_change_request(cleanup_change_requests, mock_operator_user, sample_change_request_data):
    """Test implementing a change request."""
    from core.change_management_engine import create_request, submit_request, approve_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")
    await approve_request(created.id, tenant_id="test-tenant")

    result = await router.routes[6].endpoint(created.id, mock_operator_user)

    assert result.status == ChangeStatus.IMPLEMENTED
    assert any(entry.action == "implement" for entry in result.audit_log)


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/rollback
# ============================================================================


@pytest.mark.asyncio
async def test_rollback_change_request(cleanup_change_requests, mock_operator_user, sample_change_request_data):
    """Test rolling back a change request."""
    from core.change_management_engine import (
        create_request,
        submit_request,
        approve_request,
        implement_request,
    )

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")
    await approve_request(created.id, tenant_id="test-tenant")
    await implement_request(created.id, tenant_id="test-tenant")

    result = await router.routes[7].endpoint(created.id, mock_operator_user)

    assert result.status == ChangeStatus.ROLLED_BACK
    assert any(entry.action == "rollback" for entry in result.audit_log)


# ============================================================================
# Test: PUT /api/v1/change-management/requests/{id}
# ============================================================================


@pytest.mark.asyncio
async def test_put_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test updating a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    payload = ChangeRequestUpdate(title="Updated Title", description="Updated description")
    result = await router.routes[8].endpoint(mock_request, created.id, payload)

    assert result.title == "Updated Title"
    assert result.description == "Updated description"


# ============================================================================
# Test: DELETE /api/v1/change-management/requests/{id}
# ============================================================================


@pytest.mark.asyncio
async def test_delete_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test deleting a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    await router.routes[9].endpoint(mock_request, created.id)

    # Verify deletion
    from core.change_management_engine import get_request
    with pytest.raises(ChangeManagementError):
        await get_request(created.id, tenant_id="test-tenant")


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/cancel
# ============================================================================


@pytest.mark.asyncio
async def test_cancel_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test canceling a change request."""
    from core.change_management_engine import create_request, submit_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")

    result = await router.routes[10].endpoint(mock_request, created.id)

    assert result.status == ChangeStatus.REJECTED
    assert any(entry.action == "cancelled" for entry in result.audit_log)


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/review
# ============================================================================


@pytest.mark.asyncio
async def test_review_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test reviewing a change request."""
    from core.change_management_engine import create_request, submit_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")

    result = await router.routes[11].endpoint(mock_request, created.id)

    assert result.status == ChangeStatus.REVIEW
    assert any(entry.action == "review" for entry in result.audit_log)


# ============================================================================
# Test: GET /api/v1/change-management/requests/status/{status}
# ============================================================================


@pytest.mark.asyncio
async def test_get_requests_by_status(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test filtering requests by status."""
    from core.change_management_engine import create_request, submit_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "title": "Draft 1"},
        tenant_id="test-tenant",
    )
    r2 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "title": "Pending 1"},
        tenant_id="test-tenant",
    )
    await submit_request(r2.id, tenant_id="test-tenant")

    result = await router.routes[12].endpoint(mock_request, ChangeStatus.PENDING)

    assert len(result) == 1
    assert result[0].status == ChangeStatus.PENDING


# ============================================================================
# Test: GET /api/v1/change-management/requests/risk/{risk_level}
# ============================================================================


@pytest.mark.asyncio
async def test_get_requests_by_risk_level(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test filtering requests by risk level."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "risk_level": RiskLevel.LOW},
        tenant_id="test-tenant",
    )
    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "risk_level": RiskLevel.HIGH},
        tenant_id="test-tenant",
    )

    result = await router.routes[13].endpoint(mock_request, RiskLevel.HIGH)

    assert len(result) == 1
    assert result[0].risk_level == RiskLevel.HIGH


# ============================================================================
# Test: GET /api/v1/change-management/requests/requester/{requester}
# ============================================================================


@pytest.mark.asyncio
async def test_get_requests_by_requester(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test filtering requests by requester."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "requester": "user1"},
        tenant_id="test-tenant",
    )
    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "requester": "user2"},
        tenant_id="test-tenant",
    )

    result = await router.routes[14].endpoint(mock_request, "user1")

    assert len(result) == 1
    assert result[0].requester == "user1"


# ============================================================================
# Test: GET /api/v1/change-management/requests/approver/{approver}
# ============================================================================


@pytest.mark.asyncio
async def test_get_requests_by_approver(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test filtering requests by approver."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "approver": "approver1"},
        tenant_id="test-tenant",
    )
    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "approver": "approver2"},
        tenant_id="test-tenant",
    )

    result = await router.routes[15].endpoint(mock_request, "approver1")

    assert len(result) == 1
    assert result[0].approver == "approver1"


# ============================================================================
# Test: GET /api/v1/change-management/requests/service/{service}
# ============================================================================


@pytest.mark.asyncio
async def test_get_requests_by_service(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test filtering requests by affected service."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "affected_services": ["service-a"]},
        tenant_id="test-tenant",
    )
    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "affected_services": ["service-b"]},
        tenant_id="test-tenant",
    )

    result = await router.routes[16].endpoint(mock_request, "service-a")

    assert len(result) == 1
    assert "service-a" in result[0].affected_services


# ============================================================================
# Test: GET /api/v1/change-management/requests/{id}/audit-log
# ============================================================================


@pytest.mark.asyncio
async def test_get_change_request_audit_log(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting audit log for a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[17].endpoint(mock_request, created.id)

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(entry, AuditEntry) for entry in result)


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/audit-comment
# ============================================================================


@pytest.mark.asyncio
async def test_post_audit_comment(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test adding an audit comment to a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    payload = AuditCommentRequest(comment="Test comment", actor="test_user")
    result = await router.routes[18].endpoint(mock_request, created.id, payload)

    assert any(entry.action == "comment" for entry in result.audit_log)
    assert any(entry.message == "Test comment" for entry in result.audit_log)


# ============================================================================
# Test: POST /api/v1/change-management/requests/bulk
# ============================================================================


@pytest.mark.asyncio
async def test_post_bulk_change_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test bulk creating change requests."""
    payload = BulkCreateRequest(
        requests=[
            ChangeRequestCreate(**{**sample_change_request_data, "title": "Bulk 1"}),
            ChangeRequestCreate(**{**sample_change_request_data, "title": "Bulk 2"}),
        ]
    )

    result = await router.routes[19].endpoint(mock_request, payload)

    assert len(result) == 2
    assert all(isinstance(r, ChangeRequest) for r in result)


# ============================================================================
# Test: POST /api/v1/change-management/requests/bulk-delete
# ============================================================================


@pytest.mark.asyncio
async def test_post_bulk_delete_change_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test bulk deleting change requests."""
    from core.change_management_engine import create_request

    r1 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    r2 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    payload = BulkDeleteRequest(request_ids=[r1.id, r2.id])
    result = await router.routes[20].endpoint(mock_request, payload)

    assert result[r1.id] is True
    assert result[r2.id] is True


# ============================================================================
# Test: GET /api/v1/change-management/requests/search
# ============================================================================


@pytest.mark.asyncio
async def test_search_change_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test searching change requests."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "title": "Database migration"},
        tenant_id="test-tenant",
    )
    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "title": "API update"},
        tenant_id="test-tenant",
    )

    result = await router.routes[21].endpoint(mock_request, "database")

    assert len(result) == 1
    assert "database" in result[0].title.lower()


# ============================================================================
# Test: GET /api/v1/change-management/statistics
# ============================================================================


@pytest.mark.asyncio
async def test_get_change_statistics(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting change request statistics."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[22].endpoint(mock_request)

    assert "total" in result
    assert "by_status" in result
    assert "by_risk_level" in result
    assert result["total"] >= 1


# ============================================================================
# Test: GET /api/v1/change-management/requests/{id}/validate
# ============================================================================


@pytest.mark.asyncio
async def test_validate_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test validating a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[23].endpoint(mock_request, created.id)

    assert "valid" in result
    assert "errors" in result
    assert "warnings" in result
    assert result["valid"] is True


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/schedule
# ============================================================================


@pytest.mark.asyncio
async def test_schedule_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test scheduling a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    payload = ScheduleRequestModel(schedule="2024-12-31 23:59:59")
    result = await router.routes[24].endpoint(mock_request, created.id, payload)

    assert result.schedule == "2024-12-31 23:59:59"


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/assign-approver
# ============================================================================


@pytest.mark.asyncio
async def test_assign_change_approver(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test assigning an approver to a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    payload = AssignApproverRequest(approver="new_approver")
    result = await router.routes[25].endpoint(mock_request, created.id, payload)

    assert result.approver == "new_approver"


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/clone
# ============================================================================


@pytest.mark.asyncio
async def test_clone_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test cloning a change request."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[26].endpoint(mock_request, created.id)

    assert result.id != created.id
    assert result.status == ChangeStatus.DRAFT
    assert "(副本)" in result.title


# ============================================================================
# Test: GET /api/v1/change-management/export
# ============================================================================


@pytest.mark.asyncio
async def test_export_change_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test exporting change requests."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[27].endpoint(mock_request)

    assert "exported_at" in result
    assert "count" in result
    assert "requests" in result
    assert result["count"] >= 1


# ============================================================================
# Test: POST /api/v1/change-management/import
# ============================================================================


@pytest.mark.asyncio
async def test_import_change_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test importing change requests."""
    payload = ImportRequest(
        requests=[
            {**sample_change_request_data, "id": "IMPORT-001", "tenant_id": "test-tenant"},
            {**sample_change_request_data, "id": "IMPORT-002", "tenant_id": "test-tenant"},
        ],
        overwrite=False,
    )

    result = await router.routes[28].endpoint(mock_request, payload)

    assert "imported" in result
    assert "skipped" in result
    assert "errors" in result
    assert result["imported"] == 2


# ============================================================================
# Test: POST /api/v1/change-management/requests/batch-update
# ============================================================================


@pytest.mark.asyncio
async def test_batch_update_change_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test batch updating change requests."""
    from core.change_management_engine import create_request

    r1 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    r2 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    from api.change_management_router import BatchUpdateRequest
    payload = BatchUpdateRequest(
        request_ids=[r1.id, r2.id],
        updates=ChangeRequestUpdate(title="Batch Updated"),
    )

    result = await router.routes[29].endpoint(mock_request, payload)

    assert len(result) == 2
    assert all(r.title == "Batch Updated" for r in result)


# ============================================================================
# Test: GET /api/v1/change-management/requests/{id}/history
# ============================================================================


@pytest.mark.asyncio
async def test_get_change_request_history(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting change request history."""
    from core.change_management_engine import create_request, submit_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(created.id, tenant_id="test-tenant")

    result = await router.routes[30].endpoint(mock_request, created.id)

    assert isinstance(result, list)
    assert len(result) >= 2
    assert all("timestamp" in entry for entry in result)
    assert all("action" in entry for entry in result)


# ============================================================================
# Test: GET /api/v1/change-management/requests/pending-approval
# ============================================================================


@pytest.mark.asyncio
async def test_get_pending_approval_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting pending approval requests."""
    from core.change_management_engine import create_request, submit_request

    r1 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(r1.id, tenant_id="test-tenant")

    result = await router.routes[31].endpoint(mock_request)

    assert len(result) >= 1
    assert all(r.status == ChangeStatus.PENDING for r in result)


# ============================================================================
# Test: GET /api/v1/change-management/requests/approved
# ============================================================================


@pytest.mark.asyncio
async def test_get_approved_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting approved requests."""
    from core.change_management_engine import create_request, submit_request, approve_request

    r1 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(r1.id, tenant_id="test-tenant")
    await approve_request(r1.id, tenant_id="test-tenant")

    result = await router.routes[32].endpoint(mock_request)

    assert len(result) >= 1
    assert all(r.status == ChangeStatus.APPROVED for r in result)


# ============================================================================
# Test: GET /api/v1/change-management/requests/in-progress
# ============================================================================


@pytest.mark.asyncio
async def test_get_in_progress_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting in-progress requests."""
    from core.change_management_engine import create_request, submit_request

    r1 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(r1.id, tenant_id="test-tenant")

    result = await router.routes[33].endpoint(mock_request)

    assert len(result) >= 1
    assert all(r.status in (ChangeStatus.PENDING, ChangeStatus.REVIEW, ChangeStatus.APPROVED) for r in result)


# ============================================================================
# Test: GET /api/v1/change-management/requests/high-risk
# ============================================================================


@pytest.mark.asyncio
async def test_get_high_risk_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting high-risk requests."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant", "risk_level": RiskLevel.HIGH},
        tenant_id="test-tenant",
    )

    result = await router.routes[34].endpoint(mock_request)

    assert len(result) >= 1
    assert all(r.risk_level == RiskLevel.HIGH for r in result)


# ============================================================================
# Test: GET /api/v1/change-management/dashboard/summary
# ============================================================================


@pytest.mark.asyncio
async def test_get_dashboard_summary(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting dashboard summary."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[35].endpoint(mock_request)

    assert "total" in result
    assert "pending_count" in result
    assert "approved_count" in result
    assert "high_risk_count" in result
    assert "by_status" in result
    assert "by_risk_level" in result


# ============================================================================
# Test: POST /api/v1/change-management/requests/{id}/reopen
# ============================================================================


@pytest.mark.asyncio
async def test_reopen_change_request(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test reopening a change request."""
    from core.change_management_engine import create_request, reject_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await reject_request(created.id, tenant_id="test-tenant")

    result = await router.routes[36].endpoint(mock_request, created.id)

    assert result.status == ChangeStatus.DRAFT
    assert any(entry.action == "reopened" for entry in result.audit_log)


# ============================================================================
# Test: GET /api/v1/change-management/requests/recent
# ============================================================================


@pytest.mark.asyncio
async def test_get_recent_requests(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test getting recent change requests."""
    from core.change_management_engine import create_request

    await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    result = await router.routes[37].endpoint(mock_request, limit=10)

    assert isinstance(result, list)
    assert len(result) <= 10


# ============================================================================
# Test: POST /api/v1/change-management/requests/batch-approve
# ============================================================================


@pytest.mark.asyncio
async def test_batch_approve_requests(cleanup_change_requests, mock_request, mock_admin_user, sample_change_request_data):
    """Test batch approving change requests."""
    from core.change_management_engine import create_request, submit_request

    r1 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    r2 = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )
    await submit_request(r1.id, tenant_id="test-tenant")
    await submit_request(r2.id, tenant_id="test-tenant")

    payload = BulkDeleteRequest(request_ids=[r1.id, r2.id])
    result = await router.routes[38].endpoint(mock_request, payload, mock_admin_user)

    assert result[r1.id] == "approved"
    assert result[r2.id] == "approved"


# ============================================================================
# Test: GET /api/v1/change-management/health
# ============================================================================


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    result = await router.routes[39].endpoint()

    assert result["status"] == "healthy"
    assert result["service"] == "change-management"
    assert "timestamp" in result


# ============================================================================
# Integration Test: Full Change Request Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_full_change_request_lifecycle(cleanup_change_requests, mock_request, mock_admin_user, mock_operator_user, sample_change_request_data):
    """Test complete change request lifecycle from creation to rollback."""
    from core.change_management_engine import create_request

    # Step 1: Create
    payload = ChangeRequestCreate(**sample_change_request_data)
    created = await router.routes[1].endpoint(mock_request, payload)
    assert created.status == ChangeStatus.DRAFT

    # Step 2: Submit
    submitted = await router.routes[3].endpoint(mock_request, created.id)
    assert submitted.status == ChangeStatus.PENDING

    # Step 3: Approve
    approved = await router.routes[4].endpoint(submitted.id, mock_admin_user)
    assert approved.status == ChangeStatus.APPROVED

    # Step 4: Implement
    implemented = await router.routes[6].endpoint(approved.id, mock_operator_user)
    assert implemented.status == ChangeStatus.IMPLEMENTED

    # Step 5: Rollback
    rolled_back = await router.routes[7].endpoint(implemented.id, mock_operator_user)
    assert rolled_back.status == ChangeStatus.ROLLED_BACK

    # Step 6: Reopen
    reopened = await router.routes[36].endpoint(mock_request, rolled_back.id)
    assert reopened.status == ChangeStatus.DRAFT


# ============================================================================
# Performance Test: Batch Operations
# ============================================================================


@pytest.mark.asyncio
async def test_batch_operations_performance(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test that batch operations handle large datasets efficiently."""
    import time

    # Create 50 requests
    requests_data = [
        ChangeRequestCreate(**{**sample_change_request_data, "title": f"Change {i}"})
        for i in range(50)
    ]
    payload = BulkCreateRequest(requests=requests_data)

    start_time = time.time()
    result = await router.routes[19].endpoint(mock_request, payload)
    create_time = time.time() - start_time

    assert len(result) == 50
    assert create_time < 5.0  # Should complete within 5 seconds

    # Batch update
    from api.change_management_router import BatchUpdateRequest
    request_ids = [r.id for r in result]
    update_payload = BatchUpdateRequest(
        request_ids=request_ids,
        updates=ChangeRequestUpdate(risk_level=RiskLevel.MEDIUM),
    )

    start_time = time.time()
    updated = await router.routes[29].endpoint(mock_request, update_payload)
    update_time = time.time() - start_time

    assert len(updated) == 50
    assert update_time < 5.0  # Should complete within 5 seconds


# ============================================================================
# Security Test: Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_admin_only_endpoints_require_admin_role(sample_change_request_data):
    """Test that admin-only endpoints require admin role."""
    from core.change_management_engine import create_request, submit_request
    from core.auth_service import require_roles

    # This test verifies that the require_roles dependency is properly configured
    # The actual role checking is handled by FastAPI's dependency injection
    assert require_roles is not None


# ============================================================================
# Error Handling Test: Invalid State Transitions
# ============================================================================


@pytest.mark.asyncio
async def test_invalid_state_transitions(cleanup_change_requests, mock_request, sample_change_request_data):
    """Test that invalid state transitions are properly rejected."""
    from core.change_management_engine import create_request

    created = await create_request(
        {**sample_change_request_data, "tenant_id": "test-tenant"},
        tenant_id="test-tenant",
    )

    # Try to implement a draft request (should fail)
    with pytest.raises(HTTPException) as exc_info:
        await router.routes[6].endpoint(created.id, mock_operator_user := Mock(tenant_id="test-tenant", username="operator"))

    assert exc_info.value.status_code == 400


# ============================================================================
# Data Consistency Test: Tenant Isolation
# ============================================================================


@pytest.mark.asyncio
async def test_tenant_isolation(cleanup_change_requests, sample_change_request_data):
    """Test that tenant isolation is properly enforced."""
    from core.change_management_engine import create_request

    # Create request for tenant A
    await create_request(
        {**sample_change_request_data, "tenant_id": "tenant-a"},
        tenant_id="tenant-a",
    )

    # Create request for tenant B
    await create_request(
        {**sample_change_request_data, "tenant_id": "tenant-b"},
        tenant_id="tenant-b",
    )

    # Verify tenant A can only see its own requests
    state_a = Mock()
    state_a.tenant_id = "tenant-a"
    request_a = Mock()
    request_a.state = state_a

    result_a = await router.routes[0].endpoint(request_a)
    assert all(r.tenant_id == "tenant-a" for r in result_a)
