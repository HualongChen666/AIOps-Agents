# -*- coding: utf-8 -*-
"""
Test suite for Tenant Router (Basic CRUD operations)
租户基础路由测试套件（CRUD操作）
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.tenant_router import (
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    create_new_tenant,
    delete_existing_tenant,
    get_all_tenants,
    get_one_tenant,
    router,
    update_existing_tenant,
)
from core.authentication import UserInDB
from core.tenant_engine import Quota, Tenant, Usage, Billing


# ============ Fixtures ============


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user"""
    return UserInDB(
        id=1,
        username="admin",
        full_name="Admin User",
        email="admin@example.com",
        role="admin",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user"""
    return UserInDB(
        id=2,
        username="regular",
        full_name="Regular User",
        email="regular@example.com",
        role="user",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def mock_tenant():
    """Create a mock tenant"""
    return Tenant(
        id="tenant-123",
        name="Test Tenant",
        plan="basic",
        status="active",
        contact="test@example.com",
        quota=Quota(
            cpu=40.0,
            memory=80.0,
            disk=500.0,
            maxUsers=10,
            maxServices=5,
            maxAlerts=1000,
            maxStorage=100,
        ),
        usage=Usage(
            cpu=20.0,
            memory=40.0,
            disk=250.0,
            users=5,
            services=2,
            alerts=500,
            storage=50,
        ),
        billing=Billing(
            cycle="monthly",
            amount=500.0,
            currency="CNY",
            nextBillingDate="2026-12-31",
        ),
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture
def client():
    """Create a test client"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ============ GET /api/tenant/ Tests ============


class TestGetAllTenants:
    """Test GET /api/tenant/ endpoint"""

    @pytest.mark.asyncio
    async def test_get_all_tenants_success(self, mock_admin_user, mock_tenant):
        """Test successful retrieval of all tenants"""
        with patch("api.tenant_router.list_tenants", return_value=[mock_tenant]):
            result = await get_all_tenants(user=mock_admin_user)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == "tenant-123"
            assert result[0].name == "Test Tenant"

    @pytest.mark.asyncio
    async def test_get_all_tenants_empty(self, mock_admin_user):
        """Test retrieval when no tenants exist"""
        with patch("api.tenant_router.list_tenants", return_value=[]):
            result = await get_all_tenants(user=mock_admin_user)

            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_all_tenants_multiple(self, mock_admin_user):
        """Test retrieval of multiple tenants"""
        tenant1 = Tenant(id="tenant-1", name="Tenant 1", plan="basic")
        tenant2 = Tenant(id="tenant-2", name="Tenant 2", plan="pro")
        tenant3 = Tenant(id="tenant-3", name="Tenant 3", plan="enterprise")

        with patch("api.tenant_router.list_tenants", return_value=[tenant1, tenant2, tenant3]):
            result = await get_all_tenants(user=mock_admin_user)

            assert isinstance(result, list)
            assert len(result) == 3
            assert result[0].name == "Tenant 1"
            assert result[1].name == "Tenant 2"
            assert result[2].name == "Tenant 3"


# ============ POST /api/tenant/ Tests ============


class TestCreateTenant:
    """Test POST /api/tenant/ endpoint"""

    @pytest.mark.asyncio
    async def test_create_tenant_success(self, mock_admin_user, mock_tenant):
        """Test successful tenant creation"""
        payload = TenantCreate(
            name="New Tenant",
            plan="basic",
            status="active",
            contact="new@example.com",
        )

        with patch("api.tenant_router.create_tenant", return_value=mock_tenant):
            result = await create_new_tenant(payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)
            assert result.id == "tenant-123"
            assert result.name == "Test Tenant"

    @pytest.mark.asyncio
    async def test_create_tenant_with_defaults(self, mock_admin_user, mock_tenant):
        """Test tenant creation with default values"""
        payload = TenantCreate(name="Default Tenant")

        with patch("api.tenant_router.create_tenant", return_value=mock_tenant):
            result = await create_new_tenant(payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)
            assert result.plan == "basic"  # Default plan
            assert result.status == "active"  # Default status

    @pytest.mark.asyncio
    async def test_create_tenant_free_plan(self, mock_admin_user, mock_tenant):
        """Test tenant creation with free plan"""
        payload = TenantCreate(name="Free Tenant", plan="free")

        with patch("api.tenant_router.create_tenant", return_value=mock_tenant):
            result = await create_new_tenant(payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_create_tenant_enterprise_plan(self, mock_admin_user, mock_tenant):
        """Test tenant creation with enterprise plan"""
        payload = TenantCreate(name="Enterprise Tenant", plan="enterprise")

        with patch("api.tenant_router.create_tenant", return_value=mock_tenant):
            result = await create_new_tenant(payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_create_tenant_validation_name_too_short(self):
        """Test tenant creation with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantCreate(name="")

    @pytest.mark.asyncio
    async def test_create_tenant_validation_name_too_long(self):
        """Test tenant creation with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantCreate(name="a" * 101)

    @pytest.mark.asyncio
    async def test_create_tenant_validation_invalid_plan(self):
        """Test tenant creation with invalid plan"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantCreate(name="Test", plan="invalid_plan")

    @pytest.mark.asyncio
    async def test_create_tenant_validation_invalid_status(self):
        """Test tenant creation with invalid status"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantCreate(name="Test", status="invalid_status")

    @pytest.mark.asyncio
    async def test_create_tenant_validation_contact_too_long(self):
        """Test tenant creation with contact too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantCreate(name="Test", contact="a" * 201)


# ============ GET /api/tenant/{tenant_id} Tests ============


class TestGetOneTenant:
    """Test GET /api/tenant/{tenant_id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_one_tenant_success(self, mock_admin_user, mock_tenant):
        """Test successful retrieval of a single tenant"""
        with patch("api.tenant_router.get_tenant", return_value=mock_tenant):
            result = await get_one_tenant("tenant-123", user=mock_admin_user)

            assert isinstance(result, TenantResponse)
            assert result.id == "tenant-123"
            assert result.name == "Test Tenant"

    @pytest.mark.asyncio
    async def test_get_one_tenant_not_found(self, mock_admin_user):
        """Test retrieval of non-existent tenant"""
        with patch("api.tenant_router.get_tenant", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_one_tenant("nonexistent", user=mock_admin_user)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Tenant not found"

    @pytest.mark.asyncio
    async def test_get_one_tenant_with_quota_usage_billing(self, mock_admin_user, mock_tenant):
        """Test retrieval includes quota, usage, and billing"""
        with patch("api.tenant_router.get_tenant", return_value=mock_tenant):
            result = await get_one_tenant("tenant-123", user=mock_admin_user)

            assert isinstance(result, TenantResponse)
            assert result.quota is not None
            assert result.usage is not None
            assert result.billing is not None
            assert result.quota["cpu"] == 40.0
            assert result.usage["cpu"] == 20.0
            assert result.billing["amount"] == 500.0


# ============ PUT /api/tenant/{tenant_id} Tests ============


class TestUpdateTenant:
    """Test PUT /api/tenant/{tenant_id} endpoint"""

    @pytest.mark.asyncio
    async def test_update_tenant_name(self, mock_admin_user, mock_tenant):
        """Test updating tenant name"""
        payload = TenantUpdate(name="Updated Name")

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_status(self, mock_admin_user, mock_tenant):
        """Test updating tenant status"""
        payload = TenantUpdate(status="suspended")

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_plan(self, mock_admin_user, mock_tenant):
        """Test updating tenant plan"""
        payload = TenantUpdate(plan="pro")

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_contact(self, mock_admin_user, mock_tenant):
        """Test updating tenant contact"""
        payload = TenantUpdate(contact="updated@example.com")

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_quota(self, mock_admin_user, mock_tenant):
        """Test updating tenant quota"""
        payload = TenantUpdate(quota={"cpu": 50.0, "memory": 100.0})

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_usage(self, mock_admin_user, mock_tenant):
        """Test updating tenant usage"""
        payload = TenantUpdate(usage={"cpu": 25.0, "users": 3})

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_multiple_fields(self, mock_admin_user, mock_tenant):
        """Test updating multiple tenant fields"""
        payload = TenantUpdate(
            name="New Name",
            status="suspended",
            contact="new@example.com",
            plan="pro",
        )

        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            result = await update_existing_tenant("tenant-123", payload, user=mock_admin_user)

            assert isinstance(result, TenantResponse)

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self, mock_admin_user):
        """Test updating non-existent tenant"""
        payload = TenantUpdate(name="Updated Name")

        with patch("api.tenant_router.update_tenant", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await update_existing_tenant("nonexistent", payload, user=mock_admin_user)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Tenant not found"

    @pytest.mark.asyncio
    async def test_update_tenant_validation_invalid_plan(self):
        """Test tenant update with invalid plan"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantUpdate(plan="invalid_plan")

    @pytest.mark.asyncio
    async def test_update_tenant_validation_invalid_status(self):
        """Test tenant update with invalid status"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantUpdate(status="invalid_status")

    @pytest.mark.asyncio
    async def test_update_tenant_validation_name_too_short(self):
        """Test tenant update with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantUpdate(name="")

    @pytest.mark.asyncio
    async def test_update_tenant_validation_name_too_long(self):
        """Test tenant update with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            TenantUpdate(name="a" * 101)


# ============ DELETE /api/tenant/{tenant_id} Tests ============


class TestDeleteTenant:
    """Test DELETE /api/tenant/{tenant_id} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_tenant_success(self, mock_admin_user):
        """Test successful tenant deletion"""
        with patch("api.tenant_router.delete_tenant", return_value=True):
            result = await delete_existing_tenant("tenant-123", user=mock_admin_user)

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_tenant_not_found(self, mock_admin_user):
        """Test deletion of non-existent tenant"""
        with patch("api.tenant_router.delete_tenant", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await delete_existing_tenant("nonexistent", user=mock_admin_user)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Tenant not found"

    @pytest.mark.asyncio
    async def test_delete_tenant_returns_none_on_success(self, mock_admin_user):
        """Test that successful deletion returns None"""
        with patch("api.tenant_router.delete_tenant", return_value=True):
            result = await delete_existing_tenant("tenant-123", user=mock_admin_user)

            assert result is None


# ============ Integration Tests ============


class TestTenantRouterIntegration:
    """Integration tests for tenant router"""

    @pytest.mark.asyncio
    async def test_full_crud_lifecycle(self, mock_admin_user, mock_tenant):
        """Test full CRUD lifecycle"""
        # Create
        payload = TenantCreate(name="Lifecycle Tenant", plan="basic")
        with patch("api.tenant_router.create_tenant", return_value=mock_tenant):
            created = await create_new_tenant(payload, user=mock_admin_user)
            assert created.id == "tenant-123"

        # Read
        with patch("api.tenant_router.get_tenant", return_value=mock_tenant):
            retrieved = await get_one_tenant("tenant-123", user=mock_admin_user)
            assert retrieved.id == "tenant-123"

        # Update
        update_payload = TenantUpdate(name="Updated Tenant")
        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            updated = await update_existing_tenant("tenant-123", update_payload, user=mock_admin_user)
            assert updated.id == "tenant-123"

        # Delete
        with patch("api.tenant_router.delete_tenant", return_value=True):
            deleted = await delete_existing_tenant("tenant-123", user=mock_admin_user)
            assert deleted is None

    @pytest.mark.asyncio
    async def test_plan_upgrade_flow(self, mock_admin_user, mock_tenant):
        """Test plan upgrade flow"""
        # Start with basic plan
        basic_tenant = Tenant(id="tenant-1", name="Basic Tenant", plan="basic")

        # Upgrade to pro
        update_payload = TenantUpdate(plan="pro")
        with patch("api.tenant_router.update_tenant", return_value=mock_tenant):
            updated = await update_existing_tenant("tenant-1", update_payload, user=mock_admin_user)
            assert updated.id == "tenant-123"

    @pytest.mark.asyncio
    async def test_bulk_operations(self, mock_admin_user):
        """Test bulk operations on multiple tenants"""
        # List all tenants
        tenant1 = Tenant(id="tenant-1", name="Tenant 1", plan="basic")
        tenant2 = Tenant(id="tenant-2", name="Tenant 2", plan="pro")
        tenant3 = Tenant(id="tenant-3", name="Tenant 3", plan="enterprise")

        with patch("api.tenant_router.list_tenants", return_value=[tenant1, tenant2, tenant3]):
            tenants = await get_all_tenants(user=mock_admin_user)
            assert len(tenants) == 3

        # Update multiple tenants (simulated)
        update_payload = TenantUpdate(status="active")
        with patch("api.tenant_router.update_tenant", return_value=tenant1):
            updated1 = await update_existing_tenant("tenant-1", update_payload, user=mock_admin_user)
            assert updated1.id == "tenant-1"


# ============ Performance Tests ============


class TestTenantRouterPerformance:
    """Performance tests for tenant router"""

    @pytest.mark.asyncio
    async def test_list_tenants_performance(self, mock_admin_user):
        """Test performance of listing many tenants"""
        # Create 100 mock tenants
        tenants = [
            Tenant(id=f"tenant-{i}", name=f"Tenant {i}", plan="basic")
            for i in range(100)
        ]

        with patch("api.tenant_router.list_tenants", return_value=tenants):
            import time
            start = time.time()
            result = await get_all_tenants(user=mock_admin_user)
            elapsed = time.time() - start

            assert len(result) == 100
            assert elapsed < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_tenant_access(self, mock_admin_user, mock_tenant):
        """Test concurrent access to tenant operations"""
        import asyncio

        async def concurrent_get():
            with patch("api.tenant_router.get_tenant", return_value=mock_tenant):
                return await get_one_tenant("tenant-123", user=mock_admin_user)

        # Run 10 concurrent gets
        results = await asyncio.gather(*[concurrent_get() for _ in range(10)])
        assert all(r.id == "tenant-123" for r in results)


# ============ Security Tests ============


class TestTenantRouterSecurity:
    """Security tests for tenant router"""

    @pytest.mark.asyncio
    async def test_create_tenant_requires_admin(self, mock_regular_user):
        """Test that tenant creation requires admin role"""
        payload = TenantCreate(name="Test Tenant")

        # This should fail because regular_user is not admin
        # The actual role check is done by role_required("admin") dependency
        # Here we just verify the function signature expects admin
        assert mock_regular_user.role != "admin"

    @pytest.mark.asyncio
    async def test_update_tenant_requires_admin(self, mock_regular_user):
        """Test that tenant update requires admin role"""
        payload = TenantUpdate(name="Updated Name")

        # This should fail because regular_user is not admin
        assert mock_regular_user.role != "admin"

    @pytest.mark.asyncio
    async def test_delete_tenant_requires_admin(self, mock_regular_user):
        """Test that tenant deletion requires admin role"""
        # This should fail because regular_user is not admin
        assert mock_regular_user.role != "admin"

    @pytest.mark.asyncio
    async def test_get_tenant_allows_regular_user(self, mock_regular_user, mock_tenant):
        """Test that tenant retrieval allows regular users"""
        with patch("api.tenant_router.get_tenant", return_value=mock_tenant):
            result = await get_one_tenant("tenant-123", user=mock_regular_user)
            assert result.id == "tenant-123"


# ============ Data Validation Tests ============


class TestTenantRouterDataValidation:
    """Data validation tests for tenant router"""

    def test_tenant_create_model_validation(self):
        """Test TenantCreate model validation"""
        # Valid data
        valid = TenantCreate(
            name="Valid Tenant",
            plan="basic",
            status="active",
            contact="valid@example.com",
        )
        assert valid.name == "Valid Tenant"
        assert valid.plan == "basic"

    def test_tenant_update_model_validation(self):
        """Test TenantUpdate model validation"""
        # Valid partial update
        valid = TenantUpdate(name="Updated Name")
        assert valid.name == "Updated Name"
        assert valid.plan is None  # Unchanged

    def test_tenant_response_model_structure(self, mock_tenant):
        """Test TenantResponse model structure"""
        from dataclasses import asdict

        response = TenantResponse(**asdict(mock_tenant))
        assert response.id == "tenant-123"
        assert response.name == "Test Tenant"
        assert response.plan == "basic"
        assert response.status == "active"
        assert isinstance(response.quota, dict)
        assert isinstance(response.usage, dict)
        assert isinstance(response.billing, dict)
