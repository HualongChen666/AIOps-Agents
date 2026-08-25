# -*- coding: utf-8 -*-
"""
Test suite for Assets Advanced Router
=====================================

Comprehensive tests for asset management endpoints including inventory,
relationships, lifecycle tracking, and dependency analysis.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from api.assets_advanced_router import (
    router,
    AssetType,
    AssetStatus,
    LifecycleStage,
    RelationshipType,
    AssetInventoryCreate,
    AssetInventoryUpdate,
    AssetInventoryResponse,
    AssetRelationship,
    AssetLifecycle,
    AssetDependency,
    _asset_inventory_metadata,
    _asset_relationships,
    _asset_lifecycle_data,
    _asset_dependencies,
    _get_inventory_metadata,
    _set_inventory_metadata,
    _delete_inventory_metadata,
)
from core.auth_db import Asset


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = Mock()
    user.id = 1
    user.username = "admin"
    user.tenant_id = "default"
    user.roles = ["admin"]
    return user


@pytest.fixture
def mock_operator_user():
    """Mock operator user."""
    user = Mock()
    user.id = 2
    user.username = "operator"
    user.tenant_id = "default"
    user.roles = ["operator"]
    return user


@pytest.fixture
def mock_business_user():
    """Mock business user."""
    user = Mock()
    user.id = 3
    user.username = "business"
    user.tenant_id = "default"
    user.roles = ["business"]
    return user


@pytest.fixture
def mock_asset():
    """Mock asset object."""
    asset = Mock(spec=Asset)
    asset.id = 1
    asset.name = "test-server"
    asset.service = "compute-service"
    asset.business_unit = "engineering"
    asset.env = "prod"
    asset.owner = "team-a"
    asset.created_at = datetime.utcnow()
    return asset


@pytest.fixture
def sample_inventory_create():
    """Sample inventory creation data."""
    return AssetInventoryCreate(
        name="test-server",
        asset_type=AssetType.SERVER,
        status=AssetStatus.ACTIVE,
        service="compute-service",
        business_unit="engineering",
        env="prod",
        owner="team-a",
        ip_address="192.168.1.100",
        hostname="test-server.example.com",
        location="datacenter-1",
        specifications={"cpu": "4 cores", "memory": "16GB"},
        tags=["web", "production"],
        cost_center="CC-001",
        purchase_date=datetime.utcnow() - timedelta(days=365),
        warranty_expiry=datetime.utcnow() + timedelta(days=365),
    )


@pytest.fixture
def sample_inventory_update():
    """Sample inventory update data."""
    return AssetInventoryUpdate(
        name="updated-server",
        status=AssetStatus.MAINTENANCE,
        owner="team-b",
    )


@pytest.fixture
def sample_relationship():
    """Sample asset relationship."""
    return AssetRelationship(
        source_id=1,
        target_id=2,
        relationship_type=RelationshipType.DEPENDS_ON,
        description="Server depends on database",
    )


@pytest.fixture
def sample_lifecycle():
    """Sample asset lifecycle data."""
    return AssetLifecycle(
        asset_id=1,
        current_stage=LifecycleStage.OPERATION,
        stage_start_date=datetime.utcnow() - timedelta(days=30),
        estimated_end_date=datetime.utcnow() + timedelta(days=335),
        stage_duration_days=30,
        total_lifecycle_days=30,
        next_stage=LifecycleStage.RETIREMENT,
        metadata={"environment": "prod"},
    )


@pytest.fixture
def clear_in_memory_data():
    """Clear in-memory data before each test."""
    yield
    _asset_inventory_metadata.clear()
    _asset_relationships.clear()
    _asset_lifecycle_data.clear()
    _asset_dependencies.clear()


# ============================================================================
# Test Inventory Endpoints
# ============================================================================

class TestListInventory:
    """Tests for GET /api/v1/assets/inventory"""

    @pytest.mark.asyncio
    async def test_list_inventory_empty_result(self, mock_db, mock_admin_user, clear_in_memory_data):
        """Test listing inventory with no matching results."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[0].endpoint(
                asset_type=None,
                status=None,
                env=None,
                business_unit=None,
                owner=None,
                skip=0,
                limit=100,
                db=mock_db,
                current_user=mock_admin_user,
            )

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_list_inventory_database_error(self, mock_db, mock_admin_user):
        """Test listing inventory with database error."""
        # Setup
        mock_db.query.side_effect = Exception("Database connection failed")

        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[0].endpoint(
                    asset_type=None,
                    status=None,
                    env=None,
                    business_unit=None,
                    owner=None,
                    skip=0,
                    limit=100,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 500


class TestGetInventoryItem:
    """Tests for GET /api/v1/assets/inventory/{id}"""

    @pytest.mark.asyncio
    async def test_get_inventory_item_not_found(self, mock_db, mock_admin_user):
        """Test retrieving non-existent inventory item."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[2].endpoint(
                    asset_id=999,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404


class TestUpdateInventoryItem:
    """Tests for PATCH /api/v1/assets/inventory/{id}"""

    @pytest.mark.asyncio
    async def test_update_inventory_item_not_found(self, mock_db, sample_inventory_update, mock_admin_user):
        """Test updating non-existent inventory item."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[3].endpoint(
                    asset_id=999,
                    item=sample_inventory_update,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404


class TestDeleteInventoryItem:
    """Tests for DELETE /api/v1/assets/inventory/{id}"""

    @pytest.mark.asyncio
    async def test_delete_inventory_item_not_found(self, mock_db, mock_admin_user):
        """Test deleting non-existent inventory item."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[4].endpoint(
                    asset_id=999,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404


# ============================================================================
# Test Relationships Endpoints
# ============================================================================

class TestGetAssetRelationships:
    """Tests for GET /api/v1/assets/relationships"""

    @pytest.mark.asyncio
    async def test_get_relationships_success(self, sample_relationship, mock_admin_user, clear_in_memory_data):
        """Test successful retrieval of asset relationships."""
        # Setup
        _asset_relationships.append(sample_relationship)

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[5].endpoint(
                asset_id=None,
                relationship_type=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].source_id == 1
        assert result[0].target_id == 2

    @pytest.mark.asyncio
    async def test_get_relationships_with_filters(self, sample_relationship, mock_admin_user, clear_in_memory_data):
        """Test retrieving relationships with filters."""
        # Setup
        _asset_relationships.append(sample_relationship)

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[5].endpoint(
                asset_id=1,
                relationship_type=RelationshipType.DEPENDS_ON,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1


class TestCreateAssetRelationship:
    """Tests for POST /api/v1/assets/relationships"""

    @pytest.mark.asyncio
    async def test_create_relationship_source_not_found(self, mock_db, sample_relationship, mock_admin_user):
        """Test creating relationship with non-existent source asset."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[6].endpoint(
                    relationship=sample_relationship,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_relationship_duplicate(self, mock_db, sample_relationship, mock_admin_user, clear_in_memory_data):
        """Test creating duplicate relationship."""
        # Setup
        mock_asset1 = Mock(spec=Asset)
        mock_asset1.id = 1
        mock_asset2 = Mock(spec=Asset)
        mock_asset2.id = 2
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [mock_asset1, mock_asset2]
        mock_db.query.return_value = mock_query
        _asset_relationships.append(sample_relationship)

        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[6].endpoint(
                    relationship=sample_relationship,
                    db=mock_db,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 400


# ============================================================================
# Test Lifecycle Endpoints
# ============================================================================

class TestGetAssetLifecycle:
    """Tests for GET /api/v1/assets/lifecycle"""

    @pytest.mark.asyncio
    async def test_get_lifecycle_success(self, sample_lifecycle, mock_admin_user, clear_in_memory_data):
        """Test successful retrieval of asset lifecycle."""
        # Setup
        _asset_lifecycle_data[1] = sample_lifecycle

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[7].endpoint(
                asset_id=None,
                current_stage=None,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].asset_id == 1

    @pytest.mark.asyncio
    async def test_get_lifecycle_with_filters(self, sample_lifecycle, mock_admin_user, clear_in_memory_data):
        """Test retrieving lifecycle with filters."""
        # Setup
        _asset_lifecycle_data[1] = sample_lifecycle

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[7].endpoint(
                asset_id=1,
                current_stage=LifecycleStage.OPERATION,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1


class TestUpdateAssetLifecycle:
    """Tests for PATCH /api/v1/assets/lifecycle/{id}"""

    @pytest.mark.asyncio
    async def test_update_lifecycle_success(self, sample_lifecycle, mock_admin_user, clear_in_memory_data):
        """Test successful update of asset lifecycle."""
        # Setup
        _asset_lifecycle_data[1] = sample_lifecycle

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[8].endpoint(
                asset_id=1,
                current_stage=LifecycleStage.RETIREMENT,
                current_user=mock_admin_user,
            )

        # Assert
        assert result.current_stage == LifecycleStage.RETIREMENT

    @pytest.mark.asyncio
    async def test_update_lifecycle_not_found(self, mock_admin_user):
        """Test updating lifecycle for non-existent asset."""
        # Execute & Assert
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            with pytest.raises(HTTPException) as exc_info:
                await router.routes[8].endpoint(
                    asset_id=999,
                    current_stage=LifecycleStage.RETIREMENT,
                    current_user=mock_admin_user,
                )
            assert exc_info.value.status_code == 404


# ============================================================================
# Test Dependencies Endpoints
# ============================================================================

class TestGetAssetDependencies:
    """Tests for GET /api/v1/assets/dependencies"""

    @pytest.mark.asyncio
    async def test_get_dependencies_success(self, mock_db, mock_asset, mock_admin_user, clear_in_memory_data):
        """Test successful retrieval of asset dependencies."""
        # Setup
        mock_query = Mock()
        mock_query.all.return_value = [mock_asset]
        mock_db.query.return_value = mock_query
        _asset_dependencies[1] = AssetDependency(
            asset_id=1,
            asset_name="test-server",
            dependency_type="operational",
            criticality="high",
            depends_on=[2],
            depended_by=[3],
            impact_score=85.0,
        )

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[9].endpoint(
                asset_id=None,
                criticality=None,
                db=mock_db,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].asset_id == 1

    @pytest.mark.asyncio
    async def test_get_dependencies_with_filters(self, mock_db, mock_asset, mock_admin_user, clear_in_memory_data):
        """Test retrieving dependencies with filters."""
        # Setup
        mock_query = Mock()
        mock_query.all.return_value = [mock_asset]
        mock_db.query.return_value = mock_query
        _asset_dependencies[1] = AssetDependency(
            asset_id=1,
            asset_name="test-server",
            dependency_type="operational",
            criticality="high",
            depends_on=[],
            depended_by=[],
            impact_score=85.0,
        )

        # Execute
        with patch('api.assets_advanced_router.require_roles', return_value=mock_admin_user):
            result = await router.routes[9].endpoint(
                asset_id=1,
                criticality="high",
                db=mock_db,
                current_user=mock_admin_user,
            )

        # Assert
        assert len(result) == 1
        assert result[0].criticality == "high"


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions"""

    def test_get_inventory_metadata(self, clear_in_memory_data):
        """Test getting inventory metadata."""
        # Setup
        _set_inventory_metadata(1, {"key": "value"})

        # Execute
        result = _get_inventory_metadata(1)

        # Assert
        assert result == {"key": "value"}

    def test_get_inventory_metadata_not_found(self, clear_in_memory_data):
        """Test getting inventory metadata for non-existent asset."""
        # Execute
        result = _get_inventory_metadata(999)

        # Assert
        assert result == {}

    def test_set_inventory_metadata(self, clear_in_memory_data):
        """Test setting inventory metadata."""
        # Execute
        _set_inventory_metadata(1, {"key": "value"})

        # Assert
        assert _get_inventory_metadata(1) == {"key": "value"}

    def test_delete_inventory_metadata(self, clear_in_memory_data):
        """Test deleting inventory metadata."""
        # Setup
        _set_inventory_metadata(1, {"key": "value"})

        # Execute
        _delete_inventory_metadata(1)

        # Assert
        assert _get_inventory_metadata(1) == {}
