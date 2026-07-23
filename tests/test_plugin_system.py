# -*- coding: utf-8 -*-
# tests/test_plugin_system.py
# 插件系统单元测试
import pytest

from core.plugin_system import (
    BasePlugin,
    PluginInfo,
    PluginManager,
    PluginMetadata,
    PluginStatus,
    PluginType,
    create_plugin_manager,
)


class TestPluginMetadata:
    """插件元数据测试"""

    def test_plugin_metadata_creation(self):
        """测试创建插件元数据"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.plugin_type == PluginType.COLLECTOR

    def test_plugin_metadata_to_dict(self):
        """测试插件元数据转换为字典"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        data = metadata.to_dict()
        assert data["name"] == "test_plugin"
        assert data["plugin_type"] == "collector"


class TestBasePlugin:
    """基础插件测试"""

    def test_base_plugin_initialization(self):
        """测试基础插件初始化"""

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                self._is_initialized = True
                return True

            async def execute(self, data):
                return {"result": "success"}

            def close(self):
                self._is_initialized = False

        plugin = TestPlugin()
        assert plugin.config == {}
        assert plugin._is_initialized is False

    def test_base_plugin_validate_config(self):
        """测试配置验证"""

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return {}

            def close(self):
                pass

        plugin = TestPlugin(config={"key1": "value1", "key2": "value2"})
        assert plugin.validate_config(["key1", "key2"]) is True
        assert plugin.validate_config(["key1", "key3"]) is False

    def test_base_plugin_get_status(self):
        """测试获取插件状态"""

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return {}

            def close(self):
                pass

        plugin = TestPlugin()
        status = plugin.get_status()
        assert status["initialized"] is False
        assert status["running"] is False


class TestPluginInfo:
    """插件信息测试"""

    def test_plugin_info_creation(self):
        """测试创建插件信息"""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        info = PluginInfo(
            plugin_class=BasePlugin,
            metadata=metadata,
            status=PluginStatus.LOADED,
        )

        assert info.metadata.name == "test"
        assert info.status == PluginStatus.LOADED

    def test_plugin_info_to_dict(self):
        """测试插件信息转换为字典"""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        info = PluginInfo(
            plugin_class=BasePlugin,
            metadata=metadata,
            status=PluginStatus.LOADED,
        )

        data = info.to_dict()
        assert data["metadata"]["name"] == "test"
        assert data["status"] == "loaded"


class TestPluginManager:
    """插件管理器测试"""

    def test_plugin_manager_initialization(self):
        """测试插件管理器初始化"""
        manager = PluginManager()
        assert manager.plugin_dirs == []
        assert manager._is_initialized is False

    def test_plugin_manager_initialize(self):
        """测试插件管理器初始化"""
        manager = PluginManager()
        result = manager.initialize()
        assert result is True
        assert manager._is_initialized is True

    def test_plugin_manager_register_plugin(self):
        """测试注册插件"""

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="test_plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return {}

            def close(self):
                pass

        manager = PluginManager()
        result = manager.register_plugin(TestPlugin)
        assert result is True
        assert "test_plugin" in manager._plugins

    def test_plugin_manager_list_plugins(self):
        """测试列出插件"""
        manager = PluginManager()
        manager.initialize()

        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_plugin_manager_list_plugins_by_type(self):
        """测试按类型列出插件"""
        manager = PluginManager()
        manager.initialize()

        plugins = manager.list_plugins(PluginType.COLLECTOR)
        assert isinstance(plugins, list)

    def test_plugin_manager_get_plugin(self):
        """测试获取插件信息"""
        manager = PluginManager()
        manager.initialize()

        # Try to get a non-existent plugin
        plugin = manager.get_plugin("nonexistent")
        assert plugin is None

    def test_plugin_manager_close(self):
        """测试关闭插件管理器"""
        manager = PluginManager()
        manager.initialize()

        manager.close()
        # Should not raise an error


class TestPluginManagerFactory:
    """插件管理器工厂测试"""

    def test_create_plugin_manager(self):
        """测试创建插件管理器"""
        manager = create_plugin_manager()
        assert manager is not None
        assert isinstance(manager, PluginManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
