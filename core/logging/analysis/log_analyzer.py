# -*- coding: utf-8 -*-
"""
Log Analyzer
日志分析器

Provides log analysis capabilities including statistics, trends, and pattern recognition.
"""

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class LogLevel(Enum):
    """Log level enumeration"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogStatistics:
    """Log statistics data class"""

    total_logs: int = 0
    level_counts: Dict[str, int] = field(default_factory=dict)
    module_counts: Dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0
    avg_response_time: Optional[float] = None
    unique_users: int = 0
    unique_traces: int = 0
    time_range: Tuple[datetime, datetime] = field(
        default_factory=lambda: (datetime.now(), datetime.now())
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_logs": self.total_logs,
            "level_counts": self.level_counts,
            "module_counts": self.module_counts,
            "error_rate": self.error_rate,
            "avg_response_time": self.avg_response_time,
            "unique_users": self.unique_users,
            "unique_traces": self.unique_traces,
            "time_range": {
                "start": self.time_range[0].isoformat(),
                "end": self.time_range[1].isoformat(),
            },
        }


@dataclass
class LogTrends:
    """Log trends data class"""

    time_series: List[Tuple[datetime, int]] = field(default_factory=list)
    level_trends: Dict[str, List[Tuple[datetime, int]]] = field(default_factory=dict)
    error_trend: List[Tuple[datetime, float]] = field(default_factory=list)
    growth_rate: float = 0.0
    peak_time: Optional[datetime] = None
    peak_value: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "time_series": [(t.isoformat(), v) for t, v in self.time_series],
            "level_trends": {
                level: [(t.isoformat(), v) for t, v in trends]
                for level, trends in self.level_trends.items()
            },
            "error_trend": [(t.isoformat(), v) for t, v in self.error_trend],
            "growth_rate": self.growth_rate,
            "peak_time": self.peak_time.isoformat() if self.peak_time else None,
            "peak_value": self.peak_value,
        }


@dataclass
class LogPattern:
    """Log pattern data class"""

    pattern: str
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    examples: List[str] = field(default_factory=list)
    severity: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern": self.pattern,
            "count": self.count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "examples": self.examples[:5],  # Limit examples
            "severity": self.severity,
        }


class LogAnalyzer:
    """
    Log analyzer
    日志分析器

    Provides comprehensive log analysis capabilities.
    """

    def __init__(self):
        """Initialize log analyzer"""
        self._log_buffer: List[Dict[str, Any]] = []
        self._patterns: Dict[str, LogPattern] = {}
        self._max_buffer_size = 10000

        logger.info("Log analyzer initialized")

    def add_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Add a log entry for analysis

        Args:
            log_entry: Log entry dictionary
        """
        self._log_buffer.append(log_entry)

        # Maintain buffer size
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer.pop(0)

        # Extract patterns
        self._extract_patterns(log_entry)

    def add_logs(self, log_entries: List[Dict[str, Any]]) -> None:
        """
        Add multiple log entries for analysis

        Args:
            log_entries: List of log entry dictionaries
        """
        for log_entry in log_entries:
            self.add_log(log_entry)

    def calculate_statistics(
        self, time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> LogStatistics:
        """
        Calculate log statistics

        Args:
            time_range: Optional time range filter

        Returns:
            LogStatistics object
        """
        filtered_logs = self._filter_logs_by_time(time_range)

        if not filtered_logs:
            return LogStatistics()

        stats = LogStatistics()
        stats.total_logs = len(filtered_logs)

        # Count by level
        level_counter = Counter()  # type: ignore[var-annotated]
        for log in filtered_logs:
            level = log.get("level", "INFO")
            level_counter[level] += 1
        stats.level_counts = dict(level_counter)

        # Calculate error rate
        error_count = level_counter.get("ERROR", 0) + level_counter.get("CRITICAL", 0)
        stats.error_rate = error_count / stats.total_logs if stats.total_logs > 0 else 0.0

        # Count by module
        module_counter = Counter()  # type: ignore[var-annotated]
        for log in filtered_logs:
            module = log.get("module") or log.get("logger", "unknown")
            module_counter[module] += 1
        stats.module_counts = dict(module_counter.most_common(20))

        # Calculate average response time
        response_times = [
            log.get("context", {}).get("response_time")
            for log in filtered_logs
            if log.get("context", {}).get("response_time") is not None
        ]
        if response_times:
            stats.avg_response_time = statistics.mean(response_times)

        # Count unique users
        users = set()
        for log in filtered_logs:
            user_id = log.get("context", {}).get("user_id")
            if user_id:
                users.add(user_id)
        stats.unique_users = len(users)

        # Count unique traces
        traces = set()
        for log in filtered_logs:
            trace_id = log.get("context", {}).get("trace_id")
            if trace_id:
                traces.add(trace_id)
        stats.unique_traces = len(traces)

        # Calculate time range
        if filtered_logs:
            timestamps = [
                self._parse_timestamp(log.get("timestamp"))  # type: ignore[arg-type]
                for log in filtered_logs
                if log.get("timestamp")
            ]
            if timestamps:
                stats.time_range = (min(timestamps), max(timestamps))

        return stats

    def calculate_trends(self, interval: timedelta = timedelta(minutes=5)) -> LogTrends:
        """
        Calculate log trends

        Args:
            interval: Time interval for trend analysis

        Returns:
            LogTrends object
        """
        if not self._log_buffer:
            return LogTrends()

        trends = LogTrends()

        # Sort logs by timestamp
        sorted_logs = sorted(
            self._log_buffer, key=lambda x: self._parse_timestamp(x.get("timestamp", ""))
        )

        # Group by time interval
        time_groups = defaultdict(list)
        for log in sorted_logs:
            timestamp = self._parse_timestamp(log.get("timestamp", ""))
            if timestamp:
                time_key = timestamp.replace(
                    minute=timestamp.minute // (interval.seconds // 60) * (interval.seconds // 60),
                    second=0,
                    microsecond=0,
                )
                time_groups[time_key].append(log)

        # Calculate time series
        for time_key, logs in sorted(time_groups.items()):
            trends.time_series.append((time_key, len(logs)))

            # Level trends
            level_counts = Counter(log.get("level", "INFO") for log in logs)
            for level, count in level_counts.items():
                if level not in trends.level_trends:
                    trends.level_trends[level] = []
                trends.level_trends[level].append((time_key, count))

            # Error trend
            error_count = sum(1 for log in logs if log.get("level") in ("ERROR", "CRITICAL"))
            error_rate = error_count / len(logs) if logs else 0.0
            trends.error_trend.append((time_key, error_rate))

        # Calculate growth rate
        if len(trends.time_series) >= 2:
            first_count = trends.time_series[0][1]
            last_count = trends.time_series[-1][1]
            if first_count > 0:
                trends.growth_rate = (last_count - first_count) / first_count

        # Find peak
        if trends.time_series:
            trends.peak_time, trends.peak_value = max(trends.time_series, key=lambda x: x[1])

        return trends

    def detect_patterns(self, min_occurrences: int = 3) -> List[LogPattern]:
        """
        Detect log patterns

        Args:
            min_occurrences: Minimum number of occurrences for a pattern

        Returns:
            List of detected patterns
        """
        return [pattern for pattern in self._patterns.values() if pattern.count >= min_occurrences]

    def _extract_patterns(self, log_entry: Dict[str, Any]) -> None:
        """
        Extract patterns from a log entry

        Args:
            log_entry: Log entry dictionary
        """
        message = log_entry.get("message", "")
        level = log_entry.get("level", "INFO")

        # Create pattern by replacing numbers and IDs with placeholders
        pattern = re.sub(r"\d+", "{NUM}", message)
        pattern = re.sub(r"[a-f0-9]{32}", "{UUID}", pattern)
        pattern = re.sub(r"[a-f0-9]{16}", "{ID}", pattern)
        pattern = re.sub(r"/[\w\-\.]+", "{PATH}", pattern)
        pattern = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "{IP}", pattern)

        # Update pattern
        if pattern not in self._patterns:
            self._patterns[pattern] = LogPattern(pattern=pattern)

        pattern_obj = self._patterns[pattern]
        pattern_obj.count += 1
        timestamp = self._parse_timestamp(log_entry.get("timestamp"))  # type: ignore[arg-type]

        if pattern_obj.first_seen is None:
            pattern_obj.first_seen = timestamp
        pattern_obj.last_seen = timestamp

        if len(pattern_obj.examples) < 5:
            pattern_obj.examples.append(message)

        # Set severity based on log level
        if level in ("ERROR", "CRITICAL"):
            pattern_obj.severity = "error"
        elif level == "WARNING":
            pattern_obj.severity = "warning"

    def _filter_logs_by_time(
        self, time_range: Optional[Tuple[datetime, datetime]]
    ) -> List[Dict[str, Any]]:
        """
        Filter logs by time range

        Args:
            time_range: Optional time range filter

        Returns:
            Filtered log entries
        """
        if not time_range:
            return self._log_buffer

        start_time, end_time = time_range
        return [
            log
            for log in self._log_buffer
            if start_time <= self._parse_timestamp(log.get("timestamp", "")) <= end_time
        ]

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime

        Args:
            timestamp_str: Timestamp string

        Returns:
            Datetime object
        """
        if not timestamp_str:
            return datetime.now()

        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        return datetime.now()

    def clear_buffer(self) -> None:
        """Clear log buffer"""
        self._log_buffer.clear()
        self._patterns.clear()
        logger.info("Log analyzer buffer cleared")

    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        return len(self._log_buffer)


# Global log analyzer instance
_global_log_analyzer: Optional[LogAnalyzer] = None


def get_log_analyzer() -> LogAnalyzer:
    """
    Get global log analyzer instance

    Returns:
        LogAnalyzer instance
    """
    global _global_log_analyzer
    if _global_log_analyzer is None:
        _global_log_analyzer = LogAnalyzer()
    return _global_log_analyzer
