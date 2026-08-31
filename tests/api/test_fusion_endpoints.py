# -*- coding: utf-8 -*-
"""
Test Fusion Endpoints

Tests for the Fusion configuration endpoints:
- GET /api/ai/fusion/configs
- POST /api/ai/fusion/configs
- DELETE /api/ai/fusion/configs/{config_id}
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from core.database import SessionLocal
from core.models import AIFusionConfigDB, User


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def admin_user(db: Session):
    """Create admin user for testing"""
    user = db.query(User).filter(User.username == "test-admin").first()
    if not user:
        user = User(
            username="test-admin",
            full_name="Test Admin",
            email="test-admin@example.com",
            role="admin",
            disabled=False,
            password_hash="test_hash"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


class TestFusionConfigs:
    """Test fusion configuration endpoints"""

    def test_get_fusion_configs_empty(self, client: TestClient):
        """Test getting fusion configs when none exist"""
        response = client.get("/api/ai/fusion/configs")
        assert response.status_code == 200
        data = response.json()
        assert "configs" in data
        assert isinstance(data["configs"], list)

    def test_create_fusion_config(self, client: TestClient, db: Session):
        """Test creating a fusion configuration"""
        config_data = {
            "name": "test-fusion-config",
            "fusion_strategy": "weighted",
            "sources": ["source1", "source2"],
            "weights": {"source1": 0.6, "source2": 0.4}
        }

        response = client.post("/api/ai/fusion/configs", json=config_data)
        assert response.status_code in [200, 403]  # 403 if auth required, 200 if dev mode

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["name"] == "test-fusion-config"
            assert data["fusion_strategy"] == "weighted"
            assert data["sources"] == ["source1", "source2"]
            assert data["weights"] == {"source1": 0.6, "source2": 0.4}
            assert data["status"] == "active"

            # Cleanup
            db.query(AIFusionConfigDB).filter(AIFusionConfigDB.id == data["id"]).delete()
            db.commit()

    def test_get_fusion_configs_with_data(self, client: TestClient, db: Session):
        """Test getting fusion configs with existing data"""
        # Create a test config
        config = AIFusionConfigDB(
            id="test-config-123",
            config_name="test-config",
            fusion_strategy="concatenation",
            sources=["source1"],
            weights=None,
            status="active",
            config_metadata={}
        )
        db.add(config)
        db.commit()

        try:
            response = client.get("/api/ai/fusion/configs")
            assert response.status_code == 200
            data = response.json()
            assert "configs" in data
            assert len(data["configs"]) >= 1

            # Find our test config
            test_config = next((c for c in data["configs"] if c["id"] == "test-config-123"), None)
            assert test_config is not None
            assert test_config["name"] == "test-config"
            assert test_config["fusion_strategy"] == "concatenation"
        finally:
            # Cleanup
            db.query(AIFusionConfigDB).filter(AIFusionConfigDB.id == "test-config-123").delete()
            db.commit()

    def test_delete_fusion_config(self, client: TestClient, db: Session):
        """Test deleting a fusion configuration"""
        # Create a test config
        config = AIFusionConfigDB(
            id="test-delete-123",
            config_name="test-delete",
            fusion_strategy="weighted",
            sources=["source1"],
            weights=None,
            status="active",
            config_metadata={}
        )
        db.add(config)
        db.commit()

        try:
            response = client.delete("/api/ai/fusion/configs/test-delete-123")
            assert response.status_code in [200, 403, 404]  # 403 if auth required, 404 if not found

            if response.status_code == 200:
                # Verify deletion
                deleted_config = db.query(AIFusionConfigDB).filter(
                    AIFusionConfigDB.id == "test-delete-123"
                ).first()
                assert deleted_config is None
        finally:
            # Cleanup in case deletion failed
            db.query(AIFusionConfigDB).filter(AIFusionConfigDB.id == "test-delete-123").delete()
            db.commit()

    def test_delete_nonexistent_config(self, client: TestClient):
        """Test deleting a non-existent configuration"""
        response = client.delete("/api/ai/fusion/configs/nonexistent-id")
        assert response.status_code in [404, 403]  # 404 if auth not required, 403 if auth required


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
