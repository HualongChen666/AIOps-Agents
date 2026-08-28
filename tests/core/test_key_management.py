# -*- coding: utf-8 -*-
"""
Comprehensive tests for core/key_management_service.py
Tests for Key Management Service implementation
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from core.key_management_service import (
    EnvironmentKeyBackend,
    FileKeyBackend,
    KeyBackend,
    KeyManagementService,
    get_key_service,
    initialize_key_management,
)


class TestEnvironmentKeyBackend:
    """Test environment variable key backend."""

    def test_get_key_with_prefix(self):
        """Test getting key with AIOPS_ prefix."""
        backend = EnvironmentKeyBackend()
        
        # Set environment variable
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        
        try:
            value = backend.get_key("test_key")
            assert value == "test_value"
        finally:
            del os.environ["AIOPS_TEST_KEY"]

    def test_get_key_without_prefix(self):
        """Test getting key without prefix."""
        backend = EnvironmentKeyBackend()
        
        # Set environment variable without prefix
        os.environ["CUSTOM_KEY"] = "custom_value"
        
        try:
            value = backend.get_key("custom_key")
            assert value == "custom_value"
        finally:
            del os.environ["CUSTOM_KEY"]

    def test_get_key_not_found(self):
        """Test getting non-existent key."""
        backend = EnvironmentKeyBackend()
        value = backend.get_key("nonexistent_key")
        assert value is None

    def test_set_key(self):
        """Test setting key in environment."""
        backend = EnvironmentKeyBackend()
        
        backend.set_key("test_key", "test_value")
        assert os.environ["AIOPS_TEST_KEY"] == "test_value"
        
        # Cleanup
        del os.environ["AIOPS_TEST_KEY"]

    def test_delete_key(self):
        """Test deleting key from environment."""
        backend = EnvironmentKeyBackend()
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        assert backend.delete_key("test_key") is True
        assert "AIOPS_TEST_KEY" not in os.environ

    def test_delete_key_not_found(self):
        """Test deleting non-existent key."""
        backend = EnvironmentKeyBackend()
        assert backend.delete_key("nonexistent_key") is False

    def test_key_exists(self):
        """Test checking if key exists."""
        backend = EnvironmentKeyBackend()
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        try:
            assert backend.key_exists("test_key") is True
            assert backend.key_exists("nonexistent_key") is False
        finally:
            del os.environ["AIOPS_TEST_KEY"]


class TestFileKeyBackend:
    """Test file storage key backend."""

    @pytest.fixture
    def temp_file(self):
        """Create temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    def test_file_backend_initialization(self, temp_file):
        """Test file backend initialization."""
        backend = FileKeyBackend(temp_file)
        assert backend.file_path == Path(temp_file)
        assert backend._keys == {}

    def test_set_and_get_key(self, temp_file):
        """Test setting and getting key from file."""
        backend = FileKeyBackend(temp_file)
        
        backend.set_key("test_key", "test_value")
        value = backend.get_key("test_key")
        assert value == "test_value"

    def test_get_key_not_found(self, temp_file):
        """Test getting non-existent key from file."""
        backend = FileKeyBackend(temp_file)
        value = backend.get_key("nonexistent_key")
        assert value is None

    def test_delete_key(self, temp_file):
        """Test deleting key from file."""
        backend = FileKeyBackend(temp_file)
        
        backend.set_key("test_key", "test_value")
        assert backend.delete_key("test_key") is True
        assert backend.get_key("test_key") is None

    def test_delete_key_not_found(self, temp_file):
        """Test deleting non-existent key from file."""
        backend = FileKeyBackend(temp_file)
        assert backend.delete_key("nonexistent_key") is False

    def test_key_exists(self, temp_file):
        """Test checking if key exists in file."""
        backend = FileKeyBackend(temp_file)
        
        backend.set_key("test_key", "test_value")
        assert backend.key_exists("test_key") is True
        assert backend.key_exists("nonexistent_key") is False

    def test_file_persistence(self, temp_file):
        """Test that keys persist across backend instances."""
        # First instance
        backend1 = FileKeyBackend(temp_file)
        backend1.set_key("test_key", "test_value")
        
        # Second instance should load the same keys
        backend2 = FileKeyBackend(temp_file)
        assert backend2.get_key("test_key") == "test_value"

    def test_load_existing_file(self, temp_file):
        """Test loading keys from existing file."""
        # Create file with existing keys
        test_keys = {"existing_key": "existing_value"}
        with open(temp_file, 'w') as f:
            json.dump(test_keys, f)
        
        backend = FileKeyBackend(temp_file)
        assert backend.get_key("existing_key") == "existing_value"


class TestKeyManagementService:
    """Test key management service."""

    def test_initialization_with_environment_backend(self):
        """Test initialization with environment backend."""
        service = KeyManagementService(backend_type="environment")
        assert isinstance(service.backend, EnvironmentKeyBackend)

    def test_initialization_with_file_backend(self):
        """Test initialization with file backend."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            service = KeyManagementService(backend_type="file", file_path=temp_path)
            assert isinstance(service.backend, FileKeyBackend)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_unsupported_backend_type(self):
        """Test unsupported backend type raises error."""
        with pytest.raises(ValueError, match="Unsupported backend type"):
            KeyManagementService(backend_type="unsupported")

    def test_get_key(self):
        """Test getting key."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        try:
            value = service.get_key("test_key")
            assert value == "test_value"
        finally:
            del os.environ["AIOPS_TEST_KEY"]

    def test_get_key_with_default(self):
        """Test getting key with default value."""
        service = KeyManagementService(backend_type="environment")
        value = service.get_key("nonexistent_key", default="default_value")
        assert value == "default_value"

    def test_get_key_required(self):
        """Test getting required key raises error when not found."""
        service = KeyManagementService(backend_type="environment")
        with pytest.raises(ValueError, match="Required key"):
            service.get_key("nonexistent_key", required=True)

    def test_set_key(self):
        """Test setting key."""
        service = KeyManagementService(backend_type="environment")
        result = service.set_key("test_key", "test_value")
        assert result is True
        assert os.environ["AIOPS_TEST_KEY"] == "test_value"
        
        # Cleanup
        del os.environ["AIOPS_TEST_KEY"]

    def test_delete_key(self):
        """Test deleting key."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        result = service.delete_key("test_key")
        assert result is True
        assert "AIOPS_TEST_KEY" not in os.environ

    def test_key_exists(self):
        """Test checking if key exists."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        try:
            assert service.key_exists("test_key") is True
            assert service.key_exists("nonexistent_key") is False
        finally:
            del os.environ["AIOPS_TEST_KEY"]

    def test_get_jwt_secret_key(self):
        """Test getting JWT secret key."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_JWT_SECRET_KEY"] = "jwt_secret"
        try:
            key = service.get_jwt_secret_key()
            assert key == "jwt_secret"
        finally:
            del os.environ["AIOPS_JWT_SECRET_KEY"]

    def test_get_jwt_secret_key_required(self):
        """Test getting required JWT secret key raises error."""
        service = KeyManagementService(backend_type="environment")
        with pytest.raises(ValueError, match="Required key 'JWT_SECRET_KEY' not found"):
            service.get_jwt_secret_key(required=True)

    def test_get_database_password(self):
        """Test getting database password."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_DATABASE_PASSWORD"] = "db_password"
        try:
            password = service.get_database_password()
            assert password == "db_password"
        finally:
            del os.environ["AIOPS_DATABASE_PASSWORD"]

    def test_get_api_key(self):
        """Test getting API key."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_SERVICE_API_KEY"] = "api_key"
        try:
            key = service.get_api_key("service")
            assert key == "api_key"
        finally:
            del os.environ["AIOPS_SERVICE_API_KEY"]


class TestKeyCaching:
    """Test key caching functionality."""

    def test_cache_key(self):
        """Test caching a key."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        service._cache_key("test_key", "test_value")
        assert "test_key" in service._cache
        assert service._cache["test_key"]["value"] == "test_value"

    def test_get_cached_key(self):
        """Test getting cached key."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        service._cache_key("test_key", "test_value")
        value = service._get_cached_key("test_key")
        assert value == "test_value"

    def test_cached_key_expiration(self):
        """Test cached key expiration."""
        service = KeyManagementService(backend_type="environment", cache_ttl=1)
        
        service._cache_key("test_key", "test_value")
        
        # Wait for cache to expire
        import time
        time.sleep(2)
        
        value = service._get_cached_key("test_key")
        assert value is None
        assert "test_key" not in service._cache

    def test_get_key_with_cache(self):
        """Test getting key with caching enabled."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        try:
            # First call should cache the key
            value1 = service.get_key_with_cache("test_key", use_cache=True)
            assert value1 == "test_value"
            assert "test_key" in service._cache
            
            # Second call should return cached value
            value2 = service.get_key_with_cache("test_key", use_cache=True)
            assert value2 == "test_value"
        finally:
            del os.environ["AIOPS_TEST_KEY"]

    def test_get_key_without_cache(self):
        """Test getting key without caching."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        try:
            value = service.get_key_with_cache("test_key", use_cache=False)
            assert value == "test_value"
            assert "test_key" not in service._cache
        finally:
            del os.environ["AIOPS_TEST_KEY"]

    def test_clear_cache(self):
        """Test clearing cache."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        service._cache_key("test_key", "test_value")
        service.clear_cache()
        assert len(service._cache) == 0

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        service._cache_key("test_key", "test_value")
        stats = service.get_cache_stats()
        
        assert stats["cached_keys"] == 1
        assert stats["cache_ttl"] == 60
        assert "test_key" in stats["cached_key_names"]


class TestKeyRotation:
    """Test key rotation functionality."""

    def test_rotate_key(self):
        """Test rotating a key."""
        service = KeyManagementService(backend_type="environment")
        
        os.environ["AIOPS_TEST_KEY"] = "old_value"
        try:
            result = service.rotate_key("test_key", "new_value")
            assert result is True
            assert os.environ["AIOPS_TEST_KEY"] == "new_value"
            
            # Old key should be stored with timestamp
            old_key_found = any(
                key.startswith("AIOPS_TEST_KEY_OLD_") for key in os.environ.keys()
            )
            assert old_key_found is True
        finally:
            # Cleanup
            for key in list(os.environ.keys()):
                if key.startswith("AIOPS_TEST_KEY"):
                    del os.environ[key]

    def test_rotate_key_without_existing_value(self):
        """Test rotating a key that doesn't exist."""
        service = KeyManagementService(backend_type="environment")
        
        result = service.rotate_key("test_key", "new_value")
        assert result is True
        assert os.environ["AIOPS_TEST_KEY"] == "new_value"
        
        # Cleanup
        del os.environ["AIOPS_TEST_KEY"]

    def test_rotate_key_clears_cache(self):
        """Test that key rotation clears cache."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        os.environ["AIOPS_TEST_KEY"] = "old_value"
        try:
            # Cache the key
            service._cache_key("test_key", "old_value")
            assert "test_key" in service._cache
            
            # Rotate the key
            service.rotate_key("test_key", "new_value")
            
            # Cache should be cleared
            assert "test_key" not in service._cache
        finally:
            # Cleanup
            for key in list(os.environ.keys()):
                if key.startswith("AIOPS_TEST_KEY"):
                    del os.environ[key]

    def test_cleanup_old_keys(self):
        """Test cleaning up expired old keys."""
        service = KeyManagementService(backend_type="environment")
        
        # Set up old key with expired timestamp
        old_key_name = "test_key_old_1234567890"
        service._rotation_schedule[old_key_name] = datetime.now() - timedelta(seconds=1)
        
        os.environ[f"AIOPS_{old_key_name}"] = "old_value"
        
        try:
            cleaned_count = service.cleanup_old_keys()
            assert cleaned_count >= 0
            assert old_key_name not in service._rotation_schedule
        finally:
            # Cleanup
            for key in list(os.environ.keys()):
                if key.startswith("AIOPS_TEST_KEY"):
                    del os.environ[key]

    def test_cleanup_old_keys_not_expired(self):
        """Test that non-expired keys are not cleaned up."""
        service = KeyManagementService(backend_type="environment")
        
        # Set up old key with future timestamp
        old_key_name = "test_key_old_1234567890"
        service._rotation_schedule[old_key_name] = datetime.now() + timedelta(days=1)
        
        cleaned_count = service.cleanup_old_keys()
        assert cleaned_count == 0
        assert old_key_name in service._rotation_schedule


class TestGlobalKeyService:
    """Test global key service instance."""

    def test_get_key_service_singleton(self):
        """Test that get_key_service returns singleton instance."""
        service1 = get_key_service()
        service2 = get_key_service()
        assert service1 is service2

    def test_initialize_key_management(self):
        """Test initializing global key service."""
        initialize_key_management(backend_type="environment")
        service = get_key_service()
        assert service is not None
        assert isinstance(service.backend, EnvironmentKeyBackend)

    def test_initialize_with_different_backend(self):
        """Test initializing with different backend type."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            initialize_key_management(backend_type="file", file_path=temp_path)
            service = get_key_service()
            assert isinstance(service.backend, FileKeyBackend)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestKeyBackendAbstract:
    """Test that KeyBackend is abstract."""

    def test_key_backend_is_abstract(self):
        """Test that KeyBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            KeyBackend()


class TestKeyManagementServiceIntegration:
    """Integration tests for key management service."""

    def test_full_key_lifecycle(self):
        """Test full key lifecycle: create, read, update, delete."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            service = KeyManagementService(backend_type="file", file_path=temp_path)
            
            # Create
            service.set_key("test_key", "initial_value")
            assert service.get_key("test_key") == "initial_value"
            
            # Read
            value = service.get_key("test_key")
            assert value == "initial_value"
            
            # Update
            service.set_key("test_key", "updated_value")
            assert service.get_key("test_key") == "updated_value"
            
            # Delete
            service.delete_key("test_key")
            assert service.get_key("test_key") is None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_key_rotation_with_grace_period(self):
        """Test key rotation with grace period for old key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            service = KeyManagementService(backend_type="file", file_path=temp_path)
            
            # Set initial key
            service.set_key("test_key", "old_value")
            
            # Rotate with 1 second grace period
            service.rotate_key("test_key", "new_value", old_value_retention=1)
            
            # New value should be active
            assert service.get_key("test_key") == "new_value"
            
            # Old key should still exist
            old_key_found = any(
                key.startswith("test_key_old_") for key in service.backend._keys.keys()
            )
            assert old_key_found is True
            
            # Wait for grace period to expire
            import time
            time.sleep(2)
            
            # Clean up expired keys
            service.cleanup_old_keys()
            
            # Old key should be gone
            old_key_found = any(
                key.startswith("test_key_old_") for key in service.backend._keys.keys()
            )
            assert old_key_found is False
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_concurrent_key_access(self):
        """Test concurrent key access with caching."""
        service = KeyManagementService(backend_type="environment", cache_ttl=60)
        
        os.environ["AIOPS_TEST_KEY"] = "test_value"
        try:
            # Multiple concurrent accesses should work
            values = []
            for _ in range(10):
                value = service.get_key_with_cache("test_key", use_cache=True)
                values.append(value)
            
            # All values should be the same
            assert all(v == "test_value" for v in values)
            
            # Key should be cached
            assert "test_key" in service._cache
        finally:
            del os.environ["AIOPS_TEST_KEY"]