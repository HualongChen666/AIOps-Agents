# -*- coding: utf-8 -*-
"""
Memory Usage Optimization
Enterprise-grade memory usage optimization with leak detection and auto-recovery
"""

import asyncio
import gc
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class MemoryEventType(Enum):
    """Memory event type"""

    ALLOCATION = "allocation"
    DEALLOCATION = "deallocation"
    GC_COLLECTION = "gc_collection"
    LEAK_DETECTED = "leak_detected"
    LIMIT_EXCEEDED = "limit_exceeded"


class MemoryAction(Enum):
    """Memory action"""

    COLLECT_GARBAGE = "collect_garbage"
    CLEAR_CACHE = "clear_cache"
    REDUCE_POOL_SIZE = "reduce_pool_size"
    RESTART_COMPONENT = "restart_component"
    ALERT_ONLY = "alert_only"


@dataclass
class MemorySnapshot:
    """Memory snapshot data"""

    snapshot_id: str
    timestamp: datetime
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    memory_percent: float
    gc_objects: int
    gc_collections: Dict[int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryLeak:
    """Memory leak data"""

    leak_id: str
    component: str
    leak_size_mb: float
    growth_rate_mb_per_hour: float
    detected_at: datetime
    severity: str
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryLimit:
    """Memory limit configuration"""

    component: str
    max_memory_mb: float
    warning_threshold_percent: float = 80.0
    critical_threshold_percent: float = 95.0
    action_on_exceed: MemoryAction = MemoryAction.COLLECT_GARBAGE
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryUsageOptimizer:
    """Enterprise-grade memory usage optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize memory usage optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Memory snapshots history
        self.memory_snapshots: deque = deque(maxlen=1000)

        # Memory limits
        self.memory_limits: Dict[str, MemoryLimit] = {}

        # Memory leaks detected
        self.memory_leaks: List[MemoryLeak] = []

        # Memory event history
        self.memory_events: deque = deque(maxlen=10000)

        # Component memory tracking
        self.component_memory: Dict[str, float] = defaultdict(float)

        # Configuration
        self.monitoring_interval_seconds = self.config.get("monitoring_interval_seconds", 10)
        self.gc_threshold_percent = self.config.get("gc_threshold_percent", 80.0)
        self.leak_detection_window_hours = self.config.get("leak_detection_window_hours", 24)

        # Statistics
        self.total_gc_collections = 0
        self.total_memory_freed_mb = 0.0
        self.total_leaks_detected = 0

        # Start tracing memory
        tracemalloc.start()

        logger.info("Memory usage optimizer initialized")

    def take_memory_snapshot(self, component: str = "system") -> MemorySnapshot:
        """
        Take memory snapshot

        Args:
            component: Component name

        Returns:
            Memory snapshot
        """
        # Get system memory info
        import psutil

        memory = psutil.virtual_memory()

        # Get GC info
        gc_stats = gc.get_stats()
        gc_collections = {
            0: gc_stats[0].get("collections", 0) if len(gc_stats) > 0 else 0,
            1: gc_stats[1].get("collections", 0) if len(gc_stats) > 1 else 0,
            2: gc_stats[2].get("collections", 0) if len(gc_stats) > 2 else 0,
        }

        snapshot = MemorySnapshot(
            snapshot_id=(
                f"snapshot_{component}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
            ),
            timestamp=datetime.now(timezone.utc),
            total_memory_mb=memory.total / (1024 * 1024),
            used_memory_mb=memory.used / (1024 * 1024),
            available_memory_mb=memory.available / (1024 * 1024),
            memory_percent=memory.percent,
            gc_objects=len(gc.get_objects()),
            gc_collections=gc_collections,
        )

        self.memory_snapshots.append(snapshot)
        self.component_memory[component] = snapshot.used_memory_mb

        logger.debug(f"Memory snapshot taken for {component}: {snapshot.used_memory_mb:.2f}MB")

        return snapshot

    def set_memory_limit(
        self,
        component: str,
        max_memory_mb: float,
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0,
        action_on_exceed: MemoryAction = MemoryAction.COLLECT_GARBAGE,
    ) -> None:
        """
        Set memory limit for component

        Args:
            component: Component name
            max_memory_mb: Maximum memory in MB
            warning_threshold_percent: Warning threshold percentage
            critical_threshold_percent: Critical threshold percentage
            action_on_exceed: Action when limit exceeded
        """
        self.memory_limits[component] = MemoryLimit(
            component=component,
            max_memory_mb=max_memory_mb,
            warning_threshold_percent=warning_threshold_percent,
            critical_threshold_percent=critical_threshold_percent,
            action_on_exceed=action_on_exceed,
        )

        logger.info(f"Set memory limit for {component}: {max_memory_mb}MB")

    def check_memory_limit(self, component: str) -> Dict[str, Any]:
        """
        Check if component exceeds memory limit

        Args:
            component: Component name

        Returns:
            Check result
        """
        if component not in self.memory_limits:
            return {"status": "no_limit"}

        limit = self.memory_limits[component]
        current_memory = self.component_memory.get(component, 0)

        usage_percent = (current_memory / limit.max_memory_mb) * 100

        if usage_percent >= limit.critical_threshold_percent:
            return {
                "status": "critical",
                "component": component,
                "current_memory_mb": current_memory,
                "max_memory_mb": limit.max_memory_mb,
                "usage_percent": usage_percent,
                "action": limit.action_on_exceed.value,
                "message": f"Critical memory usage: {usage_percent:.2f}%",
            }
        elif usage_percent >= limit.warning_threshold_percent:
            return {
                "status": "warning",
                "component": component,
                "current_memory_mb": current_memory,
                "max_memory_mb": limit.max_memory_mb,
                "usage_percent": usage_percent,
                "action": limit.action_on_exceed.value,
                "message": f"Warning memory usage: {usage_percent:.2f}%",
            }
        else:
            return {
                "status": "normal",
                "component": component,
                "current_memory_mb": current_memory,
                "max_memory_mb": limit.max_memory_mb,
                "usage_percent": usage_percent,
                "message": "Memory usage within limits",
            }

    def detect_memory_leaks(self, component: str = "system") -> List[MemoryLeak]:
        """
        Detect memory leaks by analyzing memory growth patterns

        Args:
            component: Component name

        Returns:
            List of detected memory leaks
        """
        # Get recent snapshots
        recent_snapshots = [
            s
            for s in self.memory_snapshots
            if s.metadata.get("component", "system") == component
            and (datetime.now(timezone.utc) - s.timestamp).total_seconds()
            <= self.leak_detection_window_hours * 3600
        ]

        if len(recent_snapshots) < 10:
            return []

        # Calculate growth rate
        memory_values = [s.used_memory_mb for s in recent_snapshots]
        timestamps = [s.timestamp for s in recent_snapshots]

        # Linear regression to estimate growth rate
        import numpy as np

        x = np.array([(t - timestamps[0]).total_seconds() / 3600 for t in timestamps])  # hours
        y = np.array(memory_values)

        if len(x) > 1:
            slope, _ = np.polyfit(x, y, 1)
            growth_rate = slope  # MB per hour
        else:
            growth_rate = 0

        leaks = []

        # Check if growth rate is significant
        if growth_rate > 10:  # Growing more than 10MB per hour
            leak = MemoryLeak(
                leak_id=f"leak_{component}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                component=component,
                leak_size_mb=memory_values[-1] - memory_values[0],
                growth_rate_mb_per_hour=growth_rate,
                detected_at=datetime.now(timezone.utc),
                severity="high" if growth_rate > 50 else "medium",
            )

            leaks.append(leak)
            self.memory_leaks.append(leak)
            self.total_leaks_detected += 1

            logger.warning(f"Memory leak detected in {component}: {growth_rate:.2f}MB/hour")

        return leaks

    def collect_garbage(self, generation: Optional[int] = None) -> Dict[str, Any]:
        """
        Collect garbage

        Args:
            generation: GC generation (0, 1, 2, or None for all)

        Returns:
            GC collection result
        """
        before_memory = self.take_memory_snapshot("gc_before")

        if generation is not None:
            collected = gc.collect(generation)
        else:
            collected = gc.collect()

        after_memory = self.take_memory_snapshot("gc_after")

        memory_freed = before_memory.used_memory_mb - after_memory.used_memory_mb
        self.total_gc_collections += 1
        self.total_memory_freed_mb += memory_freed

        # Log event
        self.memory_events.append(
            {
                "event_type": MemoryEventType.GC_COLLECTION.value,
                "timestamp": datetime.now(timezone.utc),
                "generation": generation,
                "collected_objects": collected,
                "memory_freed_mb": memory_freed,
            }
        )

        logger.info(f"GC collection: {collected} objects freed, {memory_freed:.2f}MB freed")

        return {
            "collected_objects": collected,
            "memory_freed_mb": memory_freed,
            "before_memory_mb": before_memory.used_memory_mb,
            "after_memory_mb": after_memory.used_memory_mb,
        }

    def get_memory_trace(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get memory trace for debugging

        Args:
            limit: Number of traces to return

        Returns:
            Memory trace information
        """
        # Get current memory snapshot
        snapshot = tracemalloc.take_snapshot()

        # Get top memory allocations
        top_stats = snapshot.statistics("lineno")

        traces = []
        for stat in top_stats[:limit]:
            traces.append(
                {
                    "file": stat.traceback[0].filename if stat.traceback else "unknown",
                    "line": stat.traceback[0].lineno if stat.traceback else 0,
                    "size_mb": stat.size / (1024 * 1024),
                    "count": stat.count,
                }
            )

        return traces

    def optimize_memory(self, component: str) -> Dict[str, Any]:
        """
        Optimize memory usage for component

        Args:
            component: Component name

        Returns:
            Optimization result
        """
        result: Dict[str, Any] = {
            "component": component,
            "actions_taken": [],
            "memory_freed_mb": 0.0,
        }

        # Check memory limit
        limit_check = self.check_memory_limit(component)

        if limit_check["status"] in ["warning", "critical"]:
            # Perform garbage collection
            gc_result = self.collect_garbage()
            result["actions_taken"].append("garbage_collection")
            result["memory_freed_mb"] += gc_result["memory_freed_mb"]

        # Detect memory leaks
        leaks = self.detect_memory_leaks(component)

        if leaks:
            result["leaks_detected"] = len(leaks)
            result["actions_taken"].append("leak_detection")

        return result

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if self.memory_snapshots:
            latest_snapshot = self.memory_snapshots[-1]
        else:
            latest_snapshot = self.take_memory_snapshot()

        return {
            "total_memory_mb": latest_snapshot.total_memory_mb,
            "used_memory_mb": latest_snapshot.used_memory_mb,
            "available_memory_mb": latest_snapshot.available_memory_mb,
            "memory_percent": latest_snapshot.memory_percent,
            "gc_objects": latest_snapshot.gc_objects,
            "total_gc_collections": self.total_gc_collections,
            "total_memory_freed_mb": self.total_memory_freed_mb,
            "total_leaks_detected": self.total_leaks_detected,
            "components_tracked": len(self.component_memory),
        }

    def get_component_memory(self, component: str) -> Optional[float]:
        """
        Get component memory usage

        Args:
            component: Component name

        Returns:
            Memory usage in MB or None
        """
        return self.component_memory.get(component)

    async def start_monitoring(self) -> None:
        """Start automatic memory monitoring"""

        async def monitoring_loop():
            while True:
                try:
                    # Take snapshot
                    self.take_memory_snapshot()

                    # Check all component limits
                    for component in list(self.component_memory.keys()):
                        limit_check = self.check_memory_limit(component)

                        if limit_check["status"] in ["warning", "critical"]:
                            # Execute action
                            limit = self.memory_limits.get(component)
                            if limit:
                                if limit.action_on_exceed == MemoryAction.COLLECT_GARBAGE:
                                    self.collect_garbage()
                                elif limit.action_on_exceed == MemoryAction.ALERT_ONLY:
                                    logger.warning(
                                        f"Memory alert for {component}: {limit_check['message']}"
                                    )

                    # Detect leaks periodically
                    if datetime.now(timezone.utc).minute % 10 == 0:  # Every 10 minutes
                        self.detect_memory_leaks()

                    await asyncio.sleep(self.monitoring_interval_seconds)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    await asyncio.sleep(self.monitoring_interval_seconds)

        asyncio.create_task(monitoring_loop())
        logger.info("Automatic memory monitoring started")

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "total_gc_collections": self.total_gc_collections,
            "total_memory_freed_mb": self.total_memory_freed_mb,
            "total_leaks_detected": self.total_leaks_detected,
            "total_memory_limits": len(self.memory_limits),
            "total_snapshots": len(self.memory_snapshots),
            "components_tracked": len(self.component_memory),
        }


def get_memory_usage_optimizer(config: Optional[Dict[str, Any]] = None) -> MemoryUsageOptimizer:
    """
    Factory function to get memory usage optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        MemoryUsageOptimizer: Optimizer instance
    """
    return MemoryUsageOptimizer(config)
