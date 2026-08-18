# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/backup_strategy.py
Target: 90%+ statement and branch coverage
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.backup_strategy import (
    configure_backup_strategy,
    get_backup_config,
    is_backup_enabled,
    perform_database_backup,
    perform_config_backup,
    perform_logs_backup,
    perform_full_backup,
    cleanup_old_backups,
    get_backup_history,
    get_recent_backups,
    get_backup_statistics,
    calculate_file_hash,
    verify_backup_integrity,
    encrypt_file,
    decrypt_file,
    _backup_config,
    _backup_history,
)


class TestBackupConfiguration:
    """Test suite for backup configuration functions"""

    def test_configure_backup_strategy_defaults(self):
        """Test configure_backup_strategy with default values"""
        configure_backup_strategy()
        
        assert _backup_config["enabled"] is True
        assert _backup_config["backup_interval_hours"] == 24
        assert _backup_config["retention_days"] == 30
        assert _backup_config["backup_location"] == "/backups"
        assert _backup_config["compression_enabled"] is True
        assert _backup_config["encryption_enabled"] is False
        assert _backup_config["backup_types"] == ["database", "config", "logs"]

    def test_configure_backup_strategy_custom(self):
        """Test configure_backup_strategy with custom values"""
        configure_backup_strategy(
            backup_interval_hours=12,
            retention_days=7,
            backup_location="/custom/backups",
            compression_enabled=False,
            encryption_enabled=True,
            backup_types=["database"]
        )
        
        assert _backup_config["backup_interval_hours"] == 12
        assert _backup_config["retention_days"] == 7
        assert _backup_config["backup_location"] == "/custom/backups"
        assert _backup_config["compression_enabled"] is False
        assert _backup_config["encryption_enabled"] is True
        assert _backup_config["backup_types"] == ["database"]

    def test_get_backup_config(self):
        """Test get_backup_config returns copy"""
        configure_backup_strategy()
        config = get_backup_config()
        
        assert config["enabled"] is True
        # Modify returned config should not affect original
        config["enabled"] = False
        assert _backup_config["enabled"] is True

    def test_is_backup_enabled(self):
        """Test is_backup_enabled"""
        configure_backup_strategy()
        assert is_backup_enabled() is True
        
        _backup_config["enabled"] = False
        assert is_backup_enabled() is False


class TestCalculateFileHash:
    """Test suite for calculate_file_hash function"""

    def test_calculate_file_hash_sha256(self):
        """Test SHA256 hash calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = f.name
        
        try:
            hash_result = calculate_file_hash(temp_path, "sha256")
            assert len(hash_result) == 64
            assert all(c in "0123456789abcdef" for c in hash_result)
        finally:
            os.unlink(temp_path)

    def test_calculate_file_hash_md5(self):
        """Test MD5 hash calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = f.name
        
        try:
            hash_result = calculate_file_hash(temp_path, "md5")
            assert len(hash_result) == 32
        finally:
            os.unlink(temp_path)

    def test_calculate_file_hash_sha1(self):
        """Test SHA1 hash calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = f.name
        
        try:
            hash_result = calculate_file_hash(temp_path, "sha1")
            assert len(hash_result) == 40
        finally:
            os.unlink(temp_path)

    def test_calculate_file_hash_consistency(self):
        """Test that same file produces same hash"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = f.name
        
        try:
            hash1 = calculate_file_hash(temp_path)
            hash2 = calculate_file_hash(temp_path)
            assert hash1 == hash2
        finally:
            os.unlink(temp_path)


class TestVerifyBackupIntegrity:
    """Test suite for verify_backup_integrity function"""

    def test_verify_backup_integrity_valid(self):
        """Test verification with valid hash"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = f.name
        
        try:
            expected_hash = calculate_file_hash(temp_path)
            result = verify_backup_integrity(temp_path, expected_hash)
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_verify_backup_integrity_invalid(self):
        """Test verification with invalid hash"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = f.name
        
        try:
            result = verify_backup_integrity(temp_path, "invalidhash")
            assert result is False
        finally:
            os.unlink(temp_path)

    def test_verify_backup_integrity_file_not_found(self):
        """Test verification with non-existent file"""
        result = verify_backup_integrity("/nonexistent/file", "hash")
        assert result is False


class TestEncryptDecryptFile:
    """Test suite for encrypt_file and decrypt_file functions"""

    def test_encrypt_file_no_cryptography(self):
        """Test encrypt_file when cryptography not available"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            input_path = f.name
        
        output_path = input_path + ".enc"
        
        try:
            with patch('core.backup_strategy.cryptography', None):
                result = encrypt_file(input_path, output_path)
                assert result is True
                # Should copy file unencrypted
                assert os.path.exists(output_path)
        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_decrypt_file_no_cryptography(self):
        """Test decrypt_file when cryptography not available"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            input_path = f.name
        
        output_path = input_path + ".dec"
        
        try:
            with patch('core.backup_strategy.cryptography', None):
                result = decrypt_file(input_path, output_path)
                assert result is True
                assert os.path.exists(output_path)
        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestPerformDatabaseBackup:
    """Test suite for perform_database_backup function"""

    @pytest.mark.asyncio
    async def test_perform_database_backup_success(self):
        """Test successful database backup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = False
            _backup_config["encryption_enabled"] = False
            _backup_config["integrity_check_enabled"] = False
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.POSTGRES_DB = "testdb"
                mock_config.POSTGRES_USER = "testuser"
                mock_config.POSTGRES_HOST = "localhost"
                mock_config.POSTGRES_PORT = "5432"
                mock_config.POSTGRES_PASSWORD = "testpass"
                
                # Mock pg_dump execution
                with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(return_value=(b"SQL content", b""))
                    mock_subprocess.return_value = mock_process
                    
                    result = await perform_database_backup()
                    
                    assert result["status"] == "success"
                    assert result["type"] == "database"
                    assert "backup_id" in result
                    assert "path" in result

    @pytest.mark.asyncio
    async def test_perform_database_backup_pg_dump_failure(self):
        """Test database backup when pg_dump fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = False
            _backup_config["encryption_enabled"] = False
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.POSTGRES_DB = "testdb"
                mock_config.POSTGRES_USER = "testuser"
                mock_config.POSTGRES_HOST = "localhost"
                mock_config.POSTGRES_PORT = "5432"
                mock_config.POSTGRES_PASSWORD = "testpass"
                
                with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                    mock_process = AsyncMock()
                    mock_process.returncode = 1
                    mock_process.communicate = AsyncMock(return_value=(b"", b"Error occurred"))
                    mock_subprocess.return_value = mock_process
                    
                    result = await perform_database_backup()
                    
                    assert result["status"] == "failed"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_perform_database_backup_with_compression(self):
        """Test database backup with compression enabled"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = True
            _backup_config["encryption_enabled"] = False
            _backup_config["integrity_check_enabled"] = False
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.POSTGRES_DB = "testdb"
                mock_config.POSTGRES_USER = "testuser"
                mock_config.POSTGRES_HOST = "localhost"
                mock_config.POSTGRES_PORT = "5432"
                mock_config.POSTGRES_PASSWORD = "testpass"
                
                with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(return_value=(b"SQL content", b""))
                    mock_subprocess.return_value = mock_process
                    
                    result = await perform_database_backup()
                    
                    assert result["status"] == "success"
                    assert result["compressed"] is True

    @pytest.mark.asyncio
    async def test_perform_database_backup_with_encryption(self):
        """Test database backup with encryption enabled"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = False
            _backup_config["encryption_enabled"] = True
            _backup_config["integrity_check_enabled"] = False
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.POSTGRES_DB = "testdb"
                mock_config.POSTGRES_USER = "testuser"
                mock_config.POSTGRES_HOST = "localhost"
                mock_config.POSTGRES_PORT = "5432"
                mock_config.POSTGRES_PASSWORD = "testpass"
                
                with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(return_value=(b"SQL content", b""))
                    mock_subprocess.return_value = mock_process
                    
                    with patch('core.backup_strategy.encrypt_file', return_value=True):
                        result = await perform_database_backup()
                        
                        assert result["status"] == "success"
                        assert result["encrypted"] is True

    @pytest.mark.asyncio
    async def test_perform_database_backup_integrity_check_failure(self):
        """Test database backup when integrity check fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = False
            _backup_config["encryption_enabled"] = False
            _backup_config["integrity_check_enabled"] = True
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.POSTGRES_DB = "testdb"
                mock_config.POSTGRES_USER = "testuser"
                mock_config.POSTGRES_HOST = "localhost"
                mock_config.POSTGRES_PORT = "5432"
                mock_config.POSTGRES_PASSWORD = "testpass"
                
                with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(return_value=(b"SQL content", b""))
                    mock_subprocess.return_value = mock_process
                    
                    with patch('core.backup_strategy.verify_backup_integrity', return_value=False):
                        result = await perform_database_backup()
                        
                        assert result["status"] == "failed"
                        assert "integrity" in result["error"].lower()


class TestPerformConfigBackup:
    """Test suite for perform_config_backup function"""

    @pytest.mark.asyncio
    async def test_perform_config_backup_success(self):
        """Test successful config backup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = False
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.__file__ = None
                
                result = await perform_config_backup()
                
                assert result["status"] == "success"
                assert result["type"] == "config"
                assert "backup_id" in result

    @pytest.mark.asyncio
    async def test_perform_config_backup_with_compression(self):
        """Test config backup with compression"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = True
            
            with patch('core.backup_strategy.config') as mock_config:
                mock_config.__file__ = None
                
                result = await perform_config_backup()
                
                assert result["status"] == "success"
                assert result["path"].endswith(".tar.gz")


class TestPerformLogsBackup:
    """Test suite for perform_logs_backup function"""

    @pytest.mark.asyncio
    async def test_perform_logs_backup_success(self):
        """Test successful logs backup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = False
            
            result = await perform_logs_backup()
            
            assert result["status"] == "success"
            assert result["type"] == "logs"
            assert "backup_id" in result

    @pytest.mark.asyncio
    async def test_perform_logs_backup_with_compression(self):
        """Test logs backup with compression"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _backup_config["backup_location"] = temp_dir
            _backup_config["compression_enabled"] = True
            
            result = await perform_logs_backup()
            
            assert result["status"] == "success"
            assert result["path"].endswith(".tar.gz")


class TestPerformFullBackup:
    """Test suite for perform_full_backup function"""

    @pytest.mark.asyncio
    async def test_perform_full_backup_all_types(self):
        """Test full backup with all backup types"""
        _backup_config["backup_types"] = ["database", "config", "logs"]
        
        with patch('core.backup_strategy.perform_database_backup') as mock_db:
            mock_db.return_value = {"status": "success", "type": "database"}
        
        with patch('core.backup_strategy.perform_config_backup') as mock_config:
            mock_config.return_value = {"status": "success", "type": "config"}
        
        with patch('core.backup_strategy.perform_logs_backup') as mock_logs:
            mock_logs.return_value = {"status": "success", "type": "logs"}
        
        result = await perform_full_backup()
        
        assert result["overall_status"] == "success"
        assert "database" in result["results"]
        assert "config" in result["results"]
        assert "logs" in result["results"]

    @pytest.mark.asyncio
    async def test_perform_full_backup_partial_failure(self):
        """Test full backup with partial failures"""
        _backup_config["backup_types"] = ["database", "config", "logs"]
        
        with patch('core.backup_strategy.perform_database_backup') as mock_db:
            mock_db.return_value = {"status": "success", "type": "database"}
        
        with patch('core.backup_strategy.perform_config_backup') as mock_config:
            mock_config.return_value = {"status": "failed", "type": "config"}
        
        with patch('core.backup_strategy.perform_logs_backup') as mock_logs:
            mock_logs.return_value = {"status": "success", "type": "logs"}
        
        result = await perform_full_backup()
        
        assert result["overall_status"] == "partial"

    @pytest.mark.asyncio
    async def test_perform_full_backup_custom_types(self):
        """Test full backup with custom backup types"""
        _backup_config["backup_types"] = ["database"]
        
        with patch('core.backup_strategy.perform_database_backup') as mock_db:
            mock_db.return_value = {"status": "success", "type": "database"}
        
        result = await perform_full_backup()
        
        assert "database" in result["results"]
        assert "config" not in result["results"]


class TestCleanupOldBackups:
    """Test suite for cleanup_old_backups function"""

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_empty_history(self):
        """Test cleanup with empty backup history"""
        _backup_history.clear()
        
        result = await cleanup_old_backups()
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_with_old_backups(self):
        """Test cleanup removes old backups"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create old backup entry
            old_time = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
            old_backup = {
                "backup_id": "old_backup",
                "type": "database",
                "status": "success",
                "path": os.path.join(temp_dir, "old_backup"),
                "timestamp": old_time
            }
            
            # Create recent backup entry
            recent_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            recent_backup = {
                "backup_id": "recent_backup",
                "type": "database",
                "status": "success",
                "path": os.path.join(temp_dir, "recent_backup"),
                "timestamp": recent_time
            }
            
            _backup_history.extend([old_backup, recent_backup])
            _backup_config["retention_days"] = 30
            
            # Create actual files
            with open(old_backup["path"], 'w') as f:
                f.write("old")
            with open(recent_backup["path"], 'w') as f:
                f.write("recent")
            
            result = await cleanup_old_backups()
            
            assert result >= 1
            assert len(_backup_history) == 1
            assert _backup_history[0]["backup_id"] == "recent_backup"

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_file_not_found(self):
        """Test cleanup handles missing files gracefully"""
        old_time = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        old_backup = {
            "backup_id": "old_backup",
            "type": "database",
            "status": "success",
            "path": "/nonexistent/path",
            "timestamp": old_time
        }
        
        _backup_history.append(old_backup)
        _backup_config["retention_days"] = 30
        
        result = await cleanup_old_backups()
        
        # Should still count as cleaned even if file doesn't exist
        assert result >= 1


class TestGetBackupHistory:
    """Test suite for get_backup_history function"""

    def test_get_backup_history_empty(self):
        """Test getting empty backup history"""
        _backup_history.clear()
        
        result = get_backup_history()
        
        assert result == []
        assert result is not _backup_history  # Should return copy

    def test_get_backup_history_with_data(self):
        """Test getting backup history with data"""
        _backup_history.clear()
        _backup_history.append({"backup_id": "1", "status": "success"})
        _backup_history.append({"backup_id": "2", "status": "success"})
        
        result = get_backup_history()
        
        assert len(result) == 2
        assert result is not _backup_history


class TestGetRecentBackups:
    """Test suite for get_recent_backups function"""

    def test_get_recent_backups_default_limit(self):
        """Test getting recent backups with default limit"""
        _backup_history.clear()
        for i in range(20):
            _backup_history.append({"backup_id": str(i), "status": "success"})
        
        result = get_recent_backups()
        
        assert len(result) == 10
        assert result[0]["backup_id"] == "10"
        assert result[-1]["backup_id"] == "19"

    def test_get_recent_backups_custom_limit(self):
        """Test getting recent backups with custom limit"""
        _backup_history.clear()
        for i in range(10):
            _backup_history.append({"backup_id": str(i), "status": "success"})
        
        result = get_recent_backups(count=5)
        
        assert len(result) == 5
        assert result[0]["backup_id"] == "5"
        assert result[-1]["backup_id"] == "9"

    def test_get_recent_backups_empty(self):
        """Test getting recent backups when empty"""
        _backup_history.clear()
        
        result = get_recent_backups()
        
        assert result == []


class TestGetBackupStatistics:
    """Test suite for get_backup_statistics function"""

    def test_get_backup_statistics_empty(self):
        """Test getting statistics with no backups"""
        _backup_history.clear()
        
        result = get_backup_statistics()
        
        assert result["total_backups"] == 0
        assert result["successful_backups"] == 0
        assert result["failed_backups"] == 0
        assert result["success_rate"] == "0.00%"
        assert result["total_size_bytes"] == 0
        assert result["last_backup_time"] is None

    def test_get_backup_statistics_with_data(self):
        """Test getting statistics with backup data"""
        _backup_history.clear()
        _backup_history.append({
            "backup_id": "1",
            "type": "database",
            "status": "success",
            "size_bytes": 1000,
            "duration_seconds": 10.0
        })
        _backup_history.append({
            "backup_id": "2",
            "type": "config",
            "status": "success",
            "size_bytes": 500,
            "duration_seconds": 5.0
        })
        _backup_history.append({
            "backup_id": "3",
            "type": "logs",
            "status": "failed"
        })
        
        result = get_backup_statistics()
        
        assert result["total_backups"] == 3
        assert result["successful_backups"] == 2
        assert result["failed_backups"] == 1
        assert result["success_rate"] == "66.67%"
        assert result["total_size_bytes"] == 1500
        assert result["average_duration_seconds"] == "7.50"

    def test_get_backup_statistics_by_type(self):
        """Test statistics breakdown by backup type"""
        _backup_history.clear()
        _backup_history.append({
            "backup_id": "1",
            "type": "database",
            "status": "success",
            "size_bytes": 1000
        })
        _backup_history.append({
            "backup_id": "2",
            "type": "database",
            "status": "failed"
        })
        _backup_history.append({
            "backup_id": "3",
            "type": "config",
            "status": "success",
            "size_bytes": 500
        })
        
        result = get_backup_statistics()
        
        assert "backup_types" in result
        assert "database" in result["backup_types"]
        assert "config" in result["backup_types"]
        assert result["backup_types"]["database"]["total"] == 2
        assert result["backup_types"]["database"]["successful"] == 1
        assert result["backup_types"]["database"]["failed"] == 1
