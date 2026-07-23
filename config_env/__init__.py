# -*- coding: utf-8 -*-
"""Configuration package for environment-specific settings."""

import os

# Import from main config module for backward compatibility
import sys

from .environments import (
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

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:

    _AI_CONFIG_AVAILABLE = True
except ImportError:
    _AI_CONFIG_AVAILABLE = False

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

if _AI_CONFIG_AVAILABLE:
    __all__.extend(["AI_CONFIG", "LANGFUSE_CONFIG"])
