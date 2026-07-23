# -*- coding: utf-8 -*-
# tests/test_core_business_logic.py
# 核心业务逻辑测试
import os
import sys

import pytest

from core.alert_service import AlertService
from core.api_response_standard import (
    APIResponse,
    PaginatedResponse,
    PaginationParams,
    create_error_response,
)
from core.exception_handler import DatabaseException
from core.query_optimization import BatchQueryOptimizer, QueryCache, query_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAlertService:
    """告警服务测试"""

    def test_get_alerts_with_cache(self):
        """测试带缓存的告警查询"""
        service = AlertService()

        # 第一次查询
        result1 = service.get_alerts(limit=10)
        assert "total" in result1
        assert "alerts" in result1
        assert len(result1["alerts"]) <= 10

        # 第二次查询（应该命中缓存）
        result2 = service.get_alerts(limit=10)
        assert result1 == result2

    def test_get_alerts_different_limits(self):
        """测试不同限制的告警查询"""
        service = AlertService()

        result_5 = service.get_alerts(limit=5)
        result_10 = service.get_alerts(limit=10)

        assert len(result_5["alerts"]) <= 5
        assert len(result_10["alerts"]) <= 10


class TestQueryOptimization:
    """查询优化测试"""

    def test_batch_query_optimizer(self):
        """测试批量查询优化器"""
        optimizer = BatchQueryOptimizer()

        # 测试批量获取逻辑
        test_ids = [1, 2, 3, 4, 5]
        result = optimizer.batch_get_by_ids(
            session=None, model=None, ids=test_ids, id_field="id"  # Mock session  # Mock model
        )

        # 由于session和model是mock，应该返回空字典
        assert isinstance(result, dict)

    def test_query_cache(self):
        """测试查询缓存"""
        cache = QueryCache()

        # 测试缓存设置和获取
        cache.set("test_key", "test_value")
        result = cache.get("test_key")

        assert result == "test_value"

        # 测试缓存失效
        cache.invalidate("test_key")
        result = cache.get("test_key")

        assert result is None

    def test_cache_cleanup(self):
        """测试缓存清理"""
        cache = QueryCache()

        # 设置一些缓存项
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 清理过期缓存
        cache.cleanup_expired()

        # 验证缓存被清理
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestAPIResponseStandard:
    """API响应标准测试"""

    def test_api_response_success(self):
        """测试成功响应"""
        response = APIResponse.success_response(data={"test": "data"}, message="Success")

        assert response["success"] is True
        assert response["data"] == {"test": "data"}
        assert response["message"] == "Success"
        assert "timestamp" in response
        assert "request_id" in response

    def test_api_response_error(self):
        """测试错误响应"""
        response = APIResponse.error_response(
            error="Test error", error_code="TEST_ERROR", message="Test error message"
        )

        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["error_code"] == "TEST_ERROR"
        assert "timestamp" in response
        assert "request_id" in response

    def test_pagination_params(self):
        """测试分页参数"""
        # 正常分页参数
        params = PaginationParams(page=1, size=20)
        assert params.page == 1
        assert params.size == 20
        assert params.offset == 0
        assert params.limit == 20

        # 第二页
        params = PaginationParams(page=2, size=20)
        assert params.offset == 20

        # 边界测试
        with pytest.raises(ValueError):
            PaginationParams(page=0, size=20)

        with pytest.raises(ValueError):
            PaginationParams(page=1, size=0)

        with pytest.raises(ValueError):
            PaginationParams(page=1, size=150)  # 超过max_size

    def test_paginated_response(self):
        """测试分页响应"""

        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = PaginatedResponse(items=items, total=10, page=1, size=3)

        assert response.items == items
        assert response.total == 10
        assert response.page == 1
        assert response.size == 3
        assert response.total_pages == 4
        assert response.has_next is True
        assert response.has_prev is False

        # 转换为字典
        response_dict = response.to_dict()
        assert response_dict["success"] is True
        assert "data" in response_dict


class TestIntegration:
    """集成测试"""

    def test_alert_service_with_cache(self):
        """测试告警服务与缓存集成"""

        service = AlertService()

        # 清除缓存
        query_cache.invalidate()

        # 第一次查询
        _ = service.get_alerts(limit=5)

        # 验证缓存已设置
        cached = query_cache.get("alerts_5")
        assert cached is not None

    def test_error_handling_with_standard_response(self):
        """测试错误处理与标准响应集成"""

        # 创建数据库异常
        exc = DatabaseException("Database connection failed")

        # 创建标准错误响应
        error_response = create_error_response(
            error=exc.message, error_code=exc.error_code, message=exc.message
        )

        assert error_response["success"] is False
        assert error_response["error_code"] == "DATABASE_ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
