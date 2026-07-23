# -*- coding: utf-8 -*-
# tests/unit/test_alert_service_unit.py
# 告警服务模块单元测试
from collections import deque  # noqa: F401
from unittest.mock import MagicMock, Mock, patch  # noqa: F401

import pytest  # noqa: F401


class TestAlertService:
    """告警服务测试"""

    def test_alert_service_import(self):
        """测试告警服务导入"""
        from core.alert_service import AlertService, alert_service

        assert AlertService is not None
        assert alert_service is not None
        assert isinstance(alert_service, AlertService)

    def test_alert_service_initialization(self):
        """测试告警服务初始化"""
        from core.alert_service import AlertService

        service = AlertService()
        assert service is not None

    def test_get_alerts_empty(self):
        """测试获取空告警列表"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        # 清空告警历史
        alert_history.clear()

        service = AlertService()
        result = service.get_alerts(limit=10)

        assert result["total"] == 0
        assert result["alerts"] == []

    def test_get_alerts_with_data(self):
        """测试获取有数据的告警列表"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        # 添加测试告警
        alert_history.clear()
        for i in range(5):
            alert_history.append(
                {"metric": f"test_{i}", "value": i * 10, "timestamp": "2024-01-01T10:00:00"}
            )

        service = AlertService()
        result = service.get_alerts(limit=3)

        assert result["total"] == 5
        assert len(result["alerts"]) == 3

    def test_get_alerts_limit_parameter(self):
        """测试limit参数"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()
        for i in range(10):
            alert_history.append({"metric": f"test_{i}", "value": i})

        service = AlertService()

        result1 = service.get_alerts(limit=5)
        assert len(result1["alerts"]) == 5

        result2 = service.get_alerts(limit=20)
        assert len(result2["alerts"]) == 10

    def test_get_alerts_cache_hit(self):
        """测试缓存命中"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService
        from core.query_optimization import query_cache

        alert_history.clear()
        alert_history.append({"metric": "test", "value": 100})

        service = AlertService()

        # 预填充缓存
        cache_key = "alerts_10"
        cached_data = {"total": 1, "alerts": [{"metric": "cached", "value": 50}]}
        query_cache.set(cache_key, cached_data, ttl=60)

        result = service.get_alerts(limit=10)

        # 应该返回缓存的数据
        assert result["alerts"][0]["metric"] == "cached"

    def test_clear_alerts_empty(self):
        """测试清空空告警列表"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()

        service = AlertService()
        result = service.clear_alerts(operator_ip="127.0.0.1")

        assert result["status"] == "ok"
        assert result["deleted_count"] == 0
        assert result["operator_ip"] == "127.0.0.1"

    def test_clear_alerts_with_data(self):
        """测试清空有数据的告警列表"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()
        for i in range(5):
            alert_history.append({"metric": f"test_{i}", "value": i})

        service = AlertService()
        result = service.clear_alerts(operator_ip="192.168.1.1")

        assert result["status"] == "ok"
        assert result["deleted_count"] == 5
        assert result["operator_ip"] == "192.168.1.1"
        assert len(alert_history) == 0

    def test_clear_alerts_default_operator(self):
        """测试清空告警默认操作人"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()
        alert_history.append({"metric": "test", "value": 100})

        service = AlertService()
        result = service.clear_alerts()

        assert result["operator_ip"] == "unknown"

    def test_clear_alerts_memory_exception(self):
        """测试内存清空异常"""
        from core.alert_engine import alert_history  # noqa: F401
        from core.alert_service import AlertService

        # Mock alert_history抛出异常
        with patch("core.alert_service.alert_history") as mock_history:
            mock_history.clear = Mock(side_effect=Exception("Clear error"))

            service = AlertService()
            result = service.clear_alerts(operator_ip="127.0.0.1")

            assert result["status"] == "error"
            assert result["deleted_count"] == 0

    def test_clear_alerts_db_exception(self):
        """测试数据库清空异常"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()
        alert_history.append({"metric": "test", "value": 100})

        # Mock数据库清空抛出异常
        with patch("core.alert_service.db_clear_alerts") as mock_clear:
            mock_clear.side_effect = Exception("DB error")

            service = AlertService()
            result = service.clear_alerts(operator_ip="127.0.0.1")

            # 内存应该清空成功，数据库失败不影响结果
            assert result["status"] == "ok"
            assert result["deleted_count"] == 1

    def test_clear_alerts_db_success(self):
        """测试数据库清空成功"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()
        alert_history.append({"metric": "test", "value": 100})

        # Mock数据库清空返回删除数量
        with patch("core.alert_service.db_clear_alerts") as mock_clear:
            mock_clear.return_value = 5

            service = AlertService()
            result = service.clear_alerts(operator_ip="127.0.0.1")

            assert result["status"] == "ok"
            assert result["deleted_count"] == 1
            assert result["sqlite_deleted"] == 5

    def test_alert_service_default_instance(self):
        """测试默认服务实例"""
        from core.alert_service import alert_service

        assert alert_service is not None
        assert hasattr(alert_service, "get_alerts")
        assert hasattr(alert_service, "clear_alerts")

    def test_get_alerts_cache_key_format(self):
        """测试缓存键格式"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService
        from core.query_optimization import query_cache

        alert_history.clear()
        alert_history.append({"metric": "test", "value": 100})

        service = AlertService()

        # 使用不同的limit来避免缓存冲突
        service.get_alerts(limit=16)

        # 验证缓存键格式
        assert query_cache.get("alerts_16") is not None

    def test_get_alerts_large_limit(self):
        """测试大limit参数"""
        from core.alert_engine import alert_history
        from core.alert_service import AlertService

        alert_history.clear()
        for i in range(5):
            alert_history.append({"metric": f"test_{i}", "value": i})

        service = AlertService()
        result = service.get_alerts(limit=1000)

        # 应该返回所有告警
        assert result["total"] == 5
        assert len(result["alerts"]) == 5
