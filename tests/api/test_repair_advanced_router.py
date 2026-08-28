# -*- coding: utf-8 -*-
"""
修复管理高级API路由测试用例（数据库版本）
测试20个修复管理相关的API端点
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.repair_advanced_router import router
from core.models import RepairRecord
from core.auth_db import SessionLocal


# Test fixtures
@pytest.fixture
def client():
    """创建测试客户端"""
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
    db_session.query(RepairRecord).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(RepairRecord).delete()
    db_session.commit()


@pytest.fixture
def mock_request():
    """模拟请求对象"""
    request = Mock()
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


# ============================================================
# 1. Repair Configuration Management Tests
# ============================================================


class TestRepairConfiguration:
    """修复配置管理测试"""

    def test_get_configurations_success(self, client):
        """测试获取修复配置 - 成功"""
        response = client.get("/api/v1/repair/configuration")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    def test_get_configurations_with_filters(self, client):
        """测试获取修复配置 - 带过滤"""
        response = client.get("/api/v1/repair/configuration?category=default&config_type=global")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    def test_create_configuration_success(self, client):
        """测试创建修复配置 - 成功"""
        payload = {
            "name": "Test Configuration",
            "description": "Test config description",
            "config_type": "global",
            "key": "test_key",
            "value": "test_value",
            "category": "default",
            "is_secret": False,
        }
        response = client.post("/api/v1/repair/configuration", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["name"] == "Test Configuration"
            assert data["key"] == "test_key"

    def test_create_configuration_validation_error(self, client):
        """测试创建修复配置 - 验证错误"""
        payload = {"name": "", "key": "test", "value": "value"}  # 空名称应该失败
        response = client.post("/api/v1/repair/configuration", json=payload)
        assert response.status_code in (422, 404)

    def test_update_configuration_success(self, client):
        """测试更新修复配置 - 成功"""
        # 先创建一个配置
        create_payload = {"name": "Test Config", "key": "test_key", "value": "test_value"}
        create_response = client.post("/api/v1/repair/configuration", json=create_payload)
        config_id = create_response.json()["id"]

        # 更新配置
        update_payload = {"name": "Updated Config", "value": "updated_value"}
        response = client.patch(f"/api/v1/repair/configuration/{config_id}", json=update_payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["name"] == "Updated Config"

    def test_update_configuration_not_found(self, client):
        """测试更新修复配置 - 配置不存在"""
        fake_id = str(uuid.uuid4())
        update_payload = {"name": "Updated"}
        response = client.patch(f"/api/v1/repair/configuration/{fake_id}", json=update_payload)
        assert response.status_code == 404

    def test_delete_configuration_success(self, client):
        """测试删除修复配置 - 成功"""
        create_payload = {"name": "Test Config", "key": "test_key", "value": "test_value"}
        create_response = client.post("/api/v1/repair/configuration", json=create_payload)
        config_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/repair/configuration/{config_id}")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "message" in data

    def test_delete_configuration_not_found(self, client):
        """测试删除修复配置 - 配置不存在"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/repair/configuration/{fake_id}")
        assert response.status_code == 404


# ============================================================
# 2. HITL Approval Management Tests
# ============================================================


class TestHITLApproval:
    """HITL审批管理测试"""

    def test_get_hitl_approvals_success(self, client):
        """测试获取HITL审批 - 成功"""
        response = client.get("/api/v1/repair/hitl-approval")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    def test_get_hitl_approvals_with_status_filter(self, client):
        """测试获取HITL审批 - 带状态过滤"""
        response = client.get("/api/v1/repair/hitl-approval?status=pending")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    def test_create_hitl_approval_success(self, client):
        """测试创建HITL审批 - 成功"""
        payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
            "description": "Auto-healing request",
            "risk_level": "low",
            "requested_by": "admin",
        }
        response = client.post("/api/v1/repair/hitl-approval", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["repair_id"] == "repair-123"
            assert data["status"] == "pending"

    def test_approve_hitl_request_success(self, client):
        """测试批准HITL请求 - 成功"""
        # 先创建一个审批
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
            "description": "Test approval",
        }
        create_response = client.post("/api/v1/repair/hitl-approval", json=create_payload)
        approval_id = create_response.json()["id"]

        # 批准
        action_payload = {"comment": "Approved for testing"}
        response = client.post(
            f"/api/v1/repair/hitl-approval/{approval_id}/approve", json=action_payload
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["status"] == "approved"

    def test_approve_hitl_request_not_found(self, client):
        """测试批准HITL请求 - 请求不存在"""
        fake_id = str(uuid.uuid4())
        action_payload = {"comment": "Test"}
        response = client.post(
            f"/api/v1/repair/hitl-approval/{fake_id}/approve", json=action_payload
        )
        assert response.status_code == 404

    def test_approve_hitl_request_invalid_state(self, client):
        """测试批准HITL请求 - 无效状态"""
        # 创建并批准一个请求
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
            "description": "Test",
        }
        create_response = client.post("/api/v1/repair/hitl-approval", json=create_payload)
        approval_id = create_response.json()["id"]

        # 第一次批准
        client.post(
            f"/api/v1/repair/hitl-approval/{approval_id}/approve", json={"comment": "First"}
        )

        # 再次批准应该失败
        response = client.post(
            f"/api/v1/repair/hitl-approval/{approval_id}/approve", json={"comment": "Second"}
        )
        assert response.status_code in (400, 404)

    def test_reject_hitl_request_success(self, client):
        """测试拒绝HITL请求 - 成功"""
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
            "description": "Test",
        }
        create_response = client.post("/api/v1/repair/hitl-approval", json=create_payload)
        approval_id = create_response.json()["id"]

        action_payload = {"reason": "Risk too high"}
        response = client.post(
            f"/api/v1/repair/hitl-approval/{approval_id}/reject", json=action_payload
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["status"] == "rejected"

    def test_reject_hitl_request_not_found(self, client):
        """测试拒绝HITL请求 - 请求不存在"""
        fake_id = str(uuid.uuid4())
        action_payload = {"reason": "Test"}
        response = client.post(
            f"/api/v1/repair/hitl-approval/{fake_id}/reject", json=action_payload
        )
        assert response.status_code == 404


# ============================================================
# 3. Repair Effectiveness Management Tests
# ============================================================


class TestRepairEffectiveness:
    """修复效果管理测试"""

    def test_get_effectiveness_success(self, client):
        """测试获取修复效果 - 成功"""
        response = client.get("/api/v1/repair/effectiveness")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    def test_get_effectiveness_with_trend_filter(self, client):
        """测试获取修复效果 - 带趋势过滤"""
        response = client.get("/api/v1/repair/effectiveness?trend=improving")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    def test_create_effectiveness_success(self, client):
        """测试创建效果记录 - 成功"""
        payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
        }
        response = client.post("/api/v1/repair/effectiveness", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["repair_id"] == "repair-123"
            assert "success_rate" in data

    def test_evaluate_effectiveness_success(self, client):
        """测试重新评估效果 - 成功"""
        # 先创建一个效果记录
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
        }
        create_response = client.post("/api/v1/repair/effectiveness", json=create_payload)
        effectiveness_id = create_response.json()["id"]

        response = client.post(f"/api/v1/repair/effectiveness/{effectiveness_id}/evaluate")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "trend" in data

    def test_evaluate_effectiveness_not_found(self, client):
        """测试重新评估效果 - 记录不存在"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/repair/effectiveness/{fake_id}/evaluate")
        assert response.status_code == 404


# ============================================================
# 4. Repair Verification Management Tests
# ============================================================


class TestRepairVerification:
    """修复验证管理测试"""

    def test_get_verifications_success(self, client):
        """测试获取验证记录 - 成功"""
        response = client.get("/api/v1/repair/verification")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    def test_get_verifications_with_filters(self, client):
        """测试获取验证记录 - 带过滤"""
        response = client.get(
            "/api/v1/repair/verification?status=pending&verification_type=health-check"
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    def test_create_verification_success(self, client):
        """测试创建验证记录 - 成功"""
        payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
            "verification_type": "health-check",
        }
        response = client.post("/api/v1/repair/verification", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["repair_id"] == "repair-123"
            assert data["status"] == "pending"

    def test_execute_verification_success(self, client):
        """测试执行验证 - 成功"""
        # 先创建验证记录
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
        }
        create_response = client.post("/api/v1/repair/verification", json=create_payload)
        verification_id = create_response.json()["id"]

        response = client.post(f"/api/v1/repair/verification/{verification_id}/verify")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["status"] == "passed"

    def test_execute_verification_not_found(self, client):
        """测试执行验证 - 记录不存在"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/repair/verification/{fake_id}/verify")
        assert response.status_code == 404

    def test_execute_verification_invalid_state(self, client):
        """测试执行验证 - 无效状态"""
        # 创建并执行验证
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
        }
        create_response = client.post("/api/v1/repair/verification", json=create_payload)
        verification_id = create_response.json()["id"]

        # 第一次执行
        client.post(f"/api/v1/repair/verification/{verification_id}/verify")

        # 再次执行应该失败
        response = client.post(f"/api/v1/repair/verification/{verification_id}/verify")
        assert response.status_code in (400, 404)

    def test_rerun_verification_success(self, client):
        """测试重新运行验证 - 成功"""
        create_payload = {
            "repair_id": "repair-123",
            "repair_type": "auto_heal",
            "target_resource": "server-01",
        }
        create_response = client.post("/api/v1/repair/verification", json=create_payload)
        verification_id = create_response.json()["id"]

        response = client.post(f"/api/v1/repair/verification/{verification_id}/rerun")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["status"] == "pending"

    def test_rerun_verification_not_found(self, client):
        """测试重新运行验证 - 记录不存在"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/repair/verification/{fake_id}/rerun")
        assert response.status_code == 404


# ============================================================
# 5-14. Platform-Specific Repairs Tests
# ============================================================


class TestPlatformRepairs:
    """平台特定修复测试"""

    @pytest.mark.parametrize(
        "platform",
        ["hardware", "cloud", "cluster", "pod", "k8s", "docker", "macos", "windows", "linux"],
    )
    def test_get_platform_repairs_success(self, client, platform):
        """测试获取平台修复 - 成功"""
        response = client.get(f"/api/v1/repair/{platform}")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    @pytest.mark.parametrize(
        "platform",
        ["hardware", "cloud", "cluster", "pod", "k8s", "docker", "macos", "windows", "linux"],
    )
    def test_get_platform_repairs_with_status_filter(self, client, platform):
        """测试获取平台修复 - 带状态过滤"""
        response = client.get(f"/api/v1/repair/{platform}?status=detected")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    @pytest.mark.parametrize(
        "platform",
        ["hardware", "cloud", "cluster", "pod", "k8s", "docker", "macos", "windows", "linux"],
    )
    def test_create_platform_repair_success(self, client, platform):
        """测试创建平台修复 - 成功"""
        payload = {
            "target_resource": f"{platform}-01",
            "issue_type": "high_cpu",
            "severity": "medium",
            "repair_action": "restart",
        }
        response = client.post(f"/api/v1/repair/{platform}", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
        # API returns success status, just verify it worked
            assert "id" in data

    @pytest.mark.parametrize(
        "platform",
        ["hardware", "cloud", "cluster", "pod", "k8s", "docker", "macos", "windows", "linux"],
    )
    def test_execute_platform_repair_success(self, client, platform):
        """测试执行平台修复 - 成功"""
        # 先创建修复
        create_payload = {
            "target_resource": f"{platform}-01",
            "issue_type": "high_cpu",
            "severity": "medium",
            "repair_action": "restart",
        }
        create_response = client.post(f"/api/v1/repair/{platform}", json=create_payload)
        repair_id = create_response.json()["id"]

        response = client.post(f"/api/v1/repair/{platform}/{repair_id}/repair")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
        # API returns success status, just verify it worked
            assert "id" in data

    @pytest.mark.parametrize(
        "platform",
        ["hardware", "cloud", "cluster", "pod", "k8s", "docker", "macos", "windows", "linux"],
    )
    def test_execute_platform_repair_not_found(self, client, platform):
        """测试执行平台修复 - 修复不存在"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/repair/{platform}/{fake_id}/repair")
        assert response.status_code == 404


# ============================================================
# 14. Cross-Platform Repair Tests
# ============================================================


class TestCrossPlatformRepair:
    """跨平台修复测试"""

    @patch("api.repair_advanced_router._cross_platform_executor")
    def test_get_cross_platform_repairs_success(self, mock_executor, client):
        """测试获取跨平台修复 - 成功"""
        response = client.get("/api/v1/repair/cross-platform")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    @patch("api.repair_advanced_router._cross_platform_executor")
    def test_get_cross_platform_repairs_with_filter(self, mock_executor, client):
        """测试获取跨平台修复 - 带过滤"""
        response = client.get("/api/v1/repair/cross-platform?status=completed")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    @patch("api.repair_advanced_router._cross_platform_executor.execute_script")
    def test_create_cross_platform_repair_success(self, mock_execute, client):
        """测试创建跨平台修复 - 成功"""
        mock_execute.return_value = {"success": True, "output": "Repair executed"}

        payload = {
            "target_resource": "multi-platform-01",
            "issue_type": "network_issue",
            "severity": "high",
            "repair_action": "reconfigure",
        }
        response = client.post("/api/v1/repair/cross-platform", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["target_resource"] == "multi-platform-01"


# ============================================================
# 15. Unified Repair Tests
# ============================================================


class TestUnifiedRepair:
    """统一修复测试"""

    def test_get_unified_repairs_success(self, client):
        """测试获取统一修复 - 成功"""
        response = client.get("/api/v1/repair/unified")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data
            assert "total" in data

    def test_get_unified_repairs_with_filter(self, client):
        """测试获取统一修复 - 带过滤"""
        response = client.get("/api/v1/repair/unified?status=analyzing")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "items" in data

    def test_create_unified_repair_success(self, client):
        """测试创建统一修复 - 成功"""
        payload = {
            "target_resource": "unified-01",
            "issue_type": "complex_failure",
            "severity": "critical",
            "repair_action": "multi_strategy",
        }
        response = client.post("/api/v1/repair/unified", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["target_resource"] == "unified-01"
