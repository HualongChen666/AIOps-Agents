# -*- coding: utf-8 -*-
"""
Config module tests
测试config.py模块的配置功能
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch  # noqa: F401

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSafeBool:
    """测试_safe_bool函数"""

    def test_safe_bool_true_values(self):
        """测试布尔值为True的情况"""
        os.environ["TEST_BOOL"] = "true"
        from config import _safe_bool

        assert _safe_bool("TEST_BOOL") is True

        os.environ["TEST_BOOL"] = "1"
        assert _safe_bool("TEST_BOOL") is True

        os.environ["TEST_BOOL"] = "yes"
        assert _safe_bool("TEST_BOOL") is True

        os.environ["TEST_BOOL"] = "on"
        assert _safe_bool("TEST_BOOL") is True

    def test_safe_bool_false_values(self):
        """测试布尔值为False的情况"""
        os.environ["TEST_BOOL"] = "false"
        from config import _safe_bool

        assert _safe_bool("TEST_BOOL") is False

        os.environ["TEST_BOOL"] = "0"
        assert _safe_bool("TEST_BOOL") is False

        os.environ["TEST_BOOL"] = "no"
        assert _safe_bool("TEST_BOOL") is False

        os.environ["TEST_BOOL"] = "off"
        assert _safe_bool("TEST_BOOL") is False

    def test_safe_bool_default(self):
        """测试默认值"""
        from config import _safe_bool

        assert _safe_bool("NONEXISTENT_BOOL") is False
        assert _safe_bool("NONEXISTENT_BOOL", default=True) is True

    def test_safe_bool_case_insensitive(self):
        """测试大小写不敏感"""
        os.environ["TEST_BOOL"] = "TRUE"
        from config import _safe_bool

        assert _safe_bool("TEST_BOOL") is True

        os.environ["TEST_BOOL"] = "FALSE"
        assert _safe_bool("TEST_BOOL") is False


class TestSafeInt:
    """测试_safe_int函数"""

    def test_safe_int_valid_values(self):
        """测试有效的整数值"""
        os.environ["TEST_INT"] = "42"
        from config import _safe_int

        assert _safe_int("TEST_INT") == 42

        os.environ["TEST_INT"] = "-10"
        assert _safe_int("TEST_INT") == -10

    def test_safe_int_default(self):
        """测试默认值"""
        from config import _safe_int

        assert _safe_int("NONEXISTENT_INT") == 0
        assert _safe_int("NONEXISTENT_INT", default=100) == 100

    def test_safe_int_min_bounds(self):
        """测试最小值边界"""
        os.environ["TEST_INT"] = "5"
        from config import _safe_int

        assert _safe_int("TEST_INT", min_val=10) == 10

    def test_safe_int_max_bounds(self):
        """测试最大值边界"""
        os.environ["TEST_INT"] = "15"
        from config import _safe_int

        assert _safe_int("TEST_INT", max_val=10) == 10

    def test_safe_int_invalid_value(self):
        """测试无效值"""
        os.environ["TEST_INT"] = "invalid"
        from config import _safe_int

        assert _safe_int("TEST_INT", default=100) == 100


class TestSafeFloat:
    """测试_safe_float函数"""

    def test_safe_float_valid_values(self):
        """测试有效的浮点数值"""
        os.environ["TEST_FLOAT"] = "3.14"
        from config import _safe_float

        assert _safe_float("TEST_FLOAT") == 3.14

        os.environ["TEST_FLOAT"] = "-2.5"
        assert _safe_float("TEST_FLOAT") == -2.5

    def test_safe_float_default(self):
        """测试默认值"""
        from config import _safe_float

        assert _safe_float("NONEXISTENT_FLOAT") == 0.0
        assert _safe_float("NONEXISTENT_FLOAT", default=1.5) == 1.5

    def test_safe_float_min_bounds(self):
        """测试最小值边界"""
        os.environ["TEST_FLOAT"] = "0.5"
        from config import _safe_float

        assert _safe_float("TEST_FLOAT", min_val=1.0) == 1.0

    def test_safe_float_max_bounds(self):
        """测试最大值边界"""
        os.environ["TEST_FLOAT"] = "5.5"
        from config import _safe_float

        assert _safe_float("TEST_FLOAT", max_val=5.0) == 5.0

    def test_safe_float_invalid_value(self):
        """测试无效值"""
        os.environ["TEST_FLOAT"] = "invalid"
        from config import _safe_float

        assert _safe_float("TEST_FLOAT", default=2.5) == 2.5


class TestEnvironmentVariables:
    """测试环境变量配置"""

    def test_environment_variable(self):
        """测试环境变量"""
        os.environ["ENVIRONMENT"] = "test"
        # 重新导入模块以获取新的环境变量
        import importlib

        import config

        importlib.reload(config)
        assert config.environment == "test"

    def test_teams_webhook_url(self):
        """测试Teams Webhook URL配置"""
        os.environ["TEAMS_WEBHOOK_URL"] = "https://test.webhook.url"
        import importlib

        import config

        importlib.reload(config)
        assert config.TEAMS_WEBHOOK_URL == "https://test.webhook.url"

    def test_internal_api_key(self):
        """测试内部API密钥配置"""
        os.environ["INTERNAL_API_KEY"] = "test_api_key"
        import importlib

        import config

        importlib.reload(config)
        assert config.INTERNAL_API_KEY == "test_api_key"

    def test_redis_configuration(self):
        """测试Redis配置"""
        os.environ["REDIS_HOST"] = "test.redis.host"
        os.environ["REDIS_PORT"] = "6380"
        os.environ["REDIS_DB"] = "1"
        import importlib

        import config

        importlib.reload(config)
        assert config.REDIS_HOST == "test.redis.host"
        assert config.REDIS_PORT == 6380
        assert config.REDIS_DB == 1
        assert "test.redis.host" in config.REDIS_URL


class TestDatabaseConfiguration:
    """测试数据库配置"""

    def test_postgres_configuration(self):
        """测试PostgreSQL配置"""
        os.environ["POSTGRES_HOST"] = "test.postgres.host"
        os.environ["POSTGRES_PORT"] = "5433"
        os.environ["POSTGRES_USER"] = "testuser"
        os.environ["POSTGRES_DB"] = "testdb"
        os.environ["POSTGRES_PASSWORD"] = "testpass"
        os.environ["ENVIRONMENT"] = "development"

        import importlib

        import config

        importlib.reload(config)

        assert config.POSTGRES_HOST == "test.postgres.host"
        assert config.POSTGRES_PORT == 5433
        assert config.POSTGRES_USER == "testuser"
        assert config.POSTGRES_DB == "testdb"
        assert config.POSTGRES_PASSWORD == "testpass"
        assert "testuser" in config.POSTGRES_URL

    def test_postgres_production_password_required(self):
        """测试生产环境密码要求"""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["POSTGRES_PASSWORD"] = ""

        import importlib

        import config

        with pytest.raises(ValueError, match="POSTGRES_PASSWORD must be set"):
            importlib.reload(config)


class TestLLMRouterConfiguration:
    """测试LLM路由配置"""

    def test_llm_router_models(self):
        """测试LLM路由模型配置"""
        from config import LLM_ROUTER_MODELS

        assert len(LLM_ROUTER_MODELS) > 0

    def test_llm_router_model_structure(self):
        """测试LLM路由模型结构"""
        from config import LLM_ROUTER_MODELS

        for model in LLM_ROUTER_MODELS:
            assert "provider" in model
            assert "model" in model


class TestAllowedLocalIPs:
    """测试允许的本地IP配置"""

    def test_allowed_local_ips(self):
        """测试允许的本地IP列表"""
        from config import ALLOWED_LOCAL_IPS

        assert isinstance(ALLOWED_LOCAL_IPS, list)
        assert len(ALLOWED_LOCAL_IPS) > 0

    def test_allowed_local_ips_contains_localhost(self):
        """测试允许的本地IP包含localhost"""
        from config import ALLOWED_LOCAL_IPS

        assert "localhost" in ALLOWED_LOCAL_IPS or "127.0.0.1" in ALLOWED_LOCAL_IPS


class TestConfigModuleStructure:
    """测试配置模块结构"""

    def test_config_module_exists(self):
        """测试配置模块存在"""
        import config

        assert config is not None

    def test_config_has_environment(self):
        """测试配置有environment属性"""
        from config import environment

        assert environment is not None
        assert isinstance(environment, str)

    def test_config_has_database_url(self):
        """测试配置有database_url属性"""
        from config import DATABASE_URL

        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)

    def test_config_has_redis_url(self):
        """测试配置有redis_url属性"""
        from config import REDIS_URL

        assert REDIS_URL is not None
        assert isinstance(REDIS_URL, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
