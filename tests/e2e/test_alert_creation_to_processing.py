# -*- coding: utf-8 -*-
"""
E2E Test: Alert Creation to Processing Workflow
真实E2E测试：告警创建到处理的完整工作流，不使用Mock
"""

import asyncio
import time  # noqa: F401
from datetime import datetime, timedelta
from typing import Any, Dict  # noqa: F401

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestAlertCreationToProcessingWorkflow:
    """告警创建到处理的完整工作流E2E测试"""

    @pytest.mark.asyncio
    async def test_complete_alert_lifecycle(self, http_client):
        """测试完整的告警生命周期：创建→分析→处理→关闭"""

        # 步骤1: 创建告警
        alert_data = {
            "component": "api_server",
            "severity": "critical",
            "title": "API响应时间过高",
            "description": "API服务响应时间超过阈值",
            "metrics": {
                "response_time_ms": 5000,
                "error_rate": 0.15,
                "cpu_usage": 85.0,
                "memory_usage": 75.0,
            },
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
        }

        # 创建告警
        create_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        # 验证告警创建成功
        assert create_response.status_code in [200, 201, 202]
        alert_id = create_response.json().get("id")
        assert alert_id is not None

        # 步骤2: 获取告警详情
        await asyncio.sleep(1)  # 等待系统处理
        get_response = await http_client.get(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )

        assert get_response.status_code == 200
        alert_detail = get_response.json()
        assert alert_detail["id"] == alert_id
        assert alert_detail["severity"] == "critical"

        # 步骤3: 更新告警状态（模拟处理过程）
        update_data = {"status": "processing", "assigned_to": "admin", "notes": "开始处理告警"}

        update_response = await http_client.put(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", json=update_data, timeout=10.0
        )

        assert update_response.status_code in [200, 202]

        # 步骤4: 添加处理记录
        action_data = {
            "alert_id": alert_id,
            "action": "investigation",
            "performed_by": "admin",
            "notes": "开始调查根本原因",
            "timestamp": datetime.now().isoformat(),
        }

        action_response = await http_client.post(
            "http://localhost:8000/api/v1/alert-actions", json=action_data, timeout=10.0
        )

        assert action_response.status_code in [200, 201, 202]

        # 步骤5: 关闭告警
        close_data = {
            "status": "resolved",
            "resolution": "问题已修复",
            "resolved_at": datetime.now().isoformat(),
        }

        close_response = await http_client.put(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", json=close_data, timeout=10.0
        )

        assert close_response.status_code in [200, 202]

        # 步骤6: 验证告警已关闭
        final_response = await http_client.get(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )

        assert final_response.status_code == 200
        final_alert = final_response.json()
        assert final_alert["status"] == "resolved"

        # 清理：删除测试告警
        cleanup_response = await http_client.delete(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )
        assert cleanup_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_alert_aggregation_and_correlation(self, http_client):
        """测试告警聚合和关联功能"""

        # 创建多个相关告警
        base_time = datetime.now()
        alerts = []

        for i in range(3):
            alert_data = {
                "component": "database_server",
                "severity": "warning",
                "title": f"数据库连接问题 #{i + 1}",
                "description": "数据库连接池耗尽",
                "metrics": {
                    "connection_pool_usage": 0.9 + i * 0.03,
                    "query_time_ms": 2000 + i * 500,
                },
                "source": "monitoring",
                "timestamp": (base_time + timedelta(seconds=i * 10)).isoformat(),
            }

            response = await http_client.post(
                "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
            )

            assert response.status_code in [200, 201, 202]
            alerts.append(response.json())

        # 等待聚合处理
        await asyncio.sleep(2)

        # 获取聚合后的告警
        aggregated_response = await http_client.get(
            "http://localhost:8000/api/v1/alerts/aggregated",
            params={"component": "database_server"},
            timeout=10.0,
        )

        assert aggregated_response.status_code == 200
        aggregated_alerts = aggregated_response.json()

        # 验证聚合逻辑
        assert len(aggregated_alerts) >= 1

        # 清理测试数据
        for alert in alerts:
            await http_client.delete(
                f"http://localhost:8000/api/v1/alerts/{alert['id']}", timeout=10.0
            )

    @pytest.mark.asyncio
    async def test_alert_notification_workflow(self, http_client):
        """测试告警通知工作流"""

        # 创建高优先级告警
        alert_data = {
            "component": "payment_service",
            "severity": "critical",
            "title": "支付服务异常",
            "description": "支付处理失败率超过阈值",
            "metrics": {"failure_rate": 0.25, "transaction_volume": 1000},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
        }

        create_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        assert create_response.status_code in [200, 201, 202]
        alert_id = create_response.json().get("id")

        # 等待通知处理
        await asyncio.sleep(1)

        # 检查通知历史
        notifications_response = await http_client.get(
            f"http://localhost:8000/api/v1/notifications?alert_id={alert_id}", timeout=10.0
        )

        assert notifications_response.status_code == 200
        notifications = notifications_response.json()

        # 验证通知已发送
        assert len(notifications) >= 1

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)

    @pytest.mark.asyncio
    async def test_alert_escalation_workflow(self, http_client):
        """测试告警升级工作流"""

        # 创建中等严重性告警
        alert_data = {
            "component": "storage_service",
            "severity": "warning",
            "title": "存储空间不足",
            "description": "存储空间使用率超过阈值",
            "metrics": {"disk_usage_percent": 85.0, "available_gb": 15.0},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
        }

        create_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        assert create_response.status_code in [200, 201, 202]
        alert_id = create_response.json().get("id")

        # 模拟告警未及时处理，自动升级
        await asyncio.sleep(1)

        # 手动触发升级
        escalate_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/escalate",
            json={"reason": "未在规定时间内处理"},
            timeout=10.0,
        )

        assert escalate_response.status_code in [200, 202]

        # 验证升级状态
        get_response = await http_client.get(
            f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
        )

        assert get_response.status_code == 200
        alert_detail = get_response.json()
        assert alert_detail.get("escalation_level") is not None

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)


@pytest.mark.e2e
@pytest.mark.slow
class TestAlertMetricsAndAnalytics:
    """告警指标和分析E2E测试"""

    @pytest.mark.asyncio
    async def test_alert_metrics_collection(self, http_client):
        """测试告警指标收集"""

        # 创建不同类型的告警
        severity_levels = ["info", "warning", "critical"]
        created_alerts = []

        for severity in severity_levels:
            alert_data = {
                "component": f"test_service_{severity}",
                "severity": severity,
                "title": f"测试告警_{severity}",
                "description": "测试用告警",
                "metrics": {"test_metric": 100},
                "source": "test",
                "timestamp": datetime.now().isoformat(),
            }

            response = await http_client.post(
                "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
            )

            if response.status_code in [200, 201, 202]:
                created_alerts.append(response.json())

        # 等待指标处理
        await asyncio.sleep(2)

        # 获取告警指标
        metrics_response = await http_client.get(
            "http://localhost:8000/api/v1/alerts/metrics", timeout=10.0
        )

        assert metrics_response.status_code == 200
        metrics = metrics_response.json()

        # 验证指标数据
        assert "total_alerts" in metrics
        assert "by_severity" in metrics
        assert metrics["total_alerts"] >= len(created_alerts)

        # 清理
        for alert in created_alerts:
            await http_client.delete(
                f"http://localhost:8000/api/v1/alerts/{alert['id']}", timeout=10.0
            )

    @pytest.mark.asyncio
    async def test_alert_trend_analysis(self, http_client):
        """测试告警趋势分析"""

        # 创建时间序列告警
        base_time = datetime.now()
        for i in range(10):
            alert_data = {
                "component": "trend_test_service",
                "severity": "warning" if i < 5 else "critical",
                "title": f"趋势测试告警#{i + 1}",
                "description": "用于趋势分析的测试告警",
                "metrics": {"metric_value": 100 + i * 10},
                "source": "test",
                "timestamp": (base_time - timedelta(minutes=10 - i)).isoformat(),
            }

            await http_client.post(
                "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
            )

        # 等待趋势分析处理
        await asyncio.sleep(2)

        # 获取趋势分析
        trend_response = await http_client.get(
            "http://localhost:8000/api/v1/alerts/trends",
            params={"component": "trend_test_service", "hours": 1},
            timeout=10.0,
        )

        assert trend_response.status_code == 200
        trends = trend_response.json()

        # 验证趋势数据
        assert "trend" in trends
        assert "data_points" in trends
        assert len(trends["data_points"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
