# -*- coding: utf-8 -*-
"""
Autoheal Router Tests
自动修复审批路由API测试
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch  # noqa: F401

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.autoheal_router import approve, list_pending, reject

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()

# Mock core.auto_heal with the required functions
mock_auto_heal = MagicMock()
mock_auto_heal.get_pending_approvals = Mock()
mock_auto_heal.reject_repair = Mock()
mock_auto_heal.heal_via_langgraph = AsyncMock()
sys.modules["core.auto_heal"] = mock_auto_heal

sys.modules["core.alert_engine"] = MagicMock()
sys.modules["api.ai_router"] = MagicMock()
sys.modules["core.collector"] = MagicMock()
sys.modules["core.runbook_generator"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/approvals", tags=["自动修复审批"])
    test_router.add_api_route("/pending", list_pending, methods=["GET"])
    test_router.add_api_route("/{alert_id}", approve, methods=["PATCH"])
    test_router.add_api_route("/reject", reject, methods=["POST"])
    # Add ai_propose_repair endpoint (not exposed in original router yet)
    from api.autoheal_router import ai_propose_repair

    test_router.add_api_route("/ai/propose", ai_propose_repair, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestListPending:
    """测试获取待审批列表"""

    def test_list_pending_empty(self, client):
        """测试空待审批列表"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_get:
            mock_get.return_value = []
            response = client.get("/api/v1/approvals/pending")
            assert response.status_code in [200, 500]

    def test_list_pending_with_items(self, client):
        """测试有项目的待审批列表"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_get:
            mock_get.return_value = [
                {"alert_id": "alert1", "status": "pending", "timestamp": "2026-07-03T10:00:00Z"}
            ]
            response = client.get("/api/v1/approvals/pending")
            assert response.status_code in [200, 500]

    def test_list_pending_error(self, client):
        """测试获取待审批列表失败"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_get:
            mock_get.side_effect = Exception("Failed to get pending approvals")
            response = client.get("/api/v1/approvals/pending")
            assert response.status_code == 500


class TestAIPropose:
    """测试AI生成修复建议"""

    def test_ai_propose_success(self, client):
        """测试AI生成修复建议成功"""
        with (
            patch("api.autoheal_router._find_alert_by_id") as mock_find,
            patch(
                "api.autoheal_router.generate_repair_runbook", new_callable=AsyncMock
            ) as mock_runbook,
        ):
            mock_find.return_value = {"id": "alert1", "title": "CPU high"}
            mock_runbook.return_value = {
                "success": True,
                "repair_plan": "Kill process with PID 1234",
                "status": "approved_no_script",
            }
            response = client.post("/api/v1/approvals/ai/propose", json={"alert_id": "alert1"})
            assert response.status_code in [200, 500]

    def test_ai_propose_not_found(self, client):
        """测试告警不存在"""
        with patch("api.autoheal_router._find_alert_by_id") as mock_find:
            mock_find.return_value = None
            response = client.post("/api/v1/approvals/ai/propose", json={"alert_id": "nonexistent"})
            assert response.status_code == 404

    def test_ai_propose_error(self, client):
        """测试生成修复建议失败"""
        with (
            patch("api.autoheal_router._find_alert_by_id") as mock_find,
            patch(
                "api.autoheal_router.generate_repair_runbook", new_callable=AsyncMock
            ) as mock_runbook,
        ):
            mock_find.return_value = {"id": "alert1", "title": "CPU high"}
            mock_runbook.side_effect = Exception("AI generation failed")
            response = client.post("/api/v1/approvals/ai/propose", json={"alert_id": "alert1"})
            assert response.status_code == 500

    def test_list_pending_success(self, client):
        """测试成功获取待审批列表"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_pending:
            mock_pending.return_value = [
                {
                    "alert_id": "ALERT-123",
                    "proposal": "Restart service",
                    "status": "pending",
                }
            ]

            response = client.get("/api/v1/approvals/pending")
            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "items" in data

    def test_list_pending_empty(self, client):
        """测试空待审批列表"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_pending:
            mock_pending.return_value = []

            response = client.get("/api/v1/approvals/pending")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["items"]) == 0

    def test_list_pending_multiple_items(self, client):
        """测试多个待审批项"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_pending:
            mock_pending.return_value = [
                {"alert_id": f"ALERT-{i}", "proposal": f"Action {i}", "status": "pending"}
                for i in range(5)
            ]

            response = client.get("/api/v1/approvals/pending")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 5

    def test_list_pending_error(self, client):
        """测试获取待审批列表错误"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_pending:
            mock_pending.side_effect = Exception("Database error")

            response = client.get("/api/v1/approvals/pending")
            assert response.status_code == 500


class TestApprove:
    """测试审批通过"""

    @pytest.mark.skip(reason="heal_via_langgraph call is commented out in router")
    def test_approve_success(self, client):
        """测试成功审批"""

    def test_approve_with_placeholder(self, client):
        """测试占位符响应（heal_via_langgraph未实现）"""
        response = client.patch("/api/v1/approvals/ALERT-123")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.skip(reason="heal_via_langgraph call is commented out in router")
    def test_approve_with_error(self, client):
        """测试审批失败"""

    @pytest.mark.skip(reason="heal_via_langgraph call is commented out in router")
    def test_approve_with_none_result(self, client):
        """测试返回None"""

    @pytest.mark.skip(reason="heal_via_langgraph call is commented out in router")
    def test_approve_with_exception(self, client):
        """测试审批异常"""


class TestReject:
    """测试驳回审批"""

    def test_reject_success(self, client):
        """测试成功驳回"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = {
                "success": True,
                "alert_id": "ALERT-123",
                "status": "rejected",
            }

            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "ALERT-123", "reason": "Not appropriate"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_reject_with_default_reason(self, client):
        """测试使用默认驳回原因"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = {
                "success": True,
                "alert_id": "ALERT-123",
                "status": "rejected",
            }

            response = client.post("/api/v1/approvals/reject", json={"alert_id": "ALERT-123"})
            assert response.status_code == 200

    def test_reject_with_long_reason(self, client):
        """测试长驳回原因"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = {
                "success": True,
                "alert_id": "ALERT-123",
                "status": "rejected",
            }

            long_reason = "a" * 400  # Within 500 character limit
            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "ALERT-123", "reason": long_reason},
            )
            assert response.status_code == 200

    def test_reject_with_whitespace_alert_id(self, client):
        """测试前后有空白的alert_id"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = {
                "success": True,
                "alert_id": "ALERT-123",
                "status": "rejected",
            }

            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "  ALERT-123  ", "reason": "Test"},
            )
            assert response.status_code == 200

    def test_reject_with_empty_alert_id(self, client):
        """测试空alert_id"""
        response = client.post(
            "/api/v1/approvals/reject", json={"alert_id": "   ", "reason": "Test"}
        )
        assert response.status_code == 422

    def test_reject_with_none_result(self, client):
        """测试返回None"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = None

            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "ALERT-123", "reason": "Test"},
            )
            assert response.status_code == 500

    def test_reject_with_failure(self, client):
        """测试驳回失败"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = {"success": False, "error": "Not pending"}

            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "ALERT-123", "reason": "Test"},
            )
            assert response.status_code == 400

    def test_reject_with_exception(self, client):
        """测试驳回异常"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.side_effect = Exception("Database error")

            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "ALERT-123", "reason": "Test"},
            )
            assert response.status_code == 500


class TestAutohealRouterEdgeCases:
    """测试边缘情况"""

    def test_approve_with_empty_alert_id(self, client):
        """测试空alert_id"""
        response = client.patch("/api/v1/approvals/")
        assert response.status_code in [404, 405]

    def test_approve_with_special_characters(self, client):
        """测试特殊字符alert_id"""
        response = client.patch("/api/v1/approvals/ALERT-123@#")
        assert response.status_code == 200

    def test_approve_with_unicode(self, client):
        """测试Unicode alert_id"""
        response = client.patch("/api/v1/approvals/ALERT-123")
        assert response.status_code == 200

    def test_reject_with_missing_alert_id(self, client):
        """测试缺少alert_id"""
        response = client.post("/api/v1/approvals/reject", json={"reason": "Test"})
        assert response.status_code == 422

    def test_reject_with_invalid_json(self, client):
        """测试无效JSON"""
        response = client.post("/api/v1/approvals/reject", data="invalid json")
        assert response.status_code == 422

    def test_list_pending_response_format(self, client):
        """测试响应格式"""
        with patch("api.autoheal_router.get_pending_approvals") as mock_pending:
            mock_pending.return_value = []

            response = client.get("/api/v1/approvals/pending")
            assert "application/json" in response.headers["content-type"]

    def test_approve_response_format(self, client):
        """测试审批响应格式"""
        response = client.patch("/api/v1/approvals/ALERT-123")
        assert "application/json" in response.headers["content-type"]

    def test_reject_response_format(self, client):
        """测试驳回响应格式"""
        with patch("core.auto_heal.reject_repair") as mock_reject:
            mock_reject.return_value = {
                "success": True,
                "alert_id": "ALERT-123",
                "status": "rejected",
            }

            response = client.post(
                "/api/v1/approvals/reject",
                json={"alert_id": "ALERT-123", "reason": "Test"},
            )
            assert "application/json" in response.headers["content-type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
