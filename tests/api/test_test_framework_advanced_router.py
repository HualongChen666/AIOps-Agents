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

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.test_framework_advanced_router import (
    router,
    TestFrameworkConfig,
    TestFrameworkConfigUpdate,
    FrameworkType,
    ParallelMode,
    FAKE_ADMIN,
    get_current_user,
    _framework_configs,
    _init_framework_configs,
)
from core.authentication import UserInDB


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

    @pytest.mark.asyncio
    async def test_get_framework_configurations_success(self, mock_admin_user, clear_data):
        """Test successful framework configurations retrieval"""
        _init_framework_configs()
        result = await router.get_framework_configurations(current_user=mock_admin_user)
        
        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_get_framework_configurations_with_framework_filter(self, mock_admin_user, clear_data):
        """Test framework configurations retrieval with framework filter"""
        _init_framework_configs()
        result = await router.get_framework_configurations(
            framework=FrameworkType.PYTEST, current_user=mock_admin_user
        )
        
        assert isinstance(result, list)
        assert all(c.framework == FrameworkType.PYTEST for c in result)

    @pytest.mark.asyncio
    async def test_get_framework_configurations_enabled_only(self, mock_admin_user, clear_data):
        """Test framework configurations retrieval with enabled only filter"""
        _init_framework_configs()
        result = await router.get_framework_configurations(
            enabled_only=True, current_user=mock_admin_user
        )
        
        assert isinstance(result, list)
        assert all(c.enabled for c in result)

    @pytest.mark.asyncio
    async def test_get_framework_configurations_combined_filters(self, mock_admin_user, clear_data):
        """Test framework configurations retrieval with combined filters"""
        _init_framework_configs()
        result = await router.get_framework_configurations(
            framework=FrameworkType.PYTEST,
            enabled_only=True,
            current_user=mock_admin_user
        )
        
        assert isinstance(result, list)
        assert all(c.framework == FrameworkType.PYTEST and c.enabled for c in result)

    @pytest.mark.asyncio
    async def test_get_framework_configuration_success(self, mock_admin_user, sample_config, clear_data):
        """Test successful framework configuration retrieval"""
        result = await router.get_framework_configuration(
            sample_config.id, current_user=mock_admin_user
        )
        
        assert isinstance(result, TestFrameworkConfig)
        assert result.id == sample_config.id

    @pytest.mark.asyncio
    async def test_get_framework_configuration_not_found(self, mock_admin_user, clear_data):
        """Test framework configuration retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_framework_configuration("nonexistent", current_user=mock_admin_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Configuration not found"

    @pytest.mark.asyncio
    async def test_update_framework_configuration_success(self, mock_admin_user, sample_config, clear_data):
        """Test successful framework configuration update"""
        config_update = TestFrameworkConfigUpdate(
            enabled=False,
            parallel_workers=8
        )
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        result = await router.update_framework_configuration(
            sample_config.id, config_update, request, current_user=mock_admin_user
        )
        
        assert isinstance(result, TestFrameworkConfig)
        assert result.enabled == False
        assert result.parallel_workers == 8

    @pytest.mark.asyncio
    async def test_update_framework_configuration_forbidden(self, mock_regular_user, sample_config, clear_data):
        """Test framework configuration update without admin role"""
        config_update = TestFrameworkConfigUpdate(enabled=False)
        
        from fastapi import Request
        request = Mock(spec=Request)
        
        with pytest.raises(HTTPException) as exc_info:
            await router.update_framework_configuration(
                sample_config.id, config_update, request, current_user=mock_regular_user
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_update_framework_configuration_not_found(self, mock_admin_user, clear_data):
        """Test framework configuration update when not found"""
        config_update = TestFrameworkConfigUpdate(enabled=False)
        
        from fastapi import Request
        request = Mock(spec=Request)
        
        with pytest.raises(HTTPException) as exc_info:
            await router.update_framework_configuration(
                "nonexistent", config_update, request, current_user=mock_admin_user
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Configuration not found"

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_parallel_workers_min(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with parallel workers below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(parallel_workers=0)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_parallel_workers_max(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with parallel workers above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(parallel_workers=33)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_timeout_min(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with timeout below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(timeout=0)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_timeout_max(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with timeout above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(timeout=3601)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_retry_count_min(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with retry count below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(retry_count=-1)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_retry_count_max(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with retry count above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(retry_count=6)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_coverage_threshold_min(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with coverage threshold below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(coverage_threshold=-1)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_validation_coverage_threshold_max(self, mock_admin_user, sample_config, clear_data):
        """Test framework configuration update with coverage threshold above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            TestFrameworkConfigUpdate(coverage_threshold=101)

    @pytest.mark.asyncio
    async def test_update_framework_configuration_partial(self, mock_admin_user, sample_config, clear_data):
        """Test partial framework configuration update"""
        config_update = TestFrameworkConfigUpdate(enabled=False)
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        result = await router.update_framework_configuration(
            sample_config.id, config_update, request, current_user=mock_admin_user
        )
        
        assert result.enabled == False
        assert result.parallel_workers == sample_config.parallel_workers  # Should remain unchanged


# ============ Validation Endpoints Tests ============

class TestValidationEndpoints:
    """Test validation endpoints"""

    @pytest.mark.asyncio
    async def test_validate_framework_configuration_success(self, mock_admin_user, sample_config, clear_data):
        """Test successful framework configuration validation"""
        result = await router.validate_framework_configuration(
            sample_config.id, current_user=mock_admin_user
        )
        
        assert isinstance(result, dict)
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert "config_id" in result
        assert "framework" in result

    @pytest.mark.asyncio
    async def test_validate_framework_configuration_not_found(self, mock_admin_user, clear_data):
        """Test framework configuration validation when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.validate_framework_configuration("nonexistent", current_user=mock_admin_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Configuration not found"

    @pytest.mark.asyncio
    async def test_validate_framework_configuration_no_test_paths(self, mock_admin_user, clear_data):
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
        
        result = await router.validate_framework_configuration(
            config_id, current_user=mock_admin_user
        )
        
        assert result["valid"] == True
        assert len(result["warnings"]) > 0
        assert any("test paths" in w.lower() for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_validate_framework_configuration_low_coverage_threshold(self, mock_admin_user, clear_data):
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
        
        result = await router.validate_framework_configuration(
            config_id, current_user=mock_admin_user
        )
        
        assert result["valid"] == True
        assert len(result["warnings"]) > 0
        assert any("coverage" in w.lower() for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_validate_framework_configuration_invalid_parallel(self, mock_admin_user, clear_data):
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
        
        result = await router.validate_framework_configuration(
            config_id, current_user=mock_admin_user
        )
        
        assert result["valid"] == False
        assert len(result["errors"]) > 0
        assert any("parallel" in e.lower() for e in result["errors"])


# ============ Status Endpoints Tests ============

class TestStatusEndpoints:
    """Test status endpoints"""

    @pytest.mark.asyncio
    async def test_get_framework_status_success(self, mock_admin_user, clear_data):
        """Test successful framework status retrieval"""
        _init_framework_configs()
        result = await router.get_framework_status(current_user=mock_admin_user)
        
        assert isinstance(result, dict)
        assert "total_frameworks" in result
        assert "enabled_frameworks" in result
        assert "frameworks" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_framework_status_empty(self, mock_admin_user, clear_data):
        """Test framework status retrieval when no configs exist"""
        result = await router.get_framework_status(current_user=mock_admin_user)
        
        assert isinstance(result, dict)
        assert result["total_frameworks"] == 0
        assert result["enabled_frameworks"] == 0
        assert len(result["frameworks"]) == 0

    @pytest.mark.asyncio
    async def test_get_framework_status_with_configs(self, mock_admin_user, clear_data):
        """Test framework status retrieval with configs"""
        _init_framework_configs()
        result = await router.get_framework_status(current_user=mock_admin_user)
        
        assert result["total_frameworks"] >= 2
        assert result["enabled_frameworks"] >= 2
        assert len(result["frameworks"]) >= 2


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
        with patch('api.test_framework_advanced_router.verify_token', return_value=None):
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

    @pytest.mark.asyncio
    async def test_full_config_workflow(self, mock_admin_user, clear_data):
        """Test complete config workflow"""
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        # Get configs
        _init_framework_configs()
        configs = await router.get_framework_configurations(current_user=mock_admin_user)
        assert len(configs) >= 2
        
        # Get specific config
        config = configs[0]
        retrieved = await router.get_framework_configuration(
            config.id, current_user=mock_admin_user
        )
        assert retrieved.id == config.id
        
        # Validate config
        validation = await router.validate_framework_configuration(
            config.id, current_user=mock_admin_user
        )
        assert "valid" in validation
        
        # Update config
        update = TestFrameworkConfigUpdate(enabled=False)
        updated = await router.update_framework_configuration(
            config.id, update, request, current_user=mock_admin_user
        )
        assert updated.enabled == False
        
        # Get status
        status = await router.get_framework_status(current_user=mock_admin_user)
        assert status["total_frameworks"] >= 2

    @pytest.mark.asyncio
    async def test_config_validation_workflow(self, mock_admin_user, clear_data):
        """Test config validation workflow"""
        _init_framework_configs()
        config = list(_framework_configs.values())[0]
        
        # Validate config
        validation = await router.validate_framework_configuration(
            config.id, current_user=mock_admin_user
        )
        
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

    @pytest.mark.asyncio
    async def test_concurrent_config_updates(self, mock_admin_user, clear_data):
        """Test concurrent config updates"""
        import asyncio
        
        _init_framework_configs()
        config = list(_framework_configs.values())[0]
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        async def update_config():
            update = TestFrameworkConfigUpdate(
                enabled=asyncio.current_task().get_name() == "task-0"
            )
            await router.update_framework_configuration(
                config.id, update, request, current_user=mock_admin_user
            )
        
        # Run multiple concurrent updates
        await asyncio.gather(*[update_config() for _ in range(5)])
        
        # Should not raise errors
        retrieved = await router.get_framework_configuration(
            config.id, current_user=mock_admin_user
        )
        assert retrieved.id == config.id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
