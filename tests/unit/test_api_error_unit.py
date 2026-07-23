# -*- coding: utf-8 -*-
# tests/unit/test_api_error_unit.py
# API错误处理模块单元测试
from unittest.mock import MagicMock, Mock, patch  # noqa: F401

import pytest


class TestAPIErrorCode:
    """API错误代码测试"""

    def test_api_error_code_constants(self):
        """测试API错误代码常量"""
        from core.api_error import APIErrorCode

        assert hasattr(APIErrorCode, "INTERNAL_ERROR")
        assert hasattr(APIErrorCode, "VALIDATION_ERROR")
        assert hasattr(APIErrorCode, "NOT_FOUND")
        assert hasattr(APIErrorCode, "UNAUTHORIZED")
        assert hasattr(APIErrorCode, "FORBIDDEN")
        assert hasattr(APIErrorCode, "CONFLICT")

        assert hasattr(APIErrorCode, "RESOURCE_NOT_FOUND")
        assert hasattr(APIErrorCode, "INVALID_PARAMETER")
        assert hasattr(APIErrorCode, "OPERATION_FAILED")
        assert hasattr(APIErrorCode, "STATE_INVALID")

    def test_api_error_code_values(self):
        """测试API错误代码值"""
        from core.api_error import APIErrorCode

        assert APIErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"
        assert APIErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert APIErrorCode.NOT_FOUND == "NOT_FOUND"


class TestAPIErrorHandlers:
    """API错误处理器测试"""

    @pytest.mark.asyncio
    async def test_api_error_handler_400(self):
        """测试400错误处理"""
        from fastapi import HTTPException

        from core.api_error import APIErrorCode, api_error_handler

        request = Mock()
        request.method = "POST"
        request.url.path = "/api/test"

        exc = HTTPException(status_code=400, detail="Bad Request")

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Bad Request"}

            result = await api_error_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_api_error_handler_404(self):
        """测试404错误处理"""
        from fastapi import HTTPException

        from core.api_error import APIErrorCode, api_error_handler

        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"

        exc = HTTPException(status_code=404, detail="Not Found")

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Not Found"}

            result = await api_error_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_api_error_handler_401(self):
        """测试401错误处理"""
        from fastapi import HTTPException

        from core.api_error import APIErrorCode, api_error_handler

        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"

        exc = HTTPException(status_code=401, detail="Unauthorized")

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Unauthorized"}

            result = await api_error_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_api_error_handler_403(self):
        """测试403错误处理"""
        from fastapi import HTTPException

        from core.api_error import APIErrorCode, api_error_handler

        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"

        exc = HTTPException(status_code=403, detail="Forbidden")

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Forbidden"}

            result = await api_error_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.FORBIDDEN

    @pytest.mark.asyncio
    async def test_api_error_handler_409(self):
        """测试409错误处理"""
        from fastapi import HTTPException

        from core.api_error import APIErrorCode, api_error_handler

        request = Mock()
        request.method = "POST"
        request.url.path = "/api/test"

        exc = HTTPException(status_code=409, detail="Conflict")

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Conflict"}

            result = await api_error_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.CONFLICT

    @pytest.mark.asyncio
    async def test_validation_error_handler(self):
        """测试验证错误处理"""
        from fastapi.exceptions import RequestValidationError  # noqa: F401

        from core.api_error import APIErrorCode, validation_error_handler

        request = Mock()
        request.method = "POST"
        request.url.path = "/api/test"

        # 模拟验证错误
        exc = Mock()
        exc.errors.return_value = [
            {"loc": ["field1"], "msg": "field is required", "type": "value_error.missing"}
        ]

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Validation failed"}

            result = await validation_error_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """测试通用异常处理"""
        from core.api_error import APIErrorCode, general_exception_handler

        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"

        exc = Exception("Internal server error")

        with patch("core.api_error.APIResponse") as mock_response:
            mock_response.error.return_value = {"error": "Internal error"}

            result = await general_exception_handler(request, exc)  # noqa: F841

            mock_response.error.assert_called_once()
            call_args = mock_response.error.call_args
            assert call_args[1]["code"] == APIErrorCode.INTERNAL_ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
