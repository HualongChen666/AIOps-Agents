# -*- coding: utf-8 -*-
# tests/test_multi_tenant.py
# 多租户支持单元测试
import pytest

from core.multi_tenant import (  # noqa: F401
    Tenant,
    add_user_to_tenant,
    clear_tenant_context,
    create_tenant,
    delete_tenant,
    get_tenant,
    get_tenant_config,
    get_tenant_context,
    get_tenant_stats,
    get_tenant_users,
    get_user_tenants,
    is_user_in_tenant,
    list_tenants,
    remove_user_from_tenant,
    set_tenant_context,
    update_tenant,
)


class TestTenantCreation:
    """租户创建测试"""

    def test_create_tenant(self):
        """测试创建租户"""
        result = create_tenant(
            tenant_id="tenant1",
            name="Test Tenant",
            description="A test tenant",
        )

        assert result is True
        assert get_tenant("tenant1") is not None

    def test_create_tenant_duplicate(self):
        """测试创建重复租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        result = create_tenant(tenant_id="tenant1", name="Test Tenant")

        assert result is False

    def test_create_tenant_with_config(self):
        """测试创建带配置的租户"""
        config = {"feature1": True, "feature2": False}
        result = create_tenant(
            tenant_id="tenant2",
            name="Test Tenant 2",
            config=config,
        )

        assert result is True
        tenant = get_tenant("tenant2")
        assert tenant["config"] == config


class TestTenantRetrieval:
    """租户检索测试"""

    def test_get_tenant(self):
        """测试获取租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        tenant = get_tenant("tenant1")

        assert tenant is not None
        assert tenant["tenant_id"] == "tenant1"
        assert tenant["name"] == "Test Tenant"

    def test_get_tenant_not_found(self):
        """测试获取不存在的租户"""
        tenant = get_tenant("nonexistent")
        assert tenant is None


class TestTenantUpdate:
    """租户更新测试"""

    def test_update_tenant_name(self):
        """测试更新租户名称"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        result = update_tenant(tenant_id="tenant1", name="Updated Name")

        assert result is True
        tenant = get_tenant("tenant1")
        assert tenant["name"] == "Updated Name"

    def test_update_tenant_config(self):
        """测试更新租户配置"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        new_config = {"feature1": True}
        result = update_tenant(tenant_id="tenant1", config=new_config)

        assert result is True
        tenant = get_tenant("tenant1")
        assert tenant["config"] == new_config

    def test_update_tenant_not_found(self):
        """测试更新不存在的租户"""
        result = update_tenant(tenant_id="nonexistent", name="New Name")
        assert result is False


class TestTenantDeletion:
    """租户删除测试"""

    def test_delete_tenant(self):
        """测试删除租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        result = delete_tenant("tenant1")

        assert result is True
        assert get_tenant("tenant1") is None

    def test_delete_tenant_not_found(self):
        """测试删除不存在的租户"""
        result = delete_tenant("nonexistent")
        assert result is False


class TestTenantListing:
    """租户列表测试"""

    def test_list_tenants(self):
        """测试列出租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant 1")
        create_tenant(tenant_id="tenant2", name="Test Tenant 2")

        tenants = list_tenants()
        assert len(tenants) >= 2

    def test_list_tenants_active_only(self):
        """测试仅列出活跃租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant 1")
        create_tenant(tenant_id="tenant2", name="Test Tenant 2")
        update_tenant(tenant_id="tenant2", is_active=False)

        active_tenants = list_tenants(active_only=True)
        assert len(active_tenants) >= 1
        assert all(t.get("is_active", True) for t in active_tenants)


class TestTenantContext:
    """租户上下文测试"""

    def test_set_tenant_context(self):
        """测试设置租户上下文"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        set_tenant_context("tenant1")

        assert get_tenant_context() == "tenant1"

    def test_set_tenant_context_invalid(self):
        """测试设置无效租户上下文"""
        # Clear any existing context first
        clear_tenant_context()

        set_tenant_context("nonexistent")
        # Should not raise error, but context may not be set
        assert get_tenant_context() is None

    def test_clear_tenant_context(self):
        """测试清除租户上下文"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        set_tenant_context("tenant1")
        clear_tenant_context()

        assert get_tenant_context() is None


class TestTenantUsers:
    """租户用户测试"""

    def test_add_user_to_tenant(self):
        """测试添加用户到租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        result = add_user_to_tenant("tenant1", "user1")

        assert result is True
        assert "user1" in get_tenant_users("tenant1")

    def test_add_user_duplicate(self):
        """测试添加重复用户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        add_user_to_tenant("tenant1", "user1")
        result = add_user_to_tenant("tenant1", "user1")

        assert result is False

    def test_remove_user_from_tenant(self):
        """测试从租户移除用户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        add_user_to_tenant("tenant1", "user1")
        result = remove_user_from_tenant("tenant1", "user1")

        assert result is True
        assert "user1" not in get_tenant_users("tenant1")

    def test_get_tenant_users(self):
        """测试获取租户用户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant")
        add_user_to_tenant("tenant1", "user1")
        add_user_to_tenant("tenant1", "user2")

        users = get_tenant_users("tenant1")
        assert len(users) == 2
        assert "user1" in users
        assert "user2" in users


class TestUserTenants:
    """用户租户测试"""

    def test_get_user_tenants(self):
        """测试获取用户租户"""
        create_tenant(tenant_id="tenant1", name="Test Tenant 1")
        create_tenant(tenant_id="tenant2", name="Test Tenant 2")
        add_user_to_tenant("tenant1", "user1")
        add_user_to_tenant("tenant2", "user1")

        user_tenants = get_user_tenants("user1")
        assert len(user_tenants) == 2
        assert "tenant1" in user_tenants
        assert "tenant2" in user_tenants


class TestTenantConfig:
    """租户配置测试"""

    def test_get_tenant_config(self):
        """测试获取租户配置"""
        config = {"feature1": True, "feature2": False}
        # Use a unique tenant ID to avoid conflicts
        create_tenant(tenant_id="tenant_config_test", name="Test Tenant", config=config)

        tenant_config = get_tenant_config("tenant_config_test")
        assert tenant_config == config

    def test_get_tenant_config_not_found(self):
        """测试获取不存在租户的配置"""
        config = get_tenant_config("nonexistent")
        assert config == {}


class TestTenantMembership:
    """租户成员测试"""

    def test_is_user_in_tenant(self):
        """测试用户是否在租户中"""
        # Use unique tenant ID to avoid conflicts
        create_tenant(tenant_id="tenant_membership_test", name="Test Tenant")
        add_user_to_tenant("tenant_membership_test", "user1")

        assert is_user_in_tenant("user1", "tenant_membership_test") is True
        assert is_user_in_tenant("user2", "tenant_membership_test") is False


class TestTenantStats:
    """租户统计测试"""

    def test_get_tenant_stats(self):
        """测试获取租户统计"""
        create_tenant(tenant_id="tenant1", name="Test Tenant 1")
        create_tenant(tenant_id="tenant2", name="Test Tenant 2")
        add_user_to_tenant("tenant1", "user1")
        add_user_to_tenant("tenant2", "user1")
        add_user_to_tenant("tenant2", "user2")

        stats = get_tenant_stats()

        assert stats["total_tenants"] >= 2
        assert stats["total_users"] >= 3
        assert "avg_users_per_tenant" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
