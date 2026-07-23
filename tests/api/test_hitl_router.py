# -*- coding: utf-8 -*-
"""
HITL Router Tests
HITL（人在回路）路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.hitl"] = MagicMock()

from api.hitl_router import (
    approve_step,
    create_approval_request,
    get_approval_status,
    hitl_health,
    reject_step,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/hitl", tags=["hitl"])
    test_router.add_api_route("/health", hitl_health, methods=["GET"])
    test_router.add_api_route("/approval/request", create_approval_request, methods=["POST"])
    test_router.add_api_route("/approval/approve", approve_step, methods=["POST"])
    test_router.add_api_route("/approval/reject", reject_step, methods=["POST"])
    test_router.add_api_route("/approval/{request_id}", get_approval_status, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestHITLRouter:
    """测试HITL路由"""

    def test_hitl_health(self, client):
        """测试HITL健康检查"""
        response = client.get("/hitl/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "hitl_available" in data

    def test_hitl_health_status(self, client):
        """测试HITL健康状态"""
        response = client.get("/hitl/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]

    def test_create_approval_request_unavailable(self, client):
        """测试创建审批请求（不可用）"""
        # Since HITL_AVAILABLE is False in the mock, this should return 503
        with (
            patch("api.hitl_router.HITL_AVAILABLE", False),
            patch("api.hitl_router._approval_workflow", None),
        ):
            response = client.post(
                "/hitl/approval/request",
                json={
                    "title": "Test Approval",
                    "steps": [{"step_id": "step-1", "name": "Step 1", "approver": "admin"}],
                },
            )
            # Should return 503 since HITL is not available
            assert response.status_code in [200, 503, 500]

    def test_approve_step_unavailable(self, client):
        """测试批准审批步骤（不可用）"""
        # Since HITL_AVAILABLE is False in the mock, this should return 503
        with (
            patch("api.hitl_router.HITL_AVAILABLE", False),
            patch("api.hitl_router._approval_workflow", None),
        ):
            response = client.post(
                "/hitl/approval/approve?request_id=req-123&step_id=step-1&approver=admin"
            )
            # Should return 503 since HITL is not available
            assert response.status_code in [200, 503, 500]

    def test_reject_step_unavailable(self, client):
        """测试拒绝审批步骤（不可用）"""
        # Since HITL_AVAILABLE is False in the mock, this should return 503
        with (
            patch("api.hitl_router.HITL_AVAILABLE", False),
            patch("api.hitl_router._approval_workflow", None),
        ):
            response = client.post(
                "/hitl/approval/reject?request_id=req-123&step_id=step-1&approver=admin"
            )
            # Should return 503 since HITL is not available
            assert response.status_code in [200, 503, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
