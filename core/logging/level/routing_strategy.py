# -*- coding: utf-8 -*-
"""
Log Routing Strategy
日志路由策略

Provides log routing strategies to direct logs to different targets based on level.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .level_manager import LogLevel


class LogRouter(ABC):
    """Abstract base class for log routers"""

    @abstractmethod
    def route(self, record: logging.LogRecord) -> List[str]:
        """
        Determine routing targets for a log record

        Args:
            record: Log record to route

        Returns:
            List of target identifiers where the log should be sent
        """


@dataclass
class LogLevelRouter(LogRouter):
    """
    Log level-based router
    基于日志级别的路由器

    Routes logs to different targets based on log level.
    """

    level_routes: Dict[LogLevel, List[str]] = field(default_factory=dict)
    default_routes: List[str] = field(default_factory=list)

    def route(self, record: logging.LogRecord) -> List[str]:
        """
        Determine routing targets based on log level

        Args:
            record: Log record to route

        Returns:
            List of target identifiers
        """
        record_level = LogLevel.from_int(record.levelno)

        if record_level in self.level_routes:
            return self.level_routes[record_level]

        return self.default_routes

    def add_level_route(self, level: LogLevel, targets: List[str]) -> None:
        """
        Add routing targets for a specific log level

        Args:
            level: Log level
            targets: List of target identifiers
        """
        self.level_routes[level] = targets

    def remove_level_route(self, level: LogLevel) -> None:
        """
        Remove routing targets for a specific log level

        Args:
            level: Log level to remove
        """
        if level in self.level_routes:
            del self.level_routes[level]

    def set_default_routes(self, targets: List[str]) -> None:
        """
        Set default routing targets

        Args:
            targets: List of default target identifiers
        """
        self.default_routes = targets


@dataclass
class FileRouter(LogRouter):
    """
    File-based router
    基于文件的路由器

    Routes logs to different files based on log level.
    """

    base_dir: str = "logs"
    level_files: Dict[LogLevel, str] = field(default_factory=dict)
    default_file: str = "app.log"
    enable_rotation: bool = True
    rotation_size: str = "10 MB"
    retention_days: int = 30

    def __post_init__(self):
        """Initialize base directory"""
        self.base_path = Path(self.base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def route(self, record: logging.LogRecord) -> List[str]:
        """
        Determine file path for a log record

        Args:
            record: Log record to route

        Returns:
            List containing the file path
        """
        record_level = LogLevel.from_int(record.levelno)

        if record_level in self.level_files:
            file_path = str(self.base_path / self.level_files[record_level])
        else:
            file_path = str(self.base_path / self.default_file)

        return [file_path]

    def get_file_path(self, level: LogLevel) -> str:
        """
        Get file path for a specific log level

        Args:
            level: Log level

        Returns:
            File path
        """
        if level in self.level_files:
            return str(self.base_path / self.level_files[level])
        return str(self.base_path / self.default_file)

    def set_level_file(self, level: LogLevel, filename: str) -> None:
        """
        Set file for a specific log level

        Args:
            level: Log level
            filename: Filename to use
        """
        self.level_files[level] = filename

    def set_default_file(self, filename: str) -> None:
        """
        Set default file

        Args:
            filename: Default filename
        """
        self.default_file = filename


@dataclass
class SystemRouter(LogRouter):
    """
    System-based router
    基于系统的路由器

    Routes logs to different systems (e.g., ELK, syslog, cloud services).
    """

    system_routes: Dict[str, Dict[LogLevel, bool]] = field(default_factory=dict)
    default_systems: List[str] = field(default_factory=list)
    system_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def route(self, record: logging.LogRecord) -> List[str]:
        """
        Determine system targets for a log record

        Args:
            record: Log record to route

        Returns:
            List of system identifiers
        """
        record_level = LogLevel.from_int(record.levelno)
        targets = []

        for system, level_config in self.system_routes.items():
            if record_level in level_config and level_config[record_level]:
                targets.append(system)

        if not targets:
            targets = self.default_systems

        return targets

    def add_system_route(self, system: str, level: LogLevel, enabled: bool = True) -> None:
        """
        Add system routing for a specific log level

        Args:
            system: System identifier
            level: Log level
            enabled: Whether routing is enabled for this level
        """
        if system not in self.system_routes:
            self.system_routes[system] = {}
        self.system_routes[system][level] = enabled

    def remove_system_route(self, system: str, level: LogLevel) -> None:
        """
        Remove system routing for a specific log level

        Args:
            system: System identifier
            level: Log level
        """
        if system in self.system_routes and level in self.system_routes[system]:
            del self.system_routes[system][level]

    def set_default_systems(self, systems: List[str]) -> None:
        """
        Set default systems

        Args:
            systems: List of default system identifiers
        """
        self.default_systems = systems

    def set_system_config(self, system: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a system

        Args:
            system: System identifier
            config: Configuration dictionary
        """
        self.system_config[system] = config

    def get_system_config(self, system: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a system

        Args:
            system: System identifier

        Returns:
            Configuration dictionary or None
        """
        return self.system_config.get(system)


@dataclass
class ConditionalRouter(LogRouter):
    """
    Conditional router
    条件路由器

    Routes logs based on custom conditions.
    """

    conditions: List[Callable[[logging.LogRecord], bool]] = field(default_factory=list)
    routes: List[List[str]] = field(default_factory=list)
    default_routes: List[str] = field(default_factory=list)

    def route(self, record: logging.LogRecord) -> List[str]:
        """
        Determine routing targets based on conditions

        Args:
            record: Log record to route

        Returns:
            List of target identifiers
        """
        for i, condition in enumerate(self.conditions):
            if condition(record):
                if i < len(self.routes):
                    route = self.routes[i]
                    return route if route else self.default_routes
                return self.default_routes

        return self.default_routes

    def add_condition(
        self, condition: Callable[[logging.LogRecord], bool], routes: List[str]
    ) -> None:
        """
        Add a condition and its associated routes

        Args:
            condition: Condition function
            routes: Routes to use if condition is true
        """
        self.conditions.append(condition)
        self.routes.append(routes)

    def set_default_routes(self, routes: List[str]) -> None:
        """
        Set default routes

        Args:
            routes: Default route identifiers
        """
        self.default_routes = routes
