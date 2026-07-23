# -*- coding: utf-8 -*-
# tests/test_backup_strategy.py
# 备份策略单元测试
import pytest

from core.backup_strategy import (
    cleanup_old_backups,
    configure_backup_strategy,
    get_backup_config,
    get_backup_history,
    get_backup_statistics,
    get_recent_backups,
    is_backup_enabled,
    perform_config_backup,
    perform_database_backup,
    perform_full_backup,
    perform_logs_backup,
    restore_backup,
)


class TestBackupConfiguration:
    """备份配置测试"""

    def test_configure_backup_strategy(self):
        """测试配置备份策略"""
        configure_backup_strategy(
            backup_interval_hours=12,
            retention_days=7,
            backup_location="/test/backups",
            compression_enabled=True,
            encryption_enabled=False,
            backup_types=["database", "config"],
        )

        assert is_backup_enabled() is True
        config = get_backup_config()
        assert config["backup_interval_hours"] == 12
        assert config["retention_days"] == 7
        assert config["backup_location"] == "/test/backups"

    def test_get_backup_config(self):
        """测试获取备份配置"""
        configure_backup_strategy()

        config = get_backup_config()
        assert config["enabled"] is True
        assert "backup_interval_hours" in config
        assert "retention_days" in config

    def test_is_backup_enabled(self):
        """测试检查备份是否启用"""
        # Reset to default state first
        from core.backup_strategy import _backup_config

        _backup_config["enabled"] = False

        assert is_backup_enabled() is False  # Should be disabled after reset

        configure_backup_strategy()
        assert is_backup_enabled() is True


class TestBackupExecution:
    """备份执行测试"""

    @pytest.mark.asyncio
    async def test_perform_database_backup(self):
        """测试执行数据库备份"""
        configure_backup_strategy(backup_location="/test/backups")

        result = await perform_database_backup()

        assert result is not None
        assert result["type"] == "database"
        assert "backup_id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_perform_config_backup(self):
        """测试执行配置备份"""
        configure_backup_strategy(backup_location="/test/backups")

        result = await perform_config_backup()

        assert result is not None
        assert result["type"] == "config"
        assert "backup_id" in result

    @pytest.mark.asyncio
    async def test_perform_logs_backup(self):
        """测试执行日志备份"""
        configure_backup_strategy(backup_location="/test/backups")

        result = await perform_logs_backup()

        assert result is not None
        assert result["type"] == "logs"
        assert "backup_id" in result

    @pytest.mark.asyncio
    async def test_perform_full_backup(self):
        """测试执行完整备份"""
        configure_backup_strategy(
            backup_location="/test/backups",
            backup_types=["database", "config"],
        )

        result = await perform_full_backup()

        assert result is not None
        assert "backup_id" in result
        assert "results" in result
        assert "database" in result["results"]
        assert "config" in result["results"]


class TestBackupManagement:
    """备份管理测试"""

    def test_get_backup_history(self):
        """测试获取备份历史"""
        history = get_backup_history()
        assert isinstance(history, list)

    def test_get_recent_backups(self):
        """测试获取最近的备份"""
        recent = get_recent_backups(5)
        assert isinstance(recent, list)
        assert len(recent) <= 5

    def test_get_backup_statistics_empty(self):
        """测试获取备份统计（空历史）"""
        # Reset backup history
        from core.backup_strategy import _backup_history

        _backup_history.clear()

        stats = get_backup_statistics()

        assert stats["total_backups"] == 0
        assert stats["successful_backups"] == 0
        assert stats["last_backup"] is None

    @pytest.mark.asyncio
    async def test_get_backup_statistics_with_backups(self):
        """测试获取备份统计（有备份）"""
        configure_backup_strategy(backup_location="/test/backups")

        # Perform some backups
        await perform_database_backup()
        await perform_config_backup()

        stats = get_backup_statistics()

        assert stats["total_backups"] > 0
        assert stats["successful_backups"] > 0
        assert stats["last_backup"] is not None


class TestBackupCleanup:
    """备份清理测试"""

    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self):
        """测试清理旧备份"""
        configure_backup_strategy(
            backup_location="/test/backups",
            retention_days=1,
        )

        # Perform some backups
        await perform_database_backup()
        await perform_config_backup()

        cleaned = await cleanup_old_backups()

        assert isinstance(cleaned, int)
        assert cleaned >= 0


class TestBackupRestore:
    """备份恢复测试"""

    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self):
        """测试恢复不存在的备份"""
        result = await restore_backup("nonexistent_backup")

        assert result is not None
        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_restore_backup_success(self):
        """测试成功恢复备份"""
        configure_backup_strategy(backup_location="/test/backups")

        # Create a backup
        backup_result = await perform_database_backup()
        backup_id = backup_result["backup_id"]

        # Restore from backup
        restore_result = await restore_backup(backup_id)

        assert restore_result is not None
        assert restore_result["backup_id"] == backup_id
        assert restore_result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
