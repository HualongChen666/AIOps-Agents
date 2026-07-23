# -*- coding: utf-8 -*-
"""
GraphQL Tests
"""

import pytest

from core.interface.graphql import AuthContext, DataLoader, DataLoaderRegistry, Permission, Role


class TestDataLoader:
    """Test data loader"""

    @pytest.mark.asyncio
    async def test_load_single(self):
        """Test loading single item"""

        async def batch_load_fn(keys):
            return [f"value-{k}" for k in keys]

        loader = DataLoader(batch_load_fn)
        result = await loader.load("key1")
        assert result == "value-key1"

    @pytest.mark.asyncio
    async def test_load_many(self):
        """Test loading multiple items"""

        async def batch_load_fn(keys):
            return [f"value-{k}" for k in keys]

        loader = DataLoader(batch_load_fn)
        results = await loader.load_many(["key1", "key2"])
        assert results == ["value-key1", "value-key2"]

    @pytest.mark.asyncio
    async def test_cache(self):
        """Test caching"""

        async def batch_load_fn(keys):
            return [f"value-{k}" for k in keys]

        loader = DataLoader(batch_load_fn, cache=True)

        # First load
        result1 = await loader.load("key1")

        # Second load (should use cache)
        result2 = await loader.load("key1")

        assert result1 == result2 == "value-key1"

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test cache clearing"""

        async def batch_load_fn(keys):
            return [f"value-{k}" for k in keys]

        loader = DataLoader(batch_load_fn, cache=True)
        await loader.load("key1")
        loader.clear("key1")

        # Should reload from batch function
        result = await loader.load("key1")
        assert result == "value-key1"


class TestDataLoaderRegistry:
    """Test data loader registry"""

    def test_get_alert_loader(self):
        """Test getting alert loader"""
        registry = DataLoaderRegistry()
        loader1 = registry.get_alert_loader()
        loader2 = registry.get_alert_loader()

        # Should return same instance
        assert loader1 is loader2

    def test_clear_all(self):
        """Test clearing all loaders"""
        registry = DataLoaderRegistry()
        registry.get_alert_loader()
        registry.get_repair_loader()

        registry.clear_all()

        # Should not raise errors
        registry.clear_all()


class TestAuthContext:
    """Test authentication context"""

    def test_has_permission(self):
        """Test permission checking"""
        context = AuthContext(user_id="user-1", role=Role.ADMIN, permissions=[Permission.ADMIN])

        assert context.has_permission(Permission.READ_METRICS)
        assert context.has_permission(Permission.ADMIN)

    def test_viewer_role(self):
        """Test viewer role permissions"""
        context = AuthContext(
            user_id="user-1",
            role=Role.VIEWER,
            permissions=[Permission.READ_METRICS, Permission.READ_ALERTS],
        )

        assert context.has_permission(Permission.READ_METRICS)
        assert not context.has_permission(Permission.WRITE_ALERTS)
