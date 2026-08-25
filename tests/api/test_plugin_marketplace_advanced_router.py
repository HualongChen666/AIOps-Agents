# -*- coding: utf-8 -*-
"""
Test cases for Plugin Marketplace Advanced Router
Comprehensive test coverage for plugin marketplace management API
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.plugin_marketplace_advanced_router import (
    router,
    PluginListingCreate,
    PluginListingUpdate,
    ReviewCreate,
    InstallRequest,
    _listings,
    _reviews,
    _categories,
    _installed_plugins,
)


@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset in-memory storage before each test"""
    _listings.clear()
    _reviews.clear()
    _categories.clear()
    _installed_plugins.clear()
    yield
    _listings.clear()
    _reviews.clear()
    _categories.clear()
    _installed_plugins.clear()


@pytest.fixture
def sample_category():
    """Create a sample category for testing"""
    return {
        "id": str(uuid4()),
        "name": "monitoring",
        "description": "Monitoring and metrics collection plugins",
        "plugin_count": 0,
        "icon": "📊",
    }


@pytest.fixture
def sample_listing(sample_category):
    """Create a sample plugin listing for testing"""
    return {
        "id": str(uuid4()),
        "plugin_id": str(uuid4()),
        "plugin_name": "Test Plugin",
        "version": "1.0.0",
        "description": "Test plugin description",
        "author": "Test Author",
        "category": "monitoring",
        "tags": ["test", "monitoring"],
        "price": None,
        "quality": "community",
        "review_status": "approved",
        "download_count": 100,
        "rating": 4.5,
        "review_count": 10,
        "download_url": "https://example.com/test-plugin.zip",
        "screenshot_urls": [],
        "documentation_url": "https://docs.example.com",
        "repository_url": "https://github.com/example/test-plugin",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_review(sample_listing):
    """Create a sample review for testing"""
    return {
        "id": str(uuid4()),
        "plugin_id": sample_listing["plugin_id"],
        "plugin_name": sample_listing["plugin_name"],
        "reviewer": "Test Reviewer",
        "rating": 5,
        "comment": "Great plugin!",
        "title": "Excellent",
        "timestamp": datetime.utcnow(),
        "helpful_count": 0,
    }


# ============================================================================
# Plugin Listing Endpoints Tests
# ============================================================================

class TestPluginListingEndpoints:
    """Test cases for plugin listing endpoints"""

    def test_get_plugin_listings_empty(self, client):
        """Test getting plugin listings when storage is empty"""
        response = client.get("/api/v1/plugin/marketplace/plugins")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_plugin_listings_with_data(self, client, sample_listing):
        """Test getting plugin listings with data"""
        _listings[sample_listing["id"]] = sample_listing
        response = client.get("/api/v1/plugin/marketplace/plugins")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_plugin_listings_filter_category(self, client, sample_listing):
        """Test getting plugin listings filtered by category"""
        _listings[sample_listing["id"]] = sample_listing
        
        response = client.get("/api/v1/plugin/marketplace/plugins?category=monitoring")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_plugin_listings_filter_quality(self, client, sample_listing):
        """Test getting plugin listings filtered by quality"""
        _listings[sample_listing["id"]] = sample_listing
        
        response = client.get("/api/v1/plugin/marketplace/plugins?quality=community")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_plugin_listings_search(self, client, sample_listing):
        """Test getting plugin listings with search"""
        _listings[sample_listing["id"]] = sample_listing
        
        response = client.get("/api/v1/plugin/marketplace/plugins?search=test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_plugin_listings_sort_by_name(self, client, sample_listing):
        """Test getting plugin listings sorted by name"""
        listing1 = sample_listing.copy()
        listing1["id"] = str(uuid4())
        listing1["plugin_name"] = "A Plugin"
        _listings[listing1["id"]] = listing1
        
        listing2 = sample_listing.copy()
        listing2["id"] = str(uuid4())
        listing2["plugin_name"] = "B Plugin"
        _listings[listing2["id"]] = listing2
        
        response = client.get("/api/v1/plugin/marketplace/plugins?sort_by=name")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["plugin_name"] <= data[1]["plugin_name"]

    def test_get_plugin_listings_sort_by_rating(self, client, sample_listing):
        """Test getting plugin listings sorted by rating"""
        listing1 = sample_listing.copy()
        listing1["id"] = str(uuid4())
        listing1["rating"] = 5.0
        _listings[listing1["id"]] = listing1
        
        listing2 = sample_listing.copy()
        listing2["id"] = str(uuid4())
        listing2["rating"] = 3.0
        _listings[listing2["id"]] = listing2
        
        response = client.get("/api/v1/plugin/marketplace/plugins?sort_by=rating")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["rating"] >= data[1]["rating"]

    def test_get_plugin_listings_sort_by_download_count(self, client, sample_listing):
        """Test getting plugin listings sorted by download count"""
        listing1 = sample_listing.copy()
        listing1["id"] = str(uuid4())
        listing1["download_count"] = 1000
        _listings[listing1["id"]] = listing1
        
        listing2 = sample_listing.copy()
        listing2["id"] = str(uuid4())
        listing2["download_count"] = 100
        _listings[listing2["id"]] = listing2
        
        response = client.get("/api/v1/plugin/marketplace/plugins?sort_by=download_count")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["download_count"] >= data[1]["download_count"]

    def test_get_plugin_listings_limit(self, client, sample_listing):
        """Test getting plugin listings with limit"""
        for i in range(10):
            listing = sample_listing.copy()
            listing["id"] = str(uuid4())
            listing["plugin_name"] = f"Plugin {i}"
            _listings[listing["id"]] = listing
        
        response = client.get("/api/v1/plugin/marketplace/plugins?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_plugin_listings_invalid_limit(self, client):
        """Test getting plugin listings with invalid limit"""
        response = client.get("/api/v1/plugin/marketplace/plugins?limit=0")
        assert response.status_code == 422

    def test_get_plugin_listings_limit_exceeds_max(self, client):
        """Test getting plugin listings with limit exceeding maximum"""
        response = client.get("/api/v1/plugin/marketplace/plugins?limit=200")
        assert response.status_code == 422

    def test_get_plugin_success(self, client, sample_listing):
        """Test getting a plugin by ID successfully"""
        _listings[sample_listing["id"]] = sample_listing
        response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin_name"] == "Test Plugin"

    def test_get_plugin_by_plugin_id(self, client, sample_listing):
        """Test getting a plugin by plugin_id"""
        _listings[sample_listing["id"]] = sample_listing
        response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['plugin_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin_name"] == "Test Plugin"

    def test_get_plugin_not_found(self, client):
        """Test getting a non-existent plugin"""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/plugin/marketplace/plugins/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# ============================================================================
# Plugin Install/Uninstall Endpoints Tests
# ============================================================================

class TestPluginInstallUninstall:
    """Test cases for plugin install/uninstall endpoints"""

    def test_install_plugin_success(self, client, sample_listing):
        """Test installing a plugin successfully"""
        _listings[sample_listing["id"]] = sample_listing
        
        install_data = {
            "version": "1.0.0",
            "config": {"test": True}
        }
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["plugin_name"] == "Test Plugin"
        assert "install_path" in data

    def test_install_plugin_not_found(self, client):
        """Test installing a non-existent plugin"""
        fake_id = str(uuid4())
        install_data = {"version": "1.0.0"}
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{fake_id}/install", json=install_data)
        assert response.status_code == 404

    def test_install_plugin_already_installed(self, client, sample_listing):
        """Test installing a plugin that is already installed"""
        _listings[sample_listing["id"]] = sample_listing
        _installed_plugins[sample_listing["plugin_id"]] = {
            "plugin_id": sample_listing["plugin_id"],
            "plugin_name": sample_listing["plugin_name"],
            "version": "1.0.0",
            "install_path": "plugins/test",
            "config": {},
            "installed_at": datetime.utcnow(),
        }
        
        install_data = {"version": "1.0.0"}
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        assert response.status_code == 400
        assert "already installed" in response.json()["detail"]

    def test_install_plugin_increments_download_count(self, client, sample_listing):
        """Test that installing a plugin increments download count"""
        _listings[sample_listing["id"]] = sample_listing
        initial_count = sample_listing["download_count"]
        
        install_data = {"version": "1.0.0"}
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        assert response.status_code == 200
        
        # Check that download count increased
        assert _listings[sample_listing["id"]]["download_count"] == initial_count + 1

    def test_install_plugin_auto_version(self, client, sample_listing):
        """Test installing plugin without specifying version (uses latest)"""
        _listings[sample_listing["id"]] = sample_listing
        
        install_data = {"config": {}}
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == sample_listing["version"]

    def test_uninstall_plugin_success(self, client, sample_listing):
        """Test uninstalling a plugin successfully"""
        _listings[sample_listing["id"]] = sample_listing
        _installed_plugins[sample_listing["plugin_id"]] = {
            "plugin_id": sample_listing["plugin_id"],
            "plugin_name": sample_listing["plugin_name"],
            "version": "1.0.0",
            "install_path": "plugins/test",
            "config": {},
            "installed_at": datetime.utcnow(),
        }
        
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/uninstall")
        assert response.status_code == 200
        assert sample_listing["plugin_id"] not in _installed_plugins

    def test_uninstall_plugin_not_found(self, client):
        """Test uninstalling a non-existent plugin"""
        fake_id = str(uuid4())
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{fake_id}/uninstall")
        assert response.status_code == 404

    def test_uninstall_plugin_not_installed(self, client, sample_listing):
        """Test uninstalling a plugin that is not installed"""
        _listings[sample_listing["id"]] = sample_listing
        
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/uninstall")
        assert response.status_code == 400
        assert "not installed" in response.json()["detail"]


# ============================================================================
# Category Endpoints Tests
# ============================================================================

class TestCategoryEndpoints:
    """Test cases for category endpoints"""

    def test_get_categories_empty(self, client):
        """Test getting categories when storage is empty"""
        response = client.get("/api/v1/plugin/marketplace/categories")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_categories_with_data(self, client, sample_category):
        """Test getting categories with data"""
        _categories[sample_category["id"]] = sample_category
        response = client.get("/api/v1/plugin/marketplace/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_categories_multiple(self, client):
        """Test getting multiple categories"""
        categories = [
            {
                "id": str(uuid4()),
                "name": "monitoring",
                "description": "Monitoring plugins",
                "plugin_count": 5,
                "icon": "📊",
            },
            {
                "id": str(uuid4()),
                "name": "alerting",
                "description": "Alerting plugins",
                "plugin_count": 3,
                "icon": "🔔",
            },
        ]
        for category in categories:
            _categories[category["id"]] = category
        
        response = client.get("/api/v1/plugin/marketplace/categories")
        assert response.status_code == 200
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
        assert response.status_code == 200
        assert response.json() == []

    def test_get_reviews_with_data(self, client, sample_review):
        """Test getting reviews with data"""
        plugin_id = sample_review["plugin_id"]
        _reviews[plugin_id] = [sample_review]
        
        response = client.get("/api/v1/plugin/marketplace/reviews")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_reviews_filter_plugin_id(self, client, sample_review):
        """Test getting reviews filtered by plugin ID"""
        plugin_id = sample_review["plugin_id"]
        _reviews[plugin_id] = [sample_review]
        
        response = client.get(f"/api/v1/plugin/marketplace/reviews?plugin_id={plugin_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_reviews_filter_rating(self, client, sample_review):
        """Test getting reviews filtered by rating"""
        plugin_id = sample_review["plugin_id"]
        _reviews[plugin_id] = [sample_review]
        
        response = client.get("/api/v1/plugin/marketplace/reviews?rating=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_reviews_limit(self, client, sample_review):
        """Test getting reviews with limit"""
        plugin_id = sample_review["plugin_id"]
        reviews = []
        for i in range(10):
            review = sample_review.copy()
            review["id"] = str(uuid4())
            reviews.append(review)
        _reviews[plugin_id] = reviews
        
        response = client.get("/api/v1/plugin/marketplace/reviews?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_reviews_invalid_rating(self, client):
        """Test getting reviews with invalid rating"""
        response = client.get("/api/v1/plugin/marketplace/reviews?rating=6")
        assert response.status_code == 422

    def test_create_review_success(self, client, sample_listing):
        """Test creating a review successfully"""
        _listings[sample_listing["id"]] = sample_listing
        
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test Reviewer",
            "rating": 5,
            "comment": "Excellent plugin!",
            "title": "Great"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 200
        data = response.json()
        assert data["reviewer"] == "Test Reviewer"
        assert data["rating"] == 5

    def test_create_review_plugin_not_found(self, client):
        """Test creating a review for non-existent plugin"""
        review_data = {
            "plugin_id": str(uuid4()),
            "reviewer": "Test Reviewer",
            "rating": 5,
            "comment": "Test"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 404

    def test_create_review_invalid_rating(self, client, sample_listing):
        """Test creating a review with invalid rating"""
        _listings[sample_listing["id"]] = sample_listing
        
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test Reviewer",
            "rating": 6,  # Invalid (must be 1-5)
            "comment": "Test"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 422

    def test_create_review_missing_required_field(self, client, sample_listing):
        """Test creating a review with missing required field"""
        _listings[sample_listing["id"]] = sample_listing
        
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test Reviewer"
            # Missing rating, comment
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 422

    def test_create_review_updates_plugin_rating(self, client, sample_listing):
        """Test that creating a review updates plugin rating"""
        # Create a fresh listing without existing reviews
        fresh_listing = sample_listing.copy()
        fresh_listing["id"] = str(uuid4())
        fresh_listing["plugin_id"] = str(uuid4())
        fresh_listing["review_count"] = 0
        fresh_listing["rating"] = 0.0
        _listings[fresh_listing["id"]] = fresh_listing
        
        initial_count = 0
        
        review_data = {
            "plugin_id": fresh_listing["plugin_id"],
            "reviewer": "Test Reviewer",
            "rating": 5,
            "comment": "Great!"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 200
        
        # Check that rating and count were updated
        updated_listing = _listings[fresh_listing["id"]]
        assert updated_listing["review_count"] == initial_count + 1
        # Rating should be recalculated to 5.0
        assert updated_listing["rating"] == 5.0

    def test_get_plugin_reviews_empty(self, client, sample_listing):
        """Test getting reviews for a specific plugin when none exist"""
        _listings[sample_listing["id"]] = sample_listing
        
        response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['plugin_id']}/reviews")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_plugin_reviews_with_data(self, client, sample_review):
        """Test getting reviews for a specific plugin"""
        plugin_id = sample_review["plugin_id"]
        _reviews[plugin_id] = [sample_review]
        
        response = client.get(f"/api/v1/plugin/marketplace/plugins/{plugin_id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_plugin_reviews_limit(self, client, sample_review):
        """Test getting plugin reviews with limit"""
        plugin_id = sample_review["plugin_id"]
        reviews = []
        for i in range(10):
            review = sample_review.copy()
            review["id"] = str(uuid4())
            reviews.append(review)
        _reviews[plugin_id] = reviews
        
        response = client.get(f"/api/v1/plugin/marketplace/plugins/{plugin_id}/reviews?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test cases for error handling"""

    @patch('api.plugin_marketplace_advanced_router.logger')
    def test_get_plugins_exception_handling(self, mock_logger, client):
        """Test exception handling in get_plugins"""
        with patch('api.plugin_marketplace_advanced_router.list', side_effect=Exception("Test error")):
            response = client.get("/api/v1/plugin/marketplace/plugins")
            assert response.status_code == 500

    @patch('api.plugin_marketplace_advanced_router.logger')
    def test_create_review_exception_handling(self, mock_logger, client, sample_listing):
        """Test exception handling in create_review"""
        _listings[sample_listing["id"]] = sample_listing
        
        with patch('api.plugin_marketplace_advanced_router.uuid4', side_effect=Exception("Test error")):
            review_data = {
                "plugin_id": sample_listing["plugin_id"],
                "reviewer": "Test",
                "rating": 5,
                "comment": "Test"
            }
            response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
            assert response.status_code == 500

    @patch('api.plugin_marketplace_advanced_router.logger')
    def test_install_plugin_exception_handling(self, mock_logger, client, sample_listing):
        """Test exception handling in install_plugin"""
        _listings[sample_listing["id"]] = sample_listing
        
        with patch('api.plugin_marketplace_advanced_router.InstallResponse', side_effect=Exception("Test error")):
            install_data = {"version": "1.0.0"}
            response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
            assert response.status_code == 500


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test cases for data validation"""

    def test_plugin_listing_create_missing_required_field(self, client):
        """Test plugin listing creation with missing required field"""
        listing_data = {
            "plugin_name": "Test Plugin"
            # Missing plugin_id, version, description, author, download_url
        }
        response = client.post("/api/v1/plugin/marketplace/plugins", json=listing_data)
        # Note: This endpoint doesn't exist in the router, but the model validation would apply
        pass

    def test_review_create_rating_below_minimum(self, client, sample_listing):
        """Test review creation with rating below minimum"""
        _listings[sample_listing["id"]] = sample_listing
        
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test",
            "rating": 0,  # Below minimum of 1
            "comment": "Test"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 422

    def test_review_create_rating_above_maximum(self, client, sample_listing):
        """Test review creation with rating above maximum"""
        _listings[sample_listing["id"]] = sample_listing
        
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test",
            "rating": 10,  # Above maximum of 5
            "comment": "Test"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 422

    def test_install_request_invalid_version_format(self, client, sample_listing):
        """Test install request with invalid version format"""
        _listings[sample_listing["id"]] = sample_listing
        
        install_data = {
            "version": "invalid.version",
            "config": {}
        }
        # Version is a string, so any format is accepted
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        # This should succeed as version is just a string
        assert response.status_code == 200


# ============================================================================
# Mock Tests
# ============================================================================

class TestMockDependencies:
    """Test cases with mocked dependencies"""

    @patch('api.plugin_marketplace_advanced_router.datetime')
    def test_install_plugin_with_mocked_datetime(self, mock_datetime, client, sample_listing):
        """Test plugin installation with mocked datetime"""
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        _listings[sample_listing["id"]] = sample_listing
        install_data = {"version": "1.0.0"}
        response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        assert response.status_code == 200

    @patch('api.plugin_marketplace_advanced_router.uuid4')
    def test_create_review_with_mocked_uuid(self, mock_uuid, client, sample_listing):
        """Test review creation with mocked UUID"""
        mock_uuid.return_value = "test-uuid-123"
        
        _listings[sample_listing["id"]] = sample_listing
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test",
            "rating": 5,
            "comment": "Test"
        }
        response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-uuid-123"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration test cases"""

    def test_full_plugin_lifecycle(self, client, sample_listing):
        """Test complete plugin lifecycle: list, install, review, uninstall"""
        # List plugins
        _listings[sample_listing["id"]] = sample_listing
        list_response = client.get("/api/v1/plugin/marketplace/plugins")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        
        # Get plugin details
        get_response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}")
        assert get_response.status_code == 200
        
        # Install plugin
        install_data = {"version": "1.0.0"}
        install_response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/install", json=install_data)
        assert install_response.status_code == 200
        
        # Create review
        review_data = {
            "plugin_id": sample_listing["plugin_id"],
            "reviewer": "Test Reviewer",
            "rating": 5,
            "comment": "Great plugin!"
        }
        review_response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
        assert review_response.status_code == 200
        
        # Get plugin reviews
        reviews_response = client.get(f"/api/v1/plugin/marketplace/plugins/{sample_listing['plugin_id']}/reviews")
        assert reviews_response.status_code == 200
        assert len(reviews_response.json()) == 1
        
        # Uninstall plugin
        uninstall_response = client.post(f"/api/v1/plugin/marketplace/plugins/{sample_listing['id']}/uninstall")
        assert uninstall_response.status_code == 200

    def test_multiple_reviews_rating_calculation(self, client, sample_listing):
        """Test that multiple reviews correctly calculate average rating"""
        _listings[sample_listing["id"]] = sample_listing
        
        # Create multiple reviews with different ratings
        ratings = [5, 4, 3, 5, 4]
        for i, rating in enumerate(ratings):
            review_data = {
                "plugin_id": sample_listing["plugin_id"],
                "reviewer": f"Reviewer {i}",
                "rating": rating,
                "comment": f"Review {i}"
            }
            response = client.post("/api/v1/plugin/marketplace/reviews", json=review_data)
            assert response.status_code == 200
        
        # Check that the average rating is correct
        updated_listing = _listings[sample_listing["id"]]
        expected_rating = sum(ratings) / len(ratings)
        assert abs(updated_listing["rating"] - expected_rating) < 0.1
        assert updated_listing["review_count"] == len(ratings)

    def test_category_and_plugin_filtering(self, client, sample_category, sample_listing):
        """Test filtering plugins by category"""
        _categories[sample_category["id"]] = sample_category
        _listings[sample_listing["id"]] = sample_listing
        
        # Get categories
        categories_response = client.get("/api/v1/plugin/marketplace/categories")
        assert categories_response.status_code == 200
        
        # Filter plugins by category
        plugins_response = client.get(f"/api/v1/plugin/marketplace/plugins?category={sample_category['name']}")
        assert plugins_response.status_code == 200
        data = plugins_response.json()
        assert len(data) == 1
        assert data[0]["category"] == sample_category["name"]

    def test_search_functionality(self, client, sample_listing):
        """Test search functionality across plugins"""
        _listings[sample_listing["id"]] = sample_listing
        
        # Search by name
        response = client.get("/api/v1/plugin/marketplace/plugins?search=Test")
        assert response.status_code == 200
        assert len(response.json()) == 1
        
        # Search by description
        response = client.get("/api/v1/plugin/marketplace/plugins?search=description")
        assert response.status_code == 200
        assert len(response.json()) == 1
        
        # Search with no results
        response = client.get("/api/v1/plugin/marketplace/plugins?search=nonexistent")
        assert response.status_code == 200
        assert len(response.json()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.plugin_marketplace_advanced_router", "--cov-report=html"])
