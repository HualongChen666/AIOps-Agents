# -*- coding: utf-8 -*-
"""测试插件市场模块"""

import pytest


class TestPluginMarketplaceModule:
    """测试插件市场模块"""

    def test_plugin_marketplace_module_exists(self):
        """测试插件市场模块存在"""
        from core import plugin_marketplace

        assert plugin_marketplace is not None

    def test_plugin_marketplace_has_enums(self):
        """测试插件市场模块有枚举"""
        from core import plugin_marketplace

        # 检查模块有枚举
        assert hasattr(plugin_marketplace, "PluginStatus")
        assert hasattr(plugin_marketplace, "SecurityLevel")

    def test_plugin_marketplace_has_dataclasses(self):
        """测试插件市场模块有数据类"""
        from core import plugin_marketplace

        # 检查模块有数据类
        assert hasattr(plugin_marketplace, "PluginSignature")
        assert hasattr(plugin_marketplace, "PluginPackage")

    def test_plugin_marketplace_has_classes(self):
        """测试插件市场模块有类"""
        from core import plugin_marketplace

        # 检查模块有类
        assert hasattr(plugin_marketplace, "PluginMarketplace")

    def test_plugin_marketplace_has_functions(self):
        """测试插件市场模块有函数"""
        from core import plugin_marketplace

        # 检查模块有函数
        assert hasattr(plugin_marketplace, "create_plugin_marketplace")


class TestPluginStatus:
    """测试插件状态枚举"""

    def test_plugin_status_values(self):
        """测试插件状态值"""
        from core.plugin_marketplace import PluginStatus

        assert PluginStatus.PENDING.value == "pending"
        assert PluginStatus.APPROVED.value == "approved"
        assert PluginStatus.REJECTED.value == "rejected"
        assert PluginStatus.DEPRECATED.value == "deprecated"


class TestSecurityLevel:
    """测试安全级别枚举"""

    def test_security_level_values(self):
        """测试安全级别值"""
        from core.plugin_marketplace import SecurityLevel

        assert SecurityLevel.LOW.value == "low"
        assert SecurityLevel.MEDIUM.value == "medium"
        assert SecurityLevel.HIGH.value == "high"
        assert SecurityLevel.CRITICAL.value == "critical"


class TestPluginSignature:
    """测试插件签名数据类"""

    def test_plugin_signature_creation(self):
        """测试插件签名创建"""
        from datetime import datetime

        from core.plugin_marketplace import PluginSignature

        signature = PluginSignature(
            plugin_id="plugin_1",
            version="1.0.0",
            signature="sig123",
            algorithm="SHA256",
            public_key="pub_key",
            signed_at=datetime.now(),
        )

        assert signature.plugin_id == "plugin_1"
        assert signature.version == "1.0.0"
        assert signature.algorithm == "SHA256"

    def test_plugin_signature_to_dict(self):
        """测试插件签名转换为字典"""
        from datetime import datetime

        from core.plugin_marketplace import PluginSignature

        signature = PluginSignature(
            plugin_id="plugin_1",
            version="1.0.0",
            signature="sig123",
            algorithm="SHA256",
            public_key="pub_key",
            signed_at=datetime.now(),
        )

        signature_dict = signature.to_dict()

        assert "plugin_id" in signature_dict
        assert "version" in signature_dict
        assert "signature" in signature_dict


class TestPluginPackage:
    """测试插件包数据类"""

    def test_plugin_package_creation(self):
        """测试插件包创建"""
        from datetime import datetime

        from core.plugin_marketplace import (
            PluginPackage,
            PluginStatus,
            SecurityLevel,
        )

        package = PluginPackage(
            id="plugin_1-1.0.0",
            name="Plugin 1",
            version="1.0.0",
            description="Test plugin",
            author="Author",
            status=PluginStatus.PENDING,
            security_level=SecurityLevel.MEDIUM,
            download_url="http://example.com/plugin.zip",
            checksum="abc123",
            size_bytes=1024,
            dependencies=[],
            signature=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={},
        )

        assert package.id == "plugin_1-1.0.0"
        assert package.name == "Plugin 1"
        assert package.status == PluginStatus.PENDING

    def test_plugin_package_to_dict(self):
        """测试插件包转换为字典"""
        from datetime import datetime

        from core.plugin_marketplace import (
            PluginPackage,
            PluginStatus,
            SecurityLevel,
        )

        package = PluginPackage(
            id="plugin_1-1.0.0",
            name="Plugin 1",
            version="1.0.0",
            description="Test plugin",
            author="Author",
            status=PluginStatus.PENDING,
            security_level=SecurityLevel.MEDIUM,
            download_url="http://example.com/plugin.zip",
            checksum="abc123",
            size_bytes=1024,
            dependencies=[],
            signature=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={},
        )

        package_dict = package.to_dict()

        assert "id" in package_dict
        assert "name" in package_dict
        assert "version" in package_dict


class TestPluginMarketplace:
    """测试插件市场类"""

    def test_plugin_marketplace_initialization(self):
        """测试插件市场初始化"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()

        assert marketplace.config == {}
        assert len(marketplace._plugins) == 0

    def test_plugin_marketplace_initialization_with_config(self):
        """测试插件市场初始化（带配置）"""
        from core.plugin_marketplace import PluginMarketplace

        config = {"private_key": "test_key", "public_key": "test_pub"}
        marketplace = PluginMarketplace(config=config)

        assert marketplace.config == config
        assert marketplace.private_key == "test_key"
        assert marketplace.public_key == "test_pub"

    def test_initialize(self):
        """测试初始化"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()

        result = marketplace.initialize()

        assert result is True
        assert marketplace._is_initialized is True

    def test_register_plugin(self):
        """测试注册插件"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        package = marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        assert package.name == "Test Plugin"
        assert package.version == "1.0.0"
        assert "Test Plugin-1.0.0" in marketplace._plugins

    def test_register_plugin_with_dependencies(self):
        """测试注册插件（带依赖）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        package = marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
            dependencies=["dep1", "dep2"],
        )

        assert len(package.dependencies) == 2
        assert "dep1" in package.dependencies

    def test_verify_plugin(self):
        """测试验证插件"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace(
            config={"private_key": "test_key", "public_key": "test_pub"}
        )
        marketplace.initialize()

        package_data = b"test data"
        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=package_data,
        )

        result = marketplace.verify_plugin("Test Plugin-1.0.0", package_data)

        assert result is True

    def test_verify_plugin_invalid(self):
        """测试验证插件（无效）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        result = marketplace.verify_plugin("invalid_plugin", b"data")

        assert result is False

    def test_approve_plugin(self):
        """测试批准插件"""
        from core.plugin_marketplace import (
            PluginMarketplace,
            PluginStatus,
        )

        marketplace = PluginMarketplace(
            config={"private_key": "test_key", "public_key": "test_pub"}
        )
        marketplace.initialize()

        package_data = b"test data"
        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=package_data,
        )

        result = marketplace.approve_plugin("Test Plugin-1.0.0")

        assert result is True
        assert marketplace._plugins["Test Plugin-1.0.0"].status == PluginStatus.APPROVED

    def test_approve_plugin_invalid(self):
        """测试批准插件（无效）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        result = marketplace.approve_plugin("invalid_plugin")

        assert result is False

    def test_reject_plugin(self):
        """测试拒绝插件"""
        from core.plugin_marketplace import (
            PluginMarketplace,
            PluginStatus,
        )

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        result = marketplace.reject_plugin("Test Plugin-1.0.0", "Test reason")

        assert result is True
        assert marketplace._plugins["Test Plugin-1.0.0"].status == PluginStatus.REJECTED

    def test_reject_plugin_invalid(self):
        """测试拒绝插件（无效）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        result = marketplace.reject_plugin("invalid_plugin", "reason")

        assert result is False

    def test_deprecate_plugin(self):
        """测试弃用插件"""
        from core.plugin_marketplace import (
            PluginMarketplace,
            PluginStatus,
        )

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        result = marketplace.deprecate_plugin("Test Plugin-1.0.0")

        assert result is True
        assert marketplace._plugins["Test Plugin-1.0.0"].status == PluginStatus.DEPRECATED

    def test_deprecate_plugin_invalid(self):
        """测试弃用插件（无效）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        result = marketplace.deprecate_plugin("invalid_plugin")

        assert result is False

    def test_get_plugin(self):
        """测试获取插件"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        plugin = marketplace.get_plugin("Test Plugin-1.0.0")

        assert plugin is not None
        assert plugin["name"] == "Test Plugin"

    def test_get_plugin_invalid(self):
        """测试获取插件（无效）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        plugin = marketplace.get_plugin("invalid_plugin")

        assert plugin is None

    def test_list_plugins(self):
        """测试列出插件"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        plugins = marketplace.list_plugins()

        assert len(plugins) == 1

    def test_list_plugins_with_filter(self):
        """测试列出插件（带过滤器）"""
        from core.plugin_marketplace import (
            PluginMarketplace,
            PluginStatus,
        )

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        plugins = marketplace.list_plugins(status=PluginStatus.PENDING)

        assert len(plugins) == 1

    def test_search_plugins(self):
        """测试搜索插件"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        results = marketplace.search_plugins("Test")

        assert len(results) == 1

    def test_get_plugin_versions(self):
        """测试获取插件版本"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        versions = marketplace.get_plugin_versions("Test Plugin")

        assert len(versions) == 1

    def test_check_dependencies(self):
        """测试检查依赖"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
            dependencies=["dep1"],
        )

        result = marketplace.check_dependencies("Test Plugin-1.0.0")

        assert "valid" in result
        assert result["valid"] is False  # dep1 is not registered

    def test_check_dependencies_invalid(self):
        """测试检查依赖（无效）"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        result = marketplace.check_dependencies("invalid_plugin")

        assert result["valid"] is False

    def test_get_statistics(self):
        """测试获取统计信息"""
        from core.plugin_marketplace import PluginMarketplace

        marketplace = PluginMarketplace()
        marketplace.initialize()

        marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=b"test data",
        )

        stats = marketplace.get_statistics()

        assert "total_plugins" in stats
        assert "status_counts" in stats
        assert "security_counts" in stats
        assert stats["total_plugins"] == 1


class TestCreatePluginMarketplace:
    """测试创建插件市场"""

    def test_create_plugin_marketplace(self):
        """测试创建插件市场"""
        from core.plugin_marketplace import create_plugin_marketplace

        marketplace = create_plugin_marketplace()

        assert marketplace is not None
        assert marketplace._is_initialized is True

    def test_create_plugin_marketplace_with_config(self):
        """测试创建插件市场（带配置）"""
        from core.plugin_marketplace import create_plugin_marketplace

        config = {"private_key": "test_key", "public_key": "test_pub"}
        marketplace = create_plugin_marketplace(config=config)

        assert marketplace is not None
        assert marketplace.private_key == "test_key"


class TestPluginMarketplaceIntegration:
    """测试插件市场集成"""

    def test_complete_marketplace_workflow(self):
        """测试完整市场工作流"""
        from core.plugin_marketplace import (
            PluginMarketplace,
            PluginStatus,
        )

        marketplace = PluginMarketplace(
            config={"private_key": "test_key", "public_key": "test_pub"}
        )
        marketplace.initialize()

        # Register plugin
        package_data = b"test data"
        package = marketplace.register_plugin(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            download_url="http://example.com/plugin.zip",
            package_data=package_data,
        )
        assert package.name == "Test Plugin"

        # Verify plugin
        verified = marketplace.verify_plugin("Test Plugin-1.0.0", package_data)
        assert verified is True

        # Approve plugin
        approved = marketplace.approve_plugin("Test Plugin-1.0.0")
        assert approved is True
        assert marketplace._plugins["Test Plugin-1.0.0"].status == PluginStatus.APPROVED

        # Get statistics
        stats = marketplace.get_statistics()
        assert stats["total_plugins"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
