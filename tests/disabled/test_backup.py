# -*- coding: utf-8 -*-
"""
Unit tests for core.backup module
Tests BackupManager, BackupInfo, and related functionality
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch  # noqa: F401

import pytest

from core.backup import (
    BackupInfo,
    BackupManager,
    BackupStatus,
    BackupType,
    create_backup_manager,
)


class TestBackupType:
    """Test BackupType enum"""

    def test_backup_type_values(self):
        """Test BackupType enum values"""
        assert BackupType.FULL.value == "full"
        assert BackupType.INCREMENTAL.value == "incremental"
        assert BackupType.DIFFERENTIAL.value == "differential"


class TestBackupStatus:
    """Test BackupStatus enum"""

    def test_backup_status_values(self):
        """Test BackupStatus enum values"""
        assert BackupStatus.PENDING.value == "pending"
        assert BackupStatus.RUNNING.value == "running"
        assert BackupStatus.COMPLETED.value == "completed"
        assert BackupStatus.FAILED.value == "failed"


class TestBackupInfo:
    """Test BackupInfo dataclass"""

    def test_backup_info_creation(self):
        """Test BackupInfo creation"""
        start_time = datetime.now()
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type=BackupType.FULL,
            status=BackupStatus.RUNNING,
            start_time=start_time,
        )

        assert backup_info.backup_id == "test_backup"
        assert backup_info.backup_type == BackupType.FULL
        assert backup_info.status == BackupStatus.RUNNING
        assert backup_info.start_time == start_time
        assert backup_info.end_time is None
        assert backup_info.size_bytes == 0
        assert backup_info.location == ""
        assert backup_info.error is None

    def test_backup_info_with_optional_fields(self):
        """Test BackupInfo with optional fields"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type=BackupType.FULL,
            status=BackupStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            size_bytes=1024000,
            location="s3://bucket/test_backup",
            error=None,
        )

        assert backup_info.end_time == end_time
        assert backup_info.size_bytes == 1024000
        assert backup_info.location == "s3://bucket/test_backup"

    def test_backup_info_to_dict(self):
        """Test BackupInfo to_dict method"""
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        end_time = datetime(2025, 1, 1, 13, 0, 0)
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type=BackupType.FULL,
            status=BackupStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            size_bytes=1024000,
            location="s3://bucket/test_backup",
            error=None,
        )

        result = backup_info.to_dict()

        assert result["backup_id"] == "test_backup"
        assert result["backup_type"] == "full"
        assert result["status"] == "completed"
        assert result["start_time"] == "2025-01-01T12:00:00"
        assert result["end_time"] == "2025-01-01T13:00:00"
        assert result["size_bytes"] == 1024000
        assert result["location"] == "s3://bucket/test_backup"
        assert result["error"] is None

    def test_backup_info_to_dict_with_none_end_time(self):
        """Test BackupInfo to_dict with None end_time"""
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type=BackupType.FULL,
            status=BackupStatus.RUNNING,
            start_time=start_time,
        )

        result = backup_info.to_dict()

        assert result["end_time"] is None

    def test_backup_info_to_dict_with_error(self):
        """Test BackupInfo to_dict with error"""
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type=BackupType.FULL,
            status=BackupStatus.FAILED,
            start_time=start_time,
            error="Backup failed",
        )

        result = backup_info.to_dict()

        assert result["error"] == "Backup failed"


class TestBackupManager:
    """Test BackupManager class"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            "wal_g_path": "wal-g",
            "pg_host": "localhost",
            "pg_port": "5432",
            "pg_database": "testdb",
            "pg_user": "testuser",
            "s3_bucket": "test-bucket",
            "s3_endpoint": "https://s3.amazonaws.com",
            "aws_access_key": "test_key",
            "aws_secret_key": "test_secret",
            "retention_days": 7,
        }

    @pytest.fixture
    def manager(self, config):
        """Create BackupManager instance"""
        return BackupManager(config)

    def test_manager_initialization(self, manager, config):
        """Test BackupManager initialization"""
        assert manager.wal_g_path == config["wal_g_path"]
        assert manager.pg_host == config["pg_host"]
        assert manager.pg_port == config["pg_port"]
        assert manager.pg_database == config["pg_database"]
        assert manager.pg_user == config["pg_user"]
        assert manager.s3_bucket == config["s3_bucket"]
        assert manager.s3_endpoint == config["s3_endpoint"]
        assert manager.aws_access_key == config["aws_access_key"]
        assert manager.aws_secret_key == config["aws_secret_key"]
        assert manager.retention_days == config["retention_days"]
        assert manager._is_initialized is False
        assert len(manager._backups) == 0

    def test_manager_initialization_with_defaults(self):
        """Test BackupManager initialization with config defaults"""
        config = {"wal_g_path": "wal-g"}
        manager = BackupManager(config)

        assert manager.s3_bucket == "aiops-backups"
        assert manager.s3_endpoint == "https://s3.amazonaws.com"
        assert manager.retention_days == 7

    @patch("subprocess.run")
    def test_initialize_success(self, mock_run, manager):
        """Test successful initialization"""
        mock_run.return_value = Mock(returncode=0, stdout="wal-g version 1.0", stderr="")

        result = manager.initialize()

        assert result is True
        assert manager._is_initialized is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_initialize_failure(self, mock_run, manager):
        """Test initialization failure"""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="command not found")

        result = manager.initialize()

        assert result is False
        assert manager._is_initialized is False

    @patch("subprocess.run")
    def test_initialize_exception(self, mock_run, manager):
        """Test initialization with exception"""
        mock_run.side_effect = Exception("Subprocess error")

        result = manager.initialize()

        assert result is False
        assert manager._is_initialized is False

    @patch("subprocess.run")
    async def test_create_backup_success(self, mock_run, manager):
        """Test successful backup creation"""
        # Mock initialization
        manager._is_initialized = True
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        backup_info = await manager.create_backup(BackupType.FULL)

        assert backup_info.status == BackupStatus.COMPLETED
        assert backup_info.backup_type == BackupType.FULL
        assert backup_info.end_time is not None
        assert backup_info.location is not None
        assert backup_info.error is None

    @patch("subprocess.run")
    async def test_create_backup_failure(self, mock_run, manager):
        """Test backup creation failure"""
        manager._is_initialized = True
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Backup failed")

        backup_info = await manager.create_backup(BackupType.FULL)

        assert backup_info.status == BackupStatus.FAILED
        assert backup_info.error == "Backup failed"

    @patch("subprocess.run")
    async def test_create_backup_timeout(self, mock_run, manager):
        """Test backup creation timeout"""
        from subprocess import TimeoutExpired

        manager._is_initialized = True
        mock_run.side_effect = TimeoutExpired("wal-g", 3600)

        backup_info = await manager.create_backup(BackupType.FULL)

        assert backup_info.status == BackupStatus.FAILED
        assert backup_info.error == "Backup timeout"

    async def test_create_backup_not_initialized(self, manager):
        """Test backup creation when not initialized"""
        with pytest.raises(RuntimeError, match="Backup manager not initialized"):
            await manager.create_backup(BackupType.FULL)

    @patch("subprocess.run")
    async def test_create_backup_incremental(self, mock_run, manager):
        """Test incremental backup creation"""
        manager._is_initialized = True
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        backup_info = await manager.create_backup(BackupType.INCREMENTAL)

        assert backup_info.backup_type == BackupType.INCREMENTAL
        assert backup_info.status == BackupStatus.COMPLETED

    @patch("subprocess.run")
    async def test_create_backup_differential(self, mock_run, manager):
        """Test differential backup creation"""
        manager._is_initialized = True
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        backup_info = await manager.create_backup(BackupType.DIFFERENTIAL)

        assert backup_info.backup_type == BackupType.DIFFERENTIAL
        assert backup_info.status == BackupStatus.COMPLETED

    @patch("subprocess.run")
    async def test_restore_backup_success(self, mock_run, manager):
        """Test successful restore"""
        manager._is_initialized = True
        backup_id = "full_20250101_120000"
        manager._backups[backup_id] = BackupInfo(
            backup_id=backup_id,
            backup_type=BackupType.FULL,
            status=BackupStatus.COMPLETED,
            start_time=datetime.now(),
        )
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = await manager.restore_backup(backup_id)

        assert result is True

    async def test_restore_backup_not_initialized(self, manager):
        """Test restore when not initialized"""
        with pytest.raises(RuntimeError, match="Backup manager not initialized"):
            await manager.restore_backup("test_backup")

    async def test_restore_backup_not_found(self, manager):
        """Test restore with non-existent backup"""
        manager._is_initialized = True

        result = await manager.restore_backup("nonexistent")

        assert result is False

    async def test_restore_backup_not_completed(self, manager):
        """Test restore with incomplete backup"""
        manager._is_initialized = True
        backup_id = "full_20250101_120000"
        manager._backups[backup_id] = BackupInfo(
            backup_id=backup_id,
            backup_type=BackupType.FULL,
            status=BackupStatus.RUNNING,
            start_time=datetime.now(),
        )

        result = await manager.restore_backup(backup_id)

        assert result is False

    @patch("subprocess.run")
    async def test_restore_backup_with_target_time(self, mock_run, manager):
        """Test restore with point-in-time recovery"""
        manager._is_initialized = True
        backup_id = "full_20250101_120000"
        manager._backups[backup_id] = BackupInfo(
            backup_id=backup_id,
            backup_type=BackupType.FULL,
            status=BackupStatus.COMPLETED,
            start_time=datetime.now(),
            location="s3://bucket/test_backup",
        )
        target_time = datetime(2025, 1, 1, 13, 0, 0)
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = await manager.restore_backup(backup_id, target_time)

        assert result is True
        # Verify target_time was included in command
        call_args = mock_run.call_args[0][0]
        assert "--target-time" in call_args

    @patch("subprocess.run")
    async def test_list_backups_success(self, mock_run, manager):
        """Test successful backup listing"""
        manager._is_initialized = True
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"backup_name": "backup1", "start_time": "2025-01-01T12:00:00"}]',
            stderr="",
        )

        backups = await manager.list_backups()

        assert len(backups) == 1
        assert backups[0]["backup_name"] == "backup1"

    @patch("subprocess.run")
    async def test_list_backups_failure(self, mock_run, manager):
        """Test backup listing failure"""
        manager._is_initialized = True
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Failed to list")

        backups = await manager.list_backups()

        assert backups == []

    @patch("subprocess.run")
    async def test_cleanup_old_backups_success(self, mock_run, manager):
        """Test successful cleanup of old backups"""
        manager._is_initialized = True
        old_backup = {
            "backup_name": "old_backup",
            "start_time": (datetime.now() - timedelta(days=10)).isoformat(),
        }
        new_backup = {"backup_name": "new_backup", "start_time": datetime.now().isoformat()}

        # Mock list_backups to return old and new backups
        with patch.object(manager, "list_backups", return_value=[old_backup, new_backup]):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            cleaned_count = await manager.cleanup_old_backups()

            assert cleaned_count == 1

    async def test_cleanup_old_backups_not_initialized(self, manager):
        """Test cleanup when not initialized"""
        with pytest.raises(RuntimeError, match="Backup manager not initialized"):
            await manager.cleanup_old_backups()

    def test_get_backup_status_found(self, manager):
        """Test getting status of existing backup"""
        backup_id = "test_backup"
        backup_info = BackupInfo(
            backup_id=backup_id,
            backup_type=BackupType.FULL,
            status=BackupStatus.COMPLETED,
            start_time=datetime.now(),
        )
        manager._backups[backup_id] = backup_info

        status = manager.get_backup_status(backup_id)

        assert status is not None
        assert status["backup_id"] == backup_id

    def test_get_backup_status_not_found(self, manager):
        """Test getting status of non-existent backup"""
        status = manager.get_backup_status("nonexistent")

        assert status is None

    def test_get_all_backup_statuses(self, manager):
        """Test getting all backup statuses"""
        backup1 = BackupInfo(
            backup_id="backup1",
            backup_type=BackupType.FULL,
            status=BackupStatus.COMPLETED,
            start_time=datetime.now(),
        )
        backup2 = BackupInfo(
            backup_id="backup2",
            backup_type=BackupType.INCREMENTAL,
            status=BackupStatus.RUNNING,
            start_time=datetime.now(),
        )
        manager._backups["backup1"] = backup1
        manager._backups["backup2"] = backup2

        statuses = manager.get_all_backup_statuses()

        assert len(statuses) == 2
        assert statuses[0]["backup_id"] == "backup1"
        assert statuses[1]["backup_id"] == "backup2"

    def test_get_all_backup_statuses_empty(self, manager):
        """Test getting all backup statuses when no backups"""
        statuses = manager.get_all_backup_statuses()

        assert statuses == []

    def test_schedule_backup(self, manager):
        """Test backup scheduling"""
        result = manager.schedule_backup(BackupType.FULL, "0 2 * * *")

        assert result is True

    def test_schedule_backup_default_schedule(self, manager):
        """Test backup scheduling with default schedule"""
        result = manager.schedule_backup()

        assert result is True


class TestCreateBackupManager:
    """Test create_backup_manager factory function"""

    @patch("subprocess.run")
    def test_create_backup_manager_success(self, mock_run):
        """Test successful BackupManager creation"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        config = {
            "wal_g_path": "wal-g",
            "pg_host": "localhost",
            "pg_port": "5432",
            "pg_database": "testdb",
            "pg_user": "testuser",
            "s3_bucket": "test-bucket",
        }

        manager = create_backup_manager(config)

        assert manager is not None
        assert isinstance(manager, BackupManager)

    @patch("subprocess.run")
    def test_create_backup_manager_failure(self, mock_run):
        """Test BackupManager creation failure"""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
        config = {
            "wal_g_path": "wal-g",
            "pg_host": "localhost",
            "pg_port": "5432",
            "pg_database": "testdb",
            "pg_user": "testuser",
            "s3_bucket": "test-bucket",
        }

        manager = create_backup_manager(config)

        assert manager is None

    @patch("subprocess.run")
    def test_create_backup_manager_exception(self, mock_run):
        """Test BackupManager creation with exception"""
        mock_run.side_effect = Exception("Error")
        config = {
            "wal_g_path": "wal-g",
            "pg_host": "localhost",
            "pg_port": "5432",
            "pg_database": "testdb",
            "pg_user": "testuser",
            "s3_bucket": "test-bucket",
        }

        manager = create_backup_manager(config)

        assert manager is None
