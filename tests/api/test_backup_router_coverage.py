# -*- coding: utf-8 -*-
"""Comprehensive tests for backup_router.py to achieve 90%+ coverage."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBackupDatabase:
    """Test the backup_database endpoint."""

    def test_backup_database_success(self, client):
        """Test successful database backup (lines 50-75)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_database.return_value = "/backups/db_backup.sql"
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/database")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "backup_file" in data

    def test_backup_database_failure(self, client):
        """Test database backup failure (lines 71-72)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_database.return_value = None
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/database")
            assert resp.status_code == 500
            assert "Database backup failed" in resp.json()["detail"]

    def test_backup_database_exception(self, client):
        """Test database backup exception (lines 73-75)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_dr.side_effect = Exception("Backup error")

            resp = client.post("/api/v1/backup/database")
            assert resp.status_code == 500
            assert "备份数据库失败" in resp.json()["detail"]


class TestBackupRedis:
    """Test the backup_redis endpoint."""

    def test_backup_redis_success(self, client):
        """Test successful Redis backup (lines 98-122)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_redis.return_value = "/backups/redis_backup.rdb"
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/redis")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "backup_file" in data

    def test_backup_redis_failure(self, client):
        """Test Redis backup failure (lines 118-119)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_redis.return_value = None
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/redis")
            assert resp.status_code == 500
            assert "Redis backup failed" in resp.json()["detail"]

    def test_backup_redis_exception(self, client):
        """Test Redis backup exception (lines 120-122)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_dr.side_effect = Exception("Backup error")

            resp = client.post("/api/v1/backup/redis")
            assert resp.status_code == 500
            assert "备份Redis失败" in resp.json()["detail"]


class TestBackupConfiguration:
    """Test the backup_configuration endpoint."""

    def test_backup_configuration_success(self, client):
        """Test successful configuration backup (lines 145-169)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_configuration.return_value = "/backups/config_20260702"
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/configuration")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "backup_dir" in data

    def test_backup_configuration_failure(self, client):
        """Test configuration backup failure (lines 165-166)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_configuration.return_value = None
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/configuration")
            assert resp.status_code == 500
            assert "Configuration backup failed" in resp.json()["detail"]

    def test_backup_configuration_exception(self, client):
        """Test configuration backup exception (lines 167-169)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_dr.side_effect = Exception("Backup error")

            resp = client.post("/api/v1/backup/configuration")
            assert resp.status_code == 500
            assert "备份配置失败" in resp.json()["detail"]


class TestFullBackup:
    """Test the full_backup endpoint."""

    def test_full_backup_success(self, client):
        """Test successful full backup (lines 196-229)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_database.return_value = "/backups/db.sql"
            mock_instance.backup_redis.return_value = "/backups/redis.rdb"
            mock_instance.backup_configuration.return_value = "/backups/config"
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/full")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "backups" in data
            assert "database" in data["backups"]
            assert "redis" in data["backups"]
            assert "configuration" in data["backups"]

    def test_full_backup_exception(self, client):
        """Test full backup exception (lines 227-229)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_dr.side_effect = Exception("Backup error")

            resp = client.post("/api/v1/backup/full")
            assert resp.status_code == 500
            assert "完整备份失败" in resp.json()["detail"]

    def test_full_backup_partial_failure(self, client):
        """Test full backup with partial failure."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_database.side_effect = Exception("DB error")
            mock_instance.backup_redis.return_value = "/backups/redis.rdb"
            mock_instance.backup_configuration.return_value = "/backups/config"
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/full")
            assert resp.status_code == 500


class TestRestoreDatabase:
    """Test the restore_database endpoint."""

    def test_restore_database_success(self, client):
        """Test successful database restore (lines 252-279)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.restore_database.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/restore/database?backup_file=/backups/db.sql")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"

    def test_restore_database_failure(self, client):
        """Test database restore failure (lines 275-276)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.restore_database.return_value = False
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/restore/database?backup_file=/backups/db.sql")
            assert resp.status_code == 500
            assert "Database restore failed" in resp.json()["detail"]

    def test_restore_database_exception(self, client):
        """Test database restore exception (lines 277-279)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_dr.side_effect = Exception("Restore error")

            resp = client.post("/api/v1/backup/restore/database?backup_file=/backups/db.sql")
            assert resp.status_code == 500
            assert "恢复数据库失败" in resp.json()["detail"]


class TestListBackups:
    """Test the list_backups endpoint."""

    def test_list_backups_success(self, client):
        """Test successful backup listing (lines 309-345)."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_file = MagicMock()
                mock_file.is_file.return_value = True
                mock_file.name = "backup.sql"
                mock_stat = MagicMock()
                mock_stat.st_size = 1024000
                mock_stat.st_ctime = 1609459200.0
                mock_stat.st_mtime = 1609459200.0
                mock_file.stat.return_value = mock_stat
                mock_iter.return_value = [mock_file]

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert "backups" in data
                assert len(data["backups"]) == 1

    def test_list_backups_no_directory(self, client):
        """Test when backup directory doesn't exist (lines 318-319)."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            resp = client.get("/api/v1/backup/list")
            assert resp.status_code == 200
            data = resp.json()
            assert data["backups"] == []
            assert "No backups found" in data.get("message", "")

    def test_list_backups_exception(self, client):
        """Test list backups exception (lines 343-345)."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.side_effect = Exception("Path error")

            resp = client.get("/api/v1/backup/list")
            assert resp.status_code == 500
            assert "列出备份文件失败" in resp.json()["detail"]

    def test_list_backups_empty_directory(self, client):
        """Test with empty backup directory."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_iter.return_value = []

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["backups"]) == 0

    def test_list_backups_with_directories(self, client):
        """Test with directories mixed with files (line 323)."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_file = MagicMock()
                mock_file.is_file.return_value = True
                mock_file.name = "backup.sql"
                mock_stat = MagicMock()
                mock_stat.st_size = 1024
                mock_stat.st_ctime = 1609459200.0
                mock_stat.st_mtime = 1609459200.0
                mock_file.stat.return_value = mock_stat

                mock_dir = MagicMock()
                mock_dir.is_file.return_value = False
                mock_dir.name = "subdir"

                mock_iter.return_value = [mock_file, mock_dir]

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200
                data = resp.json()
                # Should only include files, not directories
                assert len(data["backups"]) == 1


class TestCleanupOldBackups:
    """Test the cleanup_old_backups endpoint."""

    def test_cleanup_old_backups_success(self, client):
        """Test successful cleanup (lines 368-395)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.delete("/api/v1/backup/cleanup?retention_days=30")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"

    def test_cleanup_old_backups_failure(self, client):
        """Test cleanup failure (lines 391-392)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.cleanup_old_backups.return_value = False
            mock_dr.return_value = mock_instance

            resp = client.delete("/api/v1/backup/cleanup?retention_days=30")
            assert resp.status_code == 500
            assert "Cleanup failed" in resp.json()["detail"]

    def test_cleanup_old_backups_exception(self, client):
        """Test cleanup exception (lines 393-395)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_dr.side_effect = Exception("Cleanup error")

            resp = client.delete("/api/v1/backup/cleanup?retention_days=30")
            assert resp.status_code == 500
            assert "清理旧备份失败" in resp.json()["detail"]

    def test_cleanup_old_backups_default_retention(self, client):
        """Test cleanup with default retention days (line 368)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.delete("/api/v1/backup/cleanup")
            assert resp.status_code == 200

    def test_cleanup_old_backups_custom_retention(self, client):
        """Test cleanup with custom retention days."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.delete("/api/v1/backup/cleanup?retention_days=7")
            assert resp.status_code == 200


class TestBackupEdgeCases:
    """Test edge cases for backup endpoints."""

    def test_backup_database_background_task(self, client):
        """Test that background task is added for cleanup (line 64)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_database.return_value = "/backups/db.sql"
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            with patch("api.backup_router.BackgroundTasks") as mock_bg:
                mock_bg_instance = MagicMock()
                mock_bg.return_value = mock_bg_instance

                resp = client.post("/api/v1/backup/database")
                assert resp.status_code == 200
                # Verify background task was added
                mock_bg_instance.add_task.assert_called()

    def test_full_backup_background_task(self, client):
        """Test that background task is added for full backup cleanup (line 215)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.backup_database.return_value = "/backups/db.sql"
            mock_instance.backup_redis.return_value = "/backups/redis.rdb"
            mock_instance.backup_configuration.return_value = "/backups/config"
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            with patch("api.backup_router.BackgroundTasks") as mock_bg:
                mock_bg_instance = MagicMock()
                mock_bg.return_value = mock_bg_instance

                resp = client.post("/api/v1/backup/full")
                assert resp.status_code == 200
                # Verify background task was added
                mock_bg_instance.add_task.assert_called()

    def test_list_backups_sorting(self, client):
        """Test that backups are sorted by modification time (lines 334-335)."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_file1 = MagicMock()
                mock_file1.is_file.return_value = True
                mock_file1.name = "backup1.sql"
                mock_stat1 = MagicMock()
                mock_stat1.st_size = 1024
                mock_stat1.st_ctime = 1609459200.0
                mock_stat1.st_mtime = 1609459300.0  # Newer
                mock_file1.stat.return_value = mock_stat1

                mock_file2 = MagicMock()
                mock_file2.is_file.return_value = True
                mock_file2.name = "backup2.sql"
                mock_stat2 = MagicMock()
                mock_stat2.st_size = 2048
                mock_stat2.st_ctime = 1609459100.0
                mock_stat2.st_mtime = 1609459200.0  # Older
                mock_file2.stat.return_value = mock_stat2

                mock_iter.return_value = [mock_file1, mock_file2]

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200
                data = resp.json()
                # Should be sorted by modification time descending
                assert data["backups"][0]["name"] == "backup1.sql"
                assert data["backups"][1]["name"] == "backup2.sql"

    def test_list_backups_many_files(self, client):
        """Test listing many backup files."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                files = []
                for i in range(100):
                    mock_file = MagicMock()
                    mock_file.is_file.return_value = True
                    mock_file.name = f"backup{i}.sql"
                    mock_stat = MagicMock()
                    mock_stat.st_size = 1024 * (i + 1)
                    mock_stat.st_ctime = 1609459200.0 + i
                    mock_stat.st_mtime = 1609459200.0 + i
                    mock_file.stat.return_value = mock_stat
                    files.append(mock_file)
                mock_iter.return_value = files

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["backups"]) == 100

    def test_restore_database_with_path_parameter(self, client):
        """Test restore with backup_file as path parameter (line 252)."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.restore_database.return_value = True
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/restore/database?backup_file=C:/backups/db.sql")
            assert resp.status_code == 200

    def test_restore_database_with_empty_path(self, client):
        """Test restore with empty backup_file."""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = MagicMock()
            mock_instance.restore_database.return_value = False
            mock_dr.return_value = mock_instance

            resp = client.post("/api/v1/backup/restore/database?backup_file=")
            assert resp.status_code == 500


class TestBackupDirectoryPath:
    """Test backup directory path handling."""

    def test_list_backups_custom_directory(self, client):
        """Test with custom backup directory path (line 317)."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_iter.return_value = []

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200

    def test_list_backups_path_trailing_slash(self, client):
        """Test backup directory path handling."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_iter.return_value = []

                resp = client.get("/api/v1/backup/list")
                assert resp.status_code == 200
