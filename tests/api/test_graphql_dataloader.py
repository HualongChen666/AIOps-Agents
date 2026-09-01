# -*- coding: utf-8 -*-
"""
Tests for GraphQL DataLoader Endpoints
测试GraphQL DataLoader端点
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from api.graphql_router import (
    _get_dataloader_config,
    _get_dataloader_registry,
)
from core.auth_db import User


# ============================================================================
# GraphQL DataLoader Endpoint Tests
# ============================================================================


class TestGetDataLoaderConfig:
    """测试获取DataLoader配置"""

    def test_get_dataloader_config_defaults(self):
        """测试默认配置"""
        config = _get_dataloader_config()
        assert config.max_batch_size == 100
        assert config.cache_enabled is True
        assert config.batch_strategy == "auto"

    def test_get_dataloader_config_custom(self):
        """测试自定义配置"""
        with patch.dict(os.environ, {
            "GRAPHQL_DATALOADER_MAX_BATCH_SIZE": "200",
            "GRAPHQL_DATALOADER_CACHE_ENABLED": "false",
            "GRAPHQL_DATALOADER_BATCH_STRATEGY": "manual",
        }):
            config = _get_dataloader_config()
            assert config.max_batch_size == 200
            assert config.cache_enabled is False
            assert config.batch_strategy == "manual"


class TestGetDataLoaderRegistry:
    """测试获取DataLoader注册表"""

    def test_get_dataloader_registry_singleton(self):
        """测试单例模式"""
        registry1 = _get_dataloader_registry()
        registry2 = _get_dataloader_registry()
        assert registry1 is registry2


@pytest.mark.asyncio
class TestGetDataLoaderStatus:
    """测试获取DataLoader状态端点"""

    async def test_get_dataloader_status_success(self, client: AsyncClient):
        """测试成功获取DataLoader状态"""
        mock_user = User(
            id=1,
            username="testuser",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.get("/api/graphql/graphql-dataloader")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "config" in data
            assert "batch_stats" in data
            assert "performance" in data
            assert "active_loaders" in data
            assert "enabled" in data
            assert data["config"]["max_batch_size"] >= 0
            assert isinstance(data["config"]["cache_enabled"], bool)

    async def test_get_dataloader_status_unauthorized(self, client: AsyncClient):
        """测试未授权访问"""
        with patch("api.graphql_router.get_current_user", side_effect=Exception("Unauthorized")):
            response = await client.get("/api/graphql/graphql-dataloader")

            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


@pytest.mark.asyncio
class TestClearDataLoaderCache:
    """测试清除DataLoader缓存端点"""

    async def test_clear_all_cache(self, client: AsyncClient):
        """测试清除所有缓存"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.post("/api/graphql/graphql-dataloader/clear-cache")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["cleared_type"] == "all"

    async def test_clear_alert_cache(self, client: AsyncClient):
        """测试清除Alert缓存"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.post("/api/graphql/graphql-dataloader/clear-cache?loader_type=alert")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["cleared_type"] == "alert"

    async def test_clear_invalid_loader_type(self, client: AsyncClient):
        """测试清除无效的loader类型"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.post("/api/graphql/graphql-dataloader/clear-cache?loader_type=invalid")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid loader type" in response.json()["detail"]


@pytest.mark.asyncio
class TestTestDataLoader:
    """测试DataLoader测试端点"""

    async def test_test_dataloader_success(self, client: AsyncClient):
        """测试成功执行DataLoader测试"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.get("/api/graphql/graphql-dataloader/test")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "test_results" in data
            assert "items_loaded" in data["test_results"]
            assert "load_time_ms" in data["test_results"]
            assert "config" in data["test_results"]

    async def test_test_dataloader_unauthorized(self, client: AsyncClient):
        """测试未授权访问"""
        with patch("api.graphql_router.get_current_user", side_effect=Exception("Unauthorized")):
            response = await client.get("/api/graphql/graphql-dataloader/test")

            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]
