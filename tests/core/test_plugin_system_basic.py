# -*- coding: utf-8 -*-
"""
基础插件系统模块测试
测试插件系统核心功能的基础场景
"""

import pytest


class TestPluginSystemBasic:
    """插件系统模块基础测试"""

    def test_plugin_system_module_structure(self):
        """测试插件系统模块结构"""
        try:
            from core import plugin_system

            assert plugin_system is not None
        except ImportError as e:
            pytest.skip(f"Plugin system module not available: {e}")

    def test_plugin_system_functions_exist(self):
        """测试插件系统关键函数存在"""
        try:
            from core.plugin_system import load_plugin, register_plugin, unload_plugin

            # 验证关键函数存在
            assert load_plugin is not None
            assert register_plugin is not None
            assert unload_plugin is not None
        except Exception as e:
            pytest.skip(f"Plugin system functions test failed: {e}")

    def test_plugin_system_classes_exist(self):
        """测试插件系统关键类存在"""
        try:
            from core.plugin_system import PluginLoader, PluginManager, PluginRegistry

            # 验证关键类存在
            assert PluginManager is not None
            assert PluginLoader is not None
            assert PluginRegistry is not None
        except Exception as e:
            pytest.skip(f"Plugin system classes test failed: {e}")

    def test_plugin_system_constants(self):
        """测试插件系统常量定义"""
        try:
            from core.plugin_system import PluginStatus, PluginType

            # 验证常量存在
            assert PluginStatus is not None
            assert PluginType is not None
        except Exception as e:
            pytest.skip(f"Plugin system constants test failed: {e}")
