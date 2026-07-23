# -*- coding: utf-8 -*-
"""测试插件系统模块"""

import pytest


class TestPluginSystemModule:
    """测试插件系统模块"""

    def test_plugin_system_module_exists(self):
        """测试插件系统模块存在"""
        from core import plugin_system

        assert plugin_system is not None

    def test_plugin_system_has_enums(self):
        """测试插件系统模块有枚举"""
        from core import plugin_system

        # 检查模块有枚举
        assert hasattr(plugin_system, "PluginType")
        assert hasattr(plugin_system, "PluginStatus")

    def test_plugin_system_has_dataclasses(self):
        """测试插件系统模块有数据类"""
        from core import plugin_system

        # 检查模块有数据类
        assert hasattr(plugin_system, "PluginMetadata")
        assert hasattr(plugin_system, "PluginInfo")

    def test_plugin_system_has_classes(self):
        """测试插件系统模块有类"""
        from core import plugin_system

        # 检查模块有类
        assert hasattr(plugin_system, "BasePlugin")
        assert hasattr(plugin_system, "PluginManager")

    def test_plugin_system_has_functions(self):
        """测试插件系统模块有函数"""
        from core import plugin_system

        # 检查模块有函数
        assert hasattr(plugin_system, "create_plugin_manager")


class TestPluginType:
    """测试插件类型枚举"""

    def test_plugin_type_values(self):
        """测试插件类型值"""
        from core.plugin_system import PluginType

        assert PluginType.COLLECTOR.value == "collector"
        assert PluginType.ANALYZER.value == "analyzer"
        assert PluginType.EXECUTOR.value == "executor"
        assert PluginType.STORAGE.value == "storage"
        assert PluginType.NOTIFIER.value == "notifier"


class TestPluginStatus:
    """测试插件状态枚举"""

    def test_plugin_status_values(self):
        """测试插件状态值"""
        from core.plugin_system import PluginStatus

        assert PluginStatus.LOADED.value == "loaded"
        assert PluginStatus.UNLOADED.value == "unloaded"
        assert PluginStatus.ERROR.value == "error"


class TestPluginMetadata:
    """测试插件元数据数据类"""

    def test_plugin_metadata_creation(self):
        """测试插件元数据创建"""
        from core.plugin_system import (
            PluginMetadata,
            PluginType,
        )

        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.plugin_type == PluginType.COLLECTOR

    def test_plugin_metadata_to_dict(self):
        """测试插件元数据转换为字典"""
        from core.plugin_system import (
            PluginMetadata,
            PluginType,
        )

        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        metadata_dict = metadata.to_dict()

        assert "name" in metadata_dict
        assert "version" in metadata_dict
        assert "plugin_type" in metadata_dict


class TestPluginInfo:
    """测试插件信息数据类"""

    def test_plugin_info_creation(self):
        """测试插件信息创建"""
        from core.plugin_system import (
            PluginInfo,
            PluginMetadata,
            PluginStatus,
            PluginType,
        )

        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        plugin_info = PluginInfo(
            plugin_class=type("TestPlugin", (object,), {}),
            metadata=metadata,
            status=PluginStatus.LOADED,
        )

        assert plugin_info.metadata.name == "Test Plugin"
        assert plugin_info.status == PluginStatus.LOADED

    def test_plugin_info_to_dict(self):
        """测试插件信息转换为字典"""
        from core.plugin_system import (
            PluginInfo,
            PluginMetadata,
            PluginStatus,
            PluginType,
        )

        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

        plugin_info = PluginInfo(
            plugin_class=type("TestPlugin", (object,), {}),
            metadata=metadata,
            status=PluginStatus.LOADED,
        )

        plugin_info_dict = plugin_info.to_dict()

        assert "metadata" in plugin_info_dict
        assert "status" in plugin_info_dict


class TestBasePlugin:
    """测试基础插件类"""

    def test_base_plugin_initialization(self):
        """测试基础插件初始化"""
        from core.plugin_system import BasePlugin

        # Create a concrete plugin for testing
        class TestPlugin(BasePlugin):
            def get_metadata(self):
                from core.plugin_system import (
                    PluginMetadata,
                    PluginType,
                )

                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        plugin = TestPlugin()

        assert plugin.config == {}
        assert plugin._is_initialized is False

    def test_base_plugin_initialization_with_config(self):
        """测试基础插件初始化（带配置）"""
        from core.plugin_system import BasePlugin

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                from core.plugin_system import (
                    PluginMetadata,
                    PluginType,
                )

                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        config = {"key": "value"}
        plugin = TestPlugin(config)

        assert plugin.config == config

    def test_validate_config(self):
        """测试验证配置"""
        from core.plugin_system import BasePlugin

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                from core.plugin_system import (
                    PluginMetadata,
                    PluginType,
                )

                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        plugin = TestPlugin({"key1": "value1", "key2": "value2"})

        result = plugin.validate_config(["key1", "key2"])

        assert result is True

    def test_validate_config_missing_keys(self):
        """测试验证配置（缺少键）"""
        from core.plugin_system import BasePlugin

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                from core.plugin_system import (
                    PluginMetadata,
                    PluginType,
                )

                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        plugin = TestPlugin({"key1": "value1"})

        result = plugin.validate_config(["key1", "key2"])

        assert result is False

    def test_get_status(self):
        """测试获取状态"""
        from core.plugin_system import BasePlugin

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                from core.plugin_system import (
                    PluginMetadata,
                    PluginType,
                )

                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        plugin = TestPlugin({"key": "value"})

        status = plugin.get_status()

        assert "initialized" in status
        assert "running" in status
        assert "config" in status


class TestPluginManager:
    """测试插件管理器类"""

    def test_plugin_manager_initialization(self):
        """测试插件管理器初始化"""
        from core.plugin_system import PluginManager

        manager = PluginManager()

        assert manager.plugin_dirs == []
        assert len(manager._plugins) == 0

    def test_plugin_manager_initialization_with_dirs(self):
        """测试插件管理器初始化（带目录）"""
        from core.plugin_system import PluginManager

        manager = PluginManager(plugin_dirs=["/tmp/plugins"])

        assert manager.plugin_dirs == ["/tmp/plugins"]

    def test_initialize(self):
        """测试初始化"""
        from core.plugin_system import PluginManager

        manager = PluginManager()

        result = manager.initialize()

        assert result is True
        assert manager._is_initialized is True

    def test_register_plugin(self):
        """测试注册插件"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        manager = PluginManager()

        result = manager.register_plugin(TestPlugin)

        assert result is True
        assert "Test Plugin" in manager._plugins

    def test_register_plugin_duplicate(self):
        """测试注册插件（重复）"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        manager = PluginManager()

        manager.register_plugin(TestPlugin)

        result = manager.register_plugin(TestPlugin)

        assert result is False

    def test_load_plugin(self):
        """测试加载插件"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        manager = PluginManager()
        manager.register_plugin(TestPlugin)

        result = manager.load_plugin("Test Plugin")

        assert result is True
        assert manager._plugins["Test Plugin"].instance is not None

    def test_load_plugin_invalid(self):
        """测试加载插件（无效）"""
        from core.plugin_system import PluginManager

        manager = PluginManager()

        result = manager.load_plugin("invalid_plugin")

        assert result is False

    def test_unload_plugin(self):
        """测试卸载插件"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        manager.load_plugin("Test Plugin")

        result = manager.unload_plugin("Test Plugin")

        assert result is True
        assert manager._plugins["Test Plugin"].instance is None

    def test_unload_plugin_invalid(self):
        """测试卸载插件（无效）"""
        from core.plugin_system import PluginManager

        manager = PluginManager()

        result = manager.unload_plugin("invalid_plugin")

        assert result is False

    def test_get_plugin(self):
        """测试获取插件"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        manager = PluginManager()
        manager.register_plugin(TestPlugin)

        plugin = manager.get_plugin("Test Plugin")

        assert plugin is not None
        assert plugin["metadata"]["name"] == "Test Plugin"

    def test_get_plugin_invalid(self):
        """测试获取插件（无效）"""
        from core.plugin_system import PluginManager

        manager = PluginManager()

        plugin = manager.get_plugin("invalid_plugin")

        assert plugin is None

    def test_list_plugins(self):
        """测试列出插件"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        manager = PluginManager()
        manager.register_plugin(TestPlugin)

        plugins = manager.list_plugins()

        assert len(plugins) == 1

    def test_list_plugins_with_filter(self):
        """测试列出插件（带过滤器）"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    plugin_type=PluginType.COLLECTOR,
                    dependencies=[],
                )

            def initialize(self):
                return True

            async def execute(self, data):
                return data

            def close(self):
                pass

        manager = PluginManager()
        manager.register_plugin(TestPlugin)

        plugins = manager.list_plugins(plugin_type=PluginType.COLLECTOR)

        assert len(plugins) == 1

    def test_get_plugin_status(self):
        """测试获取插件状态"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        manager.load_plugin("Test Plugin")

        status = manager.get_plugin_status("Test Plugin")

        assert status is not None
        assert "initialized" in status

    def test_get_plugin_status_invalid(self):
        """测试获取插件状态（无效）"""
        from core.plugin_system import PluginManager

        manager = PluginManager()

        status = manager.get_plugin_status("invalid_plugin")

        assert status is None

    def test_reload_plugin(self):
        """测试重新加载插件"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        manager.load_plugin("Test Plugin")

        result = manager.reload_plugin("Test Plugin")

        assert result is True

    def test_close(self):
        """测试关闭"""
        from core.plugin_system import (
            BasePlugin,
            PluginManager,
            PluginMetadata,
            PluginType,
        )

        class TestPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
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
                return data

            def close(self):
                self._is_initialized = False

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        manager.load_plugin("Test Plugin")

        manager.close()

        assert manager._plugins["Test Plugin"].instance is None


class TestCreatePluginManager:
    """测试创建插件管理器"""

    def test_create_plugin_manager(self):
        """测试创建插件管理器"""
        from core.plugin_system import create_plugin_manager

        manager = create_plugin_manager()

        assert manager is not None
        assert manager._is_initialized is True

    def test_create_plugin_manager_with_dirs(self):
        """测试创建插件管理器（带目录）"""
        from core.plugin_system import create_plugin_manager

        manager = create_plugin_manager(plugin_dirs=["/tmp/plugins"])

        assert manager is not None
        assert manager.plugin_dirs == ["/tmp/plugins"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
