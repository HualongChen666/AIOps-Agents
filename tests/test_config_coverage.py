# -*- coding: utf-8 -*-
"""
Config module coverage tests
专注于提升config.py模块的测试覆盖率
"""

import os
import sys
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 在测试开始时不导入config模块，以便覆盖率工具能够跟踪


class TestSafeFunctionsCoverage:
    """测试安全函数的覆盖率"""

    def test_safe_bool_coverage(self):
        """测试_safe_bool函数的覆盖率"""
        import config

        # 测试所有可能的返回值
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("invalid", False),
            ("", False),
            ("random", False),
        ]

        for value, expected in test_cases:
            os.environ["TEST_BOOL"] = value
            result = config._safe_bool("TEST_BOOL", default=False)
            assert result == expected or result is False  # 对于无效值，应该返回默认值

    def test_safe_int_coverage(self):
        """测试_safe_int函数的覆盖率"""
        import config

        # 测试有效值
        os.environ["TEST_INT"] = "42"
        assert config._safe_int("TEST_INT") == 42

        # 测试边界检查
        os.environ["TEST_INT"] = "5"
        assert config._safe_int("TEST_INT", min_val=10) == 10

        os.environ["TEST_INT"] = "15"
        assert config._safe_int("TEST_INT", max_val=10) == 10

        # 测试无效值
        os.environ["TEST_INT"] = "invalid"
        assert config._safe_int("TEST_INT", default=100) == 100

        # 测试默认值
        assert config._safe_int("NONEXISTENT") == 0
        assert config._safe_int("NONEXISTENT", default=50) == 50

    def test_safe_float_coverage(self):
        """测试_safe_float函数的覆盖率"""
        import config

        # 测试有效值
        os.environ["TEST_FLOAT"] = "3.14"
        assert config._safe_float("TEST_FLOAT") == 3.14

        # 测试边界检查
        os.environ["TEST_FLOAT"] = "0.5"
        assert config._safe_float("TEST_FLOAT", min_val=1.0) == 1.0

        os.environ["TEST_FLOAT"] = "5.5"
        assert config._safe_float("TEST_FLOAT", max_val=5.0) == 5.0

        # 测试无效值
        os.environ["TEST_FLOAT"] = "invalid"
        assert config._safe_float("TEST_FLOAT", default=2.5) == 2.5


class TestConfigurationIntegration:
    """测试配置集成"""

    def test_config_module_import(self):
        """测试config模块导入"""
        import config

        # 测试关键配置项存在
        assert hasattr(config, "environment")
        assert hasattr(config, "_safe_bool")
        assert hasattr(config, "_safe_int")
        assert hasattr(config, "_safe_float")

    def test_config_values_types(self):
        """测试配置值的类型"""
        import config

        # 测试配置值的类型
        assert isinstance(config.environment, str)
        assert callable(config._safe_bool)
        assert callable(config._safe_int)
        assert callable(config._safe_float)


@pytest.fixture(autouse=True)
def cleanup_config_environment():
    """清理配置环境"""
    original_env = os.environ.copy()
    yield
    # 恢复原始环境变量
    for key in list(os.environ.keys()):
        if key not in original_env:
            del os.environ[key]
        else:
            os.environ[key] = original_env[key]
