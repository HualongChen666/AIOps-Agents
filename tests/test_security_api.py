# -*- coding: utf-8 -*-
"""
Security API集成测试
测试Security API端点的集成功能
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.database import SessionLocal, Base, engine
from main import app


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.integration
class TestSecurityKeyAPI:
    """测试密钥管理API"""
    
    def test_get_keys_empty(self, client: TestClient):
        """测试获取空密钥列表"""
        response = client.get("/api/v1/security/key-management/keys")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert "total" in data
        assert data["total"] == 0
    
    def test_create_key(self, client: TestClient):
        """测试创建密钥"""
        response = client.post(
            "/api/v1/security/key-management/keys",
            json={
                "name": "Test Key",
                "type": "api_key",
                "algorithm": "RSA",
                "keySize": 2048,
                "usage": ["api_access"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["type"] == "api_key"
        assert data["status"] == "active"
        assert "id" in data
    
    def test_get_keys_after_create(self, client: TestClient):
        """测试创建后获取密钥列表"""
        # Create a key first
        client.post(
            "/api/v1/security/key-management/keys",
            json={"name": "Test Key", "type": "api_key"},
        )
        
        # Get keys
        response = client.get("/api/v1/security/key-management/keys")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    def test_update_key(self, client: TestClient):
        """测试更新密钥"""
        # Create a key
        create_response = client.post(
            "/api/v1/security/key-management/keys",
            json={"name": "Test Key", "type": "api_key"},
        )
        key_id = create_response.json()["id"]
        
        # Update key
        response = client.patch(
            f"/api/v1/security/key-management/keys/{key_id}",
            json={"status": "inactive"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"


@pytest.mark.integration
class TestMfaMethodAPI:
    """测试MFA方法API"""
    
    def test_get_mfa_methods(self, client: TestClient):
        """测试获取MFA方法列表"""
        response = client.get("/api/v1/security/mfa/methods")
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
    
    def test_create_mfa_method(self, client: TestClient):
        """测试创建MFA方法"""
        response = client.post(
            "/api/v1/security/mfa/methods",
            json={
                "type": "totp",
                "name": "TOTP",
                "description": "Time-based OTP",
                "priority": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TOTP"
        assert data["type"] == "totp"


@pytest.mark.integration
class TestAbacPolicyAPI:
    """测试ABAC策略API"""
    
    def test_get_abac_policies(self, client: TestClient):
        """测试获取ABAC策略列表"""
        response = client.get("/api/v1/security/abac/policies")
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert "total" in data
    
    def test_create_abac_policy(self, client: TestClient):
        """测试创建ABAC策略"""
        response = client.post(
            "/api/v1/security/abac/policies",
            json={
                "name": "Test Policy",
                "effect": "allow",
                "resources": ["/api/test/*"],
                "actions": ["read"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Policy"
        assert data["effect"] == "allow"
    
    def test_delete_abac_policy(self, client: TestClient):
        """测试删除ABAC策略"""
        # Create a policy
        create_response = client.post(
            "/api/v1/security/abac/policies",
            json={"name": "Test Policy", "effect": "allow"},
        )
        policy_id = create_response.json()["id"]
        
        # Delete policy
        response = client.delete(f"/api/v1/security/abac/policies/{policy_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.integration
class TestRbacRoleAPI:
    """测试RBAC角色API"""
    
    def test_get_rbac_roles(self, client: TestClient):
        """测试获取RBAC角色列表"""
        response = client.get("/api/v1/security/rbac/roles")
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "total" in data
    
    def test_create_rbac_role(self, client: TestClient):
        """测试创建RBAC角色"""
        response = client.post(
            "/api/v1/security/rbac/roles",
            json={
                "name": "Test Role",
                "permissions": ["read", "write"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Role"
        assert data["permissions"] == ["read", "write"]


@pytest.mark.integration
class TestRateLimitRuleAPI:
    """测试速率限制规则API"""
    
    def test_get_rate_limit_rules(self, client: TestClient):
        """测试获取速率限制规则列表"""
        response = client.get("/api/v1/security/rate-limit/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data
    
    def test_create_rate_limit_rule(self, client: TestClient):
        """测试创建速率限制规则"""
        response = client.post(
            "/api/v1/security/rate-limit/rules",
            json={
                "name": "Test Rule",
                "endpoint": "/api/test/*",
                "limit": 100,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Rule"
        assert data["endpoint"] == "/api/test/*"
        assert data["limit"] == 100
    
    def test_delete_rate_limit_rule(self, client: TestClient):
        """测试删除速率限制规则"""
        # Create a rule
        create_response = client.post(
            "/api/v1/security/rate-limit/rules",
            json={"name": "Test Rule", "endpoint": "/api/test", "limit": 100},
        )
        rule_id = create_response.json()["id"]
        
        # Delete rule
        response = client.delete(f"/api/v1/security/rate-limit/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.integration
@pytest.mark.security
class TestSecurityAPIIntegration:
    """Security API集成测试"""
    
    def test_full_key_workflow(self, client: TestClient):
        """测试密钥完整工作流"""
        # Create
        create_response = client.post(
            "/api/v1/security/key-management/keys",
            json={"name": "Workflow Key", "type": "api_key"},
        )
        assert create_response.status_code == 200
        key_id = create_response.json()["id"]
        
        # Read
        get_response = client.get("/api/v1/security/key-management/keys")
        assert get_response.status_code == 200
        assert get_response.json()["total"] >= 1
        
        # Update
        update_response = client.patch(
            f"/api/v1/security/key-management/keys/{key_id}",
            json={"status": "inactive"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "inactive"
    
    def test_security_endpoints_respond(self, client: TestClient):
        """测试所有Security端点可访问"""
        endpoints = [
            "/api/v1/security/key-management/keys",
            "/api/v1/security/mfa/methods",
            "/api/v1/security/abac/policies",
            "/api/v1/security/rbac/roles",
            "/api/v1/security/rate-limit/rules",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Endpoint {endpoint} failed"
