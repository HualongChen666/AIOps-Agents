# -*- coding: utf-8 -*-
# tests/test_auto_heal.py
# 自动修复引擎单元测试
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.auto_heal import (
    approve_repair,
    get_pending_approvals,
    handle_alert,
    reject_repair,
    simulate_repair,
    simulate_verify,
    trigger_auto_heal,
)


@pytest.fixture
def mock_auto_heal_db():
    """Mock the database helpers in auto_heal so unit tests don't require PostgreSQL."""
    with (
        patch("core.auto_heal._create_alert_record", new=AsyncMock(return_value="alert-001")),
        patch("core.auto_heal.insert_repair_record", new=Mock(return_value="repair-001")),
        patch("core.auto_heal._create_verify_record", new=Mock(return_value="verify-001")),
        patch("core.auto_heal._create_pending_approval", new=Mock(return_value=None)),
    ):
        yield


class TestAutoHealTrigger:
    """自动修复触发测试"""

    def test_trigger_auto_heal_success(self, mock_auto_heal_db):
        """测试自动修复触发成功"""
        alert = {
            "id": "alert-001",
            "type": "cpu_high",
            "message": "CPU usage exceeds 80%",
            "host": "server-01",
        }

        result = trigger_auto_heal(alert)

        # 验证触发成功
        assert result is not None
        assert isinstance(result, dict)

    def test_trigger_auto_heal_with_empty_alert(self, mock_auto_heal_db):
        """测试空告警"""
        alert = {}

        result = trigger_auto_heal(alert)

        # 验证返回结果
        assert result is not None
        assert isinstance(result, dict)


class TestRepairApproval:
    """修复审批测试"""

    def test_approve_repair_success(self):
        """测试修复审批成功"""
        alert_id = 1

        result = approve_repair(alert_id)

        # 验证审批成功
        assert result["status"] == "approved"
        assert result["alert_id"] == alert_id

    def test_approve_repair_with_different_id(self):
        """测试不同ID审批"""
        alert_id = 999

        result = approve_repair(alert_id)

        # 验证审批成功
        assert result["status"] == "approved"
        assert result["alert_id"] == alert_id

    def test_reject_repair_success(self):
        """测试修复拒绝成功"""
        alert_id = 1

        result = reject_repair(alert_id)

        # 验证拒绝成功
        assert result["status"] == "rejected"
        assert result["alert_id"] == alert_id

    def test_reject_repair_with_reason(self):
        """测试带原因的修复拒绝"""
        alert_id = 1
        reason = "Unsafe operation"

        result = reject_repair(alert_id, reason)

        # 验证拒绝成功并记录原因
        assert result["status"] == "rejected"
        assert result["alert_id"] == alert_id
        assert result["reason"] == reason


class TestPendingApprovals:
    """待审批管理测试"""

    def test_get_pending_approvals(self):
        """测试获取待审批列表"""
        approvals = get_pending_approvals()

        # 验证返回列表
        assert isinstance(approvals, list)

    def test_get_pending_approvals_empty(self):
        """测试获取空待审批列表"""
        approvals = get_pending_approvals()

        # 验证返回空列表（当前实现返回空列表）
        assert len(approvals) == 0


class TestAutoHealUtilities:
    """自动修复工具函数测试"""

    def test_handle_alert(self, mock_auto_heal_db):
        """测试告警处理"""
        alert_payload = {
            "id": "alert-001",
            "type": "cpu_high",
            "message": "CPU usage exceeds 80%",
            "host": "server-01",
        }

        result = handle_alert(alert_payload)

        # 验证处理结果
        assert result is not None
        assert isinstance(result, dict)

    def test_simulate_repair(self):
        """测试修复模拟"""
        alert = {
            "id": "alert-001",
            "type": "cpu_high",
            "host": "server-01",
        }
        script_key = "restart_service"

        result = simulate_repair(alert, script_key)

        # 验证模拟结果
        assert result is not None
        assert isinstance(result, dict)

    def test_simulate_verify(self):
        """测试验证模拟"""
        alert = {
            "id": "alert-001",
            "type": "cpu_high",
        }
        repair_result = {
            "status": "success",
            "output": "Service restarted successfully",
        }

        result = simulate_verify(alert, repair_result)

        # 验证验证结果
        assert result is not None
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
