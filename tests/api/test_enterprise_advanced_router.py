# -*- coding: utf-8 -*-
"""
Test suite for Enterprise Advanced Router
==========================================

Comprehensive tests for enterprise functionality API endpoints including:
- Tenant management (CRUD)
- User management (CRUD)
- Role management (CRUD)
- Permission management (CRUD)
- Audit logs
- Enterprise settings
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the router
from api.enterprise_advanced_router import (
    router,
    TenantCreate,
    TenantUpdate,
    UserCreate,
    UserUpdate,
    RoleCreate,
    RoleUpdate,
    PermissionCreate,
    PermissionUpdate,
    SettingsUpdate,
    tenants,
    users,
    roles,
    permissions,
    enterprise_settings,
    ENTERPRISE_AVAILABLE
)


# Mock enterprise functionality manager
class MockAuditLog:
    def __init__(self, entry_id, tenant_id, user_id, action, resource_type, resource_id, outcome):
        self.entry_id = entry_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.outcome = outcome
        self.ip_address = "127.0.0.1"
        self.user_agent = "TestClient"
        self.timestamp = datetime.utcnow()
        self.data_classification = Mock()
        self.data_classification.value = "public"
        self.metadata = {}


class MockEnterpriseFunctionalityManager:
    def __init__(self):
        self.tenant_data_isolation = {}
        self.audit_retention_days = 90
    
    async def query_audit_logs(self, tenant_id=None, user_id=None, action=None,
                               start_date=None, end_date=None, limit=100):
        # Return mock audit logs
        return [
            MockAuditLog(
                f"log-{i}", tenant_id or "tenant-001", user_id or "user-001",
                action or "create", "document", f"doc-{i}", "success"
            )
            for i in range(min(limit, 10))
        ]


@pytest.fixture
def mock_manager():
    """Create a mock enterprise functionality manager"""
    return MockEnterpriseFunctionalityManager()


@pytest.fixture
def clear_storage():
    """Clear in-memory storage before each test"""
    tenants.clear()
    users.clear()
    roles.clear()
    permissions.clear()
    yield
    tenants.clear()
    users.clear()
    roles.clear()
    permissions.clear()


@pytest.fixture
def client(mock_manager, clear_storage):
    """Create a test client with mocked dependencies"""
    with patch('api.enterprise_advanced_router.ENTERPRISE_AVAILABLE', True):
        with patch('api.enterprise_advanced_router.enterprise_functionality_manager', mock_manager):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)


# ==================== Tenant Management Tests ====================

class TestListTenants:
    """Test cases for listing tenants"""
    
    def test_list_tenants_success(self, client):
        """Test successful tenant listing"""
        # Create test tenants
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/tenants")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "tenants" in data["data"]
        assert len(data["data"]["tenants"]) >= 1
    
    def test_list_tenants_with_status_filter(self, client):
        """Test tenant listing with status filter"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/tenants?status=active")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_list_tenants_with_plan_filter(self, client):
        """Test tenant listing with plan filter"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/tenants?plan=enterprise")
        assert response.status_code == 200
    
    def test_list_tenants_with_pagination(self, client):
        """Test tenant listing with pagination"""
        for i in range(5):
            tenants[f"tenant-{i:03d}"] = {
                "tenant_id": f"tenant-{i:03d}",
                "name": f"Tenant {i}",
                "domain": f"tenant{i}.com",
                "plan": "standard",
                "max_users": 100,
                "status": "active",
                "settings": {},
                "created_at": "2024-01-01",
                "updated_at": "2024-01-01"
            }
        
        response = client.get("/api/v1/enterprise/tenants?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["tenants"]) == 2
        assert data["data"]["total"] == 5
    
    def test_list_tenants_empty(self, client):
        """Test listing tenants when none exist"""
        response = client.get("/api/v1/enterprise/tenants")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["tenants"]) == 0


class TestCreateTenant:
    """Test cases for creating tenants"""
    
    def test_create_tenant_success(self, client):
        """Test successful tenant creation"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "name": "New Tenant",
                "domain": "newtenant.com",
                "plan": "standard",
                "max_users": 100
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "tenant_id" in data["data"]
        assert data["data"]["name"] == "New Tenant"
        assert data["data"]["status"] == "active"
    
    def test_create_tenant_with_custom_id(self, client):
        """Test tenant creation with custom ID"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "tenant_id": "custom-tenant-001",
                "name": "Custom Tenant",
                "domain": "custom.com",
                "plan": "enterprise"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["tenant_id"] == "custom-tenant-001"
    
    def test_create_tenant_duplicate_id(self, client):
        """Test tenant creation with duplicate ID"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Existing",
            "domain": "existing.com",
            "plan": "standard",
            "max_users": 100,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "tenant_id": "tenant-001",
                "name": "Duplicate",
                "domain": "duplicate.com",
                "plan": "standard"
            }
        )
        assert response.status_code == 400
    
    def test_create_tenant_missing_required_fields(self, client):
        """Test tenant creation with missing required fields"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "name": "Test"
                # Missing domain
            }
        )
        assert response.status_code == 422
    
    def test_create_tenant_invalid_max_users(self, client):
        """Test tenant creation with invalid max_users"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "name": "Test",
                "domain": "test.com",
                "max_users": 0  # Invalid: should be >= 1
            }
        )
        assert response.status_code == 422


class TestGetTenant:
    """Test cases for getting tenant details"""
    
    def test_get_tenant_success(self, client):
        """Test successful tenant retrieval"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/tenants/tenant-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["tenant_id"] == "tenant-001"
        assert "user_count" in data["data"]
    
    def test_get_tenant_with_users(self, client):
        """Test getting tenant with user count"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        users["user-001"] = {
            "user_id": "user-001",
            "tenant_id": "tenant-001",
            "username": "john",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/tenants/tenant-001")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["user_count"] == 1
    
    def test_get_tenant_not_found(self, client):
        """Test getting non-existent tenant"""
        response = client.get("/api/v1/enterprise/tenants/nonexistent")
        assert response.status_code == 404


class TestUpdateTenant:
    """Test cases for updating tenants"""
    
    def test_update_tenant_name(self, client):
        """Test updating tenant name"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Old Name",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/enterprise/tenants/tenant-001",
            json={"name": "New Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "New Name"
    
    def test_update_tenant_status(self, client):
        """Test updating tenant status"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/enterprise/tenants/tenant-001",
            json={"status": "suspended"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "suspended"
    
    def test_update_tenant_settings(self, client):
        """Test updating tenant settings"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/enterprise/tenants/tenant-001",
            json={"settings": {"feature_x": True, "feature_y": False}}
        )
        assert response.status_code == 200
    
    def test_update_tenant_not_found(self, client):
        """Test updating non-existent tenant"""
        response = client.patch(
            "/api/v1/enterprise/tenants/nonexistent",
            json={"name": "New Name"}
        )
        assert response.status_code == 404


class TestDeleteTenant:
    """Test cases for deleting tenants"""
    
    def test_delete_tenant_success(self, client):
        """Test successful tenant deletion"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.delete("/api/v1/enterprise/tenants/tenant-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["deleted"] is True
        assert "tenant-001" not in tenants
    
    def test_delete_tenant_with_users(self, client):
        """Test deleting tenant with associated users"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        users["user-001"] = {
            "user_id": "user-001",
            "tenant_id": "tenant-001",
            "username": "john",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.delete("/api/v1/enterprise/tenants/tenant-001")
        assert response.status_code == 200
        assert "user-001" not in users
    
    def test_delete_tenant_not_found(self, client):
        """Test deleting non-existent tenant"""
        response = client.delete("/api/v1/enterprise/tenants/nonexistent")
        assert response.status_code == 404


# ==================== User Management Tests ====================

class TestListUsers:
    """Test cases for listing users"""
    
    def test_list_users_success(self, client):
        """Test successful user listing"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        users["user-001"] = {
            "user_id": "user-001",
            "tenant_id": "tenant-001",
            "username": "john",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/users")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "users" in data["data"]
    
    def test_list_users_with_tenant_filter(self, client):
        """Test user listing with tenant filter"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        users["user-001"] = {
            "user_id": "user-001",
            "tenant_id": "tenant-001",
            "username": "john",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/users?tenant_id=tenant-001")
        assert response.status_code == 200
    
    def test_list_users_with_status_filter(self, client):
        """Test user listing with status filter"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        users["user-001"] = {
            "user_id": "user-001",
            "tenant_id": "tenant-001",
            "username": "john",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/users?status=active")
        assert response.status_code == 200
    
    def test_list_users_with_pagination(self, client):
        """Test user listing with pagination"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        for i in range(5):
            users[f"user-{i:03d}"] = {
                "user_id": f"user-{i:03d}",
                "tenant_id": "tenant-001",
                "username": f"user{i}",
                "email": f"user{i}@acme.com",
                "full_name": f"User {i}",
                "status": "active",
                "created_at": "2024-01-01",
                "updated_at": "2024-01-01"
            }
        
        response = client.get("/api/v1/enterprise/users?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["users"]) == 2
        assert data["data"]["total"] == 5


class TestCreateUser:
    """Test cases for creating users"""
    
    def test_create_user_success(self, client):
        """Test successful user creation"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/users",
            json={
                "tenant_id": "tenant-001",
                "username": "johndoe",
                "email": "john@acme.com",
                "full_name": "John Doe"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "user_id" in data["data"]
        assert data["data"]["username"] == "johndoe"
    
    def test_create_user_with_custom_id(self, client):
        """Test user creation with custom ID"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/users",
            json={
                "user_id": "custom-user-001",
                "tenant_id": "tenant-001",
                "username": "john",
                "email": "john@acme.com",
                "full_name": "John Doe"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["user_id"] == "custom-user-001"
    
    def test_create_user_tenant_not_found(self, client):
        """Test user creation with non-existent tenant"""
        response = client.post(
            "/api/v1/enterprise/users",
            json={
                "tenant_id": "nonexistent",
                "username": "john",
                "email": "john@acme.com",
                "full_name": "John Doe"
            }
        )
        assert response.status_code == 404
    
    def test_create_user_duplicate_id(self, client):
        """Test user creation with duplicate ID"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        users["user-001"] = {
            "user_id": "user-001",
            "tenant_id": "tenant-001",
            "username": "john",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/users",
            json={
                "user_id": "user-001",
                "tenant_id": "tenant-001",
                "username": "jane",
                "email": "jane@acme.com",
                "full_name": "Jane Doe"
            }
        )
        assert response.status_code == 400
    
    def test_create_user_missing_required_fields(self, client):
        """Test user creation with missing required fields"""
        response = client.post(
            "/api/v1/enterprise/users",
            json={
                "username": "john"
                # Missing tenant_id, email, full_name
            }
        )
        assert response.status_code == 422


# ==================== Role Management Tests ====================

class TestListRoles:
    """Test cases for listing roles"""
    
    def test_list_roles_success(self, client):
        """Test successful role listing"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        roles["role-001"] = {
            "role_id": "role-001",
            "tenant_id": "tenant-001",
            "name": "Admin",
            "description": "Administrator role",
            "permissions": ["perm-001", "perm-002"],
            "is_system_role": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/roles")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "roles" in data["data"]
    
    def test_list_roles_with_tenant_filter(self, client):
        """Test role listing with tenant filter"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        roles["role-001"] = {
            "role_id": "role-001",
            "tenant_id": "tenant-001",
            "name": "Admin",
            "description": "Administrator",
            "permissions": [],
            "is_system_role": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/roles?tenant_id=tenant-001")
        assert response.status_code == 200
    
    def test_list_roles_with_system_filter(self, client):
        """Test role listing with system role filter"""
        roles["role-001"] = {
            "role_id": "role-001",
            "tenant_id": "tenant-001",
            "name": "System Admin",
            "description": "System role",
            "permissions": [],
            "is_system_role": True,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/roles?is_system_role=true")
        assert response.status_code == 200


class TestCreateRole:
    """Test cases for creating roles"""
    
    def test_create_role_success(self, client):
        """Test successful role creation"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/roles",
            json={
                "tenant_id": "tenant-001",
                "name": "Editor",
                "description": "Editor role",
                "permissions": ["perm-001"]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "role_id" in data["data"]
        assert data["data"]["name"] == "Editor"
    
    def test_create_role_with_custom_id(self, client):
        """Test role creation with custom ID"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/roles",
            json={
                "role_id": "custom-role-001",
                "tenant_id": "tenant-001",
                "name": "Custom Role",
                "description": "Custom",
                "permissions": []
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["role_id"] == "custom-role-001"
    
    def test_create_role_tenant_not_found(self, client):
        """Test role creation with non-existent tenant"""
        response = client.post(
            "/api/v1/enterprise/roles",
            json={
                "tenant_id": "nonexistent",
                "name": "Admin",
                "description": "Admin role",
                "permissions": []
            }
        )
        assert response.status_code == 404
    
    def test_create_role_duplicate_id(self, client):
        """Test role creation with duplicate ID"""
        tenants["tenant-001"] = {
            "tenant_id": "tenant-001",
            "name": "Acme Corp",
            "domain": "acme.com",
            "plan": "enterprise",
            "max_users": 500,
            "status": "active",
            "settings": {},
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        roles["role-001"] = {
            "role_id": "role-001",
            "tenant_id": "tenant-001",
            "name": "Admin",
            "description": "Admin",
            "permissions": [],
            "is_system_role": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/roles",
            json={
                "role_id": "role-001",
                "tenant_id": "tenant-001",
                "name": "Duplicate",
                "description": "Duplicate",
                "permissions": []
            }
        )
        assert response.status_code == 400


# ==================== Permission Management Tests ====================

class TestListPermissions:
    """Test cases for listing permissions"""
    
    def test_list_permissions_success(self, client):
        """Test successful permission listing"""
        permissions["perm-001"] = {
            "permission_id": "perm-001",
            "name": "document.read",
            "resource": "document",
            "action": "read",
            "description": "Read documents",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/permissions")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "permissions" in data["data"]
    
    def test_list_permissions_with_resource_filter(self, client):
        """Test permission listing with resource filter"""
        permissions["perm-001"] = {
            "permission_id": "perm-001",
            "name": "document.read",
            "resource": "document",
            "action": "read",
            "description": "Read documents",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/permissions?resource=document")
        assert response.status_code == 200
    
    def test_list_permissions_with_action_filter(self, client):
        """Test permission listing with action filter"""
        permissions["perm-001"] = {
            "permission_id": "perm-001",
            "name": "document.read",
            "resource": "document",
            "action": "read",
            "description": "Read documents",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/enterprise/permissions?action=read")
        assert response.status_code == 200


class TestCreatePermission:
    """Test cases for creating permissions"""
    
    def test_create_permission_success(self, client):
        """Test successful permission creation"""
        response = client.post(
            "/api/v1/enterprise/permissions",
            json={
                "name": "document.write",
                "resource": "document",
                "action": "write",
                "description": "Write documents"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "permission_id" in data["data"]
        assert data["data"]["name"] == "document.write"
    
    def test_create_permission_with_custom_id(self, client):
        """Test permission creation with custom ID"""
        response = client.post(
            "/api/v1/enterprise/permissions",
            json={
                "permission_id": "custom-perm-001",
                "name": "custom.permission",
                "resource": "custom",
                "action": "custom",
                "description": "Custom permission"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["permission_id"] == "custom-perm-001"
    
    def test_create_permission_duplicate_id(self, client):
        """Test permission creation with duplicate ID"""
        permissions["perm-001"] = {
            "permission_id": "perm-001",
            "name": "document.read",
            "resource": "document",
            "action": "read",
            "description": "Read documents",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/enterprise/permissions",
            json={
                "permission_id": "perm-001",
                "name": "duplicate",
                "resource": "duplicate",
                "action": "duplicate",
                "description": "Duplicate"
            }
        )
        assert response.status_code == 400
    
    def test_create_permission_missing_required_fields(self, client):
        """Test permission creation with missing required fields"""
        response = client.post(
            "/api/v1/enterprise/permissions",
            json={
                "name": "test"
                # Missing resource, action, description
            }
        )
        assert response.status_code == 422


# ==================== Audit Logs Tests ====================

class TestAuditLogs:
    """Test cases for audit logs"""
    
    def test_list_audit_logs_success(self, client, mock_manager):
        """Test successful audit log listing"""
        response = client.get("/api/v1/enterprise/audit-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "logs" in data["data"]
    
    def test_list_audit_logs_with_filters(self, client, mock_manager):
        """Test audit log listing with filters"""
        response = client.get("/api/v1/enterprise/audit-logs?tenant_id=tenant-001&action=create")
        assert response.status_code == 200
    
    def test_list_audit_logs_with_date_range(self, client, mock_manager):
        """Test audit log listing with date range"""
        response = client.get(
            "/api/v1/enterprise/audit-logs?start_date=2024-01-01&end_date=2024-12-31"
        )
        assert response.status_code == 200
    
    def test_list_audit_logs_invalid_date_format(self, client):
        """Test audit log listing with invalid date format"""
        response = client.get("/api/v1/enterprise/audit-logs?start_date=invalid-date")
        assert response.status_code == 400
    
    def test_list_audit_logs_service_unavailable(self):
        """Test audit log listing when service is unavailable"""
        with patch('api.enterprise_advanced_router.ENTERPRISE_AVAILABLE', False):
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            
            response = client.get("/api/v1/enterprise/audit-logs")
            assert response.status_code == 503


# ==================== Enterprise Settings Tests ====================

class TestEnterpriseSettings:
    """Test cases for enterprise settings"""
    
    def test_get_settings_success(self, client):
        """Test successful settings retrieval"""
        response = client.get("/api/v1/enterprise/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "tenant_isolation_enabled" in data["data"]
    
    def test_update_settings_tenant_isolation(self, client):
        """Test updating tenant isolation setting"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"tenant_isolation_enabled": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tenant_isolation_enabled"] is False
    
    def test_update_settings_audit_retention(self, client):
        """Test updating audit retention days"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"audit_retention_days": 180}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["audit_retention_days"] == 180
    
    def test_update_settings_encryption(self, client):
        """Test updating encryption setting"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"encryption_enabled": False}
        )
        assert response.status_code == 200
    
    def test_update_settings_sso(self, client):
        """Test updating SSO setting"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"sso_enabled": True}
        )
        assert response.status_code == 200
    
    def test_update_settings_compliance_standards(self, client):
        """Test updating compliance standards"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"compliance_standards": ["gdpr", "hipaa"]}
        )
        assert response.status_code == 200
    
    def test_update_settings_custom_settings(self, client):
        """Test updating custom settings"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"custom_settings": {"feature_a": True, "feature_b": "value"}}
        )
        assert response.status_code == 200
    
    def test_update_settings_invalid_retention_days(self, client):
        """Test updating settings with invalid retention days"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={"audit_retention_days": 0}  # Invalid: should be >= 1
        )
        assert response.status_code == 422
    
    def test_update_settings_multiple_fields(self, client):
        """Test updating multiple settings at once"""
        response = client.patch(
            "/api/v1/enterprise/settings",
            json={
                "tenant_isolation_enabled": True,
                "audit_retention_days": 90,
                "encryption_enabled": True,
                "sso_enabled": True
            }
        )
        assert response.status_code == 200


# ==================== Data Validation Tests ====================

class TestDataValidation:
    """Test cases for data validation"""
    
    def test_tenant_create_validation(self):
        """Test TenantCreate model validation"""
        tenant = TenantCreate(
            name="Test Tenant",
            domain="test.com",
            plan="standard"
        )
        assert tenant.name == "Test Tenant"
        assert tenant.max_users == 100  # Default value
    
    def test_tenant_update_validation(self):
        """Test TenantUpdate model validation"""
        # All fields optional
        tenant = TenantUpdate()
        assert tenant.name is None
        assert tenant.domain is None
    
    def test_user_create_validation(self):
        """Test UserCreate model validation"""
        user = UserCreate(
            tenant_id="tenant-001",
            username="john",
            email="john@test.com",
            full_name="John Doe"
        )
        assert user.status == "active"  # Default value
    
    def test_role_create_validation(self):
        """Test RoleCreate model validation"""
        role = RoleCreate(
            tenant_id="tenant-001",
            name="Admin",
            description="Administrator",
            permissions=["perm-001"]
        )
        assert role.is_system_role is False  # Default value
    
    def test_permission_create_validation(self):
        """Test PermissionCreate model validation"""
        perm = PermissionCreate(
            name="document.read",
            resource="document",
            action="read",
            description="Read documents"
        )
        assert perm.name == "document.read"
    
    def test_settings_update_validation(self):
        """Test SettingsUpdate model validation"""
        # All fields optional
        settings = SettingsUpdate()
        assert settings.tenant_isolation_enabled is None


# ==================== Edge Cases and Error Handling ====================

class TestEdgeCases:
    """Test cases for edge cases and error handling"""
    
    def test_empty_tenant_list(self, client):
        """Test listing tenants when none exist"""
        response = client.get("/api/v1/enterprise/tenants")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["tenants"]) == 0
    
    def test_empty_user_list(self, client):
        """Test listing users when none exist"""
        response = client.get("/api/v1/enterprise/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["users"]) == 0
    
    def test_empty_role_list(self, client):
        """Test listing roles when none exist"""
        response = client.get("/api/v1/enterprise/roles")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["roles"]) == 0
    
    def test_empty_permission_list(self, client):
        """Test listing permissions when none exist"""
        response = client.get("/api/v1/enterprise/permissions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["permissions"]) == 0
    
    def test_special_characters_in_names(self, client):
        """Test creating tenant with special characters"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "name": "Tenant & Co.",
                "domain": "tenant.com",
                "plan": "standard"
            }
        )
        assert response.status_code == 201
    
    def test_unicode_in_names(self, client):
        """Test creating tenant with unicode characters"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "name": "测试租户",
                "domain": "test.com",
                "plan": "standard"
            }
        )
        assert response.status_code == 201
    
    def test_max_users_boundary(self, client):
        """Test tenant creation with max_users at boundary"""
        response = client.post(
            "/api/v1/enterprise/tenants",
            json={
                "name": "Test",
                "domain": "test.com",
                "max_users": 1  # Minimum valid value
            }
        )
        assert response.status_code == 201
    
    def test_pagination_offset_beyond_data(self, client):
        """Test pagination with offset beyond available data"""
        response = client.get("/api/v1/enterprise/tenants?limit=10&offset=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["tenants"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
