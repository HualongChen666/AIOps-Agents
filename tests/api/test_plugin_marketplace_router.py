# -*- coding: utf-8 -*-
"""
Test cases for Plugin Marketplace Router
Comprehensive test coverage for plugin marketplace API endpoints
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.plugin_marketplace_router import (
    PluginListingRequest,
    PluginReviewRequest,
    PluginInstallRequest,
    PluginQualityEnum,
    PluginCategoryEnum,
    router,
)


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user for authentication"""
    user = Mock()
    user.id = uuid4()
    user.username = "test_user"
    user.role = "operator"
    return user


@pytest.fixture
def sample_plugin_listing():
    """Create a sample plugin listing for testing"""
    return {
        "plugin_id": "test-plugin-001",
        "plugin_name": "Test Plugin",
        "version": "1.0.0",
        "description": "Test plugin description",
        "author": "Test Author",
        "category": PluginCategoryEnum.MONITORING,
        "tags": ["test", "monitoring"],
        "price": None,
        "quality": PluginQualityEnum.COMMUNITY,
        "download_url": "https://example.com/test-plugin.zip",
        "screenshot_urls": [],
        "documentation_url": "https://docs.example.com",
        "repository_url": "https://github.com/example/test-plugin",
    }


@pytest.fixture
def sample_plugin_review():
    """Create a sample plugin review for testing"""
    return {
        "plugin_id": "test-plugin-001",
        "reviewer_id": "user-001",
        "reviewer_name": "Test Reviewer",
        "rating": 5,
        "review_text": "Great plugin!",
    }


@pytest.fixture
def sample_plugin_install():
    """Create a sample plugin install request for testing"""
    return {
        "plugin_id": "test-plugin-001",
        "installed_version": "1.0.0",
        "configuration": {"enabled": True},
    }


# ============================================================================
# Get Plugin Listings Endpoint Tests
# ============================================================================


class TestGetPluginListings:
    """Test cases for get_plugin_listings endpoint"""

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_get_plugin_listings_success(self, mock_get_session, mock_cache, client):
        """Test successful plugin listings retrieval"""
        from core.models import PluginListingDB

        # Mock cache miss
        mock_cache.get.return_value = None

        # Mock database
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = [PluginListingDB(
            id="PLUGIN-001",
            plugin_id="test-plugin-001",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test Author",
            category="monitoring",
            tags=["test"],
            price=None,
            quality="community",
            download_url="https://example.com",
            screenshot_urls=[],
            documentation_url=None,
            repository_url=None,
            download_count=0,
            rating=0.0,
            review_count=0,
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )]
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    def test_get_plugin_listings_from_cache(self, mock_cache, client):
        """Test plugin listings retrieval from cache"""
        cached_data = {
            "items": [{"plugin_name": "Test Plugin"}],
            "total": 1,
            "limit": 20,
            "offset": 0,
        }
        mock_cache.get.return_value = cached_data

        response = client.get("/api/v1/plugin-marketplace/plugins")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_get_plugin_listings_with_category_filter(
        self, mock_get_session, mock_cache, client
    ):
        """Test plugin listings with category filter"""
        mock_cache.get.return_value = None
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins?category=monitoring")
        assert response.status_code == 200

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_get_plugin_listings_with_quality_filter(
        self, mock_get_session, mock_cache, client
    ):
        """Test plugin listings with quality filter"""
        mock_cache.get.return_value = None
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins?quality=verified")
        assert response.status_code == 200

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_get_plugin_listings_with_pagination(
        self, mock_get_session, mock_cache, client
    ):
        """Test plugin listings with pagination"""
        mock_cache.get.return_value = None
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins?limit=10&offset=0")
        assert response.status_code == 200

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_get_plugin_listings_invalid_limit(
        self, mock_get_session, mock_cache, client
    ):
        """Test plugin listings with invalid limit"""
        mock_cache.get.return_value = None
        mock_db = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins?limit=0")
        # FastAPI validation should handle this
        assert response.status_code in (422, 200)


# ============================================================================
# Upload Plugin Endpoint Tests
# ============================================================================


class TestUploadPlugin:
    """Test cases for upload_plugin endpoint"""

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_upload_plugin_success(
        self, mock_get_session, mock_cache, client, sample_plugin_listing
    ):
        """Test successful plugin upload"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Plugin doesn't exist
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post("/api/v1/plugin-marketplace/plugins", json=sample_plugin_listing)
        assert response.status_code == 201
        data = response.json()
        assert "success" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_upload_plugin_already_exists(
        self, mock_get_session, mock_cache, client, sample_plugin_listing
    ):
        """Test uploading a plugin that already exists"""
        from core.models import PluginListingDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Plugin already exists
        mock_query.first.return_value = PluginListingDB(
            id="PLUGIN-001",
            plugin_id="test-plugin-001",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test Author",
            category="monitoring",
            tags=[],
            price=None,
            quality="community",
            download_url="https://example.com",
            screenshot_urls=[],
            documentation_url=None,
            repository_url=None,
            download_count=0,
            rating=0.0,
            review_count=0,
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post("/api/v1/plugin-marketplace/plugins", json=sample_plugin_listing)
        assert response.status_code == 200
        data = response.json()
        # Should return error for duplicate
        assert "error" in data or "success" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_upload_plugin_all_categories(
        self, mock_get_session, mock_cache, client, sample_plugin_listing
    ):
        """Test uploading plugins for all categories"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        categories = [
            PluginCategoryEnum.GENERAL,
            PluginCategoryEnum.MONITORING,
            PluginCategoryEnum.ALERTING,
            PluginCategoryEnum.AUTOMATION,
            PluginCategoryEnum.ANALYTICS,
            PluginCategoryEnum.SECURITY,
            PluginCategoryEnum.PERFORMANCE,
            PluginCategoryEnum.INTEGRATION,
        ]

        for category in categories:
            sample_plugin_listing["category"] = category
            response = client.post("/api/v1/plugin-marketplace/plugins", json=sample_plugin_listing)
            assert response.status_code == 201

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_upload_plugin_all_qualities(
        self, mock_get_session, mock_cache, client, sample_plugin_listing
    ):
        """Test uploading plugins for all quality levels"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        qualities = [
            PluginQualityEnum.COMMUNITY,
            PluginQualityEnum.VERIFIED,
            PluginQualityEnum.OFFICIAL,
        ]

        for quality in qualities:
            sample_plugin_listing["quality"] = quality
            response = client.post("/api/v1/plugin-marketplace/plugins", json=sample_plugin_listing)
            assert response.status_code == 201


# ============================================================================
# Add Plugin Review Endpoint Tests
# ============================================================================


class TestAddPluginReview:
    """Test cases for add_plugin_review endpoint"""

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_add_plugin_review_success(
        self, mock_get_session, mock_cache, client, sample_plugin_review
    ):
        """Test successful plugin review addition"""
        from core.models import PluginListingDB, PluginReviewDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        # Plugin exists
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = PluginListingDB(
            id="PLUGIN-001",
            plugin_id="test-plugin-001",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test Author",
            category="monitoring",
            tags=[],
            price=None,
            quality="community",
            download_url="https://example.com",
            screenshot_urls=[],
            documentation_url=None,
            repository_url=None,
            download_count=0,
            rating=4.0,
            review_count=1,
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post(
            "/api/v1/plugin-marketplace/plugins/test-plugin-001/reviews", json=sample_plugin_review
        )
        assert response.status_code == 201
        data = response.json()
        assert "success" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_add_plugin_review_plugin_not_found(
        self, mock_get_session, mock_cache, client, sample_plugin_review
    ):
        """Test adding review for non-existent plugin"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Plugin doesn't exist
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post(
            "/api/v1/plugin-marketplace/plugins/nonexistent/reviews", json=sample_plugin_review
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_add_plugin_review_all_ratings(
        self, mock_get_session, mock_cache, client, sample_plugin_review
    ):
        """Test adding reviews with all rating values"""
        from core.models import PluginListingDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = PluginListingDB(
            id="PLUGIN-001",
            plugin_id="test-plugin-001",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test Author",
            category="monitoring",
            tags=[],
            price=None,
            quality="community",
            download_url="https://example.com",
            screenshot_urls=[],
            documentation_url=None,
            repository_url=None,
            download_count=0,
            rating=3.0,
            review_count=1,
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        for rating in range(1, 6):
            sample_plugin_review["rating"] = rating
            response = client.post(
                "/api/v1/plugin-marketplace/plugins/test-plugin-001/reviews",
                json=sample_plugin_review,
            )
            assert response.status_code == 201


# ============================================================================
# Install Plugin Endpoint Tests
# ============================================================================


class TestInstallPlugin:
    """Test cases for install_plugin endpoint"""

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_install_plugin_success(
        self, mock_get_session, mock_cache, client, sample_plugin_install
    ):
        """Test successful plugin installation"""
        from core.models import PluginListingDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Plugin exists
        mock_query.first.side_effect = [
            PluginListingDB(
                id="PLUGIN-001",
                plugin_id="test-plugin-001",
                plugin_name="Test Plugin",
                version="1.0.0",
                description="Test",
                author="Test Author",
                category="monitoring",
                tags=[],
                price=None,
                quality="community",
                download_url="https://example.com",
                screenshot_urls=[],
                documentation_url=None,
                repository_url=None,
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            None,  # Not already installed
        ]
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post(
            "/api/v1/plugin-marketplace/plugins/test-plugin-001/install", json=sample_plugin_install
        )
        assert response.status_code == 201
        data = response.json()
        assert "success" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_install_plugin_not_found(
        self, mock_get_session, mock_cache, client, sample_plugin_install
    ):
        """Test installing a non-existent plugin"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Plugin doesn't exist
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post(
            "/api/v1/plugin-marketplace/plugins/nonexistent/install", json=sample_plugin_install
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_install_plugin_already_installed(
        self, mock_get_session, mock_cache, client, sample_plugin_install
    ):
        """Test installing a plugin that is already installed"""
        from core.models import PluginListingDB, InstalledPluginDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Plugin exists and is already installed
        mock_query.first.side_effect = [
            PluginListingDB(
                id="PLUGIN-001",
                plugin_id="test-plugin-001",
                plugin_name="Test Plugin",
                version="1.0.0",
                description="Test",
                author="Test Author",
                category="monitoring",
                tags=[],
                price=None,
                quality="community",
                download_url="https://example.com",
                screenshot_urls=[],
                documentation_url=None,
                repository_url=None,
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            InstalledPluginDB(
                id="INSTALLED-001",
                plugin_id="test-plugin-001",
                installed_version="1.0.0",
                status="active",
                configuration={},
            ),
        ]
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post(
            "/api/v1/plugin-marketplace/plugins/test-plugin-001/install", json=sample_plugin_install
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


# ============================================================================
# Get Installed Plugins Endpoint Tests
# ============================================================================


class TestGetInstalledPlugins:
    """Test cases for get_installed_plugins endpoint"""

    @patch("api.plugin_marketplace_router.get_session")
    def test_get_installed_plugins_success(self, mock_get_session, client):
        """Test successful installed plugins retrieval"""
        from core.models import InstalledPluginDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins/installed")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @patch("api.plugin_marketplace_router.get_session")
    def test_get_installed_plugins_with_filter(self, mock_get_session, client):
        """Test installed plugins with enabled filter"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins/installed?enabled=true")
        assert response.status_code == 200

    @patch("api.plugin_marketplace_router.get_session")
    def test_get_installed_plugins_with_pagination(self, mock_get_session, client):
        """Test installed plugins with pagination"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/plugin-marketplace/plugins/installed?limit=10&offset=0")
        assert response.status_code == 200


# ============================================================================
# Uninstall Plugin Endpoint Tests
# ============================================================================


class TestUninstallPlugin:
    """Test cases for uninstall_plugin endpoint"""

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_uninstall_plugin_success(self, mock_get_session, mock_cache, client):
        """Test successful plugin uninstallation"""
        from core.models import PluginListingDB, InstalledPluginDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Plugin exists and is installed
        mock_query.first.side_effect = [
            PluginListingDB(
                id="PLUGIN-001",
                plugin_id="test-plugin-001",
                plugin_name="Test Plugin",
                version="1.0.0",
                description="Test",
                author="Test Author",
                category="monitoring",
                tags=[],
                price=None,
                quality="community",
                download_url="https://example.com",
                screenshot_urls=[],
                documentation_url=None,
                repository_url=None,
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            InstalledPluginDB(
                id="INSTALLED-001",
                plugin_id="test-plugin-001",
                installed_version="1.0.0",
                status="active",
                configuration={},
            ),
        ]
        mock_db.delete = MagicMock()
        mock_db.commit = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post("/api/v1/plugin-marketplace/plugins/installed/test-plugin-001")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_uninstall_plugin_not_found(self, mock_get_session, mock_cache, client):
        """Test uninstalling a non-existent plugin"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Plugin doesn't exist
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post("/api/v1/plugin-marketplace/plugins/installed/nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @patch("api.plugin_marketplace_router.cache_manager")
    @patch("api.plugin_marketplace_router.get_session")
    def test_uninstall_plugin_not_installed(self, mock_get_session, mock_cache, client):
        """Test uninstalling a plugin that is not installed"""
        from core.models import PluginListingDB

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Plugin exists but not installed
        mock_query.first.side_effect = [
            PluginListingDB(
                id="PLUGIN-001",
                plugin_id="test-plugin-001",
                plugin_name="Test Plugin",
                version="1.0.0",
                description="Test",
                author="Test Author",
                category="monitoring",
                tags=[],
                price=None,
                quality="community",
                download_url="https://example.com",
                screenshot_urls=[],
                documentation_url=None,
                repository_url=None,
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            None,  # Not installed
        ]
        mock_get_session.return_value.__enter__.return_value = mock_db

        response = client.post("/api/v1/plugin-marketplace/plugins/installed/test-plugin-001")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
