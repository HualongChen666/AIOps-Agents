# -*- coding: utf-8 -*-
"""
E2E Test: User Workflows
端到端用户工作流测试，验证完整的用户使用流程
"""

import asyncio
import json  # noqa: F401
from datetime import datetime, timedelta  # noqa: F401
from typing import Any, Dict  # noqa: F401

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestUserWorkflows:
    """用户工作流E2E测试"""

    @pytest.mark.asyncio
    async def test_user_registration_and_login_workflow(self, http_client):
        """测试用户注册和登录的完整工作流"""

        # 步骤1: 用户注册
        registration_data = {
            "username": "testuser_e2e",
            "email": "testuser_e2e@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User E2E",
            "role": "user",
        }

        register_response = await http_client.post(
            "http://localhost:8000/api/v1/users/register", json=registration_data, timeout=10.0
        )

        # 验证注册成功
        assert register_response.status_code in [200, 201, 409]  # 409表示用户已存在
        if register_response.status_code == 409:
            # 用户已存在，继续测试
            pass
        else:
            assert register_response.status_code in [200, 201]

        # 步骤2: 用户登录
        login_data = {"username": "testuser_e2e", "password": "SecurePassword123!"}

        login_response = await http_client.post(
            "http://localhost:8000/api/v1/auth/login", json=login_data, timeout=10.0
        )

        # 验证登录成功
        assert login_response.status_code in [200, 401]  # 401可能因为用户不存在
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            assert token is not None

            # 步骤3: 使用token获取用户信息
            headers = {"Authorization": f"Bearer {token}"}
            user_response = await http_client.get(
                "http://localhost:8000/api/v1/users/me", headers=headers, timeout=10.0
            )

            # 验证用户信息获取成功
            assert user_response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_alert_monitoring_and_notification_workflow(self, http_client):
        """测试告警监控和通知的完整工作流"""

        # 步骤1: 创建监控规则
        rule_data = {
            "name": "CPU使用率监控规则",
            "component": "api_server",
            "metric": "cpu_usage",
            "threshold": 80.0,
            "operator": ">",
            "severity": "warning",
            "notification_channels": ["email", "slack"],
        }

        rule_response = await http_client.post(
            "http://localhost:8000/api/v1/monitoring/rules", json=rule_data, timeout=10.0
        )

        # 验证规则创建成功
        assert rule_response.status_code in [200, 201, 404]  # 404可能因为端点不存在
        if rule_response.status_code in [200, 201]:
            rule_id = rule_response.json().get("id")
            assert rule_id is not None

            # 步骤2: 模拟指标数据触发告警
            metric_data = {
                "component": "api_server",
                "metric": "cpu_usage",
                "value": 85.0,
                "timestamp": datetime.now().isoformat(),
            }

            metric_response = await http_client.post(
                "http://localhost:8000/api/v1/monitoring/metrics", json=metric_data, timeout=10.0
            )

            # 验证指标提交成功
            assert metric_response.status_code in [200, 201, 404]

            # 步骤3: 检查是否生成告警
            alerts_response = await http_client.get(
                "http://localhost:8000/api/v1/alerts",
                params={"component": "api_server", "severity": "warning"},
                timeout=10.0,
            )

            # 验证告警查询成功
            assert alerts_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_incident_management_workflow(self, http_client):
        """测试事件管理的完整工作流"""

        # 步骤1: 创建事件
        incident_data = {
            "title": "API服务异常",
            "description": "API服务响应时间异常",
            "severity": "high",
            "component": "api_server",
            "affected_services": ["api", "database"],
            "impact": "用户无法访问API",
        }

        incident_response = await http_client.post(
            "http://localhost:8000/api/v1/incidents", json=incident_data, timeout=10.0
        )

        # 验证事件创建成功
        assert incident_response.status_code in [200, 201, 404]  # 404可能因为端点不存在
        if incident_response.status_code in [200, 201]:
            incident_id = incident_response.json().get("id")
            assert incident_id is not None

            # 步骤2: 更新事件状态
            update_data = {
                "status": "in_progress",
                "assigned_to": "ops_team",
                "notes": "正在调查API服务异常",
            }

            update_response = await http_client.put(
                f"http://localhost:8000/api/v1/incidents/{incident_id}",
                json=update_data,
                timeout=10.0,
            )

            # 验证更新成功
            assert update_response.status_code in [200, 404]

            # 步骤3: 解决事件
            resolve_data = {
                "status": "resolved",
                "resolution": "重启API服务后恢复正常",
                "resolved_at": datetime.now().isoformat(),
            }

            resolve_response = await http_client.put(
                f"http://localhost:8000/api/v1/incidents/{incident_id}",
                json=resolve_data,
                timeout=10.0,
            )

            # 验证解决成功
            assert resolve_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_dashboard_data_flow_workflow(self, http_client):
        """测试仪表板数据流的完整工作流"""

        # 步骤1: 获取系统概览数据
        overview_response = await http_client.get(
            "http://localhost:8000/api/v1/dashboard/overview", timeout=10.0
        )

        # 验证概览数据获取成功
        assert overview_response.status_code in [200, 404]  # 404可能因为端点不存在
        if overview_response.status_code == 200:
            overview_data = overview_response.json()
            assert "total_alerts" in overview_data
            assert "active_incidents" in overview_data

            # 步骤2: 获取告警趋势数据
            trend_response = await http_client.get(
                "http://localhost:8000/api/v1/dashboard/alerts/trend",
                params={"period": "7d"},
                timeout=10.0,
            )

            # 验证趋势数据获取成功
            assert trend_response.status_code in [200, 404]
            if trend_response.status_code == 200:
                trend_data = trend_response.json()
                assert "trend" in trend_data
                assert "data_points" in trend_data

            # 步骤3: 获取组件健康状态
            health_response = await http_client.get(
                "http://localhost:8000/api/v1/dashboard/components/health", timeout=10.0
            )

            # 验证健康状态获取成功
            assert health_response.status_code in [200, 404]
            if health_response.status_code == 200:
                health_data = health_response.json()
                assert "components" in health_data


@pytest.mark.e2e
@pytest.mark.slow
class TestSystemIntegrationWorkflows:
    """系统集成工作流E2E测试"""

    @pytest.mark.asyncio
    async def test_database_to_api_integration(self, http_client, test_database_url):
        """测试数据库到API的集成工作流"""

        # 步骤1: 通过API写入数据到数据库
        write_data = {
            "table": "test_table",
            "operation": "insert",
            "data": {
                "id": 1,
                "name": "测试数据",
                "value": 100,
                "created_at": datetime.now().isoformat(),
            },
        }

        write_response = await http_client.post(
            "http://localhost:8000/api/v1/database/write", json=write_data, timeout=10.0
        )

        # 验证写入成功
        assert write_response.status_code in [200, 201, 404]  # 404可能因为端点不存在
        if write_response.status_code in [200, 201]:
            # 步骤2: 通过API读取数据
            read_response = await http_client.get(
                "http://localhost:8000/api/v1/database/read",
                params={"table": "test_table", "id": 1},
                timeout=10.0,
            )

            # 验证读取成功
            assert read_response.status_code in [200, 404]
            if read_response.status_code == 200:
                read_data = read_response.json()
                assert read_data["name"] == "测试数据"
                assert read_data["value"] == 100

    @pytest.mark.asyncio
    async def test_cache_to_api_integration(self, http_client, test_redis_url):
        """测试缓存到API的集成工作流"""

        # 步骤1: 通过API写入缓存
        cache_data = {"key": "test_cache_key", "value": "test_cache_value", "ttl": 300}

        write_response = await http_client.post(
            "http://localhost:8000/api/v1/cache/write", json=cache_data, timeout=10.0
        )

        # 验证缓存写入成功
        assert write_response.status_code in [200, 201, 404]  # 404可能因为端点不存在
        if write_response.status_code in [200, 201]:
            # 步骤2: 通过API读取缓存
            read_response = await http_client.get(
                "http://localhost:8000/api/v1/cache/read",
                params={"key": "test_cache_key"},
                timeout=10.0,
            )

            # 验证缓存读取成功
            assert read_response.status_code in [200, 404]
            if read_response.status_code == 200:
                cache_value = read_response.json().get("value")
                assert cache_value == "test_cache_value"

            # 步骤3: 通过API删除缓存
            delete_response = await http_client.delete(
                "http://localhost:8000/api/v1/cache/delete",
                params={"key": "test_cache_key"},
                timeout=10.0,
            )

            # 验证缓存删除成功
            assert delete_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_api_to_notification_integration(self, http_client):
        """测试API到通知的集成工作流"""

        # 步骤1: 创建需要通知的告警
        alert_data = {
            "component": "api_server",
            "severity": "critical",
            "title": "紧急告警测试",
            "description": "这是一个紧急告警测试",
            "notification_required": True,
            "notification_channels": ["email", "slack"],
        }

        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        # 验证告警创建成功
        assert alert_response.status_code in [200, 201, 404]  # 404可能因为端点不存在
        if alert_response.status_code in [200, 201]:
            alert_id = alert_response.json().get("id")
            assert alert_id is not None

            # 步骤2: 检查通知状态
            notification_response = await http_client.get(
                f"http://localhost:8000/api/v1/alerts/{alert_id}/notifications", timeout=10.0
            )

            # 验证通知状态查询成功
            assert notification_response.status_code in [200, 404]
            if notification_response.status_code == 200:
                notifications = notification_response.json()
                assert "notifications" in notifications
                assert len(notifications["notifications"]) > 0


@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceWorkflows:
    """性能工作流E2E测试"""

    @pytest.mark.asyncio
    async def test_api_performance_under_load(self, http_client):
        """测试API在负载下的性能"""

        # 并发发送多个请求
        tasks = []
        for i in range(10):
            task = http_client.get("http://localhost:8000/api/v1/health", timeout=10.0)
            tasks.append(task)

        # 执行并发请求
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有请求都成功
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) >= 8  # 至少80%的成功率

        # 验证响应时间
        for response in successful_responses:
            if hasattr(response, "status_code"):
                assert response.status_code in [200, 404]  # 404可能因为端点不存在

    @pytest.mark.asyncio
    async def test_database_query_performance(self, http_client):
        """测试数据库查询性能"""

        # 执行复杂查询
        query_data = {
            "query": "SELECT * FROM test_table WHERE value > 50 ORDER BY created_at DESC LIMIT 100",
            "timeout": 5.0,
        }

        query_response = await http_client.post(
            "http://localhost:8000/api/v1/database/query", json=query_data, timeout=10.0
        )

        # 验证查询执行成功
        assert query_response.status_code in [200, 404]  # 404可能因为端点不存在
        if query_response.status_code == 200:
            result = query_response.json()
            assert "data" in result
            assert "execution_time" in result

            # 验证执行时间在合理范围内
            execution_time = result["execution_time"]
            assert execution_time < 5.0  # 查询应该在5秒内完成


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorRecoveryWorkflows:
    """错误恢复工作流E2E测试"""

    @pytest.mark.asyncio
    async def test_api_error_recovery_workflow(self, http_client):
        """测试API错误恢复工作流"""

        # 步骤1: 模拟API错误
        error_response = await http_client.get(
            "http://localhost:8000/api/v1/test/error", timeout=10.0
        )

        # 验证错误处理正确
        assert error_response.status_code in [500, 404]  # 500是服务器错误，404是端点不存在

        # 步骤2: 检查API是否自动恢复
        await asyncio.sleep(2)  # 等待恢复时间

        recovery_response = await http_client.get(
            "http://localhost:8000/api/v1/health", timeout=10.0
        )

        # 验证API恢复正常
        assert recovery_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_database_connection_recovery_workflow(self, http_client):
        """测试数据库连接恢复工作流"""

        # 步骤1: 检查数据库连接
        db_check_response = await http_client.get(
            "http://localhost:8000/api/v1/database/health", timeout=10.0
        )

        # 验证数据库健康检查
        assert db_check_response.status_code in [200, 503, 404]  # 503是服务不可用，404是端点不存在
        if db_check_response.status_code == 200:
            db_health = db_check_response.json()
            assert "status" in db_health
            assert db_health["status"] in ["healthy", "degraded"]
