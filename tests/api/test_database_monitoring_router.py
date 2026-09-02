# -*- coding: utf-8 -*-
"""
Integration tests for Database Monitoring Router
Tests API endpoints for database monitoring configuration
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import status
from fastapi.testclient import TestClient

from api.database_monitoring_router import router


# ============================================================================
# Test Client Setup
# ============================================================================

@pytest.fixture
def client():
    """Create test client"""
    from main import app
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.role = "admin"
    return user


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    return session


# ============================================================================
# Config Endpoint Tests
# ============================================================================

class TestGetMonitoringConfig:
    """Test GET /api/v1/database-monitoring/config"""

    @pytest.mark.asyncio
    async def test_get_config_success(self, client, mock_user, mock_db_session):
        """Test successful config retrieval"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_config = MagicMock()
                mock_config.enabled = True
                mock_config.collection_interval = 60
                mock_config.retention_days = 30
                mock_config.enable_realtime = True
                mock_config.enable_slow_query_log = True
                mock_config.slow_query_threshold = 1.0
                mock_config.enable_connection_monitoring = True
                mock_config.max_connections_threshold = 100
                mock_config.enable_deadlock_detection = True
                mock_repo.get_config.return_value = mock_config

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    response = client.get("/api/v1/database-monitoring/config")
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["enabled"] is True
                    assert data["collection_interval"] == 60


class TestUpdateMonitoringConfig:
    """Test PUT /api/v1/database-monitoring/config"""

    @pytest.mark.asyncio
    async def test_update_config_success(self, client, mock_user, mock_db_session):
        """Test successful config update"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_config = MagicMock()
                mock_config.enabled = True
                mock_config.collection_interval = 120
                mock_config.retention_days = 60
                mock_config.enable_realtime = True
                mock_config.enable_slow_query_log = True
                mock_config.slow_query_threshold = 1.0
                mock_config.enable_connection_monitoring = True
                mock_config.max_connections_threshold = 100
                mock_config.enable_deadlock_detection = True
                mock_repo.get_config.return_value = mock_config
                mock_repo.update_config.return_value = mock_config

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    with patch('api.database_monitoring_router.require_permission'):
                        payload = {
                            "enabled": True,
                            "collection_interval": 120,
                            "retention_days": 60,
                            "enable_realtime": True,
                            "enable_slow_query_log": True,
                            "slow_query_threshold": 1.0,
                            "enable_connection_monitoring": True,
                            "max_connections_threshold": 100,
                            "enable_deadlock_detection": True
                        }
                        response = client.put("/api/v1/database-monitoring/config", json=payload)
                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["collection_interval"] == 120


# ============================================================================
# Thresholds Endpoint Tests
# ============================================================================

class TestGetMetricThresholds:
    """Test GET /api/v1/database-monitoring/thresholds"""

    @pytest.mark.asyncio
    async def test_get_thresholds_success(self, client, mock_user, mock_db_session):
        """Test successful thresholds retrieval"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_threshold = MagicMock()
                mock_threshold.metric_type = "query_time"
                mock_threshold.warning_threshold = 100.0
                mock_threshold.critical_threshold = 500.0
                mock_threshold.enabled = True
                mock_threshold.description = "Query time threshold"
                mock_repo.get_all_thresholds.return_value = [mock_threshold]

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    response = client.get("/api/v1/database-monitoring/thresholds")
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert "query_time" in data
                    assert data["query_time"]["warning_threshold"] == 100.0


class TestUpdateMetricThreshold:
    """Test PUT /api/v1/database-monitoring/thresholds/{metric_type}"""

    @pytest.mark.asyncio
    async def test_update_threshold_success(self, client, mock_user, mock_db_session):
        """Test successful threshold update"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_threshold = MagicMock()
                mock_threshold.metric_type = "query_time"
                mock_threshold.warning_threshold = 150.0
                mock_threshold.critical_threshold = 600.0
                mock_threshold.enabled = True
                mock_threshold.description = "Updated threshold"
                mock_repo.get_threshold_by_metric_type.return_value = mock_threshold
                mock_repo.update_threshold.return_value = mock_threshold

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    with patch('api.database_monitoring_router.require_permission'):
                        payload = {
                            "metric_type": "query_time",
                            "warning_threshold": 150.0,
                            "critical_threshold": 600.0,
                            "enabled": True,
                            "description": "Updated threshold"
                        }
                        response = client.put("/api/v1/database-monitoring/thresholds/query_time", json=payload)
                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["warning_threshold"] == 150.0


# ============================================================================
# Baselines Endpoint Tests
# ============================================================================

class TestGetPerformanceBaselines:
    """Test GET /api/v1/database-monitoring/baselines"""

    @pytest.mark.asyncio
    async def test_get_baselines_success(self, client, mock_user, mock_db_session):
        """Test successful baselines retrieval"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_repo.get_all_baselines.return_value = []

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    response = client.get("/api/v1/database-monitoring/baselines")
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert isinstance(data, dict)


class TestCreatePerformanceBaseline:
    """Test POST /api/v1/database-monitoring/baselines"""

    @pytest.mark.asyncio
    async def test_create_baseline_success(self, client, mock_user, mock_db_session):
        """Test successful baseline creation"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_baseline = MagicMock()
                mock_baseline.baseline_name = "test_baseline"
                mock_baseline.established_at = "2024-01-01T00:00:00"
                mock_baseline.avg_query_time = 45.0
                mock_baseline.p95_query_time = 120.0
                mock_baseline.p99_query_time = 250.0
                mock_baseline.avg_connection_count = 35.0
                mock_baseline.peak_connection_count = 65
                mock_baseline.cache_hit_ratio = 0.92
                mock_baseline.database_size_mb = 1024.0
                mock_baseline.description = "Test baseline"
                mock_repo.get_baseline_by_name.return_value = None
                mock_repo.create_baseline.return_value = mock_baseline

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    with patch('api.database_monitoring_router.require_permission'):
                        payload = {
                            "baseline_name": "test_baseline",
                            "avg_query_time": 45.0,
                            "p95_query_time": 120.0,
                            "p99_query_time": 250.0,
                            "avg_connection_count": 35.0,
                            "peak_connection_count": 65,
                            "cache_hit_ratio": 0.92,
                            "database_size_mb": 1024.0,
                            "description": "Test baseline"
                        }
                        response = client.post("/api/v1/database-monitoring/baselines", json=payload)
                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["baseline_name"] == "test_baseline"


# ============================================================================
# Alert Rules Endpoint Tests
# ============================================================================

class TestGetAlertRules:
    """Test GET /api/v1/database-monitoring/alert-rules"""

    @pytest.mark.asyncio
    async def test_get_alert_rules_success(self, client, mock_user, mock_db_session):
        """Test successful alert rules retrieval"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_rule = MagicMock()
                mock_rule.rule_id = "test_rule"
                mock_rule.rule_name = "Test Rule"
                mock_rule.metric_type = "query_time"
                mock_rule.condition = "query_time > 500"
                mock_rule.severity = "warning"
                mock_rule.enabled = True
                mock_rule.notification_channels = ["email"]
                mock_rule.cooldown_minutes = 5
                mock_rule.description = "Test rule"
                mock_repo.get_all_alert_rules.return_value = [mock_rule]

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    response = client.get("/api/v1/database-monitoring/alert-rules")
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert "test_rule" in data


class TestCreateAlertRule:
    """Test POST /api/v1/database-monitoring/alert-rules"""

    @pytest.mark.asyncio
    async def test_create_alert_rule_success(self, client, mock_user, mock_db_session):
        """Test successful alert rule creation"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_rule = MagicMock()
                mock_rule.rule_id = "new_rule"
                mock_rule.rule_name = "New Rule"
                mock_rule.metric_type = "query_time"
                mock_rule.condition = "query_time > 500"
                mock_rule.severity = "warning"
                mock_rule.enabled = True
                mock_rule.notification_channels = ["email"]
                mock_rule.cooldown_minutes = 5
                mock_rule.description = "New rule"
                mock_repo.get_alert_rule_by_id.return_value = None
                mock_repo.create_alert_rule.return_value = mock_rule

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    with patch('api.database_monitoring_router.require_permission'):
                        payload = {
                            "rule_id": "new_rule",
                            "rule_name": "New Rule",
                            "metric_type": "query_time",
                            "condition": "query_time > 500",
                            "severity": "warning",
                            "enabled": True,
                            "notification_channels": ["email"],
                            "cooldown_minutes": 5,
                            "description": "New rule"
                        }
                        response = client.post("/api/v1/database-monitoring/alert-rules", json=payload)
                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["rule_id"] == "new_rule"


class TestDeleteAlertRule:
    """Test DELETE /api/v1/database-monitoring/alert-rules/{rule_id}"""

    @pytest.mark.asyncio
    async def test_delete_alert_rule_success(self, client, mock_user, mock_db_session):
        """Test successful alert rule deletion"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_rule = MagicMock()
                mock_repo.get_alert_rule_by_id.return_value = mock_rule
                mock_repo.delete_alert_rule.return_value = True

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    with patch('api.database_monitoring_router.require_permission'):
                        response = client.delete("/api/v1/database-monitoring/alert-rules/test_rule")
                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert "deleted successfully" in data["message"]


# ============================================================================
# Status Endpoint Tests
# ============================================================================

class TestGetMonitoringStatus:
    """Test GET /api/v1/database-monitoring/status"""

    @pytest.mark.asyncio
    async def test_get_status_success(self, client, mock_user, mock_db_session):
        """Test successful status retrieval"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_status = MagicMock()
                mock_status.monitoring_enabled = True
                mock_status.last_collection_time = "2024-01-01T00:00:00"
                mock_status.active_alerts = 0
                mock_status.total_metrics_collected = 1000
                mock_status.database_health = "healthy"
                mock_status.uptime_percentage = 100.0
                mock_repo.get_status.return_value = mock_status
                mock_repo.update_status.return_value = mock_status

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    response = client.get("/api/v1/database-monitoring/status")
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["monitoring_enabled"] is True
                    assert data["database_health"] == "healthy"


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestGetDatabaseHealth:
    """Test GET /api/v1/database-monitoring/health"""

    @pytest.mark.asyncio
    async def test_get_health_success(self, client, mock_user, mock_db_session):
        """Test successful health check"""
        with patch('api.database_monitoring_router.get_current_active_user', return_value=mock_user):
            with patch('api.database_monitoring_router.get_db', return_value=mock_db_session):
                mock_repo = AsyncMock()
                mock_status = MagicMock()
                mock_status.database_health = "healthy"
                mock_status.active_alerts = 0
                mock_repo.get_status.return_value = mock_status

                with patch('api.database_monitoring_router.DatabaseMonitoringRepository', return_value=mock_repo):
                    response = client.get("/api/v1/database-monitoring/health")
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert "metrics" in data
                    assert "alerts" in data
