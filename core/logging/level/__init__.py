# -*- coding: utf-8 -*-
"""
Logging Level Strategy Module
日志分级策略模块

Provides log level management strategies including:
- Log level definitions (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Dynamic log level adjustment
- Log filtering strategies (module, level, keyword based)
- Log routing strategies (different levels to different targets)
- Log sampling strategies (for high-traffic scenarios)
"""

from .filter_strategy import (
    CompositeFilter,
    KeywordFilter,
    LevelFilter,
    LogFilter,
    ModuleFilter,
)
from .level_manager import (
    LogLevel,
    LogLevelManager,
    get_level_manager,
    get_log_level,
    set_log_level,
)
from .routing_strategy import (
    FileRouter,
    LogLevelRouter,
    LogRouter,
    SystemRouter,
)
from .sampling_strategy import (
    DynamicSampler,
    LogSampler,
    RatioSampler,
)

__all__ = [
    "LogLevel",
    "LogLevelManager",
    "get_level_manager",
    "set_log_level",
    "get_log_level",
    "LogFilter",
    "ModuleFilter",
    "LevelFilter",
    "KeywordFilter",
    "CompositeFilter",
    "LogRouter",
    "LogLevelRouter",
    "FileRouter",
    "SystemRouter",
    "LogSampler",
    "RatioSampler",
    "DynamicSampler",
]
