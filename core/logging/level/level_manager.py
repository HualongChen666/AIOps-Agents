# -*- coding: utf-8 -*-
"""
Log Level Manager
日志级别管理器

Provides log level definitions and dynamic log level adjustment.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class LogLevel(Enum):
    """Log level enumeration"""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """
        Convert string to LogLevel

        Args:
            level_str: String representation of log level

        Returns:
            LogLevel instance

        Raises:
            ValueError: If level string is invalid
        """
        level_map = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARNING": cls.WARNING,
            "ERROR": cls.ERROR,
            "CRITICAL": cls.CRITICAL,
        }
        level_str_upper = level_str.upper()
        if level_str_upper not in level_map:
            raise ValueError(
                f"Invalid log level: {level_str}. Must be one of {list(level_map.keys())}"
            )
        return level_map[level_str_upper]

    @classmethod
    def from_int(cls, level_int: int) -> "LogLevel":
        """
        Convert integer to LogLevel

        Args:
            level_int: Integer representation of log level

        Returns:
            LogLevel instance

        Raises:
            ValueError: If level integer is invalid
        """
        for level in cls:
            if level.value == level_int:
                return level
        raise ValueError(f"Invalid log level integer: {level_int}")

    def to_string(self) -> str:
        """
        Convert LogLevel to string

        Returns:
            String representation of log level
        """
        return self.name


@dataclass
class LogLevelConfig:
    """Log level configuration"""

    default_level: LogLevel = LogLevel.INFO
    module_levels: Dict[str, LogLevel] = field(default_factory=dict)
    enable_dynamic_adjustment: bool = True
    config_file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LogLevelManager:
    """
    Log level manager
    日志级别管理器

    Manages log levels with dynamic adjustment capabilities.
    """

    def __init__(self, config: Optional[LogLevelConfig] = None):
        """
        Initialize log level manager

        Args:
            config: Log level configuration
        """
        self.config = config or LogLevelConfig()
        self._lock = threading.RLock()
        self._level_history: list = []
        self._module_levels: Dict[str, LogLevel] = dict(self.config.module_levels)

        # Initialize default log level
        self._default_level = self.config.default_level

        logger.info(
            f"Log level manager initialized with default level: {self._default_level.to_string()}"
        )

    def get_default_level(self) -> LogLevel:
        """
        Get default log level

        Returns:
            Default log level
        """
        with self._lock:
            return self._default_level

    def set_default_level(self, level: LogLevel) -> None:
        """
        Set default log level

        Args:
            level: New default log level
        """
        with self._lock:
            old_level = self._default_level
            self._default_level = level
            self._level_history.append(
                {
                    "timestamp": time.time(),
                    "action": "set_default_level",
                    "old_level": old_level.to_string(),
                    "new_level": level.to_string(),
                }
            )
            logger.info(
                f"Default log level changed from {old_level.to_string()} to {level.to_string()}"
            )

    def get_module_level(self, module_name: str) -> Optional[LogLevel]:
        """
        Get log level for specific module

        Args:
            module_name: Module name

        Returns:
            Module log level or None if not set
        """
        with self._lock:
            return self._module_levels.get(module_name)

    def set_module_level(self, module_name: str, level: LogLevel) -> None:
        """
        Set log level for specific module

        Args:
            module_name: Module name
            level: Log level for the module
        """
        with self._lock:
            old_level = self._module_levels.get(module_name)
            self._module_levels[module_name] = level
            self._level_history.append(
                {
                    "timestamp": time.time(),
                    "action": "set_module_level",
                    "module": module_name,
                    "old_level": old_level.to_string() if old_level else None,
                    "new_level": level.to_string(),
                }
            )
            logger.info(f"Module {module_name} log level set to {level.to_string()}")

    def remove_module_level(self, module_name: str) -> None:
        """
        Remove log level for specific module

        Args:
            module_name: Module name
        """
        with self._lock:
            if module_name in self._module_levels:
                old_level = self._module_levels.pop(module_name)
                self._level_history.append(
                    {
                        "timestamp": time.time(),
                        "action": "remove_module_level",
                        "module": module_name,
                        "old_level": old_level.to_string(),
                    }
                )
                logger.info(f"Module {module_name} log level removed (was {old_level.to_string()})")

    def get_effective_level(self, module_name: Optional[str] = None) -> LogLevel:
        """
        Get effective log level for a module

        Args:
            module_name: Module name (optional)

        Returns:
            Effective log level
        """
        with self._lock:
            if module_name and module_name in self._module_levels:
                return self._module_levels[module_name]
            return self._default_level

    def set_level_from_string(self, level_str: str, module_name: Optional[str] = None) -> None:
        """
        Set log level from string

        Args:
            level_str: String representation of log level
            module_name: Module name (optional, for module-specific level)
        """
        level = LogLevel.from_string(level_str)
        if module_name:
            self.set_module_level(module_name, level)
        else:
            self.set_default_level(level)

    def load_config_from_file(self, file_path: str) -> None:
        """
        Load log level configuration from file

        Args:
            file_path: Path to configuration file (JSON or YAML)
        """
        import json

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.warning(f"Config file not found: {file_path}")
            return

        try:
            with open(file_path_obj, "r", encoding="utf-8") as f:
                if file_path_obj.suffix == ".json":
                    config_data = json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {file_path_obj.suffix}")
                    return

            # Apply configuration
            if "default_level" in config_data:
                self.set_default_level(LogLevel.from_string(config_data["default_level"]))

            if "module_levels" in config_data:
                for module, level_str in config_data["module_levels"].items():
                    self.set_module_level(module, LogLevel.from_string(level_str))

            logger.info(f"Log level configuration loaded from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load log level configuration from {file_path}: {e}")

    def save_config_to_file(self, file_path: str) -> None:
        """
        Save log level configuration to file

        Args:
            file_path: Path to configuration file (JSON)
        """
        import json

        try:
            config_data = {
                "default_level": self._default_level.to_string(),
                "module_levels": {
                    module: level.to_string() for module, level in self._module_levels.items()
                },
            }

            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path_obj, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)

            # Use print instead of logger to avoid loguru dependency issues
            print(f"Log level configuration saved to {file_path}")

        except Exception as e:
            print(f"Failed to save log level configuration to {file_path}: {e}")

    def get_level_history(self) -> list:
        """
        Get log level change history

        Returns:
            List of level change events
        """
        with self._lock:
            return self._level_history.copy()

    def clear_level_history(self) -> None:
        """Clear log level change history"""
        with self._lock:
            self._level_history.clear()
            logger.info("Log level history cleared")

    def get_all_module_levels(self) -> Dict[str, str]:
        """
        Get all module-specific log levels

        Returns:
            Dictionary mapping module names to log level strings
        """
        with self._lock:
            return {module: level.to_string() for module, level in self._module_levels.items()}

    def reset_to_defaults(self) -> None:
        """Reset all log levels to default configuration"""
        with self._lock:
            old_default = self._default_level
            self._default_level = self.config.default_level
            self._module_levels = dict(self.config.module_levels)
            self._level_history.append(
                {
                    "timestamp": time.time(),
                    "action": "reset_to_defaults",
                    "old_default_level": old_default.to_string(),
                    "new_default_level": self._default_level.to_string(),
                }
            )
            logger.info(
                f"Log levels reset to defaults (default: {self._default_level.to_string()})"
            )


# Global level manager instance
_global_level_manager: Optional[LogLevelManager] = None
_level_manager_lock = threading.Lock()


def get_level_manager() -> LogLevelManager:
    """
    Get global log level manager instance

    Returns:
        LogLevelManager instance
    """
    global _global_level_manager
    with _level_manager_lock:
        if _global_level_manager is None:
            _global_level_manager = LogLevelManager()
    return _global_level_manager


def set_log_level(level: LogLevel, module_name: Optional[str] = None) -> None:
    """
    Set log level (convenience function)

    Args:
        level: Log level to set
        module_name: Module name (optional)
    """
    manager = get_level_manager()
    if module_name:
        manager.set_module_level(module_name, level)
    else:
        manager.set_default_level(level)


def get_log_level(module_name: Optional[str] = None) -> LogLevel:
    """
    Get log level (convenience function)

    Args:
        module_name: Module name (optional)

    Returns:
        Current log level
    """
    manager = get_level_manager()
    return manager.get_effective_level(module_name)
