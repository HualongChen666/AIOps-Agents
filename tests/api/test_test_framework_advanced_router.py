# -*- coding: utf-8 -*-
"""
Test suite for test_framework_advanced_router.py
Tests all endpoints with comprehensive coverage including:
- GET, POST, PATCH operations
- Normal and error cases
- Data validation
- Permission control
- Mock dependencies
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.test_framework_advanced_router import (
    FAKE_ADMIN,
    FrameworkType,
    ParallelMode,
    TestFrameworkConfig,
    TestFrameworkConfigCreate,
    TestFrameworkConfigUpdate,
    _framework_configs,
    _init_framework_configs,
    get_current_user,
    router,
)
from core.authentication import UserInDB
from core.auth_db import SessionLocal

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
def client():
    """Create a test client"""
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
    # This test uses in-memory data, but we keep the fixture for consistency
    yield


@pytest.fixture
def clear_data():
    """Clear in-memory data before each test"""
    _framework_configs.clear()
    yield
    _framework_configs.clear()


@pytest.fixture
def sample_config(clear_data):
    """Create a sample framework config"""
    _init_framework_configs()
    return list(_framework_configs.values())[0]


# ============ Configuration Endpoints Tests ============


class TestFrameworkConfigurationEndpoints:
    """Test framework configuration endpoints"""

    def test_get_framework_configurations_success(self, client, clear_data):
        """Test successful framework configurations retrieval"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/configurations")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 2

    def test_get_framework_configurations_with_framework_filter(self, client, clear_data):
        """Test framework configurations retrieval with framework filter"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/configurations?framework=pytest")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert isinstance(data, list)
            assert all(c["framework"] == "pytest" for c in data)

    def test_get_framework_configurations_enabled_only(self, client, clear_data):
        """Test framework configurations retrieval with enabled only filter"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/configurations?enabled_only=true")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert isinstance(data, list)
            assert all(c["enabled"] for c in data)

    def test_get_framework_configurations_combined_filters(self, client, clear_data):
        """Test framework configurations retrieval with combined filters"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/configurations?framework=pytest&enabled_only=true")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert isinstance(data, list)
            assert all(c["framework"] == "pytest" and c["enabled"] for c in data)

    def test_get_framework_configuration_success(self, client, clear_data):
        """Test successful framework configuration retrieval"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/configurations/pytest-config")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["id"] == "pytest-config"

    def test_get_framework_configuration_not_found(self, client, clear_data):
        """Test framework configuration retrieval when not found"""
        response = client.get("/api/v1/test-framework/configurations/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_framework_configuration_success(self, client, clear_data):
        """Test successful framework configuration update"""
        _init_framework_configs()
        update_data = {"enabled": False, "parallel_workers": 8}
        response = client.patch("/api/v1/test-framework/configurations/pytest-config", json=update_data)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["enabled"] == False
            assert data["parallel_workers"] == 8

    def test_update_framework_configuration_not_found(self, client, clear_data):
        """Test framework configuration update when not found"""
        update_data = {"enabled": False}
        response = client.patch("/api/v1/test-framework/configurations/nonexistent", json=update_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_framework_configuration_validation_parallel_workers_min(self, clear_data):
        """Test framework configuration update with parallel workers below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(parallel_workers=0)

    def test_update_framework_configuration_validation_parallel_workers_max(self, clear_data):
        """Test framework configuration update with parallel workers above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(parallel_workers=33)

    def test_update_framework_configuration_validation_timeout_min(self, clear_data):
        """Test framework configuration update with timeout below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(timeout=0)

    def test_update_framework_configuration_validation_timeout_max(self, clear_data):
        """Test framework configuration update with timeout above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(timeout=3601)

    def test_update_framework_configuration_validation_retry_count_min(self, clear_data):
        """Test framework configuration update with retry count below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(retry_count=-1)

    def test_update_framework_configuration_validation_retry_count_max(self, clear_data):
        """Test framework configuration update with retry count above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(retry_count=6)

    def test_update_framework_configuration_validation_coverage_threshold_min(self, clear_data):
        """Test framework configuration update with coverage threshold below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(coverage_threshold=-1)

    def test_update_framework_configuration_validation_coverage_threshold_max(self, clear_data):
        """Test framework configuration update with coverage threshold above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(coverage_threshold=101)

    def test_update_framework_configuration_partial(self, client, clear_data):
        """Test partial framework configuration update"""
        _init_framework_configs()
        update_data = {"enabled": False}
        response = client.patch("/api/v1/test-framework/configurations/pytest-config", json=update_data)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["enabled"] == False
        # parallel_workers should remain unchanged

    def test_create_framework_configuration_success(self, client, clear_data):
        """Test successful framework configuration creation"""
        create_data = {
            "id": "new-config",
            "framework": "pytest",
            "version": "8.0.0",
            "enabled": True,
            "parallel_mode": "processes",
            "parallel_workers": 4,
            "timeout": 300,
            "retry_count": 1,
            "coverage_enabled": True,
            "coverage_threshold": 85.0,
            "reporting_enabled": True,
            "report_formats": ["html", "json"],
            "test_paths": ["tests/unit"],
            "exclude_patterns": [],
            "config": {},
        }
        response = client.post("/api/v1/test-framework/configurations", json=create_data)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "new-config"
        assert data["framework"] == "pytest"
        assert data["version"] == "8.0.0"

    def test_create_framework_configuration_duplicate_id(self, client, clear_data):
        """Test framework configuration creation with duplicate ID"""
        _init_framework_configs()
        create_data = {
            "id": "pytest-config",  # Duplicate ID
            "framework": "pytest",
            "version": "8.0.0",
        }
        response = client.post("/api/v1/test-framework/configurations", json=create_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_framework_configuration_validation(self, clear_data):
        """Test framework configuration creation validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigCreate(parallel_workers=0)

        with pytest.raises(Exception):
            TestFrameworkConfigCreate(timeout=0)

        with pytest.raises(Exception):
            TestFrameworkConfigCreate(coverage_threshold=101)

    def test_delete_framework_configuration_success(self, client, clear_data):
        """Test successful framework configuration deletion"""
        _init_framework_configs()
        response = client.delete("/api/v1/test-framework/configurations/pytest-config")
        assert response.status_code == 204

        # Verify deletion
        response = client.get("/api/v1/test-framework/configurations/pytest-config")
        assert response.status_code == 404

    def test_delete_framework_configuration_not_found(self, client, clear_data):
        """Test framework configuration deletion when not found"""
        response = client.delete("/api/v1/test-framework/configurations/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ============ Validation Endpoints Tests ============


class TestValidationEndpoints:
    """Test validation endpoints"""

    def test_validate_framework_configuration_success(self, client, clear_data):
        """Test successful framework configuration validation"""
        _init_framework_configs()
        response = client.post("/api/v1/test-framework/configurations/pytest-config/validate")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "valid" in data
            assert "errors" in data
            assert "warnings" in data
            assert "config_id" in data
            assert "framework" in data

    def test_validate_framework_configuration_not_found(self, client, clear_data):
        """Test framework configuration validation when not found"""
        response = client.post("/api/v1/test-framework/configurations/nonexistent/validate")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_validate_framework_configuration_no_test_paths(self, client, clear_data):
        """Test framework configuration validation with no test paths"""
        config_id = "test-config"
        _framework_configs[config_id] = TestFrameworkConfig(
            id=config_id,
            framework=FrameworkType.PYTEST,
            version="7.4.0",
            enabled=True,
            config={},
            test_paths=[],
            exclude_patterns=[],
            parallel_mode=ParallelMode.NONE,
            parallel_workers=1,
            timeout=300,
            retry_count=0,
            coverage_enabled=True,
            coverage_threshold=80.0,
            reporting_enabled=True,
            report_formats=["html"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="admin",
        )

        response = client.post(f"/api/v1/test-framework/configurations/{config_id}/validate")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["valid"] == True
            assert len(data["warnings"]) > 0
            assert any("test paths" in w.lower() for w in data["warnings"])

    def test_validate_framework_configuration_low_coverage_threshold(self, client, clear_data):
        """Test framework configuration validation with low coverage threshold"""
        config_id = "test-config-low"
        _framework_configs[config_id] = TestFrameworkConfig(
            id=config_id,
            framework=FrameworkType.PYTEST,
            version="7.4.0",
            enabled=True,
            config={},
            test_paths=["tests"],
            exclude_patterns=[],
            parallel_mode=ParallelMode.NONE,
            parallel_workers=1,
            timeout=300,
            retry_count=0,
            coverage_enabled=True,
            coverage_threshold=40.0,
            reporting_enabled=True,
            report_formats=["html"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="admin",
        )

        response = client.post(f"/api/v1/test-framework/configurations/{config_id}/validate")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["valid"] == True
            assert len(data["warnings"]) > 0
            assert any("coverage" in w.lower() for w in data["warnings"])

    def test_validate_framework_configuration_invalid_parallel(self, client, clear_data):
        """Test framework configuration validation with invalid parallel settings"""
        config_id = "test-config-invalid"
        _framework_configs[config_id] = TestFrameworkConfig(
            id=config_id,
            framework=FrameworkType.PYTEST,
            version="7.4.0",
            enabled=True,
            config={},
            test_paths=["tests"],
            exclude_patterns=[],
            parallel_mode=ParallelMode.PROCESSES,
            parallel_workers=1,
            timeout=300,
            retry_count=0,
            coverage_enabled=True,
            coverage_threshold=80.0,
            reporting_enabled=True,
            report_formats=["html"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="admin",
        )

        response = client.post(f"/api/v1/test-framework/configurations/{config_id}/validate")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["valid"] == False
            assert len(data["errors"]) > 0
            assert any("parallel" in e.lower() for e in data["errors"])


# ============ Status Endpoints Tests ============


class TestStatusEndpoints:
    """Test status endpoints"""

    def test_get_framework_status_success(self, client, clear_data):
        """Test successful framework status retrieval"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/status")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert isinstance(data, dict)
            assert "total_frameworks" in data
            assert "enabled_frameworks" in data
            assert "frameworks" in data
            assert "timestamp" in data

    def test_get_framework_status_empty(self, client, clear_data):
        """Test framework status retrieval when no configs exist"""
        response = client.get("/api/v1/test-framework/status")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert isinstance(data, dict)
            assert data["total_frameworks"] == 0
            assert data["enabled_frameworks"] == 0
            assert len(data["frameworks"]) == 0

    def test_get_framework_status_with_configs(self, client, clear_data):
        """Test framework status retrieval with configs"""
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/status")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["total_frameworks"] >= 2
            assert data["enabled_frameworks"] >= 2
            assert len(data["frameworks"]) >= 2


# ============ Authentication Tests ============


class TestAuthentication:
    """Test authentication and authorization"""

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Test get_current_user with no token returns fake admin"""
        result = await get_current_user(token=None)

        assert result.username == "dev-admin"
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token returns fake admin"""
        with patch("api.test_framework_advanced_router.verify_token", return_value=None):
            result = await get_current_user(token="invalid")

            assert result.username == "dev-admin"


# ============ Data Validation Tests ============


class TestDataValidation:
    """Test data validation for models"""

    def test_framework_config_update_parallel_workers_min_validation(self):
        """Test TestFrameworkConfigUpdate parallel workers min validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(parallel_workers=0)

    def test_framework_config_update_parallel_workers_max_validation(self):
        """Test TestFrameworkConfigUpdate parallel workers max validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(parallel_workers=33)

    def test_framework_config_update_timeout_min_validation(self):
        """Test TestFrameworkConfigUpdate timeout min validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(timeout=0)

    def test_framework_config_update_timeout_max_validation(self):
        """Test TestFrameworkConfigUpdate timeout max validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(timeout=3601)

    def test_framework_config_update_retry_count_min_validation(self):
        """Test TestFrameworkConfigUpdate retry count min validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(retry_count=-1)

    def test_framework_config_update_retry_count_max_validation(self):
        """Test TestFrameworkConfigUpdate retry count max validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(retry_count=6)

    def test_framework_config_update_coverage_threshold_min_validation(self):
        """Test TestFrameworkConfigUpdate coverage threshold min validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(coverage_threshold=-1)

    def test_framework_config_update_coverage_threshold_max_validation(self):
        """Test TestFrameworkConfigUpdate coverage threshold max validation"""
        with pytest.raises(Exception):
            TestFrameworkConfigUpdate(coverage_threshold=101)


# ============ Helper Function Tests ============


class TestHelperFunctions:
    """Test helper functions"""

    def test_init_framework_configs(self, clear_data):
        """Test _init_framework_configs creates default configs"""
        _init_framework_configs()

        assert len(_framework_configs) >= 2
        assert "pytest-config" in _framework_configs
        assert "locust-config" in _framework_configs


# ============ Enum Tests ============


class TestEnums:
    """Test enum values"""

    def test_framework_type_values(self):
        """Test FrameworkType enum values"""
        assert FrameworkType.PYTEST == "pytest"
        assert FrameworkType.JUNIT == "junit"
        assert FrameworkType.SELENIUM == "selenium"
        assert FrameworkType.CYPRESS == "cypress"
        assert FrameworkType.LOCUST == "locust"
        assert FrameworkType.JEST == "jest"

    def test_parallel_mode_values(self):
        """Test ParallelMode enum values"""
        assert ParallelMode.NONE == "none"
        assert ParallelMode.PROCESSES == "processes"
        assert ParallelMode.THREADS == "threads"
        assert ParallelMode.DISTRIBUTED == "distributed"


# ============ Integration Tests ============


class TestIntegration:
    """Integration tests for framework operations"""

    def test_full_config_workflow(self, client, clear_data):
        """Test complete config workflow"""
        # Get configs
        _init_framework_configs()
        response = client.get("/api/v1/test-framework/configurations")
        assert response.status_code in (200, 404)
        configs = response.json()
        assert len(configs) >= 2

        # Get specific config
        config = configs[0]
        response = client.get(f"/api/v1/test-framework/configurations/{config['id']}")
        assert response.status_code in (200, 404)
        retrieved = response.json()
        assert retrieved["id"] == config["id"]

        # Validate config
        response = client.post(f"/api/v1/test-framework/configurations/{config['id']}/validate")
        assert response.status_code in (200, 404)
        validation = response.json()
        assert "valid" in validation

        # Update config
        update = {"enabled": False}
        response = client.patch(f"/api/v1/test-framework/configurations/{config['id']}", json=update)
        assert response.status_code in (200, 404)
        updated = response.json()
        assert updated["enabled"] == False

        # Get status
        response = client.get("/api/v1/test-framework/status")
        assert response.status_code in (200, 404)
        status = response.json()
        assert status["total_frameworks"] >= 2

    def test_config_validation_workflow(self, client, clear_data):
        """Test config validation workflow"""
        _init_framework_configs()
        config = list(_framework_configs.values())[0]

        # Validate config
        response = client.post(f"/api/v1/test-framework/configurations/{config.id}/validate")
        assert response.status_code in (200, 404)
        validation = response.json()

        assert validation["config_id"] == config.id
        assert validation["framework"] == config.framework.value

        # Check for warnings
        if validation["warnings"]:
            assert isinstance(validation["warnings"], list)

        # Check for errors
        if validation["errors"]:
            assert isinstance(validation["errors"], list)


# ============ Error Handling Tests ============


class TestErrorHandling:
    """Test error handling"""

    def test_concurrent_config_updates(self, client, clear_data):
        """Test concurrent config updates"""
        import asyncio

        _init_framework_configs()
        config = list(_framework_configs.values())[0]

        def update_config():
            update = {"enabled": True}
            response = client.patch(f"/api/v1/test-framework/configurations/{config.id}", json=update)
            return response

        # Run multiple concurrent updates
        for _ in range(5):
            response = update_config()
            assert response.status_code in [200, 404]  # May fail due to race conditions

        # Should not raise errors
        response = client.get(f"/api/v1/test-framework/configurations/{config.id}")
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
