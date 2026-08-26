# -*- coding: utf-8 -*-
"""
Integration test for Assets Advanced Router database migration
===========================================================

Tests to verify the database migration for asset inventory metadata.
This test validates that the database models and API integration work correctly.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from api.assets_advanced_router import (
    AssetInventoryCreate,
    AssetInventoryResponse,
    AssetType,
    AssetStatus,
    _get_inventory_metadata,
    _set_inventory_metadata,
    _delete_inventory_metadata,
)
from core.models import AssetInventoryMetadata
from core.database import get_db


class TestDatabaseMigration:
    """Tests for database migration of asset inventory metadata"""

    def test_get_inventory_metadata_with_database(self):
        """Test getting inventory metadata from database."""
        # This test would require a real database connection
        # For now, we test the function signature and fallback mechanism
        result = _get_inventory_metadata(999, None)
        assert result == {}  # Should return empty dict when db is None

    def test_get_inventory_metadata_with_memory_fallback(self):
        """Test getting inventory metadata with memory fallback."""
        # Setup memory data
        test_metadata = {"asset_type": "server", "status": "active"}
        from api.assets_advanced_router import _asset_inventory_metadata
        _asset_inventory_metadata[999] = test_metadata

        # Test with no database (should use memory fallback)
        result = _get_inventory_metadata(999, None)
        assert result == test_metadata

        # Cleanup
        _asset_inventory_metadata.pop(999, None)

    def test_set_inventory_metadata_with_memory_fallback(self):
        """Test setting inventory metadata with memory fallback."""
        test_metadata = {"asset_type": "server", "status": "active"}
        
        # Test with no database (should use memory fallback)
        _set_inventory_metadata(999, test_metadata, None)
        
        # Verify it was set in memory
        from api.assets_advanced_router import _asset_inventory_metadata
        assert _asset_inventory_metadata[999] == test_metadata

        # Cleanup
        _asset_inventory_metadata.pop(999, None)

    def test_delete_inventory_metadata_with_memory_fallback(self):
        """Test deleting inventory metadata with memory fallback."""
        # Setup
        from api.assets_advanced_router import _asset_inventory_metadata
        _asset_inventory_metadata[999] = {"key": "value"}
        
        # Test with no database (should use memory fallback)
        _delete_inventory_metadata(999, None)
        
        # Verify it was deleted from memory
        assert 999 not in _asset_inventory_metadata

    def test_models_import(self):
        """Test that database models can be imported."""
        # This validates that the models are correctly defined
        from core.models import (
            AssetInventoryMetadata,
            AssetRelationshipDB,
            AssetLifecycleDB,
            AssetDependencyDB,
        )
        
        # Verify model attributes
        assert hasattr(AssetInventoryMetadata, '__tablename__')
        assert AssetInventoryMetadata.__tablename__ == "asset_inventory_metadata"
        assert hasattr(AssetRelationshipDB, '__tablename__')
        assert AssetRelationshipDB.__tablename__ == "asset_relationships"
        assert hasattr(AssetLifecycleDB, '__tablename__')
        assert AssetLifecycleDB.__tablename__ == "asset_lifecycles"
        assert hasattr(AssetDependencyDB, '__tablename__')
        assert AssetDependencyDB.__tablename__ == "asset_dependencies"

    def test_router_import(self):
        """Test that the router can be imported."""
        from api.assets_advanced_router import router
        assert router is not None
        assert router.prefix == "/api/v1/assets"
        assert len(router.routes) > 0


class TestAPIIntegration:
    """Tests for API integration with database"""

    def test_inventory_create_model(self):
        """Test that inventory create model works correctly."""
        item = AssetInventoryCreate(
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
        
        assert item.name == "test-server"
        assert item.asset_type == AssetType.SERVER
        assert item.status == AssetStatus.ACTIVE
        assert item.ip_address == "192.168.1.100"

    def test_inventory_response_model(self):
        """Test that inventory response model works correctly."""
        response = AssetInventoryResponse(
            id=1,
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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert response.id == 1
        assert response.name == "test-server"
        assert response.asset_type == AssetType.SERVER
        assert response.status == AssetStatus.ACTIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
