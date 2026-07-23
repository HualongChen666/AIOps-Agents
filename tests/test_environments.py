# -*- coding: utf-8 -*-
# tests/test_environments.py
# 环境隔离单元测试
import os

import pytest

from config_env.environments import (
    Environment,
    get_cors_origins,
    get_current_environment,
    get_database_url,
    get_environment_config,
    get_environment_specific_features,
    get_redis_url,
    is_development,
    is_production,
    is_staging,
    set_environment_variable,
    validate_environment_config,
)


class TestEnvironmentDetection:
    """环境检测测试"""

    def test_get_current_environment_default(self):
        """测试获取默认环境"""
        # Reset environment variable
        if "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]

        env = get_current_environment()
        assert env == Environment.DEVELOPMENT

    def test_get_current_environment_custom(self):
        """测试获取自定义环境"""
        os.environ["ENVIRONMENT"] = "production"
        env = get_current_environment()
        assert env == Environment.PRODUCTION

        # Reset
        del os.environ["ENVIRONMENT"]

    def test_get_current_environment_invalid(self):
        """测试无效环境默认为开发环境"""
        os.environ["ENVIRONMENT"] = "invalid"
        env = get_current_environment()
        assert env == Environment.DEVELOPMENT

        # Reset
        del os.environ["ENVIRONMENT"]


class TestEnvironmentConfiguration:
    """环境配置测试"""

    def test_get_environment_config_development(self):
        """测试获取开发环境配置"""
        config = get_environment_config(Environment.DEVELOPMENT)

        assert config["debug"] is True
        assert config["log_level"] == "DEBUG"
        assert "database_url" in config

    def test_get_environment_config_production(self):
        """测试获取生产环境配置"""
        config = get_environment_config(Environment.PRODUCTION)

        assert config["debug"] is False
        assert config["log_level"] == "WARNING"
        assert "database_url" in config

    def test_get_environment_config_staging(self):
        """测试获取预发布环境配置"""
        config = get_environment_config(Environment.STAGING)

        assert config["debug"] is False
        assert config["log_level"] == "INFO"
        assert "database_url" in config

    def test_get_environment_config_test(self):
        """测试获取测试环境配置"""
        config = get_environment_config(Environment.TEST)

        assert config["debug"] is True
        assert config["enable_metrics"] is False


class TestEnvironmentValidation:
    """环境验证测试"""

    def test_validate_environment_config_valid(self):
        """测试验证有效环境配置"""
        result = validate_environment_config(Environment.DEVELOPMENT)
        assert result is True

    def test_validate_environment_config_production(self):
        """测试验证生产环境配置"""
        result = validate_environment_config(Environment.PRODUCTION)
        assert result is True


class TestEnvironmentFeatures:
    """环境功能测试"""

    def test_get_environment_specific_features_development(self):
        """测试获取开发环境功能"""
        features = get_environment_specific_features(Environment.DEVELOPMENT)

        assert features["enable_metrics"] is True
        assert features["enable_auto_heal"] is True
        assert features["debug"] is True

    def test_get_environment_specific_features_production(self):
        """测试获取生产环境功能"""
        features = get_environment_specific_features(Environment.PRODUCTION)

        assert features["enable_metrics"] is True
        assert features["debug"] is False

    def test_get_environment_specific_features_test(self):
        """测试获取测试环境功能"""
        features = get_environment_specific_features(Environment.TEST)

        assert features["enable_metrics"] is False
        assert features["enable_auto_heal"] is False


class TestEnvironmentHelpers:
    """环境辅助函数测试"""

    def test_is_production(self):
        """测试是否为生产环境"""
        # Set environment to production
        os.environ["ENVIRONMENT"] = "production"
        assert is_production() is True

        # Reset
        os.environ["ENVIRONMENT"] = "development"
        assert is_production() is False

        # Reset
        del os.environ["ENVIRONMENT"]

    def test_is_development(self):
        """测试是否为开发环境"""
        os.environ["ENVIRONMENT"] = "development"
        assert is_development() is True

        os.environ["ENVIRONMENT"] = "production"
        assert is_development() is False

        # Reset
        del os.environ["ENVIRONMENT"]

    def test_is_staging(self):
        """测试是否为预发布环境"""
        os.environ["ENVIRONMENT"] = "staging"
        assert is_staging() is True

        os.environ["ENVIRONMENT"] = "production"
        assert is_staging() is False

        # Reset
        del os.environ["ENVIRONMENT"]


class TestEnvironmentUrls:
    """环境URL测试"""

    def test_get_database_url(self):
        """测试获取数据库URL"""
        url = get_database_url(Environment.DEVELOPMENT)
        assert "sqlite" in url.lower()

    def test_get_database_url_production(self):
        """测试获取生产环境数据库URL"""
        url = get_database_url(Environment.PRODUCTION)
        assert "postgresql" in url.lower()

    def test_get_redis_url(self):
        """测试获取Redis URL"""
        url = get_redis_url(Environment.DEVELOPMENT)
        assert "redis" in url.lower()

    def test_get_cors_origins(self):
        """测试获取CORS源"""
        origins = get_cors_origins(Environment.DEVELOPMENT)
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_get_cors_origins_production(self):
        """测试获取生产环境CORS源"""
        origins = get_cors_origins(Environment.PRODUCTION)
        assert isinstance(origins, list)
        assert len(origins) > 0


class TestEnvironmentVariables:
    """环境变量测试"""

    def test_set_environment_variable(self):
        """测试设置环境变量"""
        # This should not raise an error
        set_environment_variable("TEST_VAR", "test_value", Environment.DEVELOPMENT)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
