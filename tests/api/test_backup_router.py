# -*- coding: utf-8 -*-
"""
Backup Router Tests
备份路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.backup_router import (
    backup_configuration,
    backup_database,
    backup_redis,
    cleanup_old_backups,
    full_backup,
    list_backups,
    restore_database,
)

# Mock problematic imports before importing router
mock_disaster_recovery = MagicMock()
mock_dr_instance = Mock()
mock_dr_instance.backup_database.return_value = "/backups/db_backup_20260702.sql"
mock_disaster_recovery.DisasterRecovery.return_value = mock_dr_instance
sys.modules["disaster_recovery"] = mock_disaster_recovery


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/backup", tags=["备份和恢复"])
    test_router.add_api_route("/database", backup_database, methods=["POST"])
    test_router.add_api_route("/redis", backup_redis, methods=["POST"])
    test_router.add_api_route("/configuration", backup_configuration, methods=["POST"])
    test_router.add_api_route("/full", full_backup, methods=["POST"])
    test_router.add_api_route("/restore/database", restore_database, methods=["POST"])
    test_router.add_api_route("/list", list_backups, methods=["GET"])
    test_router.add_api_route("/cleanup", cleanup_old_backups, methods=["DELETE"])
    app.include_router(test_router)
    return TestClient(app)


class TestBackupRouter:
    """测试备份路由"""

    def test_backup_database(self, client):
        """测试数据库备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_database.return_value = "/backups/db_backup_20260702.sql"
            mock_dr.return_value = mock_instance
            response = client.post("/api/v1/backup/database")
            assert response.status_code == 200

    def test_backup_redis(self, client):
        """测试Redis备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_redis.return_value = "/backups/redis_backup_20260702.rdb"
            mock_dr.return_value = mock_instance
            response = client.post("/api/v1/backup/redis")
            assert response.status_code == 200

    def test_backup_configuration(self, client):
        """测试配置备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_configuration.return_value = (
                "/backups/config_backup_20260702.tar.gz"
            )
            mock_dr.return_value = mock_instance
            response = client.post("/api/v1/backup/configuration")
            assert response.status_code == 200

    def test_full_backup(self, client):
        """测试完整备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_database.return_value = "/backups/db_backup.sql"
            mock_instance.backup_redis.return_value = "/backups/redis_backup.rdb"
            mock_instance.backup_configuration.return_value = "/backups/config_backup.tar.gz"
            mock_dr.return_value = mock_instance
            response = client.post("/api/v1/backup/full")
            assert response.status_code == 200

    def test_restore_database(self, client):
        """测试数据库恢复"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.restore_database.return_value = True
            mock_dr.return_value = mock_instance
            response = client.post(
                "/api/v1/backup/restore/database?backup_file=/backups/db_backup.sql"
            )
            assert response.status_code == 200

    def test_backup_database_error(self, client):
        """测试数据库备份失败"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_database.side_effect = Exception("Backup failed")
            mock_dr.return_value = mock_instance
            response = client.post("/api/v1/backup/database")
            assert response.status_code == 500

    def test_restore_database_not_found(self, client):
        """测试恢复不存在的备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.restore_database.return_value = False
            mock_dr.return_value = mock_instance
            response = client.post(
                "/api/v1/backup/restore/database?backup_file=/backups/nonexistent.sql"
            )
            assert response.status_code == 500

    def test_list_backups_empty(self, client):
        """测试空备份列表"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.list_backups.return_value = []
            mock_dr.return_value = mock_instance
            response = client.get("/api/v1/backup/list")
            assert response.status_code == 200

    def test_cleanup_old_backups_with_retention(self, client):
        """测试带保留策略的清理"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.cleanup_old_backups.return_value = {
                "deleted_count": 3,
                "retained_count": 10,
            }
            mock_dr.return_value = mock_instance
            response = client.delete("/api/v1/backup/cleanup?days=30&keep_min=10")
            assert response.status_code == 200

    def test_backup_database_success(self, client):
        """测试成功备份数据库"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_database.return_value = "/backups/db_backup_20260702.sql"
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/database")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "backup_file" in data

    def test_backup_redis_success(self, client):
        """测试成功备份Redis"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_redis.return_value = "/backups/redis_backup_20260702.rdb"
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/redis")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_backup_configuration_success(self, client):
        """测试成功备份配置"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_configuration.return_value = "/backups/config_20260702"
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/configuration")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_full_backup_success(self, client):
        """测试完整备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_database.return_value = "/backups/db_backup.sql"
            mock_instance.backup_redis.return_value = "/backups/redis_backup.rdb"
            mock_instance.backup_configuration.return_value = "/backups/config"
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "backups" in data

    def test_restore_database_success(self, client):
        """测试恢复数据库"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.restore_database.return_value = True
            mock_dr.return_value = mock_instance

            response = client.post(
                "/api/v1/backup/restore/database?backup_file=/backups/db_backup.sql"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_list_backups(self, client):
        """测试列出备份文件"""
        response = client.get("/api/v1/backup/list")
        assert response.status_code == 200
        data = response.json()
        assert "backups" in data

    def test_cleanup_old_backups(self, client):
        """测试清理旧备份"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.cleanup_old_backups.return_value = True
            mock_dr.return_value = mock_instance

            response = client.delete("/api/v1/backup/cleanup?retention_days=30")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_backup_redis_failed(self, client):
        """测试Redis备份返回空"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_redis.return_value = ""
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/redis")
            assert response.status_code == 500

    def test_backup_configuration_failed(self, client):
        """测试配置备份返回空"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_configuration.return_value = ""
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/configuration")
            assert response.status_code == 500

    def test_full_backup_failed(self, client):
        """测试完整备份异常"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.backup_database.side_effect = RuntimeError("db error")
            mock_dr.return_value = mock_instance

            response = client.post("/api/v1/backup/full")
            assert response.status_code == 500

    def test_cleanup_old_backups_failed(self, client):
        """测试清理旧备份返回空"""
        with patch("disaster_recovery.DisasterRecovery") as mock_dr:
            mock_instance = Mock()
            mock_instance.cleanup_old_backups.return_value = False
            mock_dr.return_value = mock_instance

            response = client.delete("/api/v1/backup/cleanup?retention_days=30")
            assert response.status_code == 500

    def test_list_backups_with_files(self, client, tmp_path):
        """测试列出实际备份文件"""
        (tmp_path / "a.sql").write_text("data")
        with patch("api.backup_router.Path") as mock_path:
            mock_path.return_value = tmp_path
            response = client.get("/api/v1/backup/list")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] >= 1

    def test_list_backups_error(self, client):
        """测试列出备份异常"""
        with patch("api.backup_router.Path") as mock_path:
            mock_path.side_effect = RuntimeError("io error")
            response = client.get("/api/v1/backup/list")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
