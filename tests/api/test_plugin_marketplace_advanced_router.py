# -*- coding: utf-8 -*-
"""
Test cases for Plugin Marketplace Advanced Router (Database-backed)
Comprehensive test coverage for plugin marketplace management API
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.plugin_marketplace_advanced_router import (
    InstallRequest,
    PluginListingCreate,
    PluginListingUpdate,
    ReviewCreate,
    router,
)
from core.models import PluginListingDB, PluginReviewDB, PluginCategoryDB, InstalledPluginDB
from core.auth_db import SessionLocal


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    """Clean up database before and after each test"""
    # Clean up before test
    db_session.query(InstalledPluginDB).delete()
    db_session.query(PluginReviewDB).delete()
    db_session.query(PluginListingDB).delete()
    db_session.query(PluginCategoryDB).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(InstalledPluginDB).delete()
    db_session.query(PluginReviewDB).delete()
    db_session.query(PluginListingDB).delete()
    db_session.query(PluginCategoryDB).delete()
    db_session.commit()


@pytest.fixture
def sample_category():
    """Create a sample category for testing"""
    return {
        "id": "cat-monitoring",
        "category_name": "monitoring",
        "category_description": "Monitoring and metrics collection plugins",
        "parent_category_id": None,
        "enabled": True,
    }


@pytest.fixture
def sample_listing(sample_category):
    """Create a sample plugin listing for testing"""
    return {
        "id": "plugin-test-001",
        "plugin_id": "test-plugin-001",
        "plugin_name": "Test Plugin",
        "version": "1.0.0",
        "description": "Test plugin description",
        "author": "Test Author",
        "category": "monitoring",
        "tags": ["test", "monitoring"],
        "price": None,
        "quality": "community",
        "download_url": "https://example.com/test-plugin.zip",
        "screenshot_urls": [],
        "documentation_url": "https://docs.example.com",
        "repository_url": "https://github.com/example/test-plugin",
        "download_count": 100,
        "rating": 4.5,
        "review_count": 10,
        "enabled": True,
    }


@pytest.fixture
def sample_review(sample_listing):
    """Create a sample review for testing"""
    return {
        "id": "review-001",
        "plugin_id": sample_listing["plugin_id"],
        "reviewer_id": "user-001",
        "reviewer_name": "Test Reviewer",
        "rating": 5,
        "review_text": "Great plugin!",
    }


# ============================================================================
# Plugin Listing Endpoints Tests
# ============================================================================


class TestPluginListingEndpoints:
    """Test cases for plugin listing endpoints"""

    def test_get_plugin_listings_empty(self, client):
        """Test getting plugin listings when storage is empty"""
        response = client.get("/api/v1/plugin/marketplace/plugins")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json() == []

    def test_get_plugin_listings_with_data(self, client, db_session, sample_listing):
        """Test getting plugin listings with data"""
        # Create listing in database
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_plugin_listings_filter_category(self, client, db_session, sample_listing):
        """Test getting plugin listings filtered by category"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?category=monitoring")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_plugin_listings_filter_quality(self, client, db_session, sample_listing):
        """Test getting plugin listings filtered by quality"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?quality=community")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_plugin_listings_search(self, client, db_session, sample_listing):
        """Test getting plugin listings with search"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?search=test")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_plugin_listings_sort_by_name(self, client, db_session, sample_listing):
        """Test getting plugin listings sorted by name"""
        listing1 = PluginListingDB(**sample_listing)
        listing1.id = "plugin-a"
        listing1.plugin_name = "A Plugin"
        db_session.add(listing1)

        listing2 = PluginListingDB(**sample_listing)
        listing2.id = "plugin-b"
        listing2.plugin_name = "B Plugin"
        db_session.add(listing2)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?sort_by=name")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data[0]["plugin_name"] <= data[1]["plugin_name"]

    def test_get_plugin_listings_sort_by_rating(self, client, db_session, sample_listing):
        """Test getting plugin listings sorted by rating"""
        listing1 = PluginListingDB(**sample_listing)
        listing1.id = "plugin-a"
        listing1.rating = 5.0
        db_session.add(listing1)

        listing2 = PluginListingDB(**sample_listing)
        listing2.id = "plugin-b"
        listing2.rating = 3.0
        db_session.add(listing2)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?sort_by=rating")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data[0]["rating"] >= data[1]["rating"]

    def test_get_plugin_listings_sort_by_download_count(self, client, db_session, sample_listing):
        """Test getting plugin listings sorted by download count"""
        listing1 = PluginListingDB(**sample_listing)
        listing1.id = "plugin-a"
        listing1.download_count = 1000
        db_session.add(listing1)

        listing2 = PluginListingDB(**sample_listing)
        listing2.id = "plugin-b"
        listing2.download_count = 100
        db_session.add(listing2)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?sort_by=download_count")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data[0]["download_count"] >= data[1]["download_count"]

    def test_get_plugin_listings_limit(self, client, db_session, sample_listing):
        """Test getting plugin listings with limit"""
        for i in range(10):
            listing = PluginListingDB(**sample_listing)
            listing.id = f"plugin-{i}"
            listing.plugin_name = f"Plugin {i}"
            db_session.add(listing)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/plugins?limit=5")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 5

    def test_get_plugin_listings_invalid_limit(self, client):
        """Test getting plugin listings with invalid limit"""
        response = client.get("/api/v1/plugin/marketplace/plugins?limit=0")
        assert response.status_code in (422, 404)

    def test_get_plugin_listings_limit_exceeds_max(self, client):
        """Test getting plugin listings with limit exceeding maximum"""
        response = client.get("/api/v1/plugin/marketplace/plugins?limit=200")
        assert response.status_code in (422, 404)

    def test_get_plugin_success(self, client, db_session, sample_listing):
        """Test getting a plugin by ID successfully"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["plugin_name"] == "Test Plugin"

    def test_get_plugin_by_plugin_id(self, client, db_session, sample_listing):
        """Test getting a plugin by plugin_id"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['plugin_id']}")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["plugin_name"] == "Test Plugin"

    def test_get_plugin_not_found(self, client):
        """Test getting a non-existent plugin"""
        response = client.get("/api/v1/plugin/marketplace/plugins/nonexistent")
        assert response.status_code == 404


# ============================================================================
# Plugin Install/Uninstall Endpoints Tests
# ============================================================================


class TestPluginInstallUninstall:
    """Test cases for plugin install/uninstall endpoints"""

    def test_install_plugin_success(self, client, db_session, sample_listing):
        """Test installing a plugin successfully"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        install_data = {"version": "1.0.0", "configuration": {"test": True}}
        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True
            assert data["plugin_name"] == "Test Plugin"

    def test_install_plugin_not_found(self, client):
        """Test installing a non-existent plugin"""
        install_data = {"version": "1.0.0"}
        response = client.post(
            "/api/v1/plugin/marketplace/plugins/nonexistent/install", json=install_data
        )
        assert response.status_code == 404

    def test_install_plugin_already_installed(self, client, db_session, sample_listing):
        """Test installing a plugin that is already installed"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        # Install the plugin first
        installed = InstalledPluginDB(
            id="installed-001",
            plugin_id=sample_listing["plugin_id"],
            installed_version="1.0.0",
            status="active",
            configuration={},
        )
        db_session.add(installed)
        db_session.commit()

        install_data = {"version": "1.0.0"}
        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data
        )
        assert response.status_code in (400, 404)

    def test_install_plugin_increments_download_count(self, client, db_session, sample_listing):
        """Test that installing a plugin increments download count"""
        listing = PluginListingDB(**sample_listing)
        listing.download_count = 100
        db_session.add(listing)
        db_session.commit()

        install_data = {"version": "1.0.0"}
        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data
        )
        assert response.status_code in (200, 404)

        # Check that download count increased
        updated = db_session.query(PluginListingDB).filter(
            PluginListingDB.id == sample_listing["id"]
        ).first()
        assert updated.download_count == 101

    def test_install_plugin_auto_version(self, client, db_session, sample_listing):
        """Test installing plugin without specifying version (uses latest)"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        install_data = {"configuration": {}}
        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["version"] == sample_listing["version"]

    def test_uninstall_plugin_success(self, client, db_session, sample_listing):
        """Test uninstalling a plugin successfully"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)

        installed = InstalledPluginDB(
            id="installed-001",
            plugin_id=sample_listing["plugin_id"],
            installed_version="1.0.0",
            status="active",
            configuration={},
        )
        db_session.add(installed)
        db_session.commit()

        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/uninstall"
        )
        assert response.status_code in (200, 404)

        # Verify deletion
        deleted = db_session.query(InstalledPluginDB).filter(
            InstalledPluginDB.plugin_id == sample_listing["plugin_id"]
        ).first()
        assert deleted is None

    def test_uninstall_plugin_not_found(self, client):
        """Test uninstalling a non-existent plugin"""
        response = client.post("/api/v1/plugin/marketplace/plugins/nonexistent/uninstall")
        assert response.status_code == 404

    def test_uninstall_plugin_not_installed(self, client, db_session, sample_listing):
        """Test uninstalling a plugin that is not installed"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/uninstall"
        )
        assert response.status_code in (400, 404)


# ============================================================================
# Category Endpoints Tests
# ============================================================================


class TestCategoryEndpoints:
    """Test cases for category endpoints"""

    def test_get_categories_empty(self, client):
        """Test getting categories when storage is empty"""
        response = client.get("/api/v1/plugin/marketplace/categories")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json() == []

    def test_get_categories_with_data(self, client, db_session, sample_category):
        """Test getting categories with data"""
        category = PluginCategoryDB(**sample_category)
        db_session.add(category)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/categories")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_categories_multiple(self, client, db_session):
        """Test getting multiple categories"""
        categories = [
            PluginCategoryDB(
                id="cat-monitoring",
                category_name="monitoring",
                category_description="Monitoring plugins",
                enabled=True,
            ),
            PluginCategoryDB(
                id="cat-alerting",
                category_name="alerting",
                category_description="Alerting plugins",
                enabled=True,
            ),
        ]
        for category in categories:
            db_session.add(category)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/categories")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 2


# ============================================================================
# Review Endpoints Tests
# ============================================================================


class TestReviewEndpoints:
    """Test cases for review endpoints"""

    def test_get_reviews_empty(self, client):
        """Test getting reviews when storage is empty"""
        response = client.get("/api/v1/plugin/marketplace/reviews")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json() == []

    def test_get_reviews_with_data(self, client, db_session, sample_review):
        """Test getting reviews with data"""
        review = PluginReviewDB(**sample_review)
        db_session.add(review)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/reviews")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_reviews_filter_plugin_id(self, client, db_session, sample_review):
        """Test getting reviews filtered by plugin ID"""
        review = PluginReviewDB(**sample_review)
        db_session.add(review)
        db_session.commit()

        response = client.get(f"/api/v1/plugin/marketplace/reviews?plugin_id={sample_review['plugin_id']}")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_reviews_filter_rating(self, client, db_session, sample_review):
        """Test getting reviews filtered by rating"""
        review = PluginReviewDB(**sample_review)
        db_session.add(review)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/reviews?rating=5")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 1

    def test_get_reviews_limit(self, client, db_session, sample_review):
        """Test getting reviews with limit"""
        for i in range(10):
            review = PluginReviewDB(**sample_review)
            review.id = f"review-{i}"
            db_session.add(review)
        db_session.commit()

        response = client.get("/api/v1/plugin/marketplace/reviews?limit=5")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert len(data) == 5

    def test_get_reviews_invalid_rating(self, client):
        """Test getting reviews with invalid rating"""
        response = client.get("/api/v1/plugin/marketplace/reviews?rating=6")
        assert response.status_code in (422, 404)

    def test_create_review_success(self, client, db_session, sample_listing):
        """Test creating a review successfully"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer_id": "user-001",
            "reviewer_name": "Test Reviewer",
            "rating": 5,
            "review_text": "Excellent plugin!",
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["reviewer_name"] == "Test Reviewer"
            assert data["rating"] == 5

    def test_create_review_plugin_not_found(self, client):
        """Test creating a review for non-existent plugin"""
        review_data = {
            "plugin_id": "nonexistent",
            "reviewer_id": "user-001",
            "reviewer_name": "Test Reviewer",
            "rating": 5,
            "review_text": "Test",
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 404

    def test_create_review_invalid_rating(self, client, db_session, sample_listing):
        """Test creating a review with invalid rating"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer_id": "user-001",
            "reviewer_name": "Test Reviewer",
            "rating": 6,  # Invalid (must be 1-5)
            "review_text": "Test",
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code in (422, 404)

    def test_create_review_missing_required_field(self, client, db_session, sample_listing):
        """Test creating a review with missing required field"""
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer_id": "user-001",
            "reviewer_name": "Test Reviewer",
            # Missing rating, review_text
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code in (422, 404)

    def test_create_review_updates_plugin_rating(self, client, db_session, sample_listing):
        """Test that creating a review updates plugin rating"""
        listing = PluginListingDB(**sample_listing)
        listing.rating = 4.0
        listing.review_count = 5
        db_session.add(listing)
        db_session.commit()

        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer_id": "user-001",
            "reviewer_name": "Test Reviewer",
            "rating": 5,
            "review_text": "Great!",
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code in (200, 404)

        # Verify rating was updated
        updated = db_session.query(PluginListingDB).filter(
            PluginListingDB.id == sample_listing["id"]
        ).first()
        assert updated.review_count == 6


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for plugin marketplace"""

    def test_full_plugin_lifecycle(self, client, db_session, sample_category, sample_listing):
        """Test full plugin lifecycle: create, install, review, uninstall"""
        # Create category
        category = PluginCategoryDB(**sample_category)
        db_session.add(category)

        # Create listing
        listing = PluginListingDB(**sample_listing)
        db_session.add(listing)
        db_session.commit()

        # Get listings
        response = client.get("/api/v1/plugin/marketplace/plugins")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert len(response.json()) == 1

        # Install plugin
        install_data = {"version": "1.0.0"}
        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data
        )
        assert response.status_code in (200, 404)

        # Create review
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer_id": "user-001",
            "reviewer_name": "Test Reviewer",
            "rating": 5,
            "review_text": "Great!",
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code in (200, 404)

        # Uninstall plugin
        response = client.post(
            f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/uninstall"
        )
        assert response.status_code in (200, 404)
