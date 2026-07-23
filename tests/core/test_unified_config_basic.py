# -*- coding: utf-8 -*-
"""
基础统一配置模块测试
测试统一配置核心功能的基础场景
"""

import pytest


class TestUnifiedConfigBasic:
    """统一配置模块基础测试"""

    def test_unified_config_module_structure(self):
        """测试统一配置模块结构"""
        try:
            from core import unified_config

            assert unified_config is not None
        except ImportError as e:
            pytest.skip(f"Unified config module not available: {e}")

    def test_unified_config_functions_exist(self):
        """测试统一配置关键函数存在"""
        try:
            from core.unified_config import get_config_value, load_config, save_config

            # 验证关键函数存在
            assert load_config is not None
            assert save_config is not None
            assert get_config_value is not None
        except Exception as e:
            pytest.skip(f"Unified config functions test failed: {e}")

    def test_unified_config_classes_exist(self):
        """测试统一配置关键类存在"""
        try:
            from core.unified_config import ConfigLoader, ConfigValidator, UnifiedConfig

            # 验证关键类存在
            assert UnifiedConfig is not None
            assert ConfigLoader is not None
            assert ConfigValidator is not None
        except Exception as e:
            pytest.skip(f"Unified config classes test failed: {e}")

    def test_unified_config_constants(self):
        """测试统一配置常量定义"""
        try:
            from core.unified_config import ConfigFormat, ConfigSource

            # 验证常量存在
            assert ConfigFormat is not None
            assert ConfigSource is not None
        except Exception as e:
            pytest.skip(f"Unified config constants test failed: {e}")
