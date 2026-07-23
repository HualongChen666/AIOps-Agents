# -*- coding: utf-8 -*-
"""
Base Collector Abstract Class
Provides common interface for all data collectors (cloud, metrics, logs, etc.)
🔧 重构:添加模板方法模式，统一采集后处理流程
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Abstract base class for all collectors

    All collectors must implement the collect, initialize, and close methods.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base collector

        Args:
            name: Collector name
            config: Collector configuration
        """
        self.name = name
        self.config = config or {}
        self._is_initialized = False
        self._is_running = False

        # OpenTelemetry instrumentation
        self._tracer = None
        self._meter = None
        self._collection_counter = None
        self._collection_duration = None
        self._error_counter = None

        # Initialize telemetry
        self._init_telemetry()

        logger.info(f"BaseCollector initialized: {name}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the collector

        Returns:
            True if initialization successful
        """

    def _init_telemetry(self) -> None:
        """Initialize OpenTelemetry tracing and metrics"""
        try:
            from core.telemetry import get_meter, get_tracer

            self._tracer = get_tracer(f"collector.{self.name}")
            self._meter = get_meter(f"collector.{self.name}")

            # Create metrics
            if self._meter is not None:
                self._collection_counter = self._meter.create_counter(
                    "aiops_collector_collection_total",
                    description=f"Total number of collections for {self.name}",
                )
                self._collection_duration = self._meter.create_histogram(
                    "aiops_collector_collection_duration_seconds",
                    description=f"Collection duration for {self.name}",
                )
                self._error_counter = self._meter.create_counter(
                    "aiops_collector_errors_total", description=f"Total errors for {self.name}"
                )

            logger.debug(f"Telemetry initialized for collector: {self.name}")
        except ImportError:
            logger.debug("OpenTelemetry not available, skipping telemetry")
        except Exception as e:
            logger.warning(f"Failed to initialize telemetry for {self.name}: {e}")

    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """
        Collect data from the source

        Returns:
            Collected data dictionary
        """

    async def collect_with_tracing(self) -> Dict[str, Any]:
        """
        Collect data with OpenTelemetry tracing and metrics

        Returns:
            Collected data dictionary
        """
        import time

        span_name = f"collector.{self.name}.collect"

        # Create span if tracer is available
        if self._tracer:
            with self._tracer.start_as_current_span(span_name) as span:
                span.set_attribute("collector.name", self.name)
                span.set_attribute("collector.type", self.__class__.__name__)

                try:
                    start_time = time.time()
                    result = await self.collect()
                    duration = time.time() - start_time

                    span.set_attribute("collection.success", True)
                    span.set_attribute("collection.duration_seconds", duration)

                    # Record metrics
                    if self._collection_counter:
                        self._collection_counter.add(1, {"collector": self.name})
                    if self._collection_duration:
                        self._collection_duration.record(duration, {"collector": self.name})

                    return result

                except Exception as e:
                    span.set_attribute("collection.success", False)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)

                    # Record error metric
                    if self._error_counter:
                        self._error_counter.add(
                            1, {"collector": self.name, "error_type": type(e).__name__}
                        )

                    logger.error(f"Collection failed for {self.name}: {e}")
                    raise
        else:
            # Fallback without tracing
            try:
                start_time = time.time()
                result = await self.collect()
                duration = time.time() - start_time

                # Record metrics only
                if self._collection_counter:
                    self._collection_counter.add(1, {"collector": self.name})
                if self._collection_duration:
                    self._collection_duration.record(duration, {"collector": self.name})

                return result

            except Exception as e:
                if self._error_counter:
                    self._error_counter.add(
                        1, {"collector": self.name, "error_type": type(e).__name__}
                    )
                logger.error(f"Collection failed for {self.name}: {e}")
                raise

    @abstractmethod
    def close(self) -> None:
        """Close the collector and release resources"""

    def validate_config(self, required_keys: List[str]) -> bool:
        """
        Validate configuration has required keys

        Args:
            required_keys: List of required configuration keys

        Returns:
            True if configuration is valid
        """
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            logger.error(f"Missing required config keys: {missing_keys}")
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get collector status

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "initialized": self._is_initialized,
            "running": self._is_running,
            "config": self.config,
        }

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class Collector(BaseCollector):
    """Concrete collector for tests and simple use cases."""

    def __init__(self, name: str = "default", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

    def initialize(self) -> bool:
        self._is_initialized = True
        return True

    async def collect(self) -> Dict[str, Any]:
        return {}

    def close(self) -> None:
        self._is_running = False


# ============================================================
# 🔧 模板方法模式 - 函数式采集器后处理包装器
# ============================================================
def collect_with_post_processing(
    collect_func: Callable[[Dict[str, Any]], Dict[str, Any]],
    host_cfg: Dict[str, Any],
    platform_name: str,
    max_failures: int,
    cooldown_sec: int,
    metric_type: str = "metrics",
) -> Dict[str, Any]:
    """模板方法包装器：为函数式采集器统一后处理流程

    Args:
        collect_func: 采集函数，接收 host_cfg，返回 snapshot
        host_cfg: 主机配置
        platform_name: 平台名称
        max_failures: 最大失败次数
        cooldown_sec: 冷却时间
        metric_type: 指标类型

    Returns:
        采集的数据（已处理后）
    """
    host = host_cfg.get("host", "unknown")

    try:
        # 1. 调用采集函数
        snapshot = collect_func(host_cfg)
    except Exception as e:
        logger.error(f"{platform_name} collection failed for {host}: {e}")
        return {}

    # 2. 推送到 Loki
    try:
        from core.loki_sink import push_to_loki

        push_to_loki(snapshot)
    except Exception as e:
        logger.debug(f"Loki push failed for {platform_name} host {host}: {e}")

    # 3. 记录到 stats_engine
    try:
        import json

        from core.stats_engine import record_collect

        record_collect(
            {
                "host": host,
                "platform": platform_name,
                "metric_type": metric_type,
                "metric": json.dumps(snapshot),
            }
        )
    except Exception as e:
        logger.error(f"Stats record failed for {platform_name} host {host}: {e}")

    # 4. 注册 PID 防护
    try:
        from core.command_guard import register_self_pid

        register_self_pid()
    except Exception as e:
        logger.debug(f"PID registration failed for {platform_name} host {host}: {e}")

    return snapshot
