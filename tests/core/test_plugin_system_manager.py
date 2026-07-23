# -*- coding: utf-8 -*-
"""测试插件系统管理器模块"""

import pytest


class TestPluginSystemManagerModule:
    """测试插件系统管理器模块"""

    def test_plugin_system_manager_module_exists(self):
        """测试插件系统管理器模块存在"""
        from core import plugin_system_manager

        assert plugin_system_manager is not None

    def test_plugin_system_manager_has_enums(self):
        """测试插件系统管理器模块有枚举"""
        from core import plugin_system_manager

        # 检查模块有枚举
        assert hasattr(plugin_system_manager, "PluginStatus")
        assert hasattr(plugin_system_manager, "PluginType")

    def test_plugin_system_manager_has_dataclasses(self):
        """测试插件系统管理器模块有数据类"""
        from core import plugin_system_manager

        # 检查模块有数据类
        assert hasattr(plugin_system_manager, "PluginMetadata")
        assert hasattr(plugin_system_manager, "PluginInterface")
        assert hasattr(plugin_system_manager, "PluginDependency")

    def test_plugin_system_manager_has_classes(self):
        """测试插件系统管理器模块有类"""
        from core import plugin_system_manager

        # 检查模块有类
        assert hasattr(plugin_system_manager, "PluginSystemManager")

    def test_plugin_system_manager_has_functions(self):
        """测试插件系统管理器模块有函数"""
        from core import plugin_system_manager

        # 检查模块有函数
        assert hasattr(plugin_system_manager, "get_plugin_system_manager")


class TestPluginStatus:
    """测试插件状态枚举"""

    def test_plugin_status_values(self):
        """测试插件状态值"""
        from core.plugin_system_manager import PluginStatus

        assert PluginStatus.INSTALLED.value == "installed"
        assert PluginStatus.ENABLED.value == "enabled"
        assert PluginStatus.DISABLED.value == "disabled"
        assert PluginStatus.ERROR.value == "error"
        assert PluginStatus.LOADING.value == "loading"
        assert PluginStatus.UNLOADED.value == "unloaded"


class TestPluginType:
    """测试插件类型枚举"""

    def test_plugin_type_values(self):
        """测试插件类型值"""
        from core.plugin_system_manager import PluginType

        assert PluginType.MONITORING.value == "monitoring"
        assert PluginType.INTEGRATION.value == "integration"
        assert PluginType.AI.value == "ai"
        assert PluginType.CUSTOM.value == "custom"


class TestPluginMetadata:
    """测试插件元数据数据类"""

    def test_plugin_metadata_creation(self):
        """测试插件元数据创建"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginType,
        )

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        assert metadata.plugin_id == "plugin_1"
        assert metadata.name == "Test Plugin"
        assert metadata.plugin_type == PluginType.MONITORING


class TestPluginInterface:
    """测试插件接口数据类"""

    def test_plugin_interface_creation(self):
        """测试插件接口创建"""
        from core.plugin_system_manager import PluginInterface

        interface = PluginInterface(
            interface_id="interface_1",
            interface_name="Test Interface",
            methods=[],
            events=[],
            configuration={},
        )

        assert interface.interface_id == "interface_1"
        assert interface.interface_name == "Test Interface"


class TestPluginDependency:
    """测试插件依赖数据类"""

    def test_plugin_dependency_creation(self):
        """测试插件依赖创建"""
        from core.plugin_system_manager import PluginDependency

        dependency = PluginDependency(
            plugin_id="dep_1",
            version_constraint=">=1.0.0",
        )

        assert dependency.plugin_id == "dep_1"
        assert dependency.version_constraint == ">=1.0.0"


class TestPluginSystemManager:
    """测试插件系统管理器类"""

    def test_plugin_system_manager_initialization(self):
        """测试插件系统管理器初始化"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        assert manager.config == {}
        assert len(manager.plugins) == 0
        assert len(manager.plugin_metadata) == 0

    def test_plugin_system_manager_initialization_with_config(self):
        """测试插件系统管理器初始化（带配置）"""
        from core.plugin_system_manager import PluginSystemManager

        config = {"system_version": "2.0", "plugin_directory": "/tmp/plugins"}
        manager = PluginSystemManager(config)

        assert manager.config == config
        assert manager.system_version == "2.0"
        assert manager.plugin_directory == "/tmp/plugins"

    def test_define_plugin_interface(self):
        """测试定义插件接口"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        interface = manager.define_plugin_interface(
            interface_id="interface_1",
            interface_name="Test Interface",
            methods=[],
            events=[],
        )

        assert interface.interface_id == "interface_1"
        assert "interface_1" in manager.interfaces

    def test_generate_plugin_interface_spec_monitoring(self):
        """测试生成插件接口规范（监控）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        spec = manager.generate_plugin_interface_spec("monitoring")

        assert spec["interface_type"] == "monitoring"
        assert "required_methods" in spec
        assert "required_events" in spec

    def test_generate_plugin_interface_spec_integration(self):
        """测试生成插件接口规范（集成）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        spec = manager.generate_plugin_interface_spec("integration")

        assert spec["interface_type"] == "integration"
        assert "required_methods" in spec

    def test_generate_plugin_interface_spec_ai(self):
        """测试生成插件接口规范（AI）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        spec = manager.generate_plugin_interface_spec("ai")

        assert spec["interface_type"] == "ai"
        assert "required_methods" in spec

    def test_generate_plugin_interface_spec_custom(self):
        """测试生成插件接口规范（自定义）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        spec = manager.generate_plugin_interface_spec("custom")

        assert spec["interface_type"] == "custom"

    def test_register_plugin(self):
        """测试注册插件"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        result = manager.register_plugin("plugin_1", metadata)

        assert result is True
        assert "plugin_1" in manager.plugin_metadata
        assert manager.total_plugins_registered == 1

    def test_register_plugin_duplicate(self):
        """测试注册插件（重复）"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)

        result = manager.register_plugin("plugin_1", metadata)

        assert result is False

    def test_register_plugin_invalid_metadata(self):
        """测试注册插件（无效元数据）"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="",  # Invalid empty plugin_id
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        result = manager.register_plugin("plugin_1", metadata)

        assert result is False

    def test_enable_plugin(self):
        """测试启用插件"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginStatus,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)

        result = manager.enable_plugin("plugin_1")

        assert result is True
        assert manager.plugin_status["plugin_1"] == PluginStatus.ENABLED
        assert manager.total_plugins_enabled == 1

    def test_enable_plugin_invalid(self):
        """测试启用插件（无效）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        result = manager.enable_plugin("invalid_plugin")

        assert result is False

    def test_disable_plugin(self):
        """测试禁用插件"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginStatus,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)
        manager.enable_plugin("plugin_1")

        result = manager.disable_plugin("plugin_1")

        assert result is True
        assert manager.plugin_status["plugin_1"] == PluginStatus.DISABLED
        assert manager.total_plugins_enabled == 0

    def test_disable_plugin_invalid(self):
        """测试禁用插件（无效）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        result = manager.disable_plugin("invalid_plugin")

        assert result is False

    def test_get_plugin_info(self):
        """测试获取插件信息"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)

        info = manager.get_plugin_info("plugin_1")

        assert info is not None
        assert info["plugin_id"] == "plugin_1"
        assert info["name"] == "Test Plugin"

    def test_get_plugin_info_invalid(self):
        """测试获取插件信息（无效）"""
        from core.plugin_system_manager import PluginSystemManager

        manager = PluginSystemManager()

        info = manager.get_plugin_info("invalid_plugin")

        assert info is None

    def test_list_plugins(self):
        """测试列出插件"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)

        plugins = manager.list_plugins()

        assert len(plugins) == 1

    def test_list_plugins_with_filter(self):
        """测试列出插件（带过滤器）"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginStatus,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)
        manager.enable_plugin("plugin_1")

        plugins = manager.list_plugins(
            plugin_type=PluginType.MONITORING, status=PluginStatus.ENABLED
        )

        assert len(plugins) == 1

    def test_get_system_summary(self):
        """测试获取系统摘要"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )

        manager.register_plugin("plugin_1", metadata)

        summary = manager.get_system_summary()

        assert "total_plugins_registered" in summary
        assert "total_plugins_enabled" in summary
        assert "total_interfaces_defined" in summary
        assert "system_version" in summary
        assert "plugins_by_type" in summary
        assert "plugins_by_status" in summary
        assert summary["total_plugins_registered"] == 1


class TestGetPluginSystemManager:
    """测试获取插件系统管理器"""

    def test_get_plugin_system_manager(self):
        """测试获取插件系统管理器"""
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()

        assert manager is not None
        assert hasattr(manager, "plugins")

    def test_get_plugin_system_manager_singleton(self):
        """测试获取插件系统管理器（单例）"""
        from core.plugin_system_manager import get_plugin_system_manager

        manager1 = get_plugin_system_manager()
        manager2 = get_plugin_system_manager()

        assert manager1 is manager2


class TestPluginSystemManagerIntegration:
    """测试插件系统管理器集成"""

    def test_complete_plugin_workflow(self):
        """测试完整插件工作流"""
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginStatus,
            PluginSystemManager,
            PluginType,
        )

        manager = PluginSystemManager()

        # Define interface
        interface = manager.define_plugin_interface(
            interface_id="monitoring_interface",
            interface_name="Monitoring Interface",
            methods=[{"name": "collect", "parameters": [], "returns": "dict"}],
            events=[{"name": "metric_collected", "data": "metric"}],
        )
        assert interface.interface_id == "monitoring_interface"

        # Register plugin
        metadata = PluginMetadata(
            plugin_id="plugin_1",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_type=PluginType.MONITORING,
        )
        manager.register_plugin("plugin_1", metadata)
        assert "plugin_1" in manager.plugin_metadata

        # Enable plugin
        manager.enable_plugin("plugin_1")
        assert manager.plugin_status["plugin_1"] == PluginStatus.ENABLED

        # Get plugin info
        info = manager.get_plugin_info("plugin_1")
        assert info["name"] == "Test Plugin"

        # List plugins
        plugins = manager.list_plugins()
        assert len(plugins) == 1

        # Get system summary
        summary = manager.get_system_summary()
        assert summary["total_plugins_registered"] == 1
        assert summary["total_plugins_enabled"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
