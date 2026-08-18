# -*- coding: utf-8 -*-
"""Coverage tests for change_management_router.py to reach 90%+ coverage.

This file uses direct imports and mocking to test the change_management_router module
without requiring full database setup.
"""

import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = [pytest.mark.api]


def _raise(exc):
    """Helper to raise an exception."""
    def _inner(*args, **kwargs):
        raise exc
    return _inner


@pytest.fixture
def mock_change_request():
    """Mock ChangeRequest object."""
    return SimpleNamespace(
        id="cr-1",
        title="Test Change",
        description="Test description",
        requester="user1",
        approver="admin",
        risk_level="low",
        schedule="2024-01-01",
        affected_services=["service1"],
        implementation_plan="Plan A",
        rollback_plan="Rollback A",
        status="draft",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


@pytest.fixture
def mock_dependencies(mock_change_request):
    """Mock all core dependencies for change_management_router."""
    with patch("api.change_management_router.list_requests") as mock_list, \
         patch("api.change_management_router.create_request") as mock_create, \
         patch("api.change_management_router.get_request") as mock_get, \
         patch("api.change_management_router.submit_request") as mock_submit, \
         patch("api.change_management_router.approve_request") as mock_approve, \
         patch("api.change_management_router.reject_request") as mock_reject, \
         patch("api.change_management_router.implement_request") as mock_implement, \
         patch("api.change_management_router.rollback_request") as mock_rollback, \
         patch("api.change_management_router.record_audit") as mock_audit:
        
        # Setup default mock returns
        mock_list.return_value = [mock_change_request]
        mock_create.return_value = mock_change_request
        mock_get.return_value = mock_change_request
        mock_submit.return_value = mock_change_request
        mock_approve.return_value = mock_change_request
        mock_reject.return_value = mock_change_request
        mock_implement.return_value = mock_change_request
        mock_rollback.return_value = mock_change_request
        
        yield {
            "list": mock_list,
            "create": mock_create,
            "get": mock_get,
            "submit": mock_submit,
            "approve": mock_approve,
            "reject": mock_reject,
            "implement": mock_implement,
            "rollback": mock_rollback,
            "audit": mock_audit,
        }


@pytest.fixture
def mock_request():
    """Mock FastAPI Request object."""
    request = MagicMock()
    request.state.tenant_id = "tenant-1"
    return request


def test_get_change_requests_success(mock_dependencies, mock_request):
    """Test successful get_change_requests endpoint (lines 45-53)."""
    from api.change_management_router import get_change_requests
    
    result = asyncio.run(get_change_requests(mock_request))
    
    assert isinstance(result, list)
    assert len(result) == 1
    mock_dependencies["list"].assert_called_once_with(tenant_id="tenant-1")


def test_get_change_requests_default_tenant(mock_dependencies):
    """Test get_change_requests with default tenant_id (line 49)."""
    from api.change_management_router import get_change_requests
    
    request = MagicMock()
    # No tenant_id in state, should use "default"
    del request.state.tenant_id
    
    result = asyncio.run(get_change_requests(request))
    
    assert isinstance(result, list)
    mock_dependencies["list"].assert_called_once_with(tenant_id="default")


def test_get_change_requests_exception_handling(mock_dependencies, mock_request):
    """Test get_change_requests exception handling (lines 51-53)."""
    from api.change_management_router import get_change_requests
    from fastapi import HTTPException
    
    mock_dependencies["list"].side_effect = Exception("Database error")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_change_requests(mock_request))
    
    assert exc_info.value.status_code == 500
    assert "获取变更请求列表失败" in str(exc_info.value.detail)


def test_post_change_request_success(mock_dependencies, mock_request, mock_change_request):
    """Test successful post_change_request endpoint (lines 56-71)."""
    from api.change_management_router import post_change_request, ChangeRequestCreate
    
    payload = ChangeRequestCreate(
        title="Test Change",
        requester="user1",
        description="Test description",
        risk_level="low",
    )
    
    result = asyncio.run(post_change_request(mock_request, payload))
    
    assert result.id == "cr-1"
    mock_dependencies["create"].assert_called_once()


def test_post_change_request_change_management_error(mock_dependencies, mock_request):
    """Test post_change_request with ChangeManagementError (lines 67-68)."""
    from api.change_management_router import post_change_request, ChangeRequestCreate
    from core.change_management_engine import ChangeManagementError
    from fastapi import HTTPException
    
    mock_dependencies["create"].side_effect = ChangeManagementError("Invalid request")
    
    payload = ChangeRequestCreate(title="Test", requester="user1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(post_change_request(mock_request, payload))
    
    assert exc_info.value.status_code == 400
    assert "Invalid request" in str(exc_info.value.detail)


def test_post_change_request_exception_handling(mock_dependencies, mock_request):
    """Test post_change_request general exception handling (lines 69-71)."""
    from api.change_management_router import post_change_request, ChangeRequestCreate
    from fastapi import HTTPException
    
    mock_dependencies["create"].side_effect = Exception("Unexpected error")
    
    payload = ChangeRequestCreate(title="Test", requester="user1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(post_change_request(mock_request, payload))
    
    assert exc_info.value.status_code == 500
    assert "创建变更请求失败" in str(exc_info.value.detail)


def test_get_change_request_success(mock_dependencies, mock_request):
    """Test successful get_change_request endpoint (lines 74-84)."""
    from api.change_management_router import get_change_request
    
    result = asyncio.run(get_change_request(mock_request, "cr-1"))
    
    assert result.id == "cr-1"
    mock_dependencies["get"].assert_called_once_with("cr-1", tenant_id="tenant-1")


def test_get_change_request_not_found_change_management_error(mock_dependencies, mock_request):
    """Test get_change_request with ChangeManagementError (lines 80-81)."""
    from api.change_management_router import get_change_request
    from core.change_management_engine import ChangeManagementError
    from fastapi import HTTPException
    
    mock_dependencies["get"].side_effect = ChangeManagementError("Request not found")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_change_request(mock_request, "cr-1"))
    
    assert exc_info.value.status_code == 404
    assert "Request not found" in str(exc_info.value.detail)


def test_get_change_request_permission_error(mock_dependencies, mock_request):
    """Test get_change_request with PermissionError (lines 80-81)."""
    from api.change_management_router import get_change_request
    from fastapi import HTTPException
    
    mock_dependencies["get"].side_effect = PermissionError("Access denied")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_change_request(mock_request, "cr-1"))
    
    assert exc_info.value.status_code == 404
    assert "Access denied" in str(exc_info.value.detail)


def test_get_change_request_exception_handling(mock_dependencies, mock_request):
    """Test get_change_request general exception handling (lines 82-84)."""
    from api.change_management_router import get_change_request
    from fastapi import HTTPException
    
    mock_dependencies["get"].side_effect = Exception("Database error")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_change_request(mock_request, "cr-1"))
    
    assert exc_info.value.status_code == 500
    assert "获取变更请求失败" in str(exc_info.value.detail)


def test_submit_change_request_success(mock_dependencies, mock_request):
    """Test successful submit_change_request endpoint (lines 87-101)."""
    from api.change_management_router import submit_change_request
    
    result = asyncio.run(submit_change_request(mock_request, "cr-1"))
    
    assert result.id == "cr-1"
    mock_dependencies["submit"].assert_called_once_with("cr-1", tenant_id="tenant-1")


def test_submit_change_request_change_management_error(mock_dependencies, mock_request):
    """Test submit_change_request with ChangeManagementError (lines 97-98)."""
    from api.change_management_router import submit_change_request
    from core.change_management_engine import ChangeManagementError
    from fastapi import HTTPException
    
    mock_dependencies["submit"].side_effect = ChangeManagementError("Cannot submit")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(submit_change_request(mock_request, "cr-1"))
    
    assert exc_info.value.status_code == 400
    assert "Cannot submit" in str(exc_info.value.detail)


def test_submit_change_request_exception_handling(mock_dependencies, mock_request):
    """Test submit_change_request general exception handling (lines 99-101)."""
    from api.change_management_router import submit_change_request
    from fastapi import HTTPException
    
    mock_dependencies["submit"].side_effect = Exception("Network error")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(submit_change_request(mock_request, "cr-1"))
    
    assert exc_info.value.status_code == 500
    assert "提交变更请求失败" in str(exc_info.value.detail)


def test_approve_change_request_success(mock_dependencies):
    """Test successful approve_change_request endpoint (lines 104-133)."""
    from api.change_management_router import approve_change_request
    from core.auth_db import User
    
    mock_user = User(
        id="user-1",
        username="admin",
        tenant_id="tenant-1",
    )
    
    result = asyncio.run(approve_change_request("cr-1", mock_user))
    
    assert result.id == "cr-1"
    mock_dependencies["approve"].assert_called_once_with("cr-1", tenant_id="tenant-1")
    mock_dependencies["audit"].assert_called_once()
    
    # Verify audit call parameters
    audit_call = mock_dependencies["audit"].call_args
    assert audit_call.kwargs["host"] == "cr-1"
    assert audit_call.kwargs["command"] == "CHANGE_APPROVE"
    assert audit_call.kwargs["risk_level"] == "high"
    assert audit_call.kwargs["result"] == "approved"


def test_approve_change_request_change_management_error(mock_dependencies):
    """Test approve_change_request with ChangeManagementError (lines 129-130)."""
    from api.change_management_router import approve_change_request
    from core.change_management_engine import ChangeManagementError
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["approve"].side_effect = ChangeManagementError("Cannot approve")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(approve_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 400
    assert "Cannot approve" in str(exc_info.value.detail)


def test_approve_change_request_exception_handling(mock_dependencies):
    """Test approve_change_request general exception handling (lines 131-133)."""
    from api.change_management_router import approve_change_request
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["approve"].side_effect = Exception("System error")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(approve_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 500
    assert "审批变更请求失败" in str(exc_info.value.detail)


def test_approve_change_request_user_without_id(mock_dependencies):
    """Test approve_change_request with user without id (line 123)."""
    from api.change_management_router import approve_change_request
    from core.auth_db import User
    
    # Mock user without id
    mock_user = User(
        id=None,
        username="admin",
        tenant_id="tenant-1",
    )
    
    result = asyncio.run(approve_change_request("cr-1", mock_user))
    
    assert result.id == "cr-1"
    audit_call = mock_dependencies["audit"].call_args
    assert audit_call.kwargs["user_id"] is None


def test_approve_change_request_user_without_tenant_id(mock_dependencies):
    """Test approve_change_request with user without tenant_id (lines 124-126)."""
    from api.change_management_router import approve_change_request
    from core.auth_db import User
    
    # Mock user without tenant_id
    mock_user = User(
        id="user-1",
        username="admin",
        tenant_id=None,
    )
    
    result = asyncio.run(approve_change_request("cr-1", mock_user))
    
    assert result.id == "cr-1"
    audit_call = mock_dependencies["audit"].call_args
    assert audit_call.kwargs["tenant_id"] is None


def test_reject_change_request_success(mock_dependencies):
    """Test successful reject_change_request endpoint (lines 136-165)."""
    from api.change_management_router import reject_change_request
    from core.auth_db import User
    
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    result = asyncio.run(reject_change_request("cr-1", mock_user))
    
    assert result.id == "cr-1"
    mock_dependencies["reject"].assert_called_once_with("cr-1", tenant_id="tenant-1")
    mock_dependencies["audit"].assert_called_once()
    
    # Verify audit call parameters
    audit_call = mock_dependencies["audit"].call_args
    assert audit_call.kwargs["host"] == "cr-1"
    assert audit_call.kwargs["command"] == "CHANGE_REJECT"
    assert audit_call.kwargs["risk_level"] == "high"
    assert audit_call.kwargs["result"] == "rejected"


def test_reject_change_request_change_management_error(mock_dependencies):
    """Test reject_change_request with ChangeManagementError (lines 161-162)."""
    from api.change_management_router import reject_change_request
    from core.change_management_engine import ChangeManagementError
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["reject"].side_effect = ChangeManagementError("Cannot reject")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(reject_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 400
    assert "Cannot reject" in str(exc_info.value.detail)


def test_reject_change_request_exception_handling(mock_dependencies):
    """Test reject_change_request general exception handling (lines 163-165)."""
    from api.change_management_router import reject_change_request
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["reject"].side_effect = Exception("System error")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(reject_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 500
    assert "拒绝变更请求失败" in str(exc_info.value.detail)


def test_implement_change_request_success(mock_dependencies):
    """Test successful implement_change_request endpoint (lines 168-197)."""
    from api.change_management_router import implement_change_request
    from core.auth_db import User
    
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    result = asyncio.run(implement_change_request("cr-1", mock_user))
    
    assert result.id == "cr-1"
    mock_dependencies["implement"].assert_called_once_with("cr-1", tenant_id="tenant-1")
    mock_dependencies["audit"].assert_called_once()
    
    # Verify audit call parameters
    audit_call = mock_dependencies["audit"].call_args
    assert audit_call.kwargs["host"] == "cr-1"
    assert audit_call.kwargs["command"] == "CHANGE_IMPLEMENT"
    assert audit_call.kwargs["risk_level"] == "critical"
    assert audit_call.kwargs["result"] == "implemented"


def test_implement_change_request_change_management_error(mock_dependencies):
    """Test implement_change_request with ChangeManagementError (lines 193-194)."""
    from api.change_management_router import implement_change_request
    from core.change_management_engine import ChangeManagementError
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["implement"].side_effect = ChangeManagementError("Cannot implement")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(implement_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 400
    assert "Cannot implement" in str(exc_info.value.detail)


def test_implement_change_request_exception_handling(mock_dependencies):
    """Test implement_change_request general exception handling (lines 195-197)."""
    from api.change_management_router import implement_change_request
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["implement"].side_effect = Exception("System error")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(implement_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 500
    assert "实施变更请求失败" in str(exc_info.value.detail)


def test_rollback_change_request_success(mock_dependencies):
    """Test successful rollback_change_request endpoint (lines 200-229)."""
    from api.change_management_router import rollback_change_request
    from core.auth_db import User
    
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    result = asyncio.run(rollback_change_request("cr-1", mock_user))
    
    assert result.id == "cr-1"
    mock_dependencies["rollback"].assert_called_once_with("cr-1", tenant_id="tenant-1")
    mock_dependencies["audit"].assert_called_once()
    
    # Verify audit call parameters
    audit_call = mock_dependencies["audit"].call_args
    assert audit_call.kwargs["host"] == "cr-1"
    assert audit_call.kwargs["command"] == "CHANGE_ROLLBACK"
    assert audit_call.kwargs["risk_level"] == "critical"
    assert audit_call.kwargs["result"] == "rolled_back"


def test_rollback_change_request_change_management_error(mock_dependencies):
    """Test rollback_change_request with ChangeManagementError (lines 225-226)."""
    from api.change_management_router import rollback_change_request
    from core.change_management_engine import ChangeManagementError
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["rollback"].side_effect = ChangeManagementError("Cannot rollback")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(rollback_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 400
    assert "Cannot rollback" in str(exc_info.value.detail)


def test_rollback_change_request_exception_handling(mock_dependencies):
    """Test rollback_change_request general exception handling (lines 227-229)."""
    from api.change_management_router import rollback_change_request
    from core.auth_db import User
    from fastapi import HTTPException
    
    mock_dependencies["rollback"].side_effect = Exception("System error")
    mock_user = User(id="user-1", username="admin", tenant_id="tenant-1")
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(rollback_change_request("cr-1", mock_user))
    
    assert exc_info.value.status_code == 500
    assert "回滚变更请求失败" in str(exc_info.value.detail)


# Original smoke tests for backward compatibility
_CASES = [
    ("GET", "/api/v1/change-management/requests", None, None, {200, 500}),
    ("POST", "/api/v1/change-management/requests", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/change-management/requests/cr-1", None, None, {200, 404, 500}),
    ("POST", "/api/v1/change-management/requests/cr-1/submit", {}, None, {200, 400, 422, 404, 500}),
    (
        "POST",
        "/api/v1/change-management/requests/cr-1/approve",
        {},
        None,
        {200, 400, 422, 404, 500},
    ),
    ("POST", "/api/v1/change-management/requests/cr-1/reject", {}, None, {200, 400, 422, 404, 500}),
    (
        "POST",
        "/api/v1/change-management/requests/cr-1/implement",
        {},
        None,
        {200, 400, 422, 404, 500},
    ),
    (
        "POST",
        "/api/v1/change-management/requests/cr-1/rollback",
        {},
        None,
        {200, 400, 422, 404, 500},
    ),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_change_management_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B17 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
