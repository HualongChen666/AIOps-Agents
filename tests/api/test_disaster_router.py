# -*- coding: utf-8 -*-
"""Comprehensive tests for disaster_router.py to achieve 90%+ coverage."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBackupManagement:
    """Test the backup-management endpoint."""

    def test_backup_management_success(self, client, admin_headers):
        """Test successful backup management overview."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_file = MagicMock()
                    mock_file.is_file.return_value = True
                    mock_file.stat.return_value = MagicMock(st_size=1024 * 1024, st_mtime=1609459200.0)
                    mock_glob.return_value = [mock_file]

                    resp = client.get("/api/disaster/backup-management", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert data["backup_count"] == 1
                    assert "total_size_mb" in data
                    assert "retention_days" in data

    def test_backup_management_no_directory(self, client, admin_headers):
        """Test when backup directory doesn't exist."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                resp = client.get("/api/disaster/backup-management", headers=admin_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["backup_count"] == 0
                assert data["total_size_mb"] == 0
                assert data["last_backup"] is None

    def test_backup_management_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/backup-management")
        assert resp.status_code == 401

    def test_backup_management_exception(self, client, admin_headers):
        """Test backup management with exception."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.side_effect = Exception("Directory error")

            resp = client.get("/api/disaster/backup-management", headers=admin_headers)
            assert resp.status_code == 500


class TestDisasterRecoveryStatus:
    """Test the disaster-recovery endpoint."""

    def test_disaster_recovery_status_success(self, client, admin_headers):
        """Test successful disaster recovery status."""
        with patch("api.disaster_router._get_dr_enabled") as mock_enabled:
            mock_enabled.return_value = True
            with patch("api.disaster_router._get_backup_dir") as mock_dir:
                mock_dir.return_value = Path("/tmp/backups")
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True
                    with patch("pathlib.Path.glob") as mock_glob:
                        mock_glob.return_value = [MagicMock()]

                        resp = client.get("/api/disaster/disaster-recovery", headers=admin_headers)
                        assert resp.status_code == 200
                        data = resp.json()
                        assert data["status"] == "success"
                        assert data["dr_enabled"] is True
                        assert "dr_status" in data

    def test_disaster_recovery_status_unhealthy(self, client, admin_headers):
        """Test disaster recovery status when unhealthy."""
        with patch("api.disaster_router._get_dr_enabled") as mock_enabled:
            mock_enabled.return_value = True
            with patch("api.disaster_router._get_backup_dir") as mock_dir:
                mock_dir.return_value = Path("/tmp/backups")
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = False

                    resp = client.get("/api/disaster/disaster-recovery", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["dr_status"] == "unhealthy"

    def test_disaster_recovery_status_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/disaster-recovery")
        assert resp.status_code == 401


class TestDRScenarios:
    """Test the dr-scenarios endpoint."""

    def test_dr_scenarios_success(self, client, admin_headers):
        """Test successful DR scenarios retrieval."""
        resp = client.get("/api/disaster/dr-scenarios", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "scenarios" in data
        assert len(data["scenarios"]) > 0
        assert "count" in data

    def test_dr_scenarios_structure(self, client, admin_headers):
        """Test DR scenarios structure."""
        resp = client.get("/api/disaster/dr-scenarios", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        scenario = data["scenarios"][0]
        assert "name" in scenario
        assert "description" in scenario
        assert "enabled" in scenario

    def test_dr_scenarios_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/dr-scenarios")
        assert resp.status_code == 401


class TestBackupRecoveryStatus:
    """Test the backup-recovery endpoint."""

    def test_backup_recovery_status_success(self, client, admin_headers):
        """Test successful backup recovery status."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_file = MagicMock()
                    mock_file.suffix = ".sql"
                    mock_glob.return_value = [mock_file]

                    resp = client.get("/api/disaster/backup-recovery", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert "recoverable_backups" in data
                    assert "recovery_status" in data

    def test_backup_recovery_status_no_backups(self, client, admin_headers):
        """Test backup recovery status with no backups."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_glob.return_value = []

                    resp = client.get("/api/disaster/backup-recovery", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["recovery_status"] == "no_backups"

    def test_backup_recovery_status_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/backup-recovery")
        assert resp.status_code == 401


class TestBackupStrategy:
    """Test the backup-strategy endpoint."""

    def test_backup_strategy_success(self, client, admin_headers):
        """Test successful backup strategy retrieval."""
        resp = client.get("/api/disaster/backup-strategy", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "strategy" in data
        strategy = data["strategy"]
        assert "backup_type" in strategy
        assert "schedule" in strategy
        assert "retention_days" in strategy

    def test_backup_strategy_environment_variables(self, client, admin_headers):
        """Test backup strategy uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_BACKUP_TYPE": "incremental",
            "AIOPS_BACKUP_SCHEDULE": "weekly",
            "AIOPS_BACKUP_RETENTION_DAYS": "90",
        }):
            resp = client.get("/api/disaster/backup-strategy", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["strategy"]["backup_type"] == "incremental"
            assert data["strategy"]["schedule"] == "weekly"
            assert data["strategy"]["retention_days"] == 90

    def test_backup_strategy_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/backup-strategy")
        assert resp.status_code == 401


class TestDataBackupStatus:
    """Test the data-backup endpoint."""

    def test_data_backup_status_success(self, client, admin_headers):
        """Test successful data backup status."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_file = MagicMock()
                    mock_file.stat.return_value = MagicMock(st_mtime=1609459200.0)
                    mock_glob.return_value = [mock_file]

                    resp = client.get("/api/disaster/data-backup", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert "database_backups" in data
                    assert "redis_backups" in data
                    assert "config_backups" in data
                    assert "total_backups" in data

    def test_data_backup_status_no_directory(self, client, admin_headers):
        """Test data backup status when directory doesn't exist."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                resp = client.get("/api/disaster/data-backup", headers=admin_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["database_backups"] == 0
                assert data["redis_backups"] == 0
                assert data["config_backups"] == 0

    def test_data_backup_status_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/data-backup")
        assert resp.status_code == 401


class TestDRDrillStatus:
    """Test the dr-drill endpoint."""

    def test_dr_drill_status_success(self, client, admin_headers):
        """Test successful DR drill status."""
        with patch("core.disaster_recovery_drill.disaster_recovery_drill") as mock_drill:
            mock_result = MagicMock()
            mock_result.scenario.value = "database_failover"
            mock_result.status.value = "completed"
            mock_result.success = True
            mock_result.duration_seconds = 120
            mock_result.start_time.isoformat.return_value = "2026-07-02T10:30:00Z"
            mock_result.end_time.isoformat.return_value = "2026-07-02T10:32:00Z"
            mock_drill.get_drill_history.return_value = [mock_result]

            resp = client.get("/api/disaster/dr-drill", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "last_drill" in data
            assert "drill_count" in data

    def test_dr_drill_status_no_history(self, client, admin_headers):
        """Test DR drill status with no history."""
        with patch("core.disaster_recovery_drill.disaster_recovery_drill") as mock_drill:
            mock_drill.get_drill_history.return_value = []

            resp = client.get("/api/disaster/dr-drill", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["drill_count"] == 0
            assert data["last_drill"] is None

    def test_dr_drill_status_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/dr-drill")
        assert resp.status_code == 401


class TestDRTestingResults:
    """Test the dr-testing endpoint."""

    def test_dr_testing_results_success(self, client, admin_headers):
        """Test successful DR testing results."""
        with patch("core.disaster_recovery_drill.disaster_recovery_drill") as mock_drill:
            mock_result = MagicMock()
            mock_result.scenario.value = "database_failover"
            mock_result.success = True
            mock_result.status.value = "completed"
            mock_result.duration_seconds = 120
            mock_result.start_time.isoformat.return_value = "2026-07-02T10:30:00Z"
            mock_drill.get_drill_history.return_value = [mock_result]
            mock_drill.get_drill_stats.return_value = {
                "total_drills": 10,
                "successful_drills": 9,
                "success_rate": 90.0,
            }

            resp = client.get("/api/disaster/dr-testing", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "test_results" in data
            assert "success_rate" in data
            assert data["success_rate"] == 90.0

    def test_dr_testing_results_empty(self, client, admin_headers):
        """Test DR testing results with no tests."""
        with patch("core.disaster_recovery_drill.disaster_recovery_drill") as mock_drill:
            mock_drill.get_drill_history.return_value = []
            mock_drill.get_drill_stats.return_value = {
                "total_drills": 0,
                "successful_drills": 0,
                "success_rate": 0.0,
            }

            resp = client.get("/api/disaster/dr-testing", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["test_results"]) == 0
            assert data["success_rate"] == 0.0

    def test_dr_testing_results_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/dr-testing")
        assert resp.status_code == 401


class TestHAConfiguration:
    """Test the ha-configuration endpoint."""

    def test_ha_configuration_success(self, client, admin_headers):
        """Test successful HA configuration retrieval."""
        resp = client.get("/api/disaster/ha-configuration", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "ha_configuration" in data
        ha_config = data["ha_configuration"]
        assert "ha_enabled" in ha_config
        assert "ha_mode" in ha_config
        assert "nodes" in ha_config

    def test_ha_configuration_environment_variables(self, client, admin_headers):
        """Test HA configuration uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_HA_ENABLED": "true",
            "AIOPS_HA_MODE": "active_active",
            "AIOPS_HA_NODES": "3",
        }):
            resp = client.get("/api/disaster/ha-configuration", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["ha_configuration"]["ha_enabled"] is True
            assert data["ha_configuration"]["ha_mode"] == "active_active"
            assert data["ha_configuration"]["nodes"] == 3

    def test_ha_configuration_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/ha-configuration")
        assert resp.status_code == 401


class TestPgBackRestStatus:
    """Test the pgbackrest endpoint."""

    def test_pgbackrest_status_success(self, client, admin_headers):
        """Test successful PgBackRest status."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/pgbackrest"
            with patch.dict(os.environ, {"AIOPS_PGBACKREST_ENABLED": "true"}):
                resp = client.get("/api/disaster/pgbackrest", headers=admin_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert "pgbackrest_enabled" in data
                assert "pgbackrest_available" in data

    def test_pgbackrest_status_not_available(self, client, admin_headers):
        """Test PgBackRest status when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            resp = client.get("/api/disaster/pgbackrest", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["pgbackrest_available"] is False

    def test_pgbackrest_status_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/pgbackrest")
        assert resp.status_code == 401


class TestRecoveryPlan:
    """Test the recovery-plan endpoint."""

    def test_recovery_plan_success(self, client, admin_headers):
        """Test successful recovery plan retrieval."""
        resp = client.get("/api/disaster/recovery-plan", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "recovery_plan" in data
        recovery_plan = data["recovery_plan"]
        assert "name" in recovery_plan
        assert "version" in recovery_plan
        assert "steps" in recovery_plan
        assert len(recovery_plan["steps"]) > 0

    def test_recovery_plan_steps_structure(self, client, admin_headers):
        """Test recovery plan steps structure."""
        resp = client.get("/api/disaster/recovery-plan", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        steps = data["recovery_plan"]["steps"]
        step = steps[0]
        assert "step" in step
        assert "action" in step
        assert "estimated_time_minutes" in step
        assert "critical" in step

    def test_recovery_plan_environment_variables(self, client, admin_headers):
        """Test recovery plan uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_RECOVERY_PLAN_NAME": "Custom Recovery Plan",
            "AIOPS_RECOVERY_PLAN_VERSION": "2.0",
        }):
            resp = client.get("/api/disaster/recovery-plan", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["recovery_plan"]["name"] == "Custom Recovery Plan"
            assert data["recovery_plan"]["version"] == "2.0"

    def test_recovery_plan_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/recovery-plan")
        assert resp.status_code == 401


class TestVeleroStatus:
    """Test the velero endpoint."""

    def test_velero_status_success(self, client, admin_headers):
        """Test successful Velero status."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/velero"
            with patch.dict(os.environ, {"AIOPS_VELERO_ENABLED": "true"}):
                resp = client.get("/api/disaster/velero", headers=admin_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert "velero_enabled" in data
                assert "velero_available" in data

    def test_velero_status_not_available(self, client, admin_headers):
        """Test Velero status when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            resp = client.get("/api/disaster/velero", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["velero_available"] is False

    def test_velero_status_environment_variables(self, client, admin_headers):
        """Test Velero status uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_VELERO_ENABLED": "true",
            "AIOPS_VELERO_BACKUP_LOCATION": "s3://custom-backups",
            "AIOPS_VELERO_SCHEDULE": "weekly",
        }):
            resp = client.get("/api/disaster/velero", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["backup_location"] == "s3://custom-backups"
            assert data["schedule"] == "weekly"

    def test_velero_status_unauthorized(self, client):
        """Test without authentication."""
        resp = client.get("/api/disaster/velero")
        assert resp.status_code == 401


class TestDisasterRouterEdgeCases:
    """Test edge cases for disaster router endpoints."""

    def test_all_endpoints_require_auth(self, client):
        """Test that all endpoints require authentication."""
        endpoints = [
            "/api/disaster/backup-management",
            "/api/disaster/disaster-recovery",
            "/api/disaster/dr-scenarios",
            "/api/disaster/backup-recovery",
            "/api/disaster/backup-strategy",
            "/api/disaster/data-backup",
            "/api/disaster/dr-drill",
            "/api/disaster/dr-testing",
            "/api/disaster/ha-configuration",
            "/api/disaster/pgbackrest",
            "/api/disaster/recovery-plan",
            "/api/disaster/velero",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            assert resp.status_code == 401, f"Endpoint {endpoint} should require authentication"

    def test_backup_management_with_many_files(self, client, admin_headers):
        """Test backup management with many backup files."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    files = []
                    for i in range(100):
                        mock_file = MagicMock()
                        mock_file.is_file.return_value = True
                        mock_file.stat.return_value = MagicMock(st_size=1024 * (i + 1), st_mtime=1609459200.0 + i)
                        files.append(mock_file)
                    mock_glob.return_value = files

                    resp = client.get("/api/disaster/backup-management", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["backup_count"] == 100

    def test_data_backup_with_mixed_files(self, client, admin_headers):
        """Test data backup with mixed file types."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    def glob_side_effect(pattern):
                        if "db_backup" in pattern:
                            return [MagicMock()]
                        elif "redis_backup" in pattern:
                            return [MagicMock(), MagicMock()]
                        elif "config" in pattern:
                            return [MagicMock()]
                        return []
                    mock_glob.side_effect = glob_side_effect

                    resp = client.get("/api/disaster/data-backup", headers=admin_headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["database_backups"] == 1
                    assert data["redis_backups"] == 2
                    assert data["config_backups"] == 1
                    assert data["total_backups"] == 4
