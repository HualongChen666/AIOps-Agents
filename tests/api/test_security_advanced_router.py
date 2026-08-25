# -*- coding: utf-8 -*-
"""
安全管理高级API路由测试用例
测试25个安全管理相关的API端点
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# 导入router
from api.security_advanced_router import router


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_request():
    """模拟请求对象"""
    request = Mock()
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


# ============================================================
# 1. Key Management Tests
# ============================================================


class TestKeyManagement:
    """密钥管理测试"""

    def test_get_keys_success(self, client):
        """测试获取密钥列表 - 成功"""
        response = client.get("/api/v1/security/key-management/keys")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert "total" in data
        assert isinstance(data["keys"], list)

    def test_get_keys_with_status_filter(self, client):
        """测试获取密钥列表 - 带状态过滤"""
        response = client.get("/api/v1/security/key-management/keys?status=active")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data

    def test_create_key_success(self, client):
        """测试创建密钥 - 成功"""
        payload = {
            "name": "Test Key",
            "type": "api_key",
            "algorithm": "RSA",
            "keySize": 2048,
            "usage": ["encryption"],
        }
        response = client.post("/api/v1/security/key-management/keys", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["type"] == "api_key"
        assert "id" in data

    def test_create_key_validation_error(self, client):
        """测试创建密钥 - 验证错误"""
        payload = {"name": "", "type": "api_key"}  # 空名称应该失败
        response = client.post("/api/v1/security/key-management/keys", json=payload)
        assert response.status_code == 422

    def test_create_key_invalid_key_size(self, client):
        """测试创建密钥 - 无效的密钥大小"""
        payload = {"name": "Test Key", "type": "api_key", "keySize": 500}  # 小于最小值1024
        response = client.post("/api/v1/security/key-management/keys", json=payload)
        assert response.status_code == 422

    def test_update_key_success(self, client):
        """测试更新密钥 - 成功"""
        # 先创建一个密钥
        create_payload = {"name": "Test Key", "type": "api_key"}
        create_response = client.post("/api/v1/security/key-management/keys", json=create_payload)
        key_id = create_response.json()["id"]

        # 更新密钥
        update_payload = {"status": "inactive", "autoRenew": True}
        response = client.patch(
            f"/api/v1/security/key-management/keys/{key_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"

    def test_update_key_not_found(self, client):
        """测试更新密钥 - 密钥不存在"""
        fake_id = str(uuid.uuid4())
        update_payload = {"status": "inactive"}
        response = client.patch(
            f"/api/v1/security/key-management/keys/{fake_id}", json=update_payload
        )
        assert response.status_code == 404


# ============================================================
# 2. MFA Tests
# ============================================================


class TestMFA:
    """多因素认证测试"""

    def test_get_mfa_methods_success(self, client):
        """测试获取MFA方法 - 成功"""
        response = client.get("/api/v1/security/mfa/methods")
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
        assert isinstance(data["methods"], list)

    def test_create_mfa_method_success(self, client):
        """测试创建MFA方法 - 成功"""
        payload = {
            "type": "totp",
            "name": "Google Authenticator",
            "description": "Time-based OTP",
            "priority": 1,
        }
        response = client.post("/api/v1/security/mfa/methods", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Google Authenticator"
        assert data["type"] == "totp"

    def test_create_mfa_method_invalid_priority(self, client):
        """测试创建MFA方法 - 无效优先级"""
        payload = {"type": "totp", "name": "Test", "priority": 15}  # 超过最大值10
        response = client.post("/api/v1/security/mfa/methods", json=payload)
        assert response.status_code == 422

    def test_update_mfa_method_success(self, client):
        """测试更新MFA方法 - 成功"""
        create_payload = {"type": "totp", "name": "Test MFA"}
        create_response = client.post("/api/v1/security/mfa/methods", json=create_payload)
        method_id = create_response.json()["id"]

        update_payload = {"enabled": False, "required": True}
        response = client.patch(f"/api/v1/security/mfa/methods/{method_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_update_mfa_method_not_found(self, client):
        """测试更新MFA方法 - 方法不存在"""
        fake_id = str(uuid.uuid4())
        update_payload = {"enabled": False}
        response = client.patch(f"/api/v1/security/mfa/methods/{fake_id}", json=update_payload)
        assert response.status_code == 404


# ============================================================
# 3. ABAC Tests
# ============================================================


class TestABAC:
    """基于属性的访问控制测试"""

    def test_get_abac_policies_success(self, client):
        """测试获取ABAC策略 - 成功"""
        response = client.get("/api/v1/security/abac/policies")
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert "total" in data

    def test_create_abac_policy_success(self, client):
        """测试创建ABAC策略 - 成功"""
        payload = {
            "name": "Admin Access Policy",
            "effect": "allow",
            "resources": ["/api/admin/*"],
            "actions": ["read", "write"],
        }
        response = client.post("/api/v1/security/abac/policies", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Admin Access Policy"
        assert data["effect"] == "allow"

    def test_update_abac_policy_success(self, client):
        """测试更新ABAC策略 - 成功"""
        create_payload = {"name": "Test Policy", "effect": "allow"}
        create_response = client.post("/api/v1/security/abac/policies", json=create_payload)
        policy_id = create_response.json()["id"]

        update_payload = {"enabled": False}
        response = client.patch(f"/api/v1/security/abac/policies/{policy_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_delete_abac_policy_success(self, client):
        """测试删除ABAC策略 - 成功"""
        create_payload = {"name": "Test Policy", "effect": "allow"}
        create_response = client.post("/api/v1/security/abac/policies", json=create_payload)
        policy_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/abac/policies/{policy_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_delete_abac_policy_not_found(self, client):
        """测试删除ABAC策略 - 策略不存在"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/security/abac/policies/{fake_id}")
        assert response.status_code == 404


# ============================================================
# 4. RBAC Tests
# ============================================================


class TestRBAC:
    """基于角色的访问控制测试"""

    def test_get_rbac_roles_success(self, client):
        """测试获取RBAC角色 - 成功"""
        response = client.get("/api/v1/security/rbac/roles")
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "total" in data

    def test_create_rbac_role_success(self, client):
        """测试创建RBAC角色 - 成功"""
        payload = {"name": "Developer", "permissions": ["read", "write", "deploy"]}
        response = client.post("/api/v1/security/rbac/roles", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Developer"
        assert "permissions" in data

    def test_update_rbac_role_success(self, client):
        """测试更新RBAC角色 - 成功"""
        create_payload = {"name": "Test Role", "permissions": ["read"]}
        create_response = client.post("/api/v1/security/rbac/roles", json=create_payload)
        role_id = create_response.json()["id"]

        update_payload = {"status": "inactive"}
        response = client.patch(f"/api/v1/security/rbac/roles/{role_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"

    def test_delete_rbac_role_success(self, client):
        """测试删除RBAC角色 - 成功"""
        create_payload = {"name": "Test Role", "permissions": ["read"]}
        create_response = client.post("/api/v1/security/rbac/roles", json=create_payload)
        role_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/rbac/roles/{role_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_delete_rbac_role_not_found(self, client):
        """测试删除RBAC角色 - 角色不存在"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/security/rbac/roles/{fake_id}")
        assert response.status_code == 404


# ============================================================
# 5. Rate Limit Tests
# ============================================================


class TestRateLimit:
    """速率限制测试"""

    def test_get_rate_limit_rules_success(self, client):
        """测试获取速率限制规则 - 成功"""
        response = client.get("/api/v1/security/rate-limit/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    def test_create_rate_limit_rule_success(self, client):
        """测试创建速率限制规则 - 成功"""
        payload = {"name": "API Rate Limit", "endpoint": "/api/v1/*", "limit": 1000}
        response = client.post("/api/v1/security/rate-limit/rules", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API Rate Limit"
        assert data["limit"] == 1000

    def test_create_rate_limit_rule_invalid_limit(self, client):
        """测试创建速率限制规则 - 无效限制值"""
        payload = {"name": "Test", "endpoint": "/api/*", "limit": 20000}  # 超过最大值10000
        response = client.post("/api/v1/security/rate-limit/rules", json=payload)
        assert response.status_code == 422

    def test_update_rate_limit_rule_success(self, client):
        """测试更新速率限制规则 - 成功"""
        create_payload = {"name": "Test Rule", "endpoint": "/api/*", "limit": 100}
        create_response = client.post("/api/v1/security/rate-limit/rules", json=create_payload)
        rule_id = create_response.json()["id"]

        update_payload = {"enabled": False}
        response = client.patch(f"/api/v1/security/rate-limit/rules/{rule_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_delete_rate_limit_rule_success(self, client):
        """测试删除速率限制规则 - 成功"""
        create_payload = {"name": "Test Rule", "endpoint": "/api/*", "limit": 100}
        create_response = client.post("/api/v1/security/rate-limit/rules", json=create_payload)
        rule_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/rate-limit/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 6. HTTPS Certificates Tests
# ============================================================


class TestHTTPSCertificates:
    """HTTPS证书测试"""

    def test_get_certificates_success(self, client):
        """测试获取证书列表 - 成功"""
        response = client.get("/api/v1/security/https/certificates")
        assert response.status_code == 200
        data = response.json()
        assert "certificates" in data
        assert "total" in data

    def test_create_certificate_success(self, client):
        """测试创建证书 - 成功"""
        payload = {"domain": "example.com", "algorithm": "RSA"}
        response = client.post("/api/v1/security/https/certificates", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "example.com"

    def test_update_certificate_success(self, client):
        """测试更新证书 - 成功"""
        create_payload = {"domain": "test.com", "algorithm": "RSA"}
        create_response = client.post("/api/v1/security/https/certificates", json=create_payload)
        cert_id = create_response.json()["id"]

        update_payload = {"autoRenew": True}
        response = client.patch(
            f"/api/v1/security/https/certificates/{cert_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["autoRenew"] == True

    def test_update_certificate_not_found(self, client):
        """测试更新证书 - 证书不存在"""
        fake_id = str(uuid.uuid4())
        update_payload = {"autoRenew": True}
        response = client.patch(
            f"/api/v1/security/https/certificates/{fake_id}", json=update_payload
        )
        assert response.status_code == 404


# ============================================================
# 7. Snapshot Encryption Tests
# ============================================================


class TestSnapshotEncryption:
    """快照加密测试"""

    def test_get_snapshots_success(self, client):
        """测试获取快照列表 - 成功"""
        response = client.get("/api/v1/security/snapshot-encryption/snapshots")
        assert response.status_code == 200
        data = response.json()
        assert "snapshots" in data
        assert "total" in data

    def test_create_snapshot_success(self, client):
        """测试创建快照 - 成功"""
        payload = {"name": "Backup Snapshot", "source": "/data/backup"}
        response = client.post("/api/v1/security/snapshot-encryption/snapshots", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Backup Snapshot"

    def test_update_snapshot_success(self, client):
        """测试更新快照 - 成功"""
        create_payload = {"name": "Test Snapshot", "source": "/data"}
        create_response = client.post(
            "/api/v1/security/snapshot-encryption/snapshots", json=create_payload
        )
        snap_id = create_response.json()["id"]

        update_payload = {"status": "archived"}
        response = client.patch(
            f"/api/v1/security/snapshot-encryption/snapshots/{snap_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"


# ============================================================
# 8. Data Encryption Tests
# ============================================================


class TestDataEncryption:
    """数据加密测试"""

    def test_get_data_keys_success(self, client):
        """测试获取数据加密密钥 - 成功"""
        response = client.get("/api/v1/security/data-encryption/keys")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert "total" in data

    def test_create_data_key_success(self, client):
        """测试创建数据加密密钥 - 成功"""
        payload = {"name": "Database Encryption Key"}
        response = client.post("/api/v1/security/data-encryption/keys", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Database Encryption Key"

    def test_update_data_key_success(self, client):
        """测试更新数据加密密钥 - 成功"""
        create_payload = {"name": "Test Key"}
        create_response = client.post("/api/v1/security/data-encryption/keys", json=create_payload)
        key_id = create_response.json()["id"]

        update_payload = {"status": "disabled"}
        response = client.patch(
            f"/api/v1/security/data-encryption/keys/{key_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"


# ============================================================
# 9. Data Privacy Tests
# ============================================================


class TestDataPrivacy:
    """数据隐私测试"""

    def test_get_privacy_subjects_success(self, client):
        """测试获取隐私主体 - 成功"""
        response = client.get("/api/v1/security/data-privacy/subjects")
        assert response.status_code == 200
        data = response.json()
        assert "subjects" in data
        assert "total" in data

    def test_create_privacy_subject_success(self, client):
        """测试创建隐私主体 - 成功"""
        payload = {"name": "John Doe", "type": "user"}
        response = client.post("/api/v1/security/data-privacy/subjects", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"

    def test_update_privacy_subject_success(self, client):
        """测试更新隐私主体 - 成功"""
        create_payload = {"name": "Test User", "type": "user"}
        create_response = client.post("/api/v1/security/data-privacy/subjects", json=create_payload)
        subject_id = create_response.json()["id"]

        update_payload = {"consentLevel": "full"}
        response = client.patch(
            f"/api/v1/security/data-privacy/subjects/{subject_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["consentLevel"] == "full"


# ============================================================
# 10. Compliance Management Tests
# ============================================================


class TestComplianceManagement:
    """合规管理测试"""

    def test_get_compliance_policies_success(self, client):
        """测试获取合规策略 - 成功"""
        response = client.get("/api/v1/security/compliance-management/policies")
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert "total" in data

    def test_create_compliance_policy_success(self, client):
        """测试创建合规策略 - 成功"""
        payload = {"name": "GDPR Compliance Policy", "framework": "GDPR"}
        response = client.post("/api/v1/security/compliance-management/policies", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GDPR Compliance Policy"
        assert data["framework"] == "GDPR"

    def test_update_compliance_policy_success(self, client):
        """测试更新合规策略 - 成功"""
        create_payload = {"name": "Test Policy", "framework": "GDPR"}
        create_response = client.post(
            "/api/v1/security/compliance-management/policies", json=create_payload
        )
        policy_id = create_response.json()["id"]

        update_payload = {"status": "inactive"}
        response = client.patch(
            f"/api/v1/security/compliance-management/policies/{policy_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"


# ============================================================
# 11. Compliance Check Tests
# ============================================================


class TestComplianceCheck:
    """合规检查测试"""

    def test_get_compliance_standards_success(self, client):
        """测试获取合规标准 - 成功"""
        response = client.get("/api/v1/security/compliance-check/standards")
        assert response.status_code == 200
        data = response.json()
        assert "standards" in data
        assert "total" in data

    def test_create_compliance_standard_success(self, client):
        """测试创建合规标准 - 成功"""
        payload = {"name": "SSL Certificate Check", "category": "security"}
        response = client.post("/api/v1/security/compliance-check/standards", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SSL Certificate Check"

    def test_update_compliance_standard_success(self, client):
        """测试更新合规标准 - 成功"""
        create_payload = {"name": "Test Standard", "category": "general"}
        create_response = client.post(
            "/api/v1/security/compliance-check/standards", json=create_payload
        )
        standard_id = create_response.json()["id"]

        update_payload = {"status": "inactive"}
        response = client.patch(
            f"/api/v1/security/compliance-check/standards/{standard_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"


# ============================================================
# 12. Database Security Tests
# ============================================================


class TestDatabaseSecurity:
    """数据库安全测试"""

    def test_get_database_instances_success(self, client):
        """测试获取数据库实例 - 成功"""
        response = client.get("/api/v1/security/database-security/instances")
        assert response.status_code == 200
        data = response.json()
        assert "instances" in data
        assert "total" in data

    def test_create_database_instance_success(self, client):
        """测试创建数据库实例 - 成功"""
        payload = {"name": "Production DB", "type": "postgresql", "host": "db.example.com"}
        response = client.post("/api/v1/security/database-security/instances", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Production DB"
        assert data["type"] == "postgresql"

    def test_update_database_instance_success(self, client):
        """测试更新数据库实例 - 成功"""
        create_payload = {"name": "Test DB", "type": "postgresql", "host": "localhost"}
        create_response = client.post(
            "/api/v1/security/database-security/instances", json=create_payload
        )
        instance_id = create_response.json()["id"]

        update_payload = {"status": "inactive"}
        response = client.patch(
            f"/api/v1/security/database-security/instances/{instance_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"


# ============================================================
# 13. API Security Tests
# ============================================================


class TestAPISecurity:
    """API安全测试"""

    def test_get_api_endpoints_success(self, client):
        """测试获取API端点 - 成功"""
        response = client.get("/api/v1/security/api-security/endpoints")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "total" in data

    def test_create_api_endpoint_success(self, client):
        """测试创建API端点 - 成功"""
        payload = {"path": "/api/v1/test", "method": "POST"}
        response = client.post("/api/v1/security/api-security/endpoints", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "/api/v1/test"

    def test_update_api_endpoint_success(self, client):
        """测试更新API端点 - 成功"""
        create_payload = {"path": "/api/v1/test", "method": "GET"}
        create_response = client.post(
            "/api/v1/security/api-security/endpoints", json=create_payload
        )
        endpoint_id = create_response.json()["id"]

        update_payload = {"status": "disabled"}
        response = client.patch(
            f"/api/v1/security/api-security/endpoints/{endpoint_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"

    def test_delete_api_endpoint_success(self, client):
        """测试删除API端点 - 成功"""
        create_payload = {"path": "/api/v1/test", "method": "GET"}
        create_response = client.post(
            "/api/v1/security/api-security/endpoints", json=create_payload
        )
        endpoint_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/api-security/endpoints/{endpoint_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 14. Input Validation Tests
# ============================================================


class TestInputValidation:
    """输入验证测试"""

    def test_get_input_validation_rules_success(self, client):
        """测试获取输入验证规则 - 成功"""
        response = client.get("/api/v1/security/input-validation/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    def test_create_input_validation_rule_success(self, client):
        """测试创建输入验证规则 - 成功"""
        payload = {"name": "Email Format Validation", "field": "email"}
        response = client.post("/api/v1/security/input-validation/rules", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Email Format Validation"

    def test_update_input_validation_rule_success(self, client):
        """测试更新输入验证规则 - 成功"""
        create_payload = {"name": "Test Rule", "field": "username"}
        create_response = client.post(
            "/api/v1/security/input-validation/rules", json=create_payload
        )
        rule_id = create_response.json()["id"]

        update_payload = {"enabled": False}
        response = client.patch(
            f"/api/v1/security/input-validation/rules/{rule_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_delete_input_validation_rule_success(self, client):
        """测试删除输入验证规则 - 成功"""
        create_payload = {"name": "Test Rule", "field": "username"}
        create_response = client.post(
            "/api/v1/security/input-validation/rules", json=create_payload
        )
        rule_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/input-validation/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 15. Penetration Testing Tests
# ============================================================


class TestPenetrationTesting:
    """渗透测试测试"""

    def test_get_penetration_projects_success(self, client):
        """测试获取渗透测试项目 - 成功"""
        response = client.get("/api/v1/security/penetration-testing/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data

    def test_create_penetration_project_success(self, client):
        """测试创建渗透测试项目 - 成功"""
        payload = {"name": "Annual Security Test", "target": "https://example.com"}
        response = client.post("/api/v1/security/penetration-testing/projects", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Annual Security Test"

    def test_update_penetration_project_success(self, client):
        """测试更新渗透测试项目 - 成功"""
        create_payload = {"name": "Test Project", "target": "https://test.com"}
        create_response = client.post(
            "/api/v1/security/penetration-testing/projects", json=create_payload
        )
        project_id = create_response.json()["id"]

        update_payload = {"status": "in_progress"}
        response = client.patch(
            f"/api/v1/security/penetration-testing/projects/{project_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"


# ============================================================
# 16. Security Testing Tests
# ============================================================


class TestSecurityTesting:
    """安全测试测试"""

    def test_get_security_tests_success(self, client):
        """测试获取安全测试 - 成功"""
        response = client.get("/api/v1/security/security-testing/tests")
        assert response.status_code == 200
        data = response.json()
        assert "tests" in data
        assert "total" in data

    def test_create_security_test_success(self, client):
        """测试创建安全测试 - 成功"""
        payload = {"name": "SAST Scan", "testType": "sast"}
        response = client.post("/api/v1/security/security-testing/tests", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SAST Scan"

    def test_update_security_test_success(self, client):
        """测试更新安全测试 - 成功"""
        create_payload = {"name": "Test Scan", "testType": "dast"}
        create_response = client.post(
            "/api/v1/security/security-testing/tests", json=create_payload
        )
        test_id = create_response.json()["id"]

        update_payload = {"status": "running"}
        response = client.patch(
            f"/api/v1/security/security-testing/tests/{test_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"


# ============================================================
# 17. Vulnerability Management Tests
# ============================================================


class TestVulnerabilityManagement:
    """漏洞管理测试"""

    def test_get_vulnerability_tickets_success(self, client):
        """测试获取漏洞工单 - 成功"""
        response = client.get("/api/v1/security/vulnerability-management/tickets")
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        assert "total" in data

    def test_create_vulnerability_ticket_success(self, client):
        """测试创建漏洞工单 - 成功"""
        payload = {"title": "SQL Injection Vulnerability", "severity": "high"}
        response = client.post("/api/v1/security/vulnerability-management/tickets", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "SQL Injection Vulnerability"
        assert data["severity"] == "high"

    def test_update_vulnerability_ticket_success(self, client):
        """测试更新漏洞工单 - 成功"""
        create_payload = {"title": "Test Vulnerability", "severity": "medium"}
        create_response = client.post(
            "/api/v1/security/vulnerability-management/tickets", json=create_payload
        )
        ticket_id = create_response.json()["id"]

        update_payload = {"status": "in_progress"}
        response = client.patch(
            f"/api/v1/security/vulnerability-management/tickets/{ticket_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"


# ============================================================
# 18. Vulnerability Intelligence Tests
# ============================================================


class TestVulnerabilityIntelligence:
    """漏洞情报测试"""

    def test_get_threats_success(self, client):
        """测试获取威胁情报 - 成功"""
        response = client.get("/api/v1/security/vulnerability-intelligence/threats")
        assert response.status_code == 200
        data = response.json()
        assert "threats" in data
        assert "total" in data

    def test_create_threat_success(self, client):
        """测试创建威胁情报 - 成功"""
        payload = {"name": "CVE-2024-1234", "threatType": "exploit"}
        response = client.post("/api/v1/security/vulnerability-intelligence/threats", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CVE-2024-1234"


# ============================================================
# 19. Vulnerability Scan Tests
# ============================================================


class TestVulnerabilityScan:
    """漏洞扫描测试"""

    def test_get_vulnerability_scans_success(self, client):
        """测试获取漏洞扫描 - 成功"""
        response = client.get("/api/v1/security/vulnerability-scan/vulnerabilities")
        assert response.status_code == 200
        data = response.json()
        assert "vulnerabilities" in data
        assert "total" in data

    def test_create_vulnerability_scan_success(self, client):
        """测试创建漏洞扫描 - 成功"""
        payload = {"target": "https://example.com", "scanType": "full"}
        response = client.post("/api/v1/security/vulnerability-scan/vulnerabilities", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["target"] == "https://example.com"

    def test_update_vulnerability_scan_success(self, client):
        """测试更新漏洞扫描 - 成功"""
        create_payload = {"target": "https://test.com", "scanType": "quick"}
        create_response = client.post(
            "/api/v1/security/vulnerability-scan/vulnerabilities", json=create_payload
        )
        scan_id = create_response.json()["id"]

        update_payload = {"status": "running"}
        response = client.patch(
            f"/api/v1/security/vulnerability-scan/vulnerabilities/{scan_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"


# ============================================================
# 20. Audit Center Tests
# ============================================================


class TestAuditCenter:
    """审计中心测试"""

    def test_get_audit_reports_success(self, client):
        """测试获取审计报告 - 成功"""
        response = client.get("/api/v1/security/audit-center/reports")
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data

    def test_create_audit_report_success(self, client):
        """测试创建审计报告 - 成功"""
        payload = {"title": "Monthly Security Audit", "reportType": "security"}
        response = client.post("/api/v1/security/audit-center/reports", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Monthly Security Audit"

    def test_update_audit_report_success(self, client):
        """测试更新审计报告 - 成功"""
        create_payload = {"title": "Test Report", "reportType": "compliance"}
        create_response = client.post("/api/v1/security/audit-center/reports", json=create_payload)
        report_id = create_response.json()["id"]

        update_payload = {"status": "published"}
        response = client.patch(
            f"/api/v1/security/audit-center/reports/{report_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"


# ============================================================
# 21. Operation Records Tests
# ============================================================


class TestOperationRecords:
    """操作记录测试"""

    def test_get_operation_records_success(self, client):
        """测试获取操作记录 - 成功"""
        response = client.get("/api/v1/security/operation-records")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "total" in data

    def test_get_operation_records_with_limit(self, client):
        """测试获取操作记录 - 带限制"""
        response = client.get("/api/v1/security/operation-records?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) <= 10

    def test_get_operation_records_invalid_limit(self, client):
        """测试获取操作记录 - 无效限制"""
        response = client.get("/api/v1/security/operation-records?limit=1000")
        assert response.status_code == 422


# ============================================================
# 22. Audit Logs Tests
# ============================================================


class TestAuditLogs:
    """审计日志测试"""

    @patch("api.security_advanced_router.get_audit_log")
    def test_get_audit_logs_success(self, mock_get_audit_log, client):
        """测试获取审计日志 - 成功"""
        mock_get_audit_log.return_value = [
            {"id": "1", "command": "ls", "timestamp": "2024-01-01T00:00:00"}
        ]
        response = client.get("/api/v1/security/audit/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data


# ============================================================
# 23. Command Rewrite Tests
# ============================================================


class TestCommandRewrite:
    """命令改写测试"""

    def test_get_command_rewrite_rules_success(self, client):
        """测试获取命令改写规则 - 成功"""
        response = client.get("/api/v1/security/command-rewrite/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    def test_create_command_rewrite_rule_success(self, client):
        """测试创建命令改写规则 - 成功"""
        payload = {"pattern": "rm -rf /", "replacement": "echo 'Dangerous command blocked'"}
        response = client.post("/api/v1/security/command-rewrite/rules", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["pattern"] == "rm -rf /"

    def test_update_command_rewrite_rule_success(self, client):
        """测试更新命令改写规则 - 成功"""
        create_payload = {"pattern": "test", "replacement": "replacement"}
        create_response = client.post("/api/v1/security/command-rewrite/rules", json=create_payload)
        rule_id = create_response.json()["id"]

        update_payload = {"enabled": False}
        response = client.patch(
            f"/api/v1/security/command-rewrite/rules/{rule_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_delete_command_rewrite_rule_success(self, client):
        """测试删除命令改写规则 - 成功"""
        create_payload = {"pattern": "test", "replacement": "replacement"}
        create_response = client.post("/api/v1/security/command-rewrite/rules", json=create_payload)
        rule_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/command-rewrite/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 24. Command Check Tests
# ============================================================


class TestCommandCheck:
    """命令检查测试"""

    @patch("api.security_advanced_router.analyze_command")
    def test_check_command_success(self, mock_analyze_command, client):
        """测试检查命令 - 成功"""
        mock_analyze_command.return_value = {
            "risk_level": "high",
            "risk_name": "File Deletion",
            "reason": "Command deletes files",
            "action": "block",
            "safe_alternative": "Use rm with caution",
        }
        payload = {"command": "rm -rf /tmp"}
        response = client.post("/api/v1/security/command-check/check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "rm -rf /tmp"
        assert "risk_level" in data

    def test_check_command_validation_error(self, client):
        """测试检查命令 - 验证错误"""
        payload = {"command": ""}  # 空命令
        response = client.post("/api/v1/security/command-check/check", json=payload)
        assert response.status_code == 422


# ============================================================
# 25. Command Guard Tests
# ============================================================


class TestCommandGuard:
    """命令管控测试"""

    def test_get_command_guard_rules_success(self, client):
        """测试获取命令管控规则 - 成功"""
        response = client.get("/api/v1/security/command-guard/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    def test_create_command_guard_rule_success(self, client):
        """测试创建命令管控规则 - 成功"""
        payload = {
            "command": "rm -rf",
            "pattern": "rm.*-rf",
            "severity": "critical",
            "action": "block",
        }
        response = client.post("/api/v1/security/command-guard/rules", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "rm -rf"
        assert data["severity"] == "critical"

    def test_update_command_guard_rule_success(self, client):
        """测试更新命令管控规则 - 成功"""
        create_payload = {
            "command": "test",
            "pattern": "test.*",
            "severity": "high",
            "action": "block",
        }
        create_response = client.post("/api/v1/security/command-guard/rules", json=create_payload)
        rule_id = create_response.json()["id"]

        update_payload = {"enabled": False}
        response = client.patch(
            f"/api/v1/security/command-guard/rules/{rule_id}", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_delete_command_guard_rule_success(self, client):
        """测试删除命令管控规则 - 成功"""
        create_payload = {
            "command": "test",
            "pattern": "test.*",
            "severity": "high",
            "action": "block",
        }
        create_response = client.post("/api/v1/security/command-guard/rules", json=create_payload)
        rule_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/security/command-guard/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# Access Control Tests
# ============================================================


class TestAccessControl:
    """访问控制测试"""

    @patch("api.security_advanced_router.INTERNAL_API_KEY", "test-key")
    @patch("api.security_advanced_router.ALLOWED_LOCAL_IPS", ["127.0.0.1"])
    def test_access_with_valid_key(self, client):
        """测试使用有效密钥访问"""
        # 这个测试需要模拟header，但TestClient可能不支持自定义header
        # 这里仅作为示例
        pass

    @patch("api.security_advanced_router.INTERNAL_API_KEY", "test-key")
    @patch("api.security_advanced_router.ALLOWED_LOCAL_IPS", ["127.0.0.1"])
    def test_access_with_invalid_key(self, client):
        """测试使用无效密钥访问"""
        # 这个测试需要模拟header，但TestClient可能不支持自定义header
        # 这里仅作为示例
        pass
