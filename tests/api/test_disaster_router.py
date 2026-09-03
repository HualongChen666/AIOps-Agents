# -*- coding: utf-8 -*-
"""Comprehensive tests for disaster_router.py to achieve 100% coverage."""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# Create a test app with disaster router
@pytest.fixture(scope="module")
def disaster_client():
    """Create a test client for disaster router with mocked auth."""
    from api.disaster_router import router, get_current_user, get_session

    app = FastAPI()
    app.include_router(router)

    # Mock user
    user = Mock()
    user.id = 1
    user.username = "test_admin"
    user.role = "admin"
    user.is_active = True
    user.disabled = False

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = lambda: Mock()

    with TestClient(app) as client:
        yield client

    # Clean up
    app.dependency_overrides = {}


class TestBackupManagement:
    """Test the backup-management endpoint."""

    def test_backup_management_success(self, disaster_client):
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

                    resp = disaster_client.get("/api/disaster/backup-management")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert data["backup_count"] == 1
                    assert "total_size_mb" in data
                    assert "retention_days" in data

    def test_backup_management_no_directory(self, disaster_client):
        """Test when backup directory doesn't exist."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                resp = disaster_client.get("/api/disaster/backup-management")
                assert resp.status_code == 200
                data = resp.json()
                assert data["backup_count"] == 0
                assert data["total_size_mb"] == 0
                assert data["last_backup"] is None

    def test_backup_management_exception(self, disaster_client):
        """Test backup management with exception."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.side_effect = Exception("Directory error")

            resp = disaster_client.get("/api/disaster/backup-management")
            assert resp.status_code == 500


class TestDisasterRecoveryStatus:
    """Test the disaster-recovery endpoint."""

    def test_disaster_recovery_status_success(self, disaster_client):
        """Test successful disaster recovery status."""
        with patch("api.disaster_router._get_dr_enabled") as mock_enabled:
            mock_enabled.return_value = True
            with patch("api.disaster_router._get_backup_dir") as mock_dir:
                mock_dir.return_value = Path("/tmp/backups")
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True
                    with patch("pathlib.Path.glob") as mock_glob:
                        mock_glob.return_value = [MagicMock()]

                        resp = disaster_client.get("/api/disaster/disaster-recovery")
                        assert resp.status_code == 200
                        data = resp.json()
                        assert data["status"] == "success"
                        assert data["dr_enabled"] is True
                        assert "dr_status" in data

    def test_disaster_recovery_status_unhealthy(self, disaster_client):
        """Test disaster recovery status when unhealthy."""
        with patch("api.disaster_router._get_dr_enabled") as mock_enabled:
            mock_enabled.return_value = True
            with patch("api.disaster_router._get_backup_dir") as mock_dir:
                mock_dir.return_value = Path("/tmp/backups")
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = False

                    resp = disaster_client.get("/api/disaster/disaster-recovery")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["dr_status"] == "unhealthy"


class TestDRScenarios:
    """Test the dr-scenarios endpoint."""

    def test_dr_scenarios_success(self, disaster_client):
        """Test successful DR scenarios retrieval."""
        resp = disaster_client.get("/api/disaster/dr-scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "scenarios" in data
        assert len(data["scenarios"]) > 0
        assert "count" in data

    def test_dr_scenarios_structure(self, disaster_client):
        """Test DR scenarios structure."""
        resp = disaster_client.get("/api/disaster/dr-scenarios")
        assert resp.status_code == 200
        data = resp.json()
        scenario = data["scenarios"][0]
        assert "name" in scenario
        assert "description" in scenario
        assert "enabled" in scenario


class TestBackupRecoveryStatus:
    """Test the backup-recovery endpoint."""

    def test_backup_recovery_status_success(self, disaster_client):
        """Test successful backup recovery status."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_file = MagicMock()
                    mock_file.suffix = ".sql"
                    mock_glob.return_value = [mock_file]

                    resp = disaster_client.get("/api/disaster/backup-recovery")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert "recoverable_backups" in data
                    assert "recovery_status" in data

    def test_backup_recovery_status_no_backups(self, disaster_client):
        """Test backup recovery status with no backups."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_glob.return_value = []

                    resp = disaster_client.get("/api/disaster/backup-recovery")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["recovery_status"] == "no_backups"


class TestBackupStrategy:
    """Test the backup-strategy endpoint."""

    def test_backup_strategy_success(self, disaster_client):
        """Test successful backup strategy retrieval."""
        resp = disaster_client.get("/api/disaster/backup-strategy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "strategy" in data
        strategy = data["strategy"]
        assert "backup_type" in strategy
        assert "schedule" in strategy
        assert "retention_days" in strategy

    def test_backup_strategy_environment_variables(self, disaster_client):
        """Test backup strategy uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_BACKUP_TYPE": "incremental",
            "AIOPS_BACKUP_SCHEDULE": "weekly",
            "AIOPS_BACKUP_RETENTION_DAYS": "90",
        }):
            resp = disaster_client.get("/api/disaster/backup-strategy")
            assert resp.status_code == 200
            data = resp.json()
            assert data["strategy"]["backup_type"] == "incremental"
            assert data["strategy"]["schedule"] == "weekly"
            assert data["strategy"]["retention_days"] == 90


class TestDataBackupStatus:
    """Test the data-backup endpoint."""

    def test_data_backup_status_success(self, disaster_client):
        """Test successful data backup status."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_file = MagicMock()
                    mock_file.stat.return_value = MagicMock(st_mtime=1609459200.0)
                    mock_glob.return_value = [mock_file]

                    resp = disaster_client.get("/api/disaster/data-backup")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert "database_backups" in data
                    assert "redis_backups" in data
                    assert "config_backups" in data
                    assert "total_backups" in data

    def test_data_backup_status_no_directory(self, disaster_client):
        """Test data backup status when directory doesn't exist."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                resp = disaster_client.get("/api/disaster/data-backup")
                assert resp.status_code == 200
                data = resp.json()
                assert data["database_backups"] == 0
                assert data["redis_backups"] == 0
                assert data["config_backups"] == 0


class TestDRDrillStatus:
    """Test the GET dr-drill endpoint."""

    def test_dr_drill_status_success(self, disaster_client):
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

            resp = disaster_client.get("/api/disaster/dr-drill")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "last_drill" in data
            assert "drill_count" in data

    def test_dr_drill_status_no_history(self, disaster_client):
        """Test DR drill status with no history."""
        with patch("core.disaster_recovery_drill.disaster_recovery_drill") as mock_drill:
            mock_drill.get_drill_history.return_value = []

            resp = disaster_client.get("/api/disaster/dr-drill")
            assert resp.status_code == 200
            data = resp.json()
            assert data["drill_count"] == 0
            assert data["last_drill"] is None


class TestDRTestingResults:
    """Test the dr-testing endpoint."""

    def test_dr_testing_results_success(self, disaster_client):
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

            resp = disaster_client.get("/api/disaster/dr-testing")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "test_results" in data
            assert "success_rate" in data
            assert data["success_rate"] == 90.0

    def test_dr_testing_results_empty(self, disaster_client):
        """Test DR testing results with no tests."""
        with patch("core.disaster_recovery_drill.disaster_recovery_drill") as mock_drill:
            mock_drill.get_drill_history.return_value = []
            mock_drill.get_drill_stats.return_value = {
                "total_drills": 0,
                "successful_drills": 0,
                "success_rate": 0.0,
            }

            resp = disaster_client.get("/api/disaster/dr-testing")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["test_results"]) == 0
            assert data["success_rate"] == 0.0


class TestHAConfiguration:
    """Test the ha-configuration endpoint."""

    def test_ha_configuration_success(self, disaster_client):
        """Test successful HA configuration retrieval."""
        resp = disaster_client.get("/api/disaster/ha-configuration")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "ha_configuration" in data
        ha_config = data["ha_configuration"]
        assert "ha_enabled" in ha_config
        assert "ha_mode" in ha_config
        assert "nodes" in ha_config

    def test_ha_configuration_environment_variables(self, disaster_client):
        """Test HA configuration uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_HA_ENABLED": "true",
            "AIOPS_HA_MODE": "active_active",
            "AIOPS_HA_NODES": "3",
        }):
            resp = disaster_client.get("/api/disaster/ha-configuration")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ha_configuration"]["ha_enabled"] is True
            assert data["ha_configuration"]["ha_mode"] == "active_active"
            assert data["ha_configuration"]["nodes"] == 3


class TestPgBackRestStatus:
    """Test the pgbackrest endpoint."""

    def test_pgbackrest_status_success(self, disaster_client):
        """Test successful PgBackRest status."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/pgbackrest"
            with patch.dict(os.environ, {"AIOPS_PGBACKREST_ENABLED": "true"}):
                resp = disaster_client.get("/api/disaster/pgbackrest")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert "pgbackrest_enabled" in data
                assert "pgbackrest_available" in data

    def test_pgbackrest_status_not_available(self, disaster_client):
        """Test PgBackRest status when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            resp = disaster_client.get("/api/disaster/pgbackrest")
            assert resp.status_code == 200
            data = resp.json()
            assert data["pgbackrest_available"] is False


class TestRecoveryPlan:
    """Test the recovery-plan endpoint."""

    def test_recovery_plan_success(self, disaster_client):
        """Test successful recovery plan retrieval."""
        resp = disaster_client.get("/api/disaster/recovery-plan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "recovery_plan" in data
        recovery_plan = data["recovery_plan"]
        assert "name" in recovery_plan
        assert "version" in recovery_plan
        assert "steps" in recovery_plan
        assert len(recovery_plan["steps"]) > 0

    def test_recovery_plan_steps_structure(self, disaster_client):
        """Test recovery plan steps structure."""
        resp = disaster_client.get("/api/disaster/recovery-plan")
        assert resp.status_code == 200
        data = resp.json()
        steps = data["recovery_plan"]["steps"]
        step = steps[0]
        assert "step" in step
        assert "action" in step
        assert "estimated_time_minutes" in step
        assert "critical" in step

    def test_recovery_plan_environment_variables(self, disaster_client):
        """Test recovery plan uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_RECOVERY_PLAN_NAME": "Custom Recovery Plan",
            "AIOPS_RECOVERY_PLAN_VERSION": "2.0",
        }):
            resp = disaster_client.get("/api/disaster/recovery-plan")
            assert resp.status_code == 200
            data = resp.json()
            assert data["recovery_plan"]["name"] == "Custom Recovery Plan"
            assert data["recovery_plan"]["version"] == "2.0"


class TestVeleroStatus:
    """Test the velero endpoint."""

    def test_velero_status_success(self, disaster_client):
        """Test successful Velero status."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/velero"
            with patch.dict(os.environ, {"AIOPS_VELERO_ENABLED": "true"}):
                resp = disaster_client.get("/api/disaster/velero")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert "velero_enabled" in data
                assert "velero_available" in data

    def test_velero_status_not_available(self, disaster_client):
        """Test Velero status when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            resp = disaster_client.get("/api/disaster/velero")
            assert resp.status_code == 200
            data = resp.json()
            assert data["velero_available"] is False

    def test_velero_status_environment_variables(self, disaster_client):
        """Test Velero status uses environment variables."""
        with patch.dict(os.environ, {
            "AIOPS_VELERO_ENABLED": "true",
            "AIOPS_VELERO_BACKUP_LOCATION": "s3://custom-backups",
            "AIOPS_VELERO_SCHEDULE": "weekly",
        }):
            resp = disaster_client.get("/api/disaster/velero")
            assert resp.status_code == 200
            data = resp.json()
            assert data["backup_location"] == "s3://custom-backups"
            assert data["schedule"] == "weekly"


class TestExecuteBackup:
    """Test the POST /backup endpoint."""

    def test_execute_backup_database(self, disaster_client):
        """Test successful database backup."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.backup_database") as mock_backup:
                mock_backup.return_value = "/tmp/backups/db_backup_20260702_103000.sql"

                resp = disaster_client.post(
                    "/api/disaster/backup",
                    json={"backup_type": "database"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["backup_type"] == "database"
                assert "backup_file" in data

    def test_execute_backup_redis(self, disaster_client):
        """Test successful Redis backup."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.backup_redis") as mock_backup:
                mock_backup.return_value = "/tmp/backups/redis_backup_20260702_103000.rdb"

                resp = disaster_client.post(
                    "/api/disaster/backup",
                    json={"backup_type": "redis"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["backup_type"] == "redis"

    def test_execute_backup_configuration(self, disaster_client):
        """Test successful configuration backup."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.backup_configuration") as mock_backup:
                mock_backup.return_value = "/tmp/backups/config_20260702_103000"

                resp = disaster_client.post(
                    "/api/disaster/backup",
                    json={"backup_type": "configuration"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["backup_type"] == "configuration"

    def test_execute_backup_all(self, disaster_client):
        """Test backup all types."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.backup_database") as mock_db:
                mock_db.return_value = "/tmp/backups/db_backup.sql"
                with patch("core.disaster_recovery.DisasterRecovery.backup_redis") as mock_redis:
                    mock_redis.return_value = "/tmp/backups/redis_backup.rdb"
                    with patch("core.disaster_recovery.DisasterRecovery.backup_configuration") as mock_config:
                        mock_config.return_value = "/tmp/backups/config_backup"

                        resp = disaster_client.post(
                            "/api/disaster/backup",
                            json={"backup_type": "all"}
                        )
                        assert resp.status_code == 200
                        data = resp.json()
                        assert data["status"] == "success"
                        assert data["backup_type"] == "all"

    def test_execute_backup_invalid_type(self, disaster_client):
        """Test backup with invalid type."""
        resp = disaster_client.post(
            "/api/disaster/backup",
            json={"backup_type": "invalid_type"}
        )
        assert resp.status_code == 400


class TestExecuteRestore:
    """Test the POST /restore endpoint."""

    def test_execute_restore_database(self, disaster_client):
        """Test successful database restore."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.restore_database") as mock_restore:
                mock_restore.return_value = True

                resp = disaster_client.post(
                    "/api/disaster/restore",
                    json={
                        "backup_file": "/tmp/backups/db_backup_20260702_103000.sql",
                        "restore_type": "database"
                    }
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["restore_type"] == "database"
                assert data["restored"] is True

    def test_execute_restore_redis(self, disaster_client):
        """Test successful Redis restore."""
        resp = disaster_client.post(
            "/api/disaster/restore",
            json={
                "backup_file": "/tmp/backups/redis_backup_20260702_103000.rdb",
                "restore_type": "redis"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["restore_type"] == "redis"

    def test_execute_restore_configuration(self, disaster_client):
        """Test successful configuration restore."""
        resp = disaster_client.post(
            "/api/disaster/restore",
            json={
                "backup_file": "/tmp/backups/config_20260702_103000",
                "restore_type": "configuration"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["restore_type"] == "configuration"

    def test_execute_restore_invalid_type(self, disaster_client):
        """Test restore with invalid type."""
        resp = disaster_client.post(
            "/api/disaster/restore",
            json={
                "backup_file": "/tmp/backups/backup.sql",
                "restore_type": "invalid_type"
            }
        )
        assert resp.status_code == 400


class TestStartDrDrill:
    """Test the POST /dr-drill endpoint."""

    def test_start_dr_drill_success(self, disaster_client):
        """Test successful DR drill start."""
        with patch("api.disaster_router._get_dr_enabled") as mock_enabled:
            mock_enabled.return_value = True
            with patch("core.disaster_recovery_drill.disaster_recovery_drill.run_drill") as mock_drill:
                from core.disaster_recovery_drill import DrillResult, DrillScenario, DrillStatus
                from datetime import datetime, timezone

                mock_result = DrillResult(
                    scenario=DrillScenario.DATABASE_FAILOVER,
                    status=DrillStatus.COMPLETED,
                    start_time=datetime.now(timezone.utc),
                    success=True,
                    duration_seconds=120
                )
                mock_drill.return_value = mock_result

                resp = disaster_client.post(
                    "/api/disaster/dr-drill",
                    json={"scenario": "database_failover"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["scenario"] == "database_failover"
                assert "drill_id" in data

    def test_start_dr_drill_invalid_scenario(self, disaster_client):
        """Test DR drill with invalid scenario."""
        resp = disaster_client.post(
            "/api/disaster/dr-drill",
            json={"scenario": "invalid_scenario"}
        )
        assert resp.status_code == 400

    def test_start_dr_drill_disabled(self, disaster_client):
        """Test DR drill when DR is disabled."""
        with patch("api.disaster_router._get_dr_enabled") as mock_enabled:
            mock_enabled.return_value = False

            resp = disaster_client.post(
                "/api/disaster/dr-drill",
                json={"scenario": "database_failover"}
            )
            assert resp.status_code == 400


class TestCleanupOldBackups:
    """Test the DELETE /backups endpoint."""

    def test_cleanup_old_backups_success(self, disaster_client):
        """Test successful backup cleanup."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.cleanup_old_backups") as mock_cleanup:
                mock_cleanup.return_value = True
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True
                    with patch("pathlib.Path.glob") as mock_glob:
                        mock_glob.return_value = [MagicMock(), MagicMock(), MagicMock()]

                        resp = disaster_client.delete("/api/disaster/backups")
                        assert resp.status_code == 200
                        data = resp.json()
                        assert data["status"] == "success"
                        assert "deleted_count" in data
                        assert "retention_days" in data

    def test_cleanup_old_backups_with_retention(self, disaster_client):
        """Test backup cleanup with custom retention days."""
        with patch("api.disaster_router._get_backup_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/backups")
            with patch("core.disaster_recovery.DisasterRecovery.cleanup_old_backups") as mock_cleanup:
                mock_cleanup.return_value = True

                resp = disaster_client.delete("/api/disaster/backups?retention_days=7")
                assert resp.status_code == 200
                data = resp.json()
                assert data["retention_days"] == 7


class TestUpdateBackupStrategy:
    """Test the PUT /backup-strategy endpoint."""

    def test_update_backup_strategy_success(self, disaster_client):
        """Test successful backup strategy update."""
        resp = disaster_client.put(
            "/api/disaster/backup-strategy",
            json={
                "backup_type": "incremental",
                "schedule": "weekly",
                "retention_days": 90
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "strategy" in data
        assert data["strategy"]["backup_type"] == "incremental"
        assert data["strategy"]["schedule"] == "weekly"
        assert data["strategy"]["retention_days"] == 90

    def test_update_backup_strategy_partial(self, disaster_client):
        """Test partial backup strategy update."""
        resp = disaster_client.put(
            "/api/disaster/backup-strategy",
            json={"retention_days": 60}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["strategy"]["retention_days"] == 60

    def test_update_backup_strategy_compression(self, disaster_client):
        """Test backup strategy update with compression settings."""
        resp = disaster_client.put(
            "/api/disaster/backup-strategy",
            json={
                "compression_enabled": False,
                "encryption_enabled": True
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["strategy"]["compression_enabled"] is False
        assert data["strategy"]["encryption_enabled"] is True


class TestVerifyBackup:
    """Test the POST /verify-backup endpoint."""

    def test_verify_backup_success(self, disaster_client):
        """Test successful backup verification."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=1024)
                with patch("builtins.open") as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = "CREATE TABLE test;"

                    resp = disaster_client.post(
                        "/api/disaster/verify-backup",
                        json={"backup_file": "/tmp/backups/db_backup.sql"}
                    )
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "success"
                    assert data["valid"] is True
                    assert "size_bytes" in data

    def test_verify_backup_not_found(self, disaster_client):
        """Test backup verification when file not found."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            resp = disaster_client.post(
                "/api/disaster/verify-backup",
                json={"backup_file": "/tmp/backups/nonexistent.sql"}
            )
            assert resp.status_code == 404

    def test_verify_backup_empty_file(self, disaster_client):
        """Test backup verification with empty file."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=0)

                resp = disaster_client.post(
                    "/api/disaster/verify-backup",
                    json={"backup_file": "/tmp/backups/empty.sql"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["valid"] is False
                assert data["reason"] == "Backup file is empty"

    def test_verify_backup_rdb_file(self, disaster_client):
        """Test backup verification with RDB file."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=1024)

                resp = disaster_client.post(
                    "/api/disaster/verify-backup",
                    json={"backup_file": "/tmp/backups/redis_backup.rdb"}
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["valid"] is True


class TestDisasterRouterEdgeCases:
    """Test edge cases for disaster router endpoints."""

    def test_backup_management_with_many_files(self, disaster_client):
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

                    resp = disaster_client.get("/api/disaster/backup-management")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["backup_count"] == 100

    def test_data_backup_with_mixed_files(self, disaster_client):
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

                    resp = disaster_client.get("/api/disaster/data-backup")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["database_backups"] == 1
                    assert data["redis_backups"] == 2
                    assert data["config_backups"] == 1
                    assert data["total_backups"] == 4
