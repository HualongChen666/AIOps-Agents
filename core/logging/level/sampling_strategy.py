# -*- coding: utf-8 -*-
"""
Log Sampling Strategy
日志采样策略

Provides log sampling strategies for high-traffic scenarios.
"""

import importlib
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from loguru import logger

from .level_manager import LogLevel

_rand = importlib.import_module("random")


class LogSampler(ABC):
    """Abstract base class for log samplers"""

    @abstractmethod
    def should_sample(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be sampled

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False if it should be sampled (dropped)
        """

    @abstractmethod
    def get_sampling_rate(self) -> float:
        """
        Get current sampling rate

        Returns:
            Sampling rate (0.0 to 1.0)
        """


@dataclass
class RatioSampler(LogSampler):
    """
    Ratio-based log sampler
    基于比例的日志采样器

    Samples logs based on a fixed ratio.
    """

    sampling_rate: float = 1.0  # 0.0 to 1.0
    seed: Optional[int] = None
    _random: Any = field(init=False)

    def __post_init__(self):
        """Initialize random number generator"""
        self._random = _rand.Random(self.seed) if self.seed is not None else _rand.Random()
        if not 0.0 <= self.sampling_rate <= 1.0:
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {self.sampling_rate}")

    def should_sample(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be sampled based on ratio

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False if it should be sampled (dropped)
        """
        return float(self._random.random()) < self.sampling_rate

    def get_sampling_rate(self) -> float:
        """
        Get current sampling rate

        Returns:
            Sampling rate (0.0 to 1.0)
        """
        return self.sampling_rate

    def set_sampling_rate(self, rate: float) -> None:
        """
        Set sampling rate

        Args:
            rate: New sampling rate (0.0 to 1.0)
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {rate}")
        self.sampling_rate = rate


@dataclass
class DynamicSampler(LogSampler):
    """
    Dynamic log sampler
    动态日志采样器

    Adjusts sampling rate based on system load or custom conditions.
    """

    initial_rate: float = 1.0
    min_rate: float = 0.1
    max_rate: float = 1.0
    adjustment_interval: float = 60.0  # seconds
    rate_adjustment_callback: Optional[callable] = None  # type: ignore[valid-type]

    def __post_init__(self):
        """Initialize dynamic sampler"""
        self._current_rate = self.initial_rate
        self._last_adjustment = time.time()
        self._lock = threading.Lock()

        if not 0.0 <= self.min_rate <= self.max_rate <= 1.0:
            raise ValueError(f"Invalid rate range: min={self.min_rate}, max={self.max_rate}")

    def should_sample(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be sampled based on dynamic rate

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False if it should be sampled (dropped)
        """
        # Check if rate adjustment is needed
        current_time = time.time()
        if current_time - self._last_adjustment > self.adjustment_interval:
            self._adjust_rate()
            self._last_adjustment = current_time

        return float(_rand.random()) < self._current_rate

    def get_sampling_rate(self) -> float:
        """
        Get current sampling rate

        Returns:
            Current sampling rate (0.0 to 1.0)
        """
        with self._lock:
            return self._current_rate

    def _adjust_rate(self) -> None:
        """Adjust sampling rate based on callback or default logic"""
        with self._lock:
            if self.rate_adjustment_callback:
                try:
                    new_rate = self.rate_adjustment_callback(self._current_rate)
                    self._current_rate = max(self.min_rate, min(self.max_rate, new_rate))
                except Exception as e:
                    logger.error(f"Error in rate adjustment callback: {e}")
            else:
                # Default: no adjustment
                pass

    def set_sampling_rate(self, rate: float) -> None:
        """
        Manually set sampling rate

        Args:
            rate: New sampling rate (0.0 to 1.0)
        """
        with self._lock:
            if not 0.0 <= rate <= 1.0:
                raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {rate}")
            self._current_rate = max(self.min_rate, min(self.max_rate, rate))

    def set_rate_adjustment_callback(self, callback: callable) -> None:  # type: ignore[valid-type]
        """
        Set custom rate adjustment callback

        Args:
            callback: Function that takes current rate and returns new rate
        """
        self.rate_adjustment_callback = callback


@dataclass
class LevelBasedSampler(LogSampler):
    """
    Level-based log sampler
    基于级别的日志采样器

    Applies different sampling rates based on log level.
    """

    level_rates: Dict[LogLevel, float] = field(default_factory=dict)
    default_rate: float = 1.0

    def __post_init__(self):
        """Initialize level-based sampler"""
        # Set default rates for different levels if not specified
        if not self.level_rates:
            self.level_rates = {
                LogLevel.DEBUG: 0.1,  # Sample 10% of debug logs
                LogLevel.INFO: 0.5,  # Sample 50% of info logs
                LogLevel.WARNING: 1.0,  # Log all warnings
                LogLevel.ERROR: 1.0,  # Log all errors
                LogLevel.CRITICAL: 1.0,  # Log all critical logs
            }

        # Validate rates
        for level, rate in self.level_rates.items():
            if not 0.0 <= rate <= 1.0:
                raise ValueError(f"Invalid sampling rate for {level}: {rate}")

    def should_sample(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be sampled based on its level

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False if it should be sampled (dropped)
        """
        record_level = LogLevel.from_int(record.levelno)
        sampling_rate = self.level_rates.get(record_level, self.default_rate)
        return float(_rand.random()) < sampling_rate

    def get_sampling_rate(self) -> float:
        """
        Get default sampling rate

        Returns:
            Default sampling rate (0.0 to 1.0)
        """
        return self.default_rate

    def get_level_sampling_rate(self, level: LogLevel) -> float:
        """
        Get sampling rate for a specific level

        Args:
            level: Log level

        Returns:
            Sampling rate for the level (0.0 to 1.0)
        """
        return self.level_rates.get(level, self.default_rate)

    def set_level_sampling_rate(self, level: LogLevel, rate: float) -> None:
        """
        Set sampling rate for a specific level

        Args:
            level: Log level
            rate: Sampling rate (0.0 to 1.0)
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {rate}")
        self.level_rates[level] = rate

    def set_default_rate(self, rate: float) -> None:
        """
        Set default sampling rate

        Args:
            rate: Default sampling rate (0.0 to 1.0)
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0, got {rate}")
        self.default_rate = rate


@dataclass
class CompositeSampler(LogSampler):
    """
    Composite log sampler
    组合日志采样器

    Combines multiple samplers with AND or OR logic.
    """

    samplers: list = field(default_factory=list)
    operator: str = "AND"  # "AND" or "OR"

    def should_sample(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be sampled based on composite logic

        Args:
            record: Log record to evaluate

        Returns:
            True if the record should be logged, False if it should be sampled (dropped)
        """
        if not self.samplers:
            return True

        results = [sampler.should_sample(record) for sampler in self.samplers]

        if self.operator.upper() == "AND":
            return all(results)
        elif self.operator.upper() == "OR":
            return any(results)
        else:
            logger.warning(
                f"Invalid composite sampler operator: {self.operator}, defaulting to AND"
            )
            return all(results)

    def get_sampling_rate(self) -> float:
        """
        Get average sampling rate

        Returns:
            Average sampling rate (0.0 to 1.0)
        """
        if not self.samplers:
            return 1.0
        rates = [s.get_sampling_rate() for s in self.samplers]
        return sum(rates) / len(rates)  # type: ignore[no-any-return]

    def add_sampler(self, sampler: LogSampler) -> None:
        """
        Add a sampler to the composite sampler

        Args:
            sampler: Sampler to add
        """
        self.samplers.append(sampler)

    def remove_sampler(self, sampler: LogSampler) -> None:
        """
        Remove a sampler from the composite sampler

        Args:
            sampler: Sampler to remove
        """
        if sampler in self.samplers:
            self.samplers.remove(sampler)
