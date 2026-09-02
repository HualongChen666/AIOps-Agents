# -*- coding: utf-8 -*-
"""
Security Repository单元测试
测试Security Repository层的所有CRUD操作
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from core.database import SessionLocal, Base, engine
from core.models import (
    SecurityKey,
    MfaMethod,
    AbacPolicy,
    RbacRole,
    RateLimitRule,
)
from core.repositories.security_repository import SecurityRepository


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # Create only Security-related tables
    security_tables = [
        SecurityKey.__table__,
        MfaMethod.__table__,
        AbacPolicy.__table__,
        RbacRole.__table__,
        RateLimitRule.__table__,
    ]
    
    for table in security_tables:
        table.create(bind=engine, checkfirst=True)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop only Security-related tables
        for table in reversed(security_tables):
            table.drop(bind=engine, checkfirst=True)


@pytest.fixture(scope="function")
def security_repo(db_session: Session):
    """创建Security Repository实例"""
    return SecurityRepository(db_session)


class TestSecurityKeyRepository:
    """测试SecurityKey Repository"""
    
    def test_create_key(self, security_repo: SecurityRepository):
        """测试创建密钥"""
        key = security_repo.create_key(
            name="Test Key",
            key_type="api_key",
            algorithm="RSA",
            key_size=2048,
            encrypted_key_value="encrypted_value",
            encrypted_key_iv="iv_value",
            usage=["api_access"],
        )
        
        assert key.id is not None
        assert key.name == "Test Key"
        assert key.key_type == "api_key"
        assert key.status == "active"
        assert key.encrypted_key_value == "encrypted_value"
    
    def test_get_key(self, security_repo: SecurityRepository):
        """测试获取密钥"""
        created_key = security_repo.create_key(
            name="Test Key",
            key_type="api_key",
            encrypted_key_value="encrypted_value",
            encrypted_key_iv="iv_value",
        )
        
        retrieved_key = security_repo.get_key(created_key.id)
        
        assert retrieved_key is not None
        assert retrieved_key.id == created_key.id
        assert retrieved_key.name == "Test Key"
    
    def test_get_keys(self, security_repo: SecurityRepository):
        """测试获取密钥列表"""
        security_repo.create_key(
            name="Key 1",
            key_type="api_key",
            encrypted_key_value="enc1",
            encrypted_key_iv="iv1",
        )
        security_repo.create_key(
            name="Key 2",
            key_type="secret_key",
            encrypted_key_value="enc2",
            encrypted_key_iv="iv2",
        )
        
        keys = security_repo.get_keys()
        
        assert len(keys) == 2
    
    def test_update_key(self, security_repo: SecurityRepository):
        """测试更新密钥"""
        key = security_repo.create_key(
            name="Test Key",
            key_type="api_key",
            encrypted_key_value="encrypted_value",
            encrypted_key_iv="iv_value",
        )
        
        updated_key = security_repo.update_key(key.id, status="inactive")
        
        assert updated_key is not None
        assert updated_key.status == "inactive"
    
    def test_delete_key(self, security_repo: SecurityRepository):
        """测试删除密钥"""
        key = security_repo.create_key(
            name="Test Key",
            key_type="api_key",
            encrypted_key_value="encrypted_value",
            encrypted_key_iv="iv_value",
        )
        
        success = security_repo.delete_key(key.id)
        
        assert success is True
        assert security_repo.get_key(key.id) is None


class TestMfaMethodRepository:
    """测试MfaMethod Repository"""
    
    def test_create_mfa_method(self, security_repo: SecurityRepository):
        """测试创建MFA方法"""
        method = security_repo.create_mfa_method(
            method_type="totp",
            name="TOTP",
            description="Time-based OTP",
            priority=1,
        )
        
        assert method.id is not None
        assert method.method_type == "totp"
        assert method.name == "TOTP"
        assert method.enabled is True
    
    def test_get_mfa_method(self, security_repo: SecurityRepository):
        """测试获取MFA方法"""
        created_method = security_repo.create_mfa_method(
            method_type="totp",
            name="TOTP",
        )
        
        retrieved_method = security_repo.get_mfa_method(created_method.id)
        
        assert retrieved_method is not None
        assert retrieved_method.id == created_method.id
        assert retrieved_method.name == "TOTP"
    
    def test_update_mfa_method(self, security_repo: SecurityRepository):
        """测试更新MFA方法"""
        method = security_repo.create_mfa_method(
            method_type="totp",
            name="TOTP",
        )
        
        updated_method = security_repo.update_mfa_method(method.id, enabled=False)
        
        assert updated_method is not None
        assert updated_method.enabled is False


class TestAbacPolicyRepository:
    """测试AbacPolicy Repository"""
    
    def test_create_abac_policy(self, security_repo: SecurityRepository):
        """测试创建ABAC策略"""
        policy = security_repo.create_abac_policy(
            name="Admin Policy",
            effect="allow",
            resources=["/api/admin/*"],
            actions=["read", "write"],
        )
        
        assert policy.id is not None
        assert policy.name == "Admin Policy"
        assert policy.effect == "allow"
        assert policy.enabled is True
    
    def test_delete_abac_policy(self, security_repo: SecurityRepository):
        """测试删除ABAC策略"""
        policy = security_repo.create_abac_policy(
            name="Test Policy",
            effect="allow",
        )
        
        success = security_repo.delete_abac_policy(policy.id)
        
        assert success is True
        assert security_repo.get_abac_policy(policy.id) is None


class TestRbacRoleRepository:
    """测试RbacRole Repository"""
    
    def test_create_rbac_role(self, security_repo: SecurityRepository):
        """测试创建RBAC角色"""
        role = security_repo.create_rbac_role(
            name="Admin",
            description="Administrator role",
            permissions=["*"],
        )
        
        assert role.id is not None
        assert role.name == "Admin"
        assert role.status == "active"
        assert role.permissions == ["*"]
    
    def test_get_rbac_roles(self, security_repo: SecurityRepository):
        """测试获取RBAC角色列表"""
        security_repo.create_rbac_role(
            name="Admin",
            permissions=["*"],
        )
        security_repo.create_rbac_role(
            name="User",
            permissions=["read"],
        )
        
        roles = security_repo.get_rbac_roles()
        
        assert len(roles) == 2


class TestRateLimitRuleRepository:
    """测试RateLimitRule Repository"""
    
    def test_create_rate_limit_rule(self, security_repo: SecurityRepository):
        """测试创建速率限制规则"""
        rule = security_repo.create_rate_limit_rule(
            name="API Limit",
            endpoint="/api/*",
            limit=1000,
            window_seconds=60,
        )
        
        assert rule.id is not None
        assert rule.name == "API Limit"
        assert rule.endpoint == "/api/*"
        assert rule.limit == 1000
        assert rule.enabled is True
    
    def test_delete_rate_limit_rule(self, security_repo: SecurityRepository):
        """测试删除速率限制规则"""
        rule = security_repo.create_rate_limit_rule(
            name="Test Rule",
            endpoint="/api/test",
            limit=100,
        )
        
        success = security_repo.delete_rate_limit_rule(rule.id)
        
        assert success is True
        assert security_repo.get_rate_limit_rule(rule.id) is None


@pytest.mark.unit
class TestSecurityRepositoryIntegration:
    """Security Repository集成测试"""
    
    def test_full_key_lifecycle(self, security_repo: SecurityRepository):
        """测试密钥完整生命周期"""
        # Create
        key = security_repo.create_key(
            name="Lifecycle Key",
            key_type="api_key",
            encrypted_key_value="enc",
            encrypted_key_iv="iv",
        )
        assert key is not None
        
        # Read
        retrieved = security_repo.get_key(key.id)
        assert retrieved.id == key.id
        
        # Update
        updated = security_repo.update_key(key.id, status="inactive")
        assert updated.status == "inactive"
        
        # Delete
        success = security_repo.delete_key(key.id)
        assert success is True
        
        # Verify deletion
        assert security_repo.get_key(key.id) is None
