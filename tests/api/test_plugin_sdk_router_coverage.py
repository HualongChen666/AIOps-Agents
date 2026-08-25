# -*- coding: utf-8 -*-
"""Test coverage for plugin_sdk_router.py to achieve 90%+ coverage."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

# Import the module to ensure coverage tracking
from api import plugin_sdk_router


class TestGetSystemStatus:
    """Tests for get_system_status endpoint."""

    @pytest.mark.asyncio
    async def test_get_system_status_success(self):
        """Test successful system status retrieval."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.get_system_summary.return_value = {
                "total_plugins": 10,
                "active_plugins": 8,
                "total_interfaces": 5,
            }
            mock.return_value = mock_manager
            result = await plugin_sdk_router.get_system_status()
            assert result["status"] == "success"
            assert "data" in result
            assert result["data"]["total_plugins"] == 10
            assert "timestamp" in result
            mock_manager.get_system_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_system_status_exception(self):
        """Test system status with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Manager error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.get_system_status()
            assert exc_info.value.status_code == 500
            assert "Manager error" in str(exc_info.value.detail)


class TestDefinePluginInterface:
    """Tests for define_plugin_interface endpoint."""

    @pytest.mark.asyncio
    async def test_define_plugin_interface_success(self):
        """Test successful interface definition."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.define_plugin_interface.return_value = SimpleNamespace(
                interface_id="test-interface",
                interface_name="Test Interface",
                methods=[{"name": "test_method"}],
                events=[{"name": "test_event"}],
            )
            mock.return_value = mock_manager
            result = await plugin_sdk_router.define_plugin_interface(
                interface_id="test-interface",
                interface_name="Test Interface",
                methods=[{"name": "test_method"}],
                events=[{"name": "test_event"}],
                configuration={"key": "value"},
            )
            assert result["status"] == "success"
            assert result["data"]["interface_id"] == "test-interface"
            assert result["data"]["method_count"] == 1
            assert result["data"]["event_count"] == 1
            assert "timestamp" in result
            mock_manager.define_plugin_interface.assert_called_once()

    @pytest.mark.asyncio
    async def test_define_plugin_interface_empty_params(self):
        """Test interface definition with empty methods and events."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.define_plugin_interface.return_value = SimpleNamespace(
                interface_id="test-interface",
                interface_name="Test Interface",
                methods=[],
                events=[],
            )
            mock.return_value = mock_manager
            result = await plugin_sdk_router.define_plugin_interface(
                interface_id="test-interface",
                interface_name="Test Interface",
                methods=[],
                events=[],
                configuration=None,
            )
            assert result["status"] == "success"
            assert result["data"]["method_count"] == 0
            assert result["data"]["event_count"] == 0

    @pytest.mark.asyncio
    async def test_define_plugin_interface_exception(self):
        """Test interface definition with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Define error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.define_plugin_interface(
                    interface_id="test", interface_name="Test"
                )
            assert exc_info.value.status_code == 500
            assert "Define error" in str(exc_info.value.detail)


class TestGetInterfaceSpec:
    """Tests for get_interface_spec endpoint."""

    @pytest.mark.asyncio
    async def test_get_interface_spec_success(self):
        """Test successful interface spec retrieval."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.generate_plugin_interface_spec.return_value = {
                "interface_type": "data-collector",
                "methods": [{"name": "collect", "params": []}],
                "events": [{"name": "on_data_collected"}],
            }
            mock.return_value = mock_manager
            result = await plugin_sdk_router.get_interface_spec("data-collector")
            assert result["status"] == "success"
            assert "data" in result
            assert result["data"]["interface_type"] == "data-collector"
            assert "timestamp" in result
            mock_manager.generate_plugin_interface_spec.assert_called_once_with("data-collector")

    @pytest.mark.asyncio
    async def test_get_interface_spec_exception(self):
        """Test interface spec retrieval with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Spec error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.get_interface_spec("monitoring")
            assert exc_info.value.status_code == 500
            assert "Spec error" in str(exc_info.value.detail)


class TestRegisterPlugin:
    """Tests for register_plugin endpoint."""

    @pytest.mark.asyncio
    async def test_register_plugin_success(self):
        """Test successful plugin registration."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.register_plugin.return_value = True
            mock.return_value = mock_manager
            result = await plugin_sdk_router.register_plugin(
                plugin_id="test-plugin",
                name="Test Plugin",
                version="1.0.0",
                description="A test plugin",
                author="Test Author",
                plugin_type="monitoring",
                dependencies={"dependencies": ["dep1", "dep2"]},
            )
            assert result["status"] == "success"
            assert result["data"]["plugin_id"] == "test-plugin"
            assert result["data"]["registered"] is True
            assert "timestamp" in result
            mock_manager.register_plugin.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_plugin_without_dependencies(self):
        """Test plugin registration without dependencies."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.register_plugin.return_value = True
            mock.return_value = mock_manager
            result = await plugin_sdk_router.register_plugin(
                plugin_id="test-plugin-2",
                name="Test Plugin 2",
                version="1.0.0",
                description="A test plugin without dependencies",
                author="Test Author",
                plugin_type="integration",
                dependencies=None,
            )
            assert result["status"] == "success"
            assert result["data"]["plugin_id"] == "test-plugin-2"

    @pytest.mark.asyncio
    async def test_register_plugin_with_empty_dependencies_dict(self):
        """Test plugin registration with empty dependencies dict (no 'dependencies' key)."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.register_plugin.return_value = True
            mock.return_value = mock_manager
            result = await plugin_sdk_router.register_plugin(
                plugin_id="test-plugin-3",
                name="Test Plugin 3",
                version="1.0.0",
                description="A test plugin with empty dependencies dict",
                author="Test Author",
                plugin_type="integration",
                dependencies={},
            )
            assert result["status"] == "success"
            assert result["data"]["plugin_id"] == "test-plugin-3"

    @pytest.mark.asyncio
    async def test_register_plugin_exception(self):
        """Test plugin registration with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Register error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.register_plugin(
                    plugin_id="test",
                    name="Test",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type="monitoring",
                )
            assert exc_info.value.status_code == 500
            assert "Register error" in str(exc_info.value.detail)


class TestEnablePlugin:
    """Tests for enable_plugin endpoint."""

    @pytest.mark.asyncio
    async def test_enable_plugin_success(self):
        """Test successful plugin enable."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.enable_plugin.return_value = True
            mock.return_value = mock_manager
            result = await plugin_sdk_router.enable_plugin("test-plugin")
            assert result["status"] == "success"
            assert result["data"]["plugin_id"] == "test-plugin"
            assert result["data"]["enabled"] is True
            assert "timestamp" in result
            mock_manager.enable_plugin.assert_called_once_with("test-plugin")

    @pytest.mark.asyncio
    async def test_enable_plugin_exception(self):
        """Test plugin enable with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Enable error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.enable_plugin("test")
            assert exc_info.value.status_code == 500
            assert "Enable error" in str(exc_info.value.detail)


class TestDisablePlugin:
    """Tests for disable_plugin endpoint."""

    @pytest.mark.asyncio
    async def test_disable_plugin_success(self):
        """Test successful plugin disable."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.disable_plugin.return_value = True
            mock.return_value = mock_manager
            result = await plugin_sdk_router.disable_plugin("test-plugin")
            assert result["status"] == "success"
            assert result["data"]["plugin_id"] == "test-plugin"
            assert result["data"]["disabled"] is True
            assert "timestamp" in result
            mock_manager.disable_plugin.assert_called_once_with("test-plugin")

    @pytest.mark.asyncio
    async def test_disable_plugin_exception(self):
        """Test plugin disable with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Disable error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.disable_plugin("test")
            assert exc_info.value.status_code == 500
            assert "Disable error" in str(exc_info.value.detail)


class TestListPlugins:
    """Tests for list_plugins endpoint."""

    @pytest.mark.asyncio
    async def test_list_plugins_success(self):
        """Test successful plugin listing without filters."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_plugins.return_value = [
                {"plugin_id": "p1", "name": "Plugin 1", "status": "enabled"}
            ]
            mock.return_value = mock_manager
            result = await plugin_sdk_router.list_plugins()
            assert result["status"] == "success"
            assert "plugins" in result["data"]
            assert result["data"]["count"] == 1
            assert "timestamp" in result
            mock_manager.list_plugins.assert_called_once_with(None, None)

    @pytest.mark.asyncio
    async def test_list_plugins_with_filters(self):
        """Test plugin listing with type and status filters."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_plugins.return_value = [
                {"plugin_id": "p1", "name": "Plugin 1", "status": "enabled"}
            ]
            mock.return_value = mock_manager
            result = await plugin_sdk_router.list_plugins(
                plugin_type="monitoring", status="enabled"
            )
            assert result["status"] == "success"
            mock_manager.list_plugins.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_plugins_with_type_only(self):
        """Test plugin listing with only type filter."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_plugins.return_value = [
                {"plugin_id": "p1", "name": "Plugin 1", "status": "enabled"}
            ]
            mock.return_value = mock_manager
            result = await plugin_sdk_router.list_plugins(plugin_type="monitoring", status=None)
            assert result["status"] == "success"
            mock_manager.list_plugins.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_plugins_with_status_only(self):
        """Test plugin listing with only status filter."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_plugins.return_value = [
                {"plugin_id": "p1", "name": "Plugin 1", "status": "enabled"}
            ]
            mock.return_value = mock_manager
            result = await plugin_sdk_router.list_plugins(plugin_type=None, status="enabled")
            assert result["status"] == "success"
            mock_manager.list_plugins.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_plugins_exception(self):
        """Test plugin listing with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("List error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.list_plugins()
            assert exc_info.value.status_code == 500
            assert "List error" in str(exc_info.value.detail)


class TestGetPluginInfo:
    """Tests for get_plugin_info endpoint."""

    @pytest.mark.asyncio
    async def test_get_plugin_info_success(self):
        """Test successful plugin info retrieval."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.get_plugin_info.return_value = {
                "plugin_id": "p1",
                "name": "Plugin 1",
                "version": "1.0.0",
            }
            mock.return_value = mock_manager
            result = await plugin_sdk_router.get_plugin_info("p1")
            assert result["status"] == "success"
            assert result["data"]["plugin_id"] == "p1"
            assert result["data"]["name"] == "Plugin 1"
            assert "timestamp" in result
            mock_manager.get_plugin_info.assert_called_once_with("p1")

    @pytest.mark.asyncio
    async def test_get_plugin_info_not_found(self):
        """Test plugin info retrieval for non-existent plugin."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.get_plugin_info.return_value = None
            mock.return_value = mock_manager
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.get_plugin_info("non-existent")
            assert exc_info.value.status_code == 404
            assert "Plugin not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_plugin_info_exception(self):
        """Test plugin info retrieval with exception."""
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock:
            mock.side_effect = Exception("Info error")
            with pytest.raises(HTTPException) as exc_info:
                await plugin_sdk_router.get_plugin_info("test")
            assert exc_info.value.status_code == 500
            assert "Info error" in str(exc_info.value.detail)
