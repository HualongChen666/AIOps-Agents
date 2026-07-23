# -*- coding: utf-8 -*-
"""
Enhanced L4 Storage Manager Tests
Direct testing of storage manager functionality without heavy mocking
"""

from unittest.mock import Mock, patch

import pytest

from core.storage.l4.storage_manager import L4StorageManager


class TestL4StorageManagerDirect:
    """Direct testing of L4 Storage Manager"""

    def test_manager_initialization_empty_config(self):
        """Test manager initialization with empty config"""
        manager = L4StorageManager({})
        assert manager.config == {}
        assert manager.victoriametrics is None
        assert manager.loki is None
        assert manager.tempo is None
        assert manager._is_initialized is False

    def test_manager_initialization_with_config(self):
        """Test manager initialization with config"""
        config = {
            "victoriametrics": {"enabled": False},
            "loki": {"enabled": False},
            "tempo": {"enabled": False},
        }
        manager = L4StorageManager(config)
        assert manager.config == config
        assert manager._is_initialized is False

    def test_initialize_no_backends_enabled(self):
        """Test initialization when no backends are enabled"""
        manager = L4StorageManager({})
        result = manager.initialize()
        assert result is True
        assert manager._is_initialized is True
        # All backends should remain None
        assert manager.victoriametrics is None
        assert manager.loki is None
        assert manager.tempo is None

    def test_initialize_single_backend_enabled(self):
        """Test initialization with only one backend enabled"""
        config = {"victoriametrics": {"enabled": True, "base_url": "http://localhost:8428"}}
        manager = L4StorageManager(config)

        # Mock the VictoriaMetricsStorage to avoid actual connection
        with patch("core.storage.l4.storage_manager.VictoriaMetricsStorage") as mock_vm:
            mock_vm_instance = Mock()
            mock_vm_instance.initialize.return_value = True
            mock_vm.return_value = mock_vm_instance

            result = manager.initialize()

            assert result is True
            assert manager._is_initialized is True
            assert manager.victoriametrics is not None
            assert manager.loki is None
            assert manager.tempo is None

    def test_get_victoriametrics_none(self):
        """Test getting VictoriaMetrics when not initialized"""
        manager = L4StorageManager({})
        assert manager.get_victoriametrics() is None

    def test_get_loki_none(self):
        """Test getting Loki when not initialized"""
        manager = L4StorageManager({})
        assert manager.get_loki() is None

    def test_get_tempo_none(self):
        """Test getting Tempo when not initialized"""
        manager = L4StorageManager({})
        assert manager.get_tempo() is None

    def test_get_status_not_initialized(self):
        """Test getting status when not initialized"""
        manager = L4StorageManager({})
        status = manager.get_status()
        assert status["initialized"] is False
        assert status["victoriametrics"] is None
        assert status["loki"] is None
        assert status["tempo"] is None

    def test_get_status_initialized(self):
        """Test getting status when initialized"""
        manager = L4StorageManager({})
        manager.initialize()
        status = manager.get_status()
        assert status["initialized"] is True
        # All backends should be None since none are enabled
        assert status["victoriametrics"] is None
        assert status["loki"] is None
        assert status["tempo"] is None

    def test_close_not_initialized(self):
        """Test close when not initialized"""
        manager = L4StorageManager({})
        # Should not raise any exception
        manager.close()
        assert manager._is_initialized is False

    def test_close_initialized(self):
        """Test close when initialized"""
        manager = L4StorageManager({})
        manager.initialize()
        manager.close()
        # After close, _is_initialized flag is reset by close() method
        assert manager._is_initialized is False

    def test_initialize_with_partial_config(self):
        """Test initialization with partial configuration"""
        config = {"victoriametrics": {"enabled": True}, "loki": {"enabled": False}}
        manager = L4StorageManager(config)

        with patch("core.storage.l4.storage_manager.VictoriaMetricsStorage") as mock_vm:
            mock_vm_instance = Mock()
            mock_vm_instance.initialize.return_value = True
            mock_vm.return_value = mock_vm_instance

            result = manager.initialize()

            assert result is True
            assert manager.victoriametrics is not None
            assert manager.loki is None
            assert manager.tempo is None


class TestL4StorageManagerErrorHandling:
    """Test error handling in L4 Storage Manager"""

    def test_initialize_with_exception(self):
        """Test initialization when an exception occurs"""
        config = {"victoriametrics": {"enabled": True}}
        manager = L4StorageManager(config)

        with patch("core.storage.l4.storage_manager.VictoriaMetricsStorage") as mock_vm:
            mock_vm.side_effect = Exception("Connection failed")

            result = manager.initialize()

            # Should handle exception gracefully
            assert result is False
            assert manager._is_initialized is False

    def test_backend_initialization_failure(self):
        """Test when backend initialization fails"""
        config = {"victoriametrics": {"enabled": True}}
        manager = L4StorageManager(config)

        with patch("core.storage.l4.storage_manager.VictoriaMetricsStorage") as mock_vm:
            mock_vm_instance = Mock()
            mock_vm_instance.initialize.return_value = False
            mock_vm.return_value = mock_vm_instance

            result = manager.initialize()

            # Should still return True as initialization completes
            assert result is True
            assert manager._is_initialized is True
            # But backend should be set even if initialization failed
            assert manager.victoriametrics is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
