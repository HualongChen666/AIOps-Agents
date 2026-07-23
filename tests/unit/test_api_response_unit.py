# -*- coding: utf-8 -*-
# tests/unit/test_api_response_unit.py
# API响应模块单元测试
import json  # noqa: F401
from datetime import datetime, timezone  # noqa: F401
from unittest.mock import AsyncMock, Mock, patch  # noqa: F401

import pytest


class TestAPIResponse:
    """API响应测试"""

    def test_success_response_basic(self):
        """测试基本成功响应"""
        from core.api_response import APIResponse

        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "Success"
        assert response["data"] is None
        assert "timestamp" in response

    def test_success_response_with_data(self):
        """测试带数据的成功响应"""
        from core.api_response import APIResponse

        test_data = {"user_id": 123, "name": "test"}
        response = APIResponse.success(data=test_data)

        assert response["success"] is True
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_response_with_message(self):
        """测试带自定义消息的成功响应"""
        from core.api_response import APIResponse

        response = APIResponse.success(message="Operation completed")

        assert response["success"] is True
        assert response["message"] == "Operation completed"

    def test_success_response_with_meta(self):
        """测试带元数据的成功响应"""
        from core.api_response import APIResponse

        meta = {"page": 1, "total": 100}
        response = APIResponse.success(meta=meta)

        assert response["success"] is True
        assert response["meta"] == meta
        assert "timestamp" in response

    def test_error_response_basic(self):
        """测试基本错误响应"""
        from core.api_response import APIResponse

        response = APIResponse.error(code="TEST_ERROR", message="Test error message")

        assert response["success"] is False
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test error message"
        assert response["error"]["details"] is None
        assert "timestamp" in response

    def test_error_response_with_details(self):
        """测试带详细信息的错误响应"""
        from core.api_response import APIResponse

        response = APIResponse.error(
            code="VALIDATION_ERROR", message="Validation failed", details="Field 'name' is required"
        )

        assert response["success"] is False
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["details"] == "Field 'name' is required"

    def test_error_response_with_status_code(self):
        """测试带状态码的错误响应"""
        from core.api_response import APIResponse

        response = APIResponse.error(
            code="NOT_FOUND", message="Resource not found", status_code=404
        )

        assert response["success"] is False
        assert response["error"]["code"] == "NOT_FOUND"

    def test_timestamp_format(self):
        """测试时间戳格式"""
        from core.api_response import APIResponse

        response = APIResponse.success()

        assert "timestamp" in response
        assert response["timestamp"].endswith("Z")
        # 验证是ISO格式（简单验证）
        assert "T" in response["timestamp"]


class TestAPIResponseMiddleware:
    """API响应中间件测试"""

    @pytest.mark.asyncio
    async def test_middleware_with_json_response(self):
        """测试中间件处理JSON响应"""
        from core.api_response import api_response_middleware

        request = Mock()
        request.url.path = "/api/test"

        call_next = AsyncMock()

        # 模拟已经是统一格式的响应
        response = Mock()
        response.body = b'{"success": true, "message": "test"}'
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response

        result = await api_response_middleware(request, call_next)  # noqa: F841

        # 应该直接返回原响应
        assert result == response  # noqa: F841

    @pytest.mark.asyncio
    async def test_middleware_wraps_non_standard_response(self):
        """测试中间件包装非标准响应"""
        from fastapi.responses import JSONResponse

        from core.api_response import api_response_middleware

        request = Mock()
        request.url.path = "/api/test"

        call_next = AsyncMock()

        # 模拟非统一格式的JSON响应
        original_response = JSONResponse(content={"data": "test"})
        call_next.return_value = original_response

        result = await api_response_middleware(request, call_next)  # noqa: F841

        # 应该包装为统一格式
        assert result is not None

        # 应该被包装为统一格式
        assert isinstance(result, JSONResponse)

    @pytest.mark.asyncio
    async def test_middleware_already_unified_response(self):
        """测试中间件处理已经是统一格式的响应"""
        from fastapi.responses import JSONResponse

        from core.api_response import APIResponse, api_response_middleware

        request = Mock()
        request.url.path = "/api/test"

        call_next = AsyncMock()

        # 模拟已经是统一格式的响应
        unified_data = APIResponse.success(data={"message": "test"})
        original_response = JSONResponse(content=unified_data)
        call_next.return_value = original_response

        result = await api_response_middleware(request, call_next)  # noqa: F841

        # 应该直接返回原响应
        assert result == original_response  # noqa: F841

    @pytest.mark.asyncio
    async def test_middleware_invalid_json_response(self):
        """测试中间件处理无效JSON响应"""
        from fastapi.responses import JSONResponse

        from core.api_response import api_response_middleware

        request = Mock()
        request.url.path = "/api/test"

        call_next = AsyncMock()

        # 模拟无效JSON的响应
        response = Mock(spec=JSONResponse)
        response.body = b"invalid json content"
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response

        result = await api_response_middleware(request, call_next)  # noqa: F841

        # 解析失败时应该返回原响应
        assert result == response  # noqa: F841

    @pytest.mark.asyncio
    async def test_middleware_adds_process_time(self):
        """测试中间件添加处理时间"""
        from core.api_response import api_response_middleware

        request = Mock()
        request.url.path = "/api/test"

        call_next = AsyncMock()

        response = Mock()
        response.body = b'{"success": true}'
        response.headers = {}
        call_next.return_value = response

        result = await api_response_middleware(request, call_next)  # noqa: F841

        # 应该添加处理时间头
        assert "X-Process-Time" in response.headers

    @pytest.mark.asyncio
    async def test_middleware_non_json_response(self):
        """测试中间件处理非JSON响应"""
        from core.api_response import api_response_middleware

        request = Mock()
        request.url.path = "/api/test"

        call_next = AsyncMock()

        # 模拟非JSON响应
        response = Mock()
        response.headers = {}
        call_next.return_value = response

        result = await api_response_middleware(request, call_next)  # noqa: F841

        # 非JSON响应应该直接返回
        assert result == response  # noqa: F841


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
