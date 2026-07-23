# -*- coding: utf-8 -*-
# tests/unit/test_api_deprecation_unit.py
# API弃用警告模块单元测试
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch  # noqa: F401

import pytest


class TestAPIDeprecation:
    """API弃用警告测试"""

    def test_mark_deprecated(self):
        """测试标记端点为弃用"""
        from core.api_deprecation import DEPRECATED_ENDPOINTS, mark_deprecated

        # 清空现有弃用端点
        DEPRECATED_ENDPOINTS.clear()

        sunset_date = datetime.now(timezone.utc) + timedelta(days=30)
        replacement = "/api/v2/test"

        mark_deprecated("/api/v1/test", sunset_date, replacement)

        assert "/api/v1/test" in DEPRECATED_ENDPOINTS
        assert DEPRECATED_ENDPOINTS["/api/v1/test"]["sunset_date"] == sunset_date
        assert DEPRECATED_ENDPOINTS["/api/v1/test"]["replacement"] == replacement

    def test_mark_deprecated_without_replacement(self):
        """测试标记端点为弃用（无替代端点）"""
        from core.api_deprecation import DEPRECATED_ENDPOINTS, mark_deprecated

        # 清空现有弃用端点
        DEPRECATED_ENDPOINTS.clear()

        sunset_date = datetime.now(timezone.utc) + timedelta(days=30)

        mark_deprecated("/api/v1/old", sunset_date)

        assert "/api/v1/old" in DEPRECATED_ENDPOINTS
        assert DEPRECATED_ENDPOINTS["/api/v1/old"]["sunset_date"] == sunset_date
        assert DEPRECATED_ENDPOINTS["/api/v1/old"]["replacement"] is None

    @pytest.mark.asyncio
    async def test_deprecation_middleware_active(self):
        """测试弃用中间件（激活状态）"""
        from core.api_deprecation import (
            DEPRECATED_ENDPOINTS,
            deprecation_middleware,
            mark_deprecated,
        )

        # 清空并设置弃用端点
        DEPRECATED_ENDPOINTS.clear()
        sunset_date = datetime.now(timezone.utc) + timedelta(days=30)
        mark_deprecated("/api/v1/old", sunset_date, "/api/v2/new")

        request = Mock()
        request.url.path = "/api/v1/old"

        call_next = AsyncMock()
        response = Mock()
        response.headers = {}
        call_next.return_value = response

        result = await deprecation_middleware(request, call_next)  # noqa: F841

        assert "X-API-Deprecated" in response.headers
        assert response.headers["X-API-Deprecated"] == "true"
        assert "X-API-Sunset-Date" in response.headers
        assert "X-API-Days-Until-Sunset" in response.headers
        assert "X-API-Replacement" in response.headers
        assert response.headers["X-API-Replacement"] == "/api/v2/new"

    @pytest.mark.asyncio
    async def test_deprecation_middleware_inactive(self):
        """测试弃用中间件（非弃用端点）"""
        from core.api_deprecation import DEPRECATED_ENDPOINTS, deprecation_middleware

        # 清空弃用端点
        DEPRECATED_ENDPOINTS.clear()

        request = Mock()
        request.url.path = "/api/v1/active"

        call_next = AsyncMock()
        response = Mock()
        response.headers = {}
        call_next.return_value = response

        result = await deprecation_middleware(request, call_next)  # noqa: F841

        # 非弃用端点不应该添加弃用头
        assert "X-API-Deprecated" not in response.headers

    @pytest.mark.asyncio
    async def test_deprecation_middleware_without_replacement(self):
        """测试弃用中间件（无替代端点）"""
        from core.api_deprecation import (
            DEPRECATED_ENDPOINTS,
            deprecation_middleware,
            mark_deprecated,
        )

        # 清空并设置弃用端点（无替代）
        DEPRECATED_ENDPOINTS.clear()
        sunset_date = datetime.now(timezone.utc) + timedelta(days=30)
        mark_deprecated("/api/v1/old", sunset_date)

        request = Mock()
        request.url.path = "/api/v1/old"

        call_next = AsyncMock()
        response = Mock()
        response.headers = {}
        call_next.return_value = response

        result = await deprecation_middleware(request, call_next)  # noqa: F841

        assert "X-API-Deprecated" in response.headers
        assert "X-API-Sunset-Date" in response.headers
        # 不应该有替代端点头
        assert "X-API-Replacement" not in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
