# -*- coding: utf-8 -*-
# tests/test_rbac.py
# RBAC权限模型单元测试
import pytest

from core.fine_rbac import check_permission, grant_permission, revoke_permission
from core.rbac import get_all_user_tenants, get_user_tenant, set_user_tenant


class TestUserTenantMapping:
    """用户租户映射测试"""

    def test_get_user_tenant_existing(self):
        """测试获取已存在的用户租户"""
        tenant = get_user_tenant("admin")
        assert tenant == "default"

    def test_get_user_tenant_nonexistent(self):
        """测试获取不存在的用户租户"""
        tenant = get_user_tenant("nonexistent_user")
        assert tenant is None

    def test_set_user_tenant(self):
        """测试设置用户租户"""
        set_user_tenant("test_user", "test_tenant")
        tenant = get_user_tenant("test_user")
        assert tenant == "test_tenant"

    def test_get_all_user_tenants(self):
        """测试获取所有用户租户映射"""
        mappings = get_all_user_tenants()
        assert isinstance(mappings, dict)
        assert "admin" in mappings


class TestFineGrainedRBAC:
    """细粒度RBAC测试"""

    def test_grant_permission(self):
        """测试授予权限"""
        grant_permission("default", "test_resource", "read", "admin")
        result = check_permission("default", "test_resource", "read", "admin")
        assert result is True

    def test_check_permission_granted(self):
        """测试检查已授予的权限"""
        grant_permission("default", "metrics", "read", "user")
        result = check_permission("default", "metrics", "read", "user")
        assert result is True

    def test_check_permission_denied(self):
        """测试检查未授予的权限"""
        result = check_permission("default", "admin", "delete", "user")
        assert result is False

    def test_revoke_permission(self):
        """测试撤销权限"""
        grant_permission("default", "test_resource", "write", "admin")
        revoke_permission("default", "test_resource", "write", "admin")
        result = check_permission("default", "test_resource", "write", "admin")
        assert result is False

    def test_revoke_nonexistent_permission(self):
        """测试撤销不存在的权限（不应报错）"""
        revoke_permission("default", "nonexistent", "action", "role")
        # Should not raise an exception


class TestRBACIntegration:
    """RBAC集成测试"""

    def test_admin_full_access(self):
        """测试管理员完全访问权限"""
        # Admin should have access to everything based on demo policies
        result = check_permission("default", "*", "*", "admin")
        assert result is True

    def test_user_limited_access(self):
        """测试用户有限访问权限"""
        # User should have read access to metrics based on demo policies
        result = check_permission("default", "metrics", "read", "user")
        assert result is True

    def test_user_no_write_access(self):
        """测试用户无写入权限"""
        # User should not have write access to metrics based on demo policies
        result = check_permission("default", "metrics", "write", "user")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
