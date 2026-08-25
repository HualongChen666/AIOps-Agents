# -*- coding: utf-8 -*-
"""
Test cases for Localization Advanced Router
Comprehensive test coverage for localization management API
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.localization_advanced_router import (
    AdapterCreate,
    LanguageCreate,
    LanguageUpdate,
    ResourceCreate,
    ResourceUpdate,
    TranslationCreate,
    _adapters,
    _languages,
    _resources,
    _translations,
    router,
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
    _languages.clear()
    _resources.clear()
    _translations.clear()
    _adapters.clear()
    yield
    _languages.clear()
    _resources.clear()
    _translations.clear()
    _adapters.clear()


@pytest.fixture
def sample_language():
    """Create a sample language for testing"""
    return {
        "id": str(uuid4()),
        "code": "zh-CN",
        "name": "Chinese (Simplified)",
        "native_name": "简体中文",
        "enabled": True,
        "is_default": True,
        "metadata": {"region": "CN"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_resource():
    """Create a sample resource for testing"""
    return {
        "id": str(uuid4()),
        "language_code": "zh-CN",
        "namespace": "common",
        "key": "welcome",
        "value": "欢迎",
        "context": "Greeting message",
        "metadata": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_translation():
    """Create a sample translation for testing"""
    return {
        "id": str(uuid4()),
        "source_language": "en-US",
        "target_language": "zh-CN",
        "namespace": "common",
        "key": "welcome",
        "source_value": "Welcome",
        "target_value": "欢迎",
        "status": "published",
        "metadata": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_adapter():
    """Create a sample adapter for testing"""
    return {
        "id": str(uuid4()),
        "name": "Date Adapter",
        "type": "date",
        "config": {"format": "YYYY-MM-DD"},
        "enabled": True,
        "priority": 10,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


# ============================================================================
# Language Endpoints Tests
# ============================================================================


class TestLanguageEndpoints:
    """Test cases for language endpoints"""

    def test_get_languages_empty(self, client):
        """Test getting languages when storage is empty"""
        response = client.get("/api/v1/localization/languages")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_languages_with_data(self, client, sample_language):
        """Test getting languages with data"""
        _languages[sample_language["id"]] = sample_language
        response = client.get("/api/v1/localization/languages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "zh-CN"

    def test_get_languages_filter_enabled(self, client, sample_language):
        """Test getting languages filtered by enabled status"""
        sample_language["enabled"] = True
        _languages[sample_language["id"]] = sample_language

        disabled_lang = sample_language.copy()
        disabled_lang["id"] = str(uuid4())
        disabled_lang["code"] = "en-US"
        disabled_lang["enabled"] = False
        _languages[disabled_lang["id"]] = disabled_lang

        response = client.get("/api/v1/localization/languages?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["enabled"] == True

    def test_get_languages_search(self, client, sample_language):
        """Test getting languages with search parameter"""
        _languages[sample_language["id"]] = sample_language

        response = client.get("/api/v1/localization/languages?search=chinese")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_create_language_success(self, client):
        """Test creating a language successfully"""
        language_data = {
            "code": "fr-FR",
            "name": "French",
            "native_name": "Français",
            "enabled": True,
            "is_default": False,
            "metadata": {"region": "FR"},
        }
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "fr-FR"
        assert data["name"] == "French"
        assert "id" in data

    def test_create_language_duplicate_code(self, client, sample_language):
        """Test creating a language with duplicate code"""
        _languages[sample_language["id"]] = sample_language

        language_data = {
            "code": "zh-CN",
            "name": "Chinese Duplicate",
            "native_name": "简体中文",
            "enabled": True,
            "is_default": False,
        }
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_language_invalid_code(self, client):
        """Test creating a language with invalid code"""
        language_data = {"code": "x", "name": "Invalid", "native_name": "Invalid", "enabled": True}
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 422  # Validation error

    def test_create_language_set_default(self, client, sample_language):
        """Test creating a language and setting it as default"""
        sample_language["is_default"] = True
        _languages[sample_language["id"]] = sample_language

        language_data = {
            "code": "en-US",
            "name": "English",
            "native_name": "English",
            "enabled": True,
            "is_default": True,
        }
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 200
        # Check that previous default is no longer default
        assert _languages[sample_language["id"]]["is_default"] == False

    def test_get_language_success(self, client, sample_language):
        """Test getting a language by ID successfully"""
        _languages[sample_language["id"]] = sample_language
        response = client.get(f"/api/v1/localization/languages/{sample_language['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "zh-CN"

    def test_get_language_not_found(self, client):
        """Test getting a non-existent language"""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/localization/languages/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_language_success(self, client, sample_language):
        """Test updating a language successfully"""
        _languages[sample_language["id"]] = sample_language

        update_data = {"name": "Chinese (Simplified) Updated", "enabled": False}
        response = client.patch(
            f"/api/v1/localization/languages/{sample_language['id']}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Chinese (Simplified) Updated"
        assert data["enabled"] == False

    def test_update_language_not_found(self, client):
        """Test updating a non-existent language"""
        fake_id = str(uuid4())
        update_data = {"name": "Updated"}
        response = client.patch(f"/api/v1/localization/languages/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_update_language_set_default(self, client, sample_language):
        """Test updating a language to set it as default"""
        sample_language["is_default"] = True
        _languages[sample_language["id"]] = sample_language

        new_lang = sample_language.copy()
        new_lang["id"] = str(uuid4())
        new_lang["code"] = "en-US"
        new_lang["is_default"] = False
        _languages[new_lang["id"]] = new_lang

        update_data = {"is_default": True}
        response = client.patch(
            f"/api/v1/localization/languages/{new_lang['id']}", json=update_data
        )
        assert response.status_code == 200
        assert _languages[sample_language["id"]]["is_default"] == False

    def test_delete_language_success(self, client, sample_language):
        """Test deleting a language successfully"""
        sample_language["is_default"] = False
        _languages[sample_language["id"]] = sample_language

        response = client.delete(f"/api/v1/localization/languages/{sample_language['id']}")
        assert response.status_code == 200
        assert sample_language["id"] not in _languages

    def test_delete_language_not_found(self, client):
        """Test deleting a non-existent language"""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/localization/languages/{fake_id}")
        assert response.status_code == 404

    def test_delete_default_language(self, client, sample_language):
        """Test deleting a default language (should fail)"""
        sample_language["is_default"] = True
        _languages[sample_language["id"]] = sample_language

        response = client.delete(f"/api/v1/localization/languages/{sample_language['id']}")
        assert response.status_code == 400
        assert "Cannot delete default language" in response.json()["detail"]


# ============================================================================
# Resource Endpoints Tests
# ============================================================================


class TestResourceEndpoints:
    """Test cases for resource endpoints"""

    def test_get_resources_empty(self, client):
        """Test getting resources when storage is empty"""
        response = client.get("/api/v1/localization/resources")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_resources_with_data(self, client, sample_resource):
        """Test getting resources with data"""
        _resources[sample_resource["id"]] = sample_resource
        response = client.get("/api/v1/localization/resources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_resources_filter_language_code(self, client, sample_resource):
        """Test getting resources filtered by language code"""
        _resources[sample_resource["id"]] = sample_resource

        response = client.get("/api/v1/localization/resources?language_code=zh-CN")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_resources_filter_namespace(self, client, sample_resource):
        """Test getting resources filtered by namespace"""
        _resources[sample_resource["id"]] = sample_resource

        response = client.get("/api/v1/localization/resources?namespace=common")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_create_resource_success(self, client):
        """Test creating a resource successfully"""
        resource_data = {
            "language_code": "zh-CN",
            "namespace": "common",
            "key": "greeting",
            "value": "你好",
            "context": "Greeting",
            "metadata": {},
        }
        response = client.post("/api/v1/localization/resources", json=resource_data)
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "greeting"
        assert data["value"] == "你好"

    def test_create_resource_duplicate_key(self, client, sample_resource):
        """Test creating a resource with duplicate key"""
        _resources[sample_resource["id"]] = sample_resource

        resource_data = {
            "language_code": "zh-CN",
            "namespace": "common",
            "key": "welcome",
            "value": "欢迎2",
        }
        response = client.post("/api/v1/localization/resources", json=resource_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_resource_success(self, client, sample_resource):
        """Test getting a resource by ID successfully"""
        _resources[sample_resource["id"]] = sample_resource
        response = client.get(f"/api/v1/localization/resources/{sample_resource['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "welcome"

    def test_get_resource_not_found(self, client):
        """Test getting a non-existent resource"""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/localization/resources/{fake_id}")
        assert response.status_code == 404

    def test_update_resource_success(self, client, sample_resource):
        """Test updating a resource successfully"""
        _resources[sample_resource["id"]] = sample_resource

        update_data = {"value": "欢迎 (Updated)", "context": "Updated context"}
        response = client.patch(
            f"/api/v1/localization/resources/{sample_resource['id']}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "欢迎 (Updated)"

    def test_update_resource_not_found(self, client):
        """Test updating a non-existent resource"""
        fake_id = str(uuid4())
        update_data = {"value": "Updated"}
        response = client.patch(f"/api/v1/localization/resources/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_delete_resource_success(self, client, sample_resource):
        """Test deleting a resource successfully"""
        _resources[sample_resource["id"]] = sample_resource

        response = client.delete(f"/api/v1/localization/resources/{sample_resource['id']}")
        assert response.status_code == 200
        assert sample_resource["id"] not in _resources

    def test_delete_resource_not_found(self, client):
        """Test deleting a non-existent resource"""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/localization/resources/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Translation Endpoints Tests
# ============================================================================


class TestTranslationEndpoints:
    """Test cases for translation endpoints"""

    def test_get_translations_empty(self, client):
        """Test getting translations when storage is empty"""
        response = client.get("/api/v1/localization/translations")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_translations_with_data(self, client, sample_translation):
        """Test getting translations with data"""
        _translations[sample_translation["id"]] = sample_translation
        response = client.get("/api/v1/localization/translations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_translations_filter_source_language(self, client, sample_translation):
        """Test getting translations filtered by source language"""
        _translations[sample_translation["id"]] = sample_translation

        response = client.get("/api/v1/localization/translations?source_language=en-US")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_translations_filter_target_language(self, client, sample_translation):
        """Test getting translations filtered by target language"""
        _translations[sample_translation["id"]] = sample_translation

        response = client.get("/api/v1/localization/translations?target_language=zh-CN")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_translations_filter_status(self, client, sample_translation):
        """Test getting translations filtered by status"""
        _translations[sample_translation["id"]] = sample_translation

        response = client.get("/api/v1/localization/translations?status=published")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_create_translation_success(self, client):
        """Test creating a translation successfully"""
        translation_data = {
            "source_language": "en-US",
            "target_language": "fr-FR",
            "namespace": "common",
            "key": "greeting",
            "source_value": "Hello",
            "target_value": "Bonjour",
            "status": "draft",
            "metadata": {},
        }
        response = client.post("/api/v1/localization/translations", json=translation_data)
        assert response.status_code == 200
        data = response.json()
        assert data["source_value"] == "Hello"
        assert data["target_value"] == "Bonjour"


# ============================================================================
# Adapter Endpoints Tests
# ============================================================================


class TestAdapterEndpoints:
    """Test cases for adapter endpoints"""

    def test_get_adapters_empty(self, client):
        """Test getting adapters when storage is empty"""
        response = client.get("/api/v1/localization/adapters")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_adapters_with_data(self, client, sample_adapter):
        """Test getting adapters with data"""
        _adapters[sample_adapter["id"]] = sample_adapter
        response = client.get("/api/v1/localization/adapters")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_adapters_filter_enabled(self, client, sample_adapter):
        """Test getting adapters filtered by enabled status"""
        sample_adapter["enabled"] = True
        _adapters[sample_adapter["id"]] = sample_adapter

        disabled_adapter = sample_adapter.copy()
        disabled_adapter["id"] = str(uuid4())
        disabled_adapter["enabled"] = False
        _adapters[disabled_adapter["id"]] = disabled_adapter

        response = client.get("/api/v1/localization/adapters?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["enabled"] == True

    def test_get_adapters_filter_type(self, client, sample_adapter):
        """Test getting adapters filtered by type"""
        _adapters[sample_adapter["id"]] = sample_adapter

        response = client.get("/api/v1/localization/adapters?type=date")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_create_adapter_success(self, client):
        """Test creating an adapter successfully"""
        adapter_data = {
            "name": "Number Adapter",
            "type": "number",
            "config": {"decimal_separator": ".", "thousands_separator": ","},
            "enabled": True,
            "priority": 5,
        }
        response = client.post("/api/v1/localization/adapters", json=adapter_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Number Adapter"
        assert data["type"] == "number"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test cases for error handling"""

    @patch("api.localization_advanced_router.logger")
    def test_get_languages_exception_handling(self, mock_logger, client):
        """Test exception handling in get_languages"""
        with patch(
            "api.localization_advanced_router.LanguageResponse", side_effect=Exception("Test error")
        ):
            sample_language = {
                "id": str(uuid4()),
                "code": "zh-CN",
                "name": "Chinese",
                "native_name": "简体中文",
                "enabled": True,
                "is_default": False,
                "metadata": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            _languages[sample_language["id"]] = sample_language
            response = client.get("/api/v1/localization/languages")
            assert response.status_code == 500

    @patch("api.localization_advanced_router.logger")
    def test_create_language_exception_handling(self, mock_logger, client):
        """Test exception handling in create_language"""
        with patch(
            "api.localization_advanced_router.LanguageResponse", side_effect=Exception("Test error")
        ):
            language_data = {"code": "fr-FR", "name": "French", "native_name": "Français"}
            response = client.post("/api/v1/localization/languages", json=language_data)
            assert response.status_code == 500

    @patch("api.localization_advanced_router.logger")
    def test_get_language_exception_handling(self, mock_logger, client):
        """Test exception handling in get_language"""
        with patch(
            "api.localization_advanced_router.LanguageResponse", side_effect=Exception("Test error")
        ):
            sample_language = {
                "id": str(uuid4()),
                "code": "zh-CN",
                "name": "Chinese",
                "native_name": "简体中文",
                "enabled": True,
                "is_default": False,
                "metadata": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            _languages[sample_language["id"]] = sample_language
            response = client.get(f"/api/v1/localization/languages/{sample_language['id']}")
            assert response.status_code == 500


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Test cases for data validation"""

    def test_language_create_missing_required_field(self, client):
        """Test language creation with missing required field"""
        language_data = {
            "name": "French"
            # Missing code, native_name
        }
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 422

    def test_language_create_invalid_type(self, client):
        """Test language creation with invalid field type"""
        language_data = {
            "code": "fr-FR",
            "name": "French",
            "native_name": "Français",
            "enabled": "not_a_boolean",  # Invalid type
        }
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 422

    def test_resource_create_missing_required_field(self, client):
        """Test resource creation with missing required field"""
        resource_data = {
            "language_code": "zh-CN"
            # Missing namespace, key, value
        }
        response = client.post("/api/v1/localization/resources", json=resource_data)
        assert response.status_code == 422

    def test_translation_create_missing_required_field(self, client):
        """Test translation creation with missing required field"""
        translation_data = {
            "source_language": "en-US"
            # Missing target_language, namespace, key, etc.
        }
        response = client.post("/api/v1/localization/translations", json=translation_data)
        assert response.status_code == 422


# ============================================================================
# Mock Tests
# ============================================================================


class TestMockDependencies:
    """Test cases with mocked dependencies"""

    @patch("api.localization_advanced_router.datetime")
    def test_create_language_with_mocked_datetime(self, mock_datetime, client):
        """Test language creation with mocked datetime"""
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)

        language_data = {"code": "fr-FR", "name": "French", "native_name": "Français"}
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 200

    @patch("api.localization_advanced_router.uuid4")
    def test_create_language_with_mocked_uuid(self, mock_uuid, client):
        """Test language creation with mocked UUID"""
        mock_uuid.return_value = "test-uuid-123"

        language_data = {"code": "fr-FR", "name": "French", "native_name": "Français"}
        response = client.post("/api/v1/localization/languages", json=language_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-uuid-123"


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration test cases"""

    def test_full_language_workflow(self, client):
        """Test complete language workflow: create, read, update, delete"""
        # Create
        language_data = {
            "code": "de-DE",
            "name": "German",
            "native_name": "Deutsch",
            "enabled": True,
            "is_default": False,
        }
        create_response = client.post("/api/v1/localization/languages", json=language_data)
        assert create_response.status_code == 200
        language_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/api/v1/localization/languages/{language_id}")
        assert get_response.status_code == 200

        # Update
        update_data = {"name": "German (Germany)"}
        update_response = client.patch(
            f"/api/v1/localization/languages/{language_id}", json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "German (Germany)"

        # Delete
        delete_response = client.delete(f"/api/v1/localization/languages/{language_id}")
        assert delete_response.status_code == 200

    def test_full_resource_workflow(self, client):
        """Test complete resource workflow: create, read, update, delete"""
        # Create
        resource_data = {
            "language_code": "en-US",
            "namespace": "test",
            "key": "test_key",
            "value": "Test Value",
        }
        create_response = client.post("/api/v1/localization/resources", json=resource_data)
        assert create_response.status_code == 200
        resource_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/api/v1/localization/resources/{resource_id}")
        assert get_response.status_code == 200

        # Update
        update_data = {"value": "Updated Value"}
        update_response = client.patch(
            f"/api/v1/localization/resources/{resource_id}", json=update_data
        )
        assert update_response.status_code == 200

        # Delete
        delete_response = client.delete(f"/api/v1/localization/resources/{resource_id}")
        assert delete_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.localization_advanced_router", "--cov-report=html"])
