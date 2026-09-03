# -*- coding: utf-8 -*-
"""
Tests for GraphQL DataLoader Endpoints
测试GraphQL DataLoader端点

注意：DataLoader端点的测试已移至 test_graphql_router.py 中统一管理
此文件保留用于DataLoader核心功能的单元测试
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.interface.graphql.dataloader import (
    AlertDataLoader,
    DataLoader,
    DataLoaderRegistry,
    MetricsDataLoader,
    RepairDataLoader,
)


# ============================================================================
# DataLoader Core Functionality Tests
# ============================================================================


class TestDataLoaderBasic:
    """测试DataLoader基本功能"""

    @pytest.mark.asyncio
    async def test_dataloader_load_single(self):
        """测试加载单个项目"""

        async def batch_load_fn(keys):
            return [f"item_{key}" for key in keys]

        loader = DataLoader(batch_load_fn, max_batch_size=10)
        result = await loader.load(1)
        assert result == "item_1"

    @pytest.mark.asyncio
    async def test_dataloader_load_many(self):
        """测试加载多个项目"""

        async def batch_load_fn(keys):
            return [f"item_{key}" for key in keys]

        loader = DataLoader(batch_load_fn, max_batch_size=10)
        results = await loader.load_many([1, 2, 3])
        assert results == ["item_1", "item_2", "item_3"]

    @pytest.mark.asyncio
    async def test_dataloader_caching(self):
        """测试缓存功能"""

        async def batch_load_fn(keys):
            return [f"item_{key}" for key in keys]

        loader = DataLoader(batch_load_fn, max_batch_size=10, cache=True)

        # 第一次加载
        result1 = await loader.load(1)
        assert result1 == "item_1"

        # 第二次加载应该从缓存获取
        result2 = await loader.load(1)
        assert result2 == "item_1"

    @pytest.mark.asyncio
    async def test_dataloader_cache_clear(self):
        """测试清除缓存"""

        async def batch_load_fn(keys):
            return [f"item_{key}" for key in keys]

        loader = DataLoader(batch_load_fn, max_batch_size=10, cache=True)

        await loader.load(1)
        loader.clear(1)

        # 清除后应该重新加载
        result = await loader.load(1)
        assert result == "item_1"

    @pytest.mark.asyncio
    async def test_dataloader_prime_cache(self):
        """测试预填充缓存"""

        async def batch_load_fn(keys):
            return [f"item_{key}" for key in keys]

        loader = DataLoader(batch_load_fn, max_batch_size=10, cache=True)

        # 预填充缓存
        loader.prime(1, "item_1")

        # 应该从缓存获取
        result = await loader.load(1)
        assert result == "item_1"

    @pytest.mark.asyncio
    async def test_dataloader_batch_splitting(self):
        """测试批次分割"""

        call_count = 0

        async def batch_load_fn(keys):
            nonlocal call_count
            call_count += 1
            return [f"item_{key}" for key in keys]

        loader = DataLoader(batch_load_fn, max_batch_size=5)

        # 加载超过批次大小的项目
        await loader.load_many(list(range(10)))

        # 应该分成2个批次
        assert call_count == 2


class TestDataLoaderRegistry:
    """测试DataLoader注册表"""

    def test_registry_singleton(self):
        """测试单例模式"""
        registry1 = DataLoaderRegistry()
        registry2 = DataLoaderRegistry()
        # 每次创建新实例，但可以验证方法存在
        assert hasattr(registry1, "get_alert_loader")
        assert hasattr(registry2, "get_repair_loader")

    def test_get_alert_loader(self):
        """测试获取Alert loader"""
        registry = DataLoaderRegistry()
        loader = registry.get_alert_loader()
        assert isinstance(loader, AlertDataLoader)
        # 验证单例
        assert registry.get_alert_loader() is loader

    def test_get_repair_loader(self):
        """测试获取Repair loader"""
        registry = DataLoaderRegistry()
        loader = registry.get_repair_loader()
        assert isinstance(loader, RepairDataLoader)
        assert registry.get_repair_loader() is loader

    def test_get_metrics_loader(self):
        """测试获取Metrics loader"""
        registry = DataLoaderRegistry()
        loader = registry.get_metrics_loader()
        assert isinstance(loader, MetricsDataLoader)
        assert registry.get_metrics_loader() is loader

    def test_clear_all(self):
        """测试清除所有缓存"""
        registry = DataLoaderRegistry()

        # 获取所有loader
        alert_loader = registry.get_alert_loader()
        repair_loader = registry.get_repair_loader()
        metrics_loader = registry.get_metrics_loader()

        # 预填充一些数据
        alert_loader.prime(1, "test")
        repair_loader.prime(1, "test")
        metrics_loader.prime(1, "test")

        # 清除所有
        registry.clear_all()

        # 验证缓存已清除
        assert len(alert_loader._cache) == 0
        assert len(repair_loader._cache) == 0
        assert len(metrics_loader._cache) == 0


class TestSpecificDataLoaders:
    """测试特定DataLoader"""

    @pytest.mark.asyncio
    async def test_alert_data_loader(self):
        """测试AlertDataLoader"""
        loader = AlertDataLoader()
        assert loader.max_batch_size > 0
        assert loader.cache is True

    @pytest.mark.asyncio
    async def test_repair_data_loader(self):
        """测试RepairDataLoader"""
        loader = RepairDataLoader()
        assert loader.max_batch_size > 0
        assert loader.cache is True

    @pytest.mark.asyncio
    async def test_metrics_data_loader(self):
        """测试MetricsDataLoader"""
        loader = MetricsDataLoader()
        assert loader.max_batch_size > 0
        assert loader.cache is True
