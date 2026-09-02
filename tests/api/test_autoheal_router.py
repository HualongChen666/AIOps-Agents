# -*- coding: utf-8 -*-
"""
完整的autoheal_router测试文件
测试所有30个API端点，使用pytest-xdist并行测试
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.api]

from fastapi import HTTPException

# Import the module
import api.autoheal_router as autoheal_router
from modules.high_availability.self_healing import (
    FailureType,
    RemediationAction,
    SelfHealingPolicy,
    FailureEvent,
)


# ---------------------------------------------------------------------------
# 测试配置
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_request():
    """创建模拟请求对象"""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "test-key"}
    return request


@pytest.fixture
def mock_engine():
    """创建模拟自愈引擎"""
    engine = MagicMock()
    engine.policies = {}
    engine.failure_history = []
    engine.remediation_history = []
    engine.cooldowns = {}
    return engine


# ---------------------------------------------------------------------------
# 策略管理端点测试 (4个)
# ---------------------------------------------------------------------------


class TestPolicyManagement:
    """测试策略管理端点"""

    @pytest.mark.asyncio
    async def test_create_policy_success(self, mock_request, mock_engine):
        """测试创建策略成功"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.CreatePolicyRequest(
                    id="test-policy",
                    name="Test Policy",
                    failure_type="service_down",
                    remediation_actions=["restart_service"],
                )

                result = await autoheal_router.create_policy(payload, mock_request)

                assert result["success"] is True
                assert result["policy_id"] == "test-policy"
                assert "test-policy" in mock_engine.policies

    @pytest.mark.asyncio
    async def test_create_policy_duplicate(self, mock_request, mock_engine):
        """测试创建重复策略"""
        mock_engine.policies["test-policy"] = MagicMock()

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.CreatePolicyRequest(
                    id="test-policy",
                    name="Test Policy",
                    failure_type="service_down",
                    remediation_actions=["restart_service"],
                )

                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.create_policy(payload, mock_request)
                assert exc_info.value.status_code == 400
                assert "已存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_policy_invalid_failure_type(self, mock_request):
        """测试创建策略时使用无效的故障类型"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with pytest.raises(ValueError) as exc_info:
                autoheal_router.CreatePolicyRequest(
                    id="test-policy",
                    name="Test Policy",
                    failure_type="invalid_type",
                    remediation_actions=["restart_service"],
                )
            assert "无效的故障类型" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_policies_success(self, mock_request, mock_engine):
        """测试获取策略列表成功"""
        policy = SelfHealingPolicy(
            id="test-policy",
            name="Test Policy",
            failure_type=FailureType.SERVICE_DOWN,
            remediation_actions=[RemediationAction.RESTART_SERVICE],
        )
        mock_engine.policies["test-policy"] = policy

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.list_policies(mock_request)

                assert result["total"] == 1
                assert len(result["items"]) == 1
                assert result["items"][0]["id"] == "test-policy"

    @pytest.mark.asyncio
    async def test_get_policy_success(self, mock_request, mock_engine):
        """测试获取单个策略成功"""
        policy = SelfHealingPolicy(
            id="test-policy",
            name="Test Policy",
            failure_type=FailureType.SERVICE_DOWN,
            remediation_actions=[RemediationAction.RESTART_SERVICE],
        )
        mock_engine.policies["test-policy"] = policy

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.get_policy("test-policy", mock_request)

                assert result["id"] == "test-policy"
                assert result["name"] == "Test Policy"

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self, mock_request, mock_engine):
        """测试获取不存在的策略"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.get_policy("nonexistent", mock_request)
                assert exc_info.value.status_code == 404
                assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_policy_success(self, mock_request, mock_engine):
        """测试删除策略成功"""
        mock_engine.policies["test-policy"] = MagicMock()

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.delete_policy("test-policy", mock_request)

                assert result["success"] is True
                assert "test-policy" not in mock_engine.policies

    @pytest.mark.asyncio
    async def test_delete_policy_not_found(self, mock_request, mock_engine):
        """测试删除不存在的策略"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.delete_policy("nonexistent", mock_request)
                assert exc_info.value.status_code == 404
                assert "不存在" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 故障管理端点测试 (5个)
# ---------------------------------------------------------------------------


class TestFailureManagement:
    """测试故障管理端点"""

    @pytest.mark.asyncio
    async def test_detect_failure_success(self, mock_request, mock_engine):
        """测试检测故障成功"""
        failure_event = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.detect_failure.return_value = failure_event

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.DetectFailureRequest(
                    failure_type="service_down",
                    component="test-service",
                    severity="high",
                    description="Test failure",
                )

                result = await autoheal_router.detect_failure(payload, mock_request)

                assert result["success"] is True
                assert result["failure_id"] == "failure-1"
                mock_engine.detect_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_failure_invalid_severity(self):
        """测试检测故障时使用无效的严重程度"""
        with pytest.raises(ValueError) as exc_info:
            autoheal_router.DetectFailureRequest(
                failure_type="service_down",
                component="test-service",
                severity="invalid",
                description="Test failure",
            )
        assert "无效的严重程度" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_failures_success(self, mock_request, mock_engine):
        """测试获取故障历史成功"""
        failure = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.failure_history = [failure]

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.list_failures(mock_request, limit=10, offset=0)

                assert result["total"] == 1
                assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_failure_success(self, mock_request, mock_engine):
        """测试获取故障详情成功"""
        failure = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.failure_history = [failure]

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.get_failure("failure-1", mock_request)

                assert result["id"] == "failure-1"
                assert result["component"] == "test-service"

    @pytest.mark.asyncio
    async def test_get_failure_not_found(self, mock_request, mock_engine):
        """测试获取不存在的故障"""
        mock_engine.failure_history = []

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.get_failure("nonexistent", mock_request)
                assert exc_info.value.status_code == 404
                assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_trigger_healing_success(self, mock_request, mock_engine):
        """测试触发自愈成功"""
        failure = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.failure_history = [failure]
        mock_engine.trigger_self_healing.return_value = []

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.trigger_healing("failure-1", mock_request)

                assert result["success"] is True
                assert result["failure_id"] == "failure-1"
                mock_engine.trigger_self_healing.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_healing_not_found(self, mock_request, mock_engine):
        """测试触发不存在的故障的自愈"""
        mock_engine.failure_history = []

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.trigger_healing("nonexistent", mock_request)
                assert exc_info.value.status_code == 404
                assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_remediation_success(self, mock_request, mock_engine):
        """测试验证修复成功"""
        failure = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.failure_history = [failure]
        mock_engine.verify_remediation.return_value = True

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.verify_remediation("failure-1", mock_request)

                assert result["success"] is True
                assert result["verified"] is True
                mock_engine.verify_remediation.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_remediation_not_found(self, mock_request, mock_engine):
        """测试验证不存在的故障的修复"""
        mock_engine.failure_history = []

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.verify_remediation("nonexistent", mock_request)
                assert exc_info.value.status_code == 404
                assert "不存在" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 修复动作端点测试 (7个)
# ---------------------------------------------------------------------------


class TestRemediationActions:
    """测试修复动作端点"""

    @pytest.mark.asyncio
    async def test_action_restart_success(self, mock_request, mock_engine):
        """测试重启服务成功"""
        mock_engine._handle_restart.return_value = (True, "Service restarted")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_restart(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "restart_service"
                mock_engine._handle_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_scale_up_success(self, mock_request, mock_engine):
        """测试扩容成功"""
        mock_engine._handle_scale_up.return_value = (True, "Scaled up")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_scale_up(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "scale_up"
                mock_engine._handle_scale_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_scale_down_success(self, mock_request, mock_engine):
        """测试缩容成功"""
        mock_engine._handle_scale_down.return_value = (True, "Scaled down")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_scale_down(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "scale_down"
                mock_engine._handle_scale_down.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_rollback_success(self, mock_request, mock_engine):
        """测试回滚成功"""
        mock_engine._handle_rollback.return_value = (True, "Rolled back")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_rollback(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "rollback"
                mock_engine._handle_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_clear_cache_success(self, mock_request, mock_engine):
        """测试清空缓存成功"""
        mock_engine._handle_clear_cache.return_value = (True, "Cache cleared")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_clear_cache(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "clear_cache"
                mock_engine._handle_clear_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_rebalance_success(self, mock_request, mock_engine):
        """测试重新平衡成功"""
        mock_engine._handle_rebalance.return_value = (True, "Rebalanced")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_rebalance(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "rebalance"
                mock_engine._handle_rebalance.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_isolate_success(self, mock_request, mock_engine):
        """测试隔离组件成功"""
        mock_engine._handle_isolate.return_value = (True, "Isolated")

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.ExecuteActionRequest(component="test-service")

                result = await autoheal_router.action_isolate(payload, mock_request)

                assert result["success"] is True
                assert result["action"] == "isolate"
                mock_engine._handle_isolate.assert_called_once()


# ---------------------------------------------------------------------------
# 批量操作端点测试 (3个)
# ---------------------------------------------------------------------------


class TestBatchOperations:
    """测试批量操作端点"""

    @pytest.mark.asyncio
    async def test_batch_detect_failures_success(self, mock_request, mock_engine):
        """测试批量检测故障成功"""
        failure_event = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.detect_failure.return_value = failure_event

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.BatchDetectFailuresRequest(
                    failures=[
                        autoheal_router.DetectFailureRequest(
                            failure_type="service_down",
                            component="test-service",
                            severity="high",
                            description="Test failure",
                        )
                    ]
                )

                result = await autoheal_router.batch_detect_failures(payload, mock_request)

                assert result["success"] is True
                assert result["total"] == 1
                assert result["success_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_detect_failures_batch_size(self, mock_request, mock_engine):
        """测试批量检测故障的分批处理"""
        failure_event = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.detect_failure.return_value = failure_event

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                # 创建15个故障，超过batch_size=10
                failures = [
                    autoheal_router.DetectFailureRequest(
                        failure_type="service_down",
                        component=f"test-service-{i}",
                        severity="high",
                        description=f"Test failure {i}",
                    )
                    for i in range(15)
                ]
                payload = autoheal_router.BatchDetectFailuresRequest(failures=failures)

                result = await autoheal_router.batch_detect_failures(payload, mock_request)

                assert result["success"] is True
                assert result["total"] == 15
                assert result["success_count"] == 15

    @pytest.mark.asyncio
    async def test_batch_heal_failures_success(self, mock_request, mock_engine):
        """测试批量触发自愈成功"""
        failure = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.failure_history = [failure]
        mock_engine.trigger_self_healing.return_value = []

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.BatchHealFailuresRequest(failure_ids=["failure-1"])

                result = await autoheal_router.batch_heal_failures(payload, mock_request)

                assert result["success"] is True
                assert result["total"] == 1
                assert result["success_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_heal_failures_not_found(self, mock_request, mock_engine):
        """测试批量触发自愈时故障不存在"""
        mock_engine.failure_history = []

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.BatchHealFailuresRequest(failure_ids=["nonexistent"])

                result = await autoheal_router.batch_heal_failures(payload, mock_request)

                assert result["success"] is True
                assert result["total"] == 1
                assert result["success_count"] == 0
                assert result["failure_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_verify_remediations_success(self, mock_request, mock_engine):
        """测试批量验证修复成功"""
        failure = FailureEvent(
            id="failure-1",
            failure_type=FailureType.SERVICE_DOWN,
            component="test-service",
            severity="high",
            description="Test failure",
        )
        mock_engine.failure_history = [failure]
        mock_engine.verify_remediation.return_value = True

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                payload = autoheal_router.BatchVerifyRemediationsRequest(failure_ids=["failure-1"])

                result = await autoheal_router.batch_verify_remediations(payload, mock_request)

                assert result["success"] is True
                assert result["total"] == 1
                assert result["success_count"] == 1
                assert result["verified_count"] == 1


# ---------------------------------------------------------------------------
# 监控和健康端点测试 (4个)
# ---------------------------------------------------------------------------


class TestMonitoringAndHealth:
    """测试监控和健康端点"""

    @pytest.mark.asyncio
    async def test_health_check_available(self, mock_request, mock_engine):
        """测试健康检查 - 模块可用"""
        mock_engine.get_statistics.return_value = {
            "total_failures": 0,
            "total_remediations": 0,
            "successful_remediations": 0,
            "success_rate": 0,
            "active_policies": 0,
            "total_policies": 0,
        }

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.health_check(mock_request)

                assert result["status"] == "healthy"
                assert result["available"] is True
                assert "statistics" in result

    @pytest.mark.asyncio
    async def test_health_check_unavailable(self, mock_request):
        """测试健康检查 - 模块不可用"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", False):
            result = await autoheal_router.health_check(mock_request)

            assert result["status"] == "unavailable"
            assert result["available"] is False

    @pytest.mark.asyncio
    async def test_list_remediations_success(self, mock_request, mock_engine):
        """测试获取修复历史成功"""
        from modules.high_availability.self_healing import RemediationResult

        remediation = RemediationResult(
            policy_id="test-policy",
            action=RemediationAction.RESTART_SERVICE,
            success=True,
            message="Success",
        )
        mock_engine.remediation_history = [remediation]

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.list_remediations(mock_request, limit=10, offset=0)

                assert result["total"] == 1
                assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_cooldowns_success(self, mock_request, mock_engine):
        """测试获取冷却期状态成功"""
        from datetime import timedelta

        cooldown_end = datetime.now() + timedelta(minutes=5)
        mock_engine.cooldowns = {"test-policy": cooldown_end}

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.list_cooldowns(mock_request)

                assert result["total"] == 1
                assert len(result["items"]) == 1
                assert result["items"][0]["policy_id"] == "test-policy"
                assert result["items"][0]["in_cooldown"] is True

    @pytest.mark.asyncio
    async def test_clear_cooldown_success(self, mock_request, mock_engine):
        """测试清除冷却期成功"""
        mock_engine.policies["test-policy"] = MagicMock()
        mock_engine.cooldowns["test-policy"] = datetime.now()

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.clear_cooldown("test-policy", mock_request)

                assert result["success"] is True
                assert "test-policy" not in mock_engine.cooldowns

    @pytest.mark.asyncio
    async def test_clear_cooldown_not_found(self, mock_request, mock_engine):
        """测试清除不存在的策略的冷却期"""
        mock_engine.policies = {}

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.clear_cooldown("nonexistent", mock_request)
                assert exc_info.value.status_code == 404
                assert "不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_engine_status_success(self, mock_request, mock_engine):
        """测试获取引擎状态成功"""
        mock_engine.get_statistics.return_value = {
            "total_failures": 0,
            "total_remediations": 0,
            "successful_remediations": 0,
            "success_rate": 0,
            "active_policies": 0,
            "total_policies": 0,
        }
        mock_engine.policies = {}
        mock_engine.failure_history = []
        mock_engine.remediation_history = []
        mock_engine.cooldowns = {}

        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                result = await autoheal_router.get_engine_status(mock_request)

                assert result["status"] == "running"
                assert result["available"] is True
                assert "statistics" in result
                assert result["policies_count"] == 0


# ---------------------------------------------------------------------------
# 原有端点测试 (6个)
# ---------------------------------------------------------------------------


class TestOriginalEndpoints:
    """测试原有端点"""

    @pytest.mark.asyncio
    async def test_list_pending_success(self, mock_request):
        """测试获取待审批列表成功"""
        with patch.object(autoheal_router, "INTERNAL_API_KEY", None):
            with patch("api.autoheal_router.get_pending_approvals", return_value=[]):
                result = await autoheal_router.list_pending(mock_request)

                assert result["total"] == 0
                assert result["items"] == []

    @pytest.mark.asyncio
    async def test_approve_success(self, mock_request):
        """测试审批通过成功"""
        with patch.object(autoheal_router, "INTERNAL_API_KEY", "test-key"):
            with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                with patch("gateway.services_client.approve_and_execute", AsyncMock(return_value={"success": True})):
                    with patch("api.autoheal_router.async_update_approval_status_by_alert", AsyncMock()):
                        result = await autoheal_router.approve("A1", mock_request)

                        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_reject_success(self, mock_request):
        """测试驳回成功"""
        with patch.object(autoheal_router, "INTERNAL_API_KEY", None):
            with patch("core.auto_heal.reject_repair", return_value={"success": True}):
                with patch("api.autoheal_router.get_pending_approvals", return_value=[]):
                    payload = autoheal_router.RejectRequest(alert_id="A1", reason="Test")
                    result = await autoheal_router.reject(payload, mock_request)

                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_takeover_success(self, mock_request):
        """测试接管成功"""
        with patch.object(autoheal_router, "INTERNAL_API_KEY", None):
            with patch("core.auto_heal.reject_repair", return_value={"success": True}):
                result = await autoheal_router.takeover("A1", mock_request)

                assert result["success"] is True
                assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_ai_propose_success(self, mock_request):
        """测试AI方案生成成功"""
        with patch.object(autoheal_router, "INTERNAL_API_KEY", None):
            with patch.object(autoheal_router, "is_runbook_available", True):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    with patch("api.autoheal_router._collect_rich_context_for_ai", AsyncMock(return_value=({}, {}))):
                        with patch("api.autoheal_router._generate_runbook", AsyncMock(return_value={"success": True})):
                            with patch("api.autoheal_router.get_pending_approvals", AsyncMock(return_value=[])):
                                payload = autoheal_router.AIProposeRequest(alert_id="A1")
                                result = await autoheal_router.ai_propose_repair(payload, mock_request)

                                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_statistics_success(self, mock_request):
        """测试获取统计信息成功"""
        with patch.object(autoheal_router, "INTERNAL_API_KEY", None):
            with patch("api.autoheal_router.get_pending_approvals", return_value=[]):
                result = await autoheal_router.get_statistics(mock_request)

                assert "total_tasks" in result
                assert "success_rate" in result


# ---------------------------------------------------------------------------
# 集成测试
# ---------------------------------------------------------------------------


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_request, mock_engine):
        """测试完整工作流：创建策略 -> 检测故障 -> 触发自愈 -> 验证修复"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                # 1. 创建策略
                policy_payload = autoheal_router.CreatePolicyRequest(
                    id="integration-policy",
                    name="Integration Test Policy",
                    failure_type="service_down",
                    remediation_actions=["restart_service"],
                )
                policy_result = await autoheal_router.create_policy(policy_payload, mock_request)
                assert policy_result["success"] is True

                # 2. 检测故障
                failure_event = FailureEvent(
                    id="integration-failure",
                    failure_type=FailureType.SERVICE_DOWN,
                    component="integration-service",
                    severity="high",
                    description="Integration test failure",
                )
                mock_engine.detect_failure.return_value = failure_event
                mock_engine.failure_history.append(failure_event)

                failure_payload = autoheal_router.DetectFailureRequest(
                    failure_type="service_down",
                    component="integration-service",
                    severity="high",
                    description="Integration test failure",
                )
                failure_result = await autoheal_router.detect_failure(failure_payload, mock_request)
                assert failure_result["success"] is True

                # 3. 触发自愈
                mock_engine.trigger_self_healing.return_value = []
                heal_result = await autoheal_router.trigger_healing("integration-failure", mock_request)
                assert heal_result["success"] is True

                # 4. 验证修复
                mock_engine.verify_remediation.return_value = True
                verify_result = await autoheal_router.verify_remediation("integration-failure", mock_request)
                assert verify_result["success"] is True
                assert verify_result["verified"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_request, mock_engine):
        """测试错误处理"""
        with patch.object(autoheal_router, "SELF_HEALING_AVAILABLE", True):
            with patch.object(autoheal_router, "get_self_healing_engine", return_value=mock_engine):
                # 测试引擎异常
                mock_engine.detect_failure.side_effect = Exception("Engine error")

                payload = autoheal_router.DetectFailureRequest(
                    failure_type="service_down",
                    component="test-service",
                    severity="high",
                    description="Test failure",
                )

                with pytest.raises(HTTPException) as exc_info:
                    await autoheal_router.detect_failure(payload, mock_request)
                assert exc_info.value.status_code == 500
