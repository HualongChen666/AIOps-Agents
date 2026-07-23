# -*- coding: utf-8 -*-
# tests/test_api_response_format.py
# API响应格式测试
import pytest

from core.api_response_standard import (
    APIResponse,
    ErrorCode,
    PaginatedResponse,
    PaginationParams,
    create_error_response,
    create_paginated_response,
    create_success_response,
)


class TestAPIResponse:
    """API响应类测试"""

    def test_success_response_creation(self):
        """测试成功响应创建"""
        response = APIResponse(success=True, data={"key": "value"}, message="Operation successful")

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Operation successful"
        assert response.error is None
        assert response.error_code is None

    def test_error_response_creation(self):
        """测试错误响应创建"""
        response = APIResponse(
            success=False,
            error="Operation failed",
            error_code="OPERATION_ERROR",
            message="Detailed error message",
        )

        assert response.success is False
        assert response.error == "Operation failed"
        assert response.error_code == "OPERATION_ERROR"
        assert response.message == "Detailed error message"

    def test_response_to_dict(self):
        """测试响应转换为字典"""
        response = APIResponse(success=True, data={"test": "data"}, message="Test message")

        response_dict = response.to_dict()

        assert response_dict["success"] is True
        assert response_dict["data"] == {"test": "data"}
        assert response_dict["message"] == "Test message"
        assert "timestamp" in response_dict
        assert "request_id" in response_dict

    def test_response_with_request_id(self):
        """测试带请求ID的响应"""
        custom_request_id = "custom-request-123"
        response = APIResponse(success=True, data={}, request_id=custom_request_id)

        assert response.request_id == custom_request_id


class TestErrorCode:
    """错误码枚举测试"""

    def test_error_code_values(self):
        """测试错误码值"""
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.AUTHENTICATION_ERROR == "AUTHENTICATION_ERROR"
        assert ErrorCode.AUTHORIZATION_ERROR == "AUTHORIZATION_ERROR"
        assert ErrorCode.RESOURCE_NOT_FOUND == "RESOURCE_NOT_FOUND"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"
        assert ErrorCode.RATE_LIMIT_EXCEEDED == "RATE_LIMIT_EXCEEDED"
        assert ErrorCode.SERVICE_UNAVAILABLE == "SERVICE_UNAVAILABLE"

    def test_business_error_codes(self):
        """测试业务错误码"""
        assert ErrorCode.ALERT_NOT_FOUND == "ALERT_NOT_FOUND"
        assert ErrorCode.ALERT_PROCESSING_FAILED == "ALERT_PROCESSING_FAILED"
        assert ErrorCode.AI_ANALYSIS_FAILED == "AI_ANALYSIS_FAILED"
        assert ErrorCode.DATABASE_ERROR == "DATABASE_ERROR"


class TestPaginationParams:
    """分页参数测试"""

    def test_normal_pagination(self):
        """测试正常分页参数"""
        params = PaginationParams(page=1, size=20)

        assert params.page == 1
        assert params.size == 20
        assert params.offset == 0
        assert params.limit == 20

    def test_second_page(self):
        """测试第二页"""
        params = PaginationParams(page=2, size=20)

        assert params.page == 2
        assert params.offset == 20

    def test_different_page_sizes(self):
        """测试不同的页面大小"""
        params_10 = PaginationParams(page=1, size=10)
        params_50 = PaginationParams(page=1, size=50)

        assert params_10.size == 10
        assert params_50.size == 50

    def test_invalid_page(self):
        """测试无效页码"""
        with pytest.raises(ValueError):
            PaginationParams(page=0, size=20)

        with pytest.raises(ValueError):
            PaginationParams(page=-1, size=20)

    def test_invalid_size(self):
        """测试无效大小"""
        with pytest.raises(ValueError):
            PaginationParams(page=1, size=0)

        with pytest.raises(ValueError):
            PaginationParams(page=1, size=-1)

    def test_size_exceeds_max(self):
        """测试大小超过最大值"""
        with pytest.raises(ValueError):
            PaginationParams(page=1, size=150)

    def test_custom_max_size(self):
        """测试自定义最大大小"""
        params = PaginationParams(page=1, size=80, max_size=100)
        assert params.size == 80

        with pytest.raises(ValueError):
            PaginationParams(page=1, size=150, max_size=100)


class TestPaginatedResponse:
    """分页响应测试"""

    def test_paginated_response_creation(self):
        """测试分页响应创建"""
        items = [{"id": i} for i in range(1, 4)]
        response = PaginatedResponse(items=items, total=10, page=1, size=3)

        assert len(response.items) == 3
        assert response.total == 10
        assert response.page == 1
        assert response.size == 3
        assert response.total_pages == 4
        assert response.has_next is True
        assert response.has_prev is False

    def test_last_page(self):
        """测试最后一页"""
        items = [{"id": 10}]
        response = PaginatedResponse(items=items, total=10, page=4, size=3)

        assert response.has_next is False
        assert response.has_prev is True

    def test_single_page(self):
        """测试单页"""
        items = [{"id": i} for i in range(1, 6)]
        response = PaginatedResponse(items=items, total=5, page=1, size=10)

        assert response.total_pages == 1
        assert response.has_next is False
        assert response.has_prev is False

    def test_empty_response(self):
        """测试空响应"""
        response = PaginatedResponse(items=[], total=0, page=1, size=10)

        assert response.total == 0
        assert response.total_pages == 0
        assert response.has_next is False
        assert response.has_prev is False


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_success_response(self):
        """测试创建成功响应"""
        response = create_success_response(
            data={"result": "success"}, message="Operation completed"
        )

        assert response["success"] is True
        assert response["data"] == {"result": "success"}
        assert response["message"] == "Operation completed"

    def test_create_error_response(self):
        """测试创建错误响应"""
        response = create_error_response(
            error="Something went wrong",
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Detailed error",
        )

        assert response["success"] is False
        assert response["error"] == "Something went wrong"
        assert response["error_code"] == "INTERNAL_ERROR"

    def test_create_paginated_response(self):
        """测试创建分页响应"""
        items = [{"id": i} for i in range(1, 11)]
        response = create_paginated_response(items=items, total=25, page=1, size=10)

        assert response["success"] is True
        assert response["data"]["items"] == items
        assert response["data"]["total"] == 25
        assert response["data"]["page"] == 1
        assert response["data"]["size"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
