# -*- coding: utf-8 -*-
"""
Log Filter Strategy
日志过滤策略

Provides log filtering strategies based on module, level, and keywords.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Set

from loguru import logger

from .level_manager import LogLevel


class LogFilter(ABC):
    """Abstract base class for log filters"""

    @abstractmethod
    def should_log(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be logged

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False otherwise
        """


@dataclass
class ModuleFilter(LogFilter):
    """
    Module-based log filter
    基于模块的日志过滤器

    Filters logs based on module names.
    """

    include_modules: Set[str] = field(default_factory=set)
    exclude_modules: Set[str] = field(default_factory=set)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    default_action: bool = True  # True = include by default, False = exclude by default

    def __post_init__(self):
        """Compile regex patterns"""
        self._compiled_include_patterns = [re.compile(pattern) for pattern in self.include_patterns]
        self._compiled_exclude_patterns = [re.compile(pattern) for pattern in self.exclude_patterns]

    def should_log(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be logged based on module

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False otherwise
        """
        module_name = record.name

        # Check exclude modules first
        if module_name in self.exclude_modules:
            return False

        # Check include modules
        if self.include_modules:
            return module_name in self.include_modules

        # Check exclude patterns
        for pattern in self._compiled_exclude_patterns:
            if pattern.match(module_name):
                return False

        # Check include patterns
        if self._compiled_include_patterns:
            for pattern in self._compiled_include_patterns:
                if pattern.match(module_name):
                    return True
            return False

        # Default action
        return self.default_action


@dataclass
class LevelFilter(LogFilter):
    """
    Level-based log filter
    基于级别的日志过滤器

    Filters logs based on log levels.
    """

    min_level: LogLevel = LogLevel.DEBUG
    max_level: LogLevel = LogLevel.CRITICAL
    allowed_levels: Set[LogLevel] = field(default_factory=set)

    def should_log(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be logged based on level

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False otherwise
        """
        record_level = LogLevel.from_int(record.levelno)

        # If specific levels are defined, check against them
        if self.allowed_levels:
            return record_level in self.allowed_levels

        # Otherwise, check range
        return self.min_level.value <= record_level.value <= self.max_level.value


@dataclass
class KeywordFilter(LogFilter):
    """
    Keyword-based log filter
    基于关键词的日志过滤器

    Filters logs based on keywords in the log message.
    """

    include_keywords: Set[str] = field(default_factory=set)
    exclude_keywords: Set[str] = field(default_factory=set)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    case_sensitive: bool = False

    def __post_init__(self):
        """Compile regex patterns"""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._compiled_include_patterns = [
            re.compile(pattern, flags) for pattern in self.include_patterns
        ]
        self._compiled_exclude_patterns = [
            re.compile(pattern, flags) for pattern in self.exclude_patterns
        ]

    def should_log(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be logged based on keywords

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False otherwise
        """
        message = record.getMessage()

        # Check exclude keywords first
        for keyword in self.exclude_keywords:
            if self.case_sensitive:
                if keyword in message:
                    return False
            else:
                if keyword.lower() in message.lower():
                    return False

        # Check include keywords
        if self.include_keywords:
            for keyword in self.include_keywords:
                if self.case_sensitive:
                    if keyword in message:
                        return True
                else:
                    if keyword.lower() in message.lower():
                        return True
            return False

        # Check exclude patterns
        for pattern in self._compiled_exclude_patterns:
            if pattern.search(message):
                return False

        # Check include patterns
        if self._compiled_include_patterns:
            for pattern in self._compiled_include_patterns:
                if pattern.search(message):
                    return True
            return False

        # Default: allow if no include keywords/patterns are specified
        return True


@dataclass
class CompositeFilter(LogFilter):
    """
    Composite log filter
    组合日志过滤器

    Combines multiple filters with AND or OR logic.
    """

    filters: List[LogFilter] = field(default_factory=list)
    operator: str = "AND"  # "AND" or "OR"

    def should_log(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be logged based on composite filter

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False otherwise
        """
        if not self.filters:
            return True

        if self.operator.upper() == "AND":
            return all(f.should_log(record) for f in self.filters)
        elif self.operator.upper() == "OR":
            return any(f.should_log(record) for f in self.filters)
        else:
            logger.warning(f"Invalid composite filter operator: {self.operator}, defaulting to AND")
            return all(f.should_log(record) for f in self.filters)

    def add_filter(self, filter_instance: LogFilter) -> None:
        """
        Add a filter to the composite filter

        Args:
            filter_instance: Filter to add
        """
        self.filters.append(filter_instance)

    def remove_filter(self, filter_instance: LogFilter) -> None:
        """
        Remove a filter from the composite filter

        Args:
            filter_instance: Filter to remove
        """
        if filter_instance in self.filters:
            self.filters.remove(filter_instance)
