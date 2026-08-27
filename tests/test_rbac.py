# -*- coding: utf-8 -*-
"""
RBAC Tests
基于角色的访问控制测试

测试权限管理系统的正确性
"""

import pytest
from core.rbac import (
    Permission,
    Role,
    RBACManager,
    require_permission,
    require_role,
    require_any_role,
)


class TestRBACManager:
    """RBAC管理器测试"""

    def test_admin_has_all_permissions(self):
        """测试管理员拥有所有权限"""
        for permission in Permission:
            assert RBACManager.has_permission(Role.ADMIN, permission)

    def test_viewer_has_limited_permissions(self):
        """测试查看者权限受限"""
        assert RBACManager.has_permission(Role.VIEWER, Permission.READ)
        assert RBACManager.has_permission(Role.VIEWER, Permission.BUSINESS_IMPACT_READ)
        assert not RBACManager.has_permission(Role.VIEWER, Permission.WRITE)
        assert not RBACManager.has_permission(Role.VIEWER, Permission.DELETE)

    def test_operator_permissions(self):
        """测试运维人员权限"""
        assert RBACManager.has_permission(Role.OPERATOR, Permission.READ)
        assert RBACManager.has_permission(Role.OPERATOR, Permission.CHAOS_EXECUTE)
        assert not RBACManager.has_permission(Role.OPERATOR, Permission.USER_MANAGE)
        assert not RBACManager.has_permission(Role.OPERATOR, Permission.SYSTEM_CONFIG)

    def test_developer_permissions(self):
        """测试开发人员权限"""
        assert RBACManager.has_permission(Role.DEVELOPER, Permission.AI_TRAIN)
        assert RBACManager.has_permission(Role.DEVELOPER, Permission.PLUGIN_UPLOAD)
        assert not RBACManager.has_permission(Role.DEVELOPER, Permission.CHAOS_EXECUTE)
        assert not RBACManager.has_permission(Role.DEVELOPER, Permission.USER_MANAGE)

    def test_has_any_permission(self):
        """测试任一权限检查"""
        assert RBACManager.has_any_permission(
            Role.VIEWER,
            [Permission.READ, Permission.WRITE]
        )
        assert not RBACManager.has_any_permission(
            Role.VIEWER,
            [Permission.WRITE, Permission.DELETE]
        )

    def test_has_all_permissions(self):
        """测试所有权限检查"""
        assert RBACManager.has_all_permissions(
            Role.ADMIN,
            [Permission.READ, Permission.WRITE, Permission.DELETE]
        )
        assert not RBACManager.has_all_permissions(
            Role.VIEWER,
            [Permission.READ, Permission.WRITE]
        )

    def test_get_user_permissions(self):
        """测试获取用户权限"""
        viewer_permissions = RBACManager.get_user_permissions(Role.VIEWER)
        assert Permission.READ in viewer_permissions
        assert Permission.WRITE not in viewer_permissions
        
        admin_permissions = RBACManager.get_user_permissions(Role.ADMIN)
        assert len(admin_permissions) == len(Permission)


class TestRBACDecorators:
    """RBAC装饰器测试"""

    @pytest.mark.asyncio
    async def test_require_permission_decorator(self):
        """测试权限装饰器"""
        @require_permission(Permission.READ)
        async def protected_function():
            return "success"
        
        # 由于装饰器默认使用VIEWER角色，READ权限应该通过
        result = await protected_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_role_decorator(self):
        """测试角色装饰器"""
        @require_role(Role.ADMIN)
        async def admin_function():
            return "admin_success"
        
        # 由于装饰器默认使用VIEWER角色，应该失败
        try:
            await admin_function()
            assert False, "Should have raised HTTPException"
        except Exception as e:
            assert "Role denied" in str(e)

    @pytest.mark.asyncio
    async def test_require_any_role_decorator(self):
        """测试多角色装饰器"""
        @require_any_role(Role.ADMIN, Role.OPERATOR)
        async def protected_function():
            return "success"
        
        # 由于装饰器默认使用VIEWER角色，应该失败
        try:
            await protected_function()
            assert False, "Should have raised HTTPException"
        except Exception as e:
            assert "Role denied" in str(e)


class TestRBACIntegration:
    """RBAC集成测试"""

    def test_role_hierarchy(self):
        """测试角色层级"""
        # 管理员应该拥有所有角色的权限
        admin_permissions = RBACManager.get_user_permissions(Role.ADMIN)
        operator_permissions = RBACManager.get_user_permissions(Role.OPERATOR)
        
        assert operator_permissions.issubset(admin_permissions)

    def test_permission_coverage(self):
        """测试权限覆盖"""
        # 确保所有权限都被至少一个角色拥有
        all_permissions = set(Permission)
        covered_permissions = set()
        
        for role in Role:
            role_permissions = RBACManager.get_user_permissions(role)
            covered_permissions.update(role_permissions)
        
        assert all_permissions == covered_permissions, "Some permissions are not assigned to any role"

    def test_business_impact_permissions(self):
        """测试业务影响分析权限"""
        assert RBACManager.has_permission(Role.ADMIN, Permission.BUSINESS_IMPACT_READ)
        assert RBACManager.has_permission(Role.ADMIN, Permission.BUSINESS_IMPACT_WRITE)
        assert RBACManager.has_permission(Role.ADMIN, Permission.BUSINESS_IMPACT_DELETE)
        
        assert RBACManager.has_permission(Role.OPERATOR, Permission.BUSINESS_IMPACT_READ)
        assert RBACManager.has_permission(Role.OPERATOR, Permission.BUSINESS_IMPACT_WRITE)
        assert not RBACManager.has_permission(Role.OPERATOR, Permission.BUSINESS_IMPACT_DELETE)

    def test_chaos_engineering_permissions(self):
        """测试混沌工程权限"""
        assert RBACManager.has_permission(Role.ADMIN, Permission.CHAOS_EXECUTE)
        assert RBACManager.has_permission(Role.OPERATOR, Permission.CHAOS_EXECUTE)
        assert not RBACManager.has_permission(Role.DEVELOPER, Permission.CHAOS_EXECUTE)
        assert not RBACManager.has_permission(Role.VIEWER, Permission.CHAOS_EXECUTE)

    def test_ai_permissions(self):
        """测试AI功能权限"""
        assert RBACManager.has_permission(Role.ADMIN, Permission.AI_TRAIN)
        assert RBACManager.has_permission(Role.DEVELOPER, Permission.AI_TRAIN)
        assert not RBACManager.has_permission(Role.OPERATOR, Permission.AI_TRAIN)
        assert not RBACManager.has_permission(Role.VIEWER, Permission.AI_TRAIN)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])