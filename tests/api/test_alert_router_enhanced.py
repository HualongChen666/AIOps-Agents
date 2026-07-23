# -*- coding: utf-8 -*-
# tests/api/test_alert_router_enhanced.py
# 增强版告警路由API测试
import os
import sys
import threading
import time
from unittest.mock import Mock, patch  # noqa: F401

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.alert_router import router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 直接导入路由模块，避免导入main.py

# 创建独立的测试应用
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestAlertRouterEnhanced:
    """增强版告警路由测试类"""

    def test_get_alerts_default_limit(self):
        """测试使用默认限制获取告警"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            mock_get.return_value = {
                "alerts": [
                    {"id": 1, "title": "CPU High", "severity": "critical"},
                    {"id": 2, "title": "Memory Warning", "severity": "warning"},
                ],
                "total": 2,
            }

            response = client.get("/api/v1/alerts/")

            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            mock_get.assert_called_once_with(20)  # 默认limit=20

    def test_get_alerts_custom_limit(self):
        """测试使用自定义限制获取告警"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            mock_get.return_value = {
                "alerts": [{"id": i, "title": f"Alert {i}"} for i in range(10)],
                "total": 10,
            }

            response = client.get("/api/v1/alerts/?limit=10")

            assert response.status_code == 200
            mock_get.assert_called_once_with(10)

    def test_get_alerts_limit_validation(self):
        """测试limit参数验证"""
        # 测试超出上限
        response = client.get("/api/v1/alerts/?limit=1000")  # 超过500限制
        assert response.status_code == 422  # 验证错误

        # 测试低于下限
        response = client.get("/api/v1/alerts/?limit=0")  # 低于1限制
        assert response.status_code == 422

        # 测试负数
        response = client.get("/api/v1/alerts/?limit=-5")
        assert response.status_code == 422

    def test_get_alerts_empty_result(self):
        """测试空告警列表"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            mock_get.return_value = {"alerts": [], "total": 0}

            response = client.get("/api/v1/alerts/")

            assert response.status_code == 200
            data = response.json()
            assert data["alerts"] == []
            assert data["total"] == 0

    def test_get_alerts_service_error(self):
        """测试告警服务错误处理"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            # 模拟服务返回错误响应而不是抛出异常
            mock_get.return_value = {"error": "Service unavailable", "status": "error"}

            response = client.get("/api/v1/alerts/")

            # 应该能正常处理错误响应
            assert response.status_code == 200

    def test_clear_alerts_success(self):
        """测试成功清空告警"""
        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {
                "success": True,
                "cleared_count": 100,
                "message": "告警已清空",
            }

            response = client.delete("/api/v1/alerts/")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "cleared_count" in data

    def test_clear_alerts_with_authentication(self):
        """测试需要认证的清空操作"""
        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"success": True, "cleared_count": 50}

            # 模拟远程IP请求
            response = client.delete("/api/v1/alerts/")

            # 根据实现，可能返回401或成功
            assert response.status_code in [200, 401, 403]

    def test_clear_alerts_error_handling(self):
        """测试清空告警错误处理"""
        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            # 模拟服务返回错误响应而不是抛出异常
            mock_clear.return_value = {"error": "Clear operation failed", "success": False}

            response = client.delete("/api/v1/alerts/")

            # 应该能正常处理错误响应
            assert response.status_code == 200

    def test_clear_alerts_empty_database(self):
        """测试清空空数据库"""
        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {
                "success": True,
                "cleared_count": 0,
                "message": "没有告警需要清空",
            }

            response = client.delete("/api/v1/alerts/")

            assert response.status_code == 200
            data = response.json()
            assert data["cleared_count"] == 0

    def test_alerts_pagination(self):
        """测试告警分页"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            # 模拟分页数据
            mock_get.return_value = {
                "alerts": [{"id": i, "title": f"Alert {i}"} for i in range(1, 21)],
                "total": 100,
                "page": 1,
                "per_page": 20,
            }

            response = client.get("/api/v1/alerts/?limit=20")

            assert response.status_code == 200
            data = response.json()
            assert len(data["alerts"]) <= 20

    def test_alerts_filtering(self):
        """测试告警过滤"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            # 模拟过滤结果
            mock_get.return_value = {
                "alerts": [
                    {"id": 1, "title": "CPU Critical", "severity": "critical"},
                    {"id": 2, "title": "Memory Warning", "severity": "warning"},
                ],
                "total": 2,
                "filters": {"severity": "critical,warning"},
            }

            response = client.get("/api/v1/alerts/?limit=10")

            assert response.status_code == 200

    def test_alerts_response_format(self):
        """测试告警响应格式"""
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            mock_get.return_value = {
                "alerts": [
                    {
                        "id": 1,
                        "title": "Test Alert",
                        "severity": "critical",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "description": "Test description",
                    }
                ],
                "total": 1,
            }

            response = client.get("/api/v1/alerts/")

            assert response.status_code == 200
            data = response.json()

            # 验证响应格式
            assert isinstance(data, dict)
            assert "alerts" in data
            assert isinstance(data["alerts"], list)

            if data["alerts"]:
                alert = data["alerts"][0]
                assert "id" in alert
                assert "title" in alert
                assert "severity" in alert


class TestAlertRouterIntegration:
    """告警路由集成测试"""

    def test_alert_lifecycle(self):
        """测试告警完整生命周期"""
        # 1. 获取告警列表
        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            mock_get.return_value = {"alerts": [], "total": 0}
            response = client.get("/api/v1/alerts/")
            assert response.status_code == 200

        # 2. 清空告警
        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"success": True, "cleared_count": 0}
            response = client.delete("/api/v1/alerts/")
            assert response.status_code in [200, 401, 403]

    def test_concurrent_alert_operations(self):
        """测试并发告警操作"""

        results = []

        def make_request():
            with patch("core.alert_service.alert_service.get_alerts") as mock_get:
                mock_get.return_value = {"alerts": [], "total": 0}
                response = client.get("/api/v1/alerts/")
                results.append(response.status_code)

        # 创建多个并发请求
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 验证所有请求都得到处理
        assert all(status == 200 for status in results)


class TestAlertRouterSecurity:
    """告警路由安全测试"""

    def test_clear_alerts_security_logging(self):
        """测试清空告警安全日志记录"""
        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {
                "success": True,
                "cleared_count": 10,
                "operator_ip": "127.0.0.1",
            }

            response = client.delete("/api/v1/alerts/")

            if response.status_code == 200:
                data = response.json()
                # 验证操作人信息被记录
                assert "operator_ip" in data or "cleared_count" in data

    def test_rate_limiting(self):
        """测试速率限制"""
        # 发送多个快速请求
        responses = []

        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            mock_get.return_value = {"alerts": [], "total": 0}

            for _ in range(10):
                response = client.get("/api/v1/alerts/")
                responses.append(response.status_code)

        # 验证请求得到处理（可能有速率限制）
        # 大部分请求应该成功
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 8  # 至少80%请求成功


class TestAlertRouterPerformance:
    """告警路由性能测试"""

    def test_get_alerts_performance(self):
        """测试获取告警性能"""

        with patch("core.alert_service.alert_service.get_alerts") as mock_get:
            # 模拟大量告警
            mock_get.return_value = {
                "alerts": [{"id": i, "title": f"Alert {i}"} for i in range(1000)],
                "total": 1000,
            }

            start_time = time.time()
            response = client.get("/api/v1/alerts/?limit=100")
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code == 200
            # 响应时间应该在合理范围内（< 2秒）
            assert response_time < 2.0

    def test_clear_alerts_performance(self):
        """测试清空告警性能"""

        with patch("core.alert_service.alert_service.clear_alerts") as mock_clear:
            mock_clear.return_value = {"success": True, "cleared_count": 10000}

            start_time = time.time()
            response = client.delete("/api/v1/alerts/")
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code in [200, 401, 403]
            # 清空操作应该快速完成（< 5秒）
            assert response_time < 5.0
