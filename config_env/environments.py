# -*- coding: utf-8 -*-
"""Environment isolation and configuration management.

This module provides environment-specific configuration management
for development, staging, and production environments.
"""

import os
from enum import Enum
from typing import Any, Dict, Optional, cast

from loguru import logger


class Environment(Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# Environment-specific configurations
_ENVIRONMENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "development": {
        "debug": True,
        "log_level": "DEBUG",
        "database_url": "sqlite:///./aiops_dev.db",
        "redis_url": "redis://localhost:6379/0",
        "api_rate_limit": "1000/hour",
        "enable_metrics": True,
        "enable_alert_rules": True,
        "enable_auto_heal": True,
        "cors_origins": ["http://localhost:3000", "http://localhost:8000"],
    },
    "staging": {
        "debug": False,
        "log_level": "INFO",
        "database_url": "postgresql://user:pass@staging-db:5432/aiops",
        "redis_url": "redis://staging-redis:6379/0",
        "api_rate_limit": "500/hour",
        "enable_metrics": True,
        "enable_alert_rules": True,
        "enable_auto_heal": True,
        "cors_origins": ["https://staging.example.com"],
    },
    "production": {
        "debug": False,
        "log_level": "WARNING",
        "database_url": "postgresql://user:pass@prod-db:5432/aiops",
        "redis_url": "redis://prod-redis:6379/0",
        "api_rate_limit": "200/hour",
        "enable_metrics": True,
        "enable_alert_rules": True,
        "enable_auto_heal": True,
        "cors_origins": ["https://api.example.com"],
    },
    "test": {
        "debug": True,
        "log_level": "DEBUG",
        "database_url": "sqlite:///./aiops_test.db",
        "redis_url": "redis://localhost:6379/1",
        "api_rate_limit": "10000/hour",
        "enable_metrics": False,
        "enable_alert_rules": False,
        "enable_auto_heal": False,
        "cors_origins": ["*"],
    },
}


def get_current_environment() -> Environment:
    """Get the current environment.

    Returns:
        Current environment enum
    """
    env_name = os.getenv("ENVIRONMENT", "development").lower()
    try:
        return Environment(env_name)
    except ValueError:
        logger.warning(f"Invalid environment '{env_name}', defaulting to development")
        return Environment.DEVELOPMENT


def get_environment_config(environment: Optional[Environment] = None) -> Dict[str, Any]:
    """Get configuration for a specific environment.

    Args:
        environment: Environment to get config for (defaults to current)

    Returns:
        Environment configuration dictionary
    """
    env = environment or get_current_environment()
    return _ENVIRONMENT_CONFIGS.get(env.value, _ENVIRONMENT_CONFIGS["development"]).copy()


def set_environment_variable(
    key: str, value: str, environment: Optional[Environment] = None
) -> None:
    """Set an environment variable for a specific environment.

    Args:
        key: Environment variable key
        value: Environment variable value
        environment: Target environment (defaults to current)
    """
    env = environment or get_current_environment()
    # In production, this would set environment-specific variables
    logger.info(f"Setting {key} for environment {env.value}")


def validate_environment_config(environment: Optional[Environment] = None) -> bool:
    """Validate environment configuration.

    Args:
        environment: Environment to validate (defaults to current)

    Returns:
        True if configuration is valid
    """
    env = environment or get_current_environment()
    config = get_environment_config(env)

    # Validate required fields
    required_fields = ["database_url", "redis_url", "log_level"]
    for field in required_fields:
        if field not in config or not config[field]:
            logger.error(f"Missing required field '{field}' in environment {env.value}")
            return False

    return True


def get_environment_specific_features(environment: Optional[Environment] = None) -> Dict[str, bool]:
    """Get feature flags for a specific environment.

    Args:
        environment: Environment to get features for (defaults to current)

    Returns:
        Dictionary of feature flags
    """
    env = environment or get_current_environment()
    config = get_environment_config(env)

    return {
        "enable_metrics": config.get("enable_metrics", False),
        "enable_alert_rules": config.get("enable_alert_rules", False),
        "enable_auto_heal": config.get("enable_auto_heal", False),
        "debug": config.get("debug", False),
    }


def is_production() -> bool:
    """Check if current environment is production.

    Returns:
        True if production environment
    """
    return get_current_environment() == Environment.PRODUCTION


def is_development() -> bool:
    """Check if current environment is development.

    Returns:
        True if development environment
    """
    return get_current_environment() == Environment.DEVELOPMENT


def is_staging() -> bool:
    """Check if current environment is staging.

    Returns:
        True if staging environment
    """
    return get_current_environment() == Environment.STAGING


def get_cors_origins(environment: Optional[Environment] = None) -> list:
    """Get CORS origins for a specific environment.

    Args:
        environment: Environment to get CORS origins for (defaults to current)

    Returns:
        List of allowed CORS origins
    """
    env = environment or get_current_environment()
    config = get_environment_config(env)
    return cast(list[Any], config.get("cors_origins", ["*"]))


def get_database_url(environment: Optional[Environment] = None) -> str:
    """Get database URL for a specific environment.

    Args:
        environment: Environment to get database URL for (defaults to current)

    Returns:
        Database connection URL
    """
    env = environment or get_current_environment()
    config = get_environment_config(env)
    return cast(str, config.get("database_url", ""))


def get_redis_url(environment: Optional[Environment] = None) -> str:
    """Get Redis URL for a specific environment.

    Args:
        environment: Environment to get Redis URL for (defaults to current)

    Returns:
        Redis connection URL
    """
    env = environment or get_current_environment()
    config = get_environment_config(env)
    return cast(str, config.get("redis_url", ""))


__all__ = [
    "Environment",
    "get_current_environment",
    "get_environment_config",
    "set_environment_variable",
    "validate_environment_config",
    "get_environment_specific_features",
    "is_production",
    "is_development",
    "is_staging",
    "get_cors_origins",
    "get_database_url",
    "get_redis_url",
]
