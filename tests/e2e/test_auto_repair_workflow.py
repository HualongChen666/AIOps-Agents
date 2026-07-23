# -*- coding: utf-8 -*-
"""
E2E Test: Auto-Repair Workflow
真实E2E测试：自动修复的完整工作流，不使用Mock
"""

import asyncio
import time  # noqa: F401
from datetime import datetime, timedelta  # noqa: F401
from typing import Any, Dict  # noqa: F401

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestAutoRepairWorkflow:
    """自动修复完整工作流E2E测试"""

    @pytest.mark.asyncio
    async def test_complete_auto_repair_lifecycle(self, http_client):
        """测试完整的自动修复生命周期：告警→分析→修复→验证"""

        # 步骤1: 创建需要修复的告警
        alert_data = {
            "component": "web_server",
            "severity": "critical",
            "title": "Web服务器CPU过高",
            "description": "Web服务器CPU使用率超过90%",
            "metrics": {"cpu_usage": 92.0, "memory_usage": 75.0, "response_time_ms": 3000},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "auto_repair_enabled": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        assert alert_response.status_code in [200, 201, 202]
        alert_id = alert_response.json().get("id")

        # 步骤2: 触发自动修复分析
        analysis_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/auto-repair/analyze",  # noqa: F541
            json={"repair_type": "automatic", "safety_level": "high"},
            timeout=20.0,
        )

        assert analysis_response.status_code in [200, 202]
        analysis_result = analysis_response.json()

        # 验证分析结果
        assert "repair_actions" in analysis_result
        assert "confidence" in analysis_result
        assert "risk_assessment" in analysis_result

        # 步骤3: 执行修复操作
        if analysis_result.get("repair_actions"):
            repair_action = analysis_result["repair_actions"][0]

            execution_response = await http_client.post(
                f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
                json={
                    "alert_id": alert_id,
                    "action": repair_action,
                    "approval": "auto",  # 自动批准
                },
                timeout=30.0,
            )

            assert execution_response.status_code in [200, 202]
            execution_result = execution_response.json()

            # 验证执行结果
            assert "status" in execution_result
            assert execution_result["status"] in ["completed", "failed", "partial"]

        # 步骤4: 验证修复效果
        verification_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/verify-repair",
            timeout=15.0,  # noqa: F541
        )

        assert verification_response.status_code in [200, 202]
        verification_result = verification_response.json()

        # 验证验证结果
        assert "repair_successful" in verification_result
        assert "metrics_after_repair" in verification_result

        # 步骤5: 更新告警状态
        if verification_result["repair_successful"]:
            update_response = await http_client.put(
                f"http://localhost:8000/api/v1/alerts/{alert_id}",  # noqa: F541
                json={
                    "status": "resolved",
                    "resolution": "自动修复成功",
                    "resolved_at": datetime.now().isoformat(),
                },
                timeout=10.0,
            )

            assert update_response.status_code in [200, 202]

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541

    @pytest.mark.asyncio
    async def test_multi_stage_repair_process(self, http_client):
        """测试多阶段修复过程"""

        # 创建需要多阶段修复的告警
        alert_data = {
            "component": "database_cluster",
            "severity": "critical",
            "title": "数据库集群性能下降",
            "description": "需要多阶段修复的数据库问题",
            "metrics": {
                "query_time_p95": 5000,
                "connection_timeout_rate": 0.15,
                "replication_lag_ms": 8000,
            },
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "auto_repair_enabled": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = alert_response.json().get("id")

        # 阶段1: 紧急修复
        stage1_response = await http_client.post(
            f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
            json={
                "alert_id": alert_id,
                "action": {
                    "type": "emergency",
                    "script": "kill_slow_queries",
                    "params": {"threshold_ms": 3000},
                },
                "stage": 1,
            },
            timeout=30.0,
        )

        assert stage1_response.status_code in [200, 202]

        # 等待第一阶段完成
        await asyncio.sleep(2)

        # 阶段2: 根本修复
        stage2_response = await http_client.post(
            f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
            json={
                "alert_id": alert_id,
                "action": {
                    "type": "root_cause",
                    "script": "optimize_database_config",
                    "params": {"target": "connection_pool"},
                },
                "stage": 2,
            },
            timeout=30.0,
        )

        assert stage2_response.status_code in [200, 202]

        # 阶段3: 预防措施
        stage3_response = await http_client.post(
            f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
            json={
                "alert_id": alert_id,
                "action": {
                    "type": "prevention",
                    "script": "setup_monitoring",
                    "params": {"metric": "query_time"},
                },
                "stage": 3,
            },
            timeout=30.0,
        )

        assert stage3_response.status_code in [200, 202]

        # 验证多阶段修复完成
        verification_response = await http_client.get(
            f"http://localhost:8000/api/v1/repair/{alert_id}/stages", timeout=10.0  # noqa: F541
        )

        assert verification_response.status_code == 200
        stages = verification_response.json()
        assert len(stages) == 3
        assert all(stage["status"] == "completed" for stage in stages)

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541

    @pytest.mark.asyncio
    async def test_repair_approval_workflow(self, http_client):
        """测试修复审批工作流"""

        # 创建高风险告警，需要人工审批
        alert_data = {
            "component": "production_database",
            "severity": "critical",
            "title": "生产数据库需要重启",
            "description": "需要重启生产数据库",
            "metrics": {"connection_errors": 100},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "auto_repair_enabled": True,
            "requires_approval": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = alert_response.json().get("id")

        # 请求修复操作（需要审批）
        repair_request = {
            "alert_id": alert_id,
            "action": {"type": "restart", "target": "production_database", "risk": "high"},
            "requested_by": "system",
            "reason": "数据库连接异常",
        }

        request_response = await http_client.post(
            "http://localhost:8000/api/v1/repair/request", json=repair_request, timeout=10.0
        )

        assert request_response.status_code in [200, 201, 202]
        repair_request_id = request_response.json().get("request_id")

        # 模拟审批
        approval_response = await http_client.post(
            f"http://localhost:8000/api/v1/repair/requests/{repair_request_id}/approve",  # noqa: E501
            json={
                "approved_by": "admin",
                "reason": "维护窗口已确认",
                "approved_at": datetime.now().isoformat(),
            },
            timeout=10.0,
        )

        assert approval_response.status_code in [200, 202]

        # 执行已批准的修复
        execution_response = await http_client.post(
            f"http://localhost:8000/api/v1/repair/execute-approved",  # noqa: F541
            json={"request_id": repair_request_id},
            timeout=30.0,
        )

        assert execution_response.status_code in [200, 202]
        execution_result = execution_response.json()

        # 验证修复执行
        assert execution_result["status"] in ["completed", "failed"]

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541

    @pytest.mark.asyncio
    async def test_repair_rollback_mechanism(self, http_client):
        """测试修复回滚机制"""

        # 创建告警
        alert_data = {
            "component": "config_service",
            "severity": "warning",
            "title": "配置服务异常",
            "description": "配置需要修复",
            "metrics": {"config_errors": 5},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "auto_repair_enabled": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = alert_response.json().get("id")

        # 执行可能失败的修复操作
        risky_repair = {
            "alert_id": alert_id,
            "action": {
                "type": "config_change",
                "script": "update_critical_config",
                "params": {"config_key": "timeout"},
                "rollback_on_failure": True,
            },
        }

        execution_response = await httpx.AsyncClient(timeout=30.0).post(
            "http://localhost:8000/api/v1/repair/execute", json=risky_repair
        )

        # 如果修复失败，验证回滚
        if (
            execution_response.status_code != 200
            or execution_response.json().get("status") == "failed"
        ):
            rollback_response = await http_client.post(
                f"http://localhost:8000/api/v1/repair/{alert_id}/rollback",
                timeout=15.0,  # noqa: F541
            )

            assert rollback_response.status_code in [200, 202]
            rollback_result = rollback_response.json()

            # 验证回滚成功
            assert rollback_result["rollback_successful"]
            assert rollback_result["system_state"] == "restored"

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541

    @pytest.mark.asyncio
    async def test_repair_history_tracking(self, http_client):
        """测试修复历史跟踪"""

        # 创建告警并执行多次修复
        alert_data = {
            "component": "cache_service",
            "severity": "warning",
            "title": "缓存服务异常",
            "description": "需要修复缓存问题",
            "metrics": {"cache_errors": 10},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "auto_repair_enabled": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = alert_response.json().get("id")

        # 执行第一次修复
        await http_client.post(
            f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
            json={"alert_id": alert_id, "action": {"type": "cache_clear", "script": "clear_cache"}},
            timeout=20.0,
        )

        # 执行第二次修复
        await http_client.post(
            f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
            json={
                "alert_id": alert_id,
                "action": {"type": "cache_restart", "script": "restart_cache"},
            },
            timeout=20.0,
        )

        # 获取修复历史
        history_response = await http_client.get(
            f"http://localhost:8000/api/v1/repair/{alert_id}/history", timeout=10.0  # noqa: F541
        )

        assert history_response.status_code == 200
        history = history_response.json()

        # 验证修复历史记录
        assert len(history) >= 2
        assert all("timestamp" in entry for entry in history)
        assert all("action" in entry for entry in history)
        assert all("result" in entry for entry in history)

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541


@pytest.mark.e2e
@pytest.mark.slow
class TestRepairSafeguards:
    """修复安全防护E2E测试"""

    @pytest.mark.asyncio
    async def test_repair_command_validation(self, http_client):
        """测试修复命令验证"""

        # 尝试执行危险命令
        dangerous_repair = {
            "alert_id": "test_alert_123",
            "action": {"type": "dangerous", "script": "rm -rf /"},  # 危险命令
        }

        # 应该被命令护栏拒绝
        validation_response = await http_client.post(
            "http://localhost:8000/api/v1/repair/validate", json=dangerous_repair, timeout=10.0
        )

        assert validation_response.status_code in [200, 400, 403]
        validation_result = validation_response.json()

        if validation_response.status_code == 200:
            assert validation_result["allowed"] is False
            assert "reason" in validation_result

    @pytest.mark.asyncio
    async def test_repair_rate_limiting(self, http_client):
        """测试修复速率限制"""

        # 创建告警
        alert_data = {
            "component": "rate_limit_test",
            "severity": "warning",
            "title": "速率限制测试",
            "description": "测试修复速率限制",
            "metrics": {"test": 100},
            "source": "test",
            "timestamp": datetime.now().isoformat(),
            "auto_rearm_enabled": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = alert_response.json().get("id")

        # 快速连续请求修复
        repair_responses = []
        for i in range(10):
            response = await http_client.post(
                f"http://localhost:8000/api/v1/repair/execute",  # noqa: F541
                json={"alert_id": alert_id, "action": {"type": "test", "script": "test_script"}},
                timeout=5.0,
            )
            repair_responses.append(response)

        # 验证速率限制生效
        # 应该有一些请求被拒绝
        rate_limited_count = sum(1 for r in repair_responses if r.status_code == 429)
        assert rate_limited_count > 0

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541

    @pytest.mark.asyncio
    async def test_repair_timeout_handling(self, http_client):
        """测试修复超时处理"""

        # 创建告警
        alert_data = {
            "component": "timeout_test",
            "severity": "warning",
            "title": "超时测试",
            "description": "测试修复超时处理",
            "metrics": {"test": 100},
            "source": "test",
            "timestamp": datetime.now().isoformat(),
            "auto_repair_enabled": True,
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = alert_response.json().get("id")

        # 执行可能超时的修复
        timeout_repair = {
            "alert_id": alert_id,
            "action": {
                "type": "long_running",
                "script": "sleep_and_work",
                "params": {"duration": 300},  # 5分钟
            },
        }

        try:
            await asyncio.wait_for(
                http_client.post(
                    "http://localhost:8000/api/v1/repair/execute",
                    json=timeout_repair,
                    timeout=15.0,  # 设置较短超时
                ),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            # 验证超时处理
            timeout_check_response = await http_client.get(
                f"http://localhost:8000/api/v1/repair/{alert_id}/status", timeout=10.0  # noqa: F541
            )

            assert timeout_check_response.status_code == 200
            status = timeout_check_response.json()
            assert status["status"] in ["timeout", "cancelled", "failed"]

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )  # noqa: F541


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
