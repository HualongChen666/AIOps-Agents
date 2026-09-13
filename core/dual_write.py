# -*- coding: utf-8 -*-
"""
Dual Write Strategy for Metrics Storage
Implements dual-write to SQLite and VictoriaMetrics for gradual migration
"""

import asyncio
from typing import Any, Dict, Optional

from loguru import logger


class DualWriteStrategy:
    """
    Dual write strategy for metrics storage

    Writes metrics to both SQLite (existing) and VictoriaMetrics (new)
    to enable gradual migration and fallback capability.
    """

    def __init__(
        self,
        victoria_metrics_enabled: bool = False,
        fallback_on_error: bool = True,
        async_write: bool = True,
    ):
        """
        Initialize dual write strategy

        Args:
            victoria_metrics_enabled: Whether to enable VictoriaMetrics writes
            fallback_on_error: Whether to fall back to SQLite on VictoriaMetrics error
            async_write: Whether to write to VictoriaMetrics asynchronously
        """
        self.victoria_metrics_enabled = victoria_metrics_enabled
        self.fallback_on_error = fallback_on_error
        self.async_write = async_write

        self._vm_storage: Any = None
        self._stats = {"sqlite_writes": 0, "vm_writes": 0, "vm_errors": 0, "fallbacks": 0}
        # 异步（fire-and-forget）VM 写入的在飞任务；其成败通过 done 回调记账，
        # 避免此前「立即记 vm_writes、失败既不计数也不触发 fallback」的失真。
        self._pending_vm_tasks: set = set()

    async def initialize(self) -> None:
        """Initialize VictoriaMetrics storage if enabled"""
        if not self.victoria_metrics_enabled:
            logger.info("VictoriaMetrics dual-write disabled")
            return

        try:
            from core.storage.l4.storage_manager import init_l4_storage_manager

            # Initialize L4 storage manager with VictoriaMetrics config
            config = {"victoriametrics": {"enabled": True, "base_url": "http://localhost:8428"}}

            manager = init_l4_storage_manager(config)
            self._vm_storage = manager.get_victoriametrics()

            if self._vm_storage and self._vm_storage.initialize():
                logger.info("VictoriaMetrics dual-write initialized successfully")
            else:
                logger.warning("Failed to initialize VictoriaMetrics, dual-write disabled")
                self.victoria_metrics_enabled = False

        except Exception as e:
            logger.error(f"Failed to initialize dual-write: {e}")
            self.victoria_metrics_enabled = False

    async def write_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Write metric to both SQLite and VictoriaMetrics

        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Metric labels
            timestamp: Optional timestamp (Unix epoch in seconds)

        Returns:
            True if at least one write succeeded
        """
        sqlite_success = await self._write_to_sqlite(metric_name, value, labels, timestamp)
        vm_success = await self._write_to_victoriametrics(metric_name, value, labels, timestamp)

        return sqlite_success or vm_success

    async def _write_to_sqlite(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Write metric to SQLite (existing storage)

        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Metric labels
            timestamp: Optional timestamp

        Returns:
            True if write succeeded
        """
        try:
            import datetime

            from core.metrics_history import METRICS_HISTORY as metrics_history

            service = labels.get("service", "default") if isinstance(labels, dict) else "default"
            ts: datetime.datetime | None = None
            if timestamp is not None:
                ts = datetime.datetime.fromtimestamp(int(timestamp), tz=datetime.timezone.utc)

            metrics_history.push_metric(metric_name, value, service=service, timestamp=ts)

            self._stats["sqlite_writes"] += 1
            return True

        except Exception as e:
            logger.error(f"SQLite write failed for {metric_name}: {e}")
            return False

    async def _write_to_victoriametrics(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Write metric to VictoriaMetrics (new storage)

        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Metric labels
            timestamp: Optional timestamp

        Returns:
            True if write succeeded
        """
        if not self.victoria_metrics_enabled or not self._vm_storage:
            return False

        try:
            # Convert to VictoriaMetrics format
            vm_labels = {**labels, "__name__": metric_name}

            if self.async_write:
                # 异步写：立即返回，但把任务登记在册并由回调真实记账
                # （成功计 vm_writes，失败计 vm_errors 并按需计 fallbacks）。
                task = asyncio.create_task(
                    self._store_vm_and_account(metric_name, value, vm_labels)
                )
                self._pending_vm_tasks.add(task)
                task.add_done_callback(self._pending_vm_tasks.discard)
                return True
            else:
                # Synchronous write
                result = await self._vm_storage.store(metric_name, value, {"labels": vm_labels})
                if result:
                    self._stats["vm_writes"] += 1
                else:
                    self._stats["vm_errors"] += 1
                    if self.fallback_on_error:
                        self._stats["fallbacks"] += 1
                return bool(result)

        except Exception as e:
            logger.error(f"VictoriaMetrics write failed for {metric_name}: {e}")
            self._stats["vm_errors"] += 1
            if self.fallback_on_error:
                self._stats["fallbacks"] += 1
            return False

    async def _store_vm_and_account(
        self, metric_name: str, value: float, vm_labels: Dict[str, Any]
    ) -> bool:
        """执行一次异步 VM 写入并按真实结果记账。"""
        try:
            result = await self._vm_storage.store(
                metric_name, value, {"labels": vm_labels}
            )
        except Exception as e:
            logger.error(f"VictoriaMetrics async write failed for {metric_name}: {e}")
            self._stats["vm_errors"] += 1
            if self.fallback_on_error:
                self._stats["fallbacks"] += 1
            return False

        if result:
            self._stats["vm_writes"] += 1
        else:
            self._stats["vm_errors"] += 1
            if self.fallback_on_error:
                self._stats["fallbacks"] += 1
        return bool(result)

    async def flush(self) -> None:
        """等待所有在飞的异步 VM 写入完成（保证记账/落盘可见）。"""
        if not self._pending_vm_tasks:
            return
        await asyncio.gather(*list(self._pending_vm_tasks), return_exceptions=True)

    async def write_batch_metrics(self, metrics: list[Dict[str, Any]]) -> bool:
        """
        Write batch of metrics to both storages

        Args:
            metrics: List of metric dictionaries with name, value, labels, timestamp

        Returns:
            True if at least one write succeeded for each metric
        """
        if not metrics:
            return True

        # Write to SQLite in parallel for better performance
        sqlite_tasks = [
            self._write_to_sqlite(
                metric["name"], metric["value"], metric.get("labels", {}), metric.get("timestamp")
            )
            for metric in metrics
        ]
        sqlite_results = await asyncio.gather(*sqlite_tasks, return_exceptions=True)

        # Convert exceptions to False
        sqlite_results = [
            result if isinstance(result, bool) else False for result in sqlite_results
        ]

        # Write to VictoriaMetrics (batch if available)
        if self.victoria_metrics_enabled and self._vm_storage:
            try:
                # Convert to batch format
                batch_data = [
                    {
                        "name": m["name"],
                        "value": m["value"],
                        "labels": {**m.get("labels", {}), "__name__": m["name"]},
                    }
                    for m in metrics
                ]

                # Use batch write if available
                result = await self._vm_storage.store("batch", batch_data, {})
                if result:
                    self._stats["vm_writes"] += len(metrics)
                else:
                    self._stats["vm_errors"] += len(metrics)
            except Exception as e:
                logger.error(f"VictoriaMetrics batch write failed: {e}")
                self._stats["vm_errors"] += len(metrics)

        return all(sqlite_results)

    async def write_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Persist a ``collect_all()`` system snapshot through the dual-write path.

        Converts the snapshot to Prometheus exposition text (via
        :class:`core.metrics_converter.MetricsConverter`), then writes each
        resulting series to SQLite and (when enabled) VictoriaMetrics. This is
        the real integration point the Phase-1 migration was missing: previously
        callers passed the raw snapshot dictionary straight into
        :meth:`write_batch_metrics`, which expects ``{"name", "value"}`` records
        and therefore failed for every key.

        Args:
            snapshot: Snapshot dictionary from ``core.collector.collect_all``.

        Returns:
            True when at least one series was written.
        """
        from core.metrics_converter import MetricsConverter

        text = MetricsConverter.system_snapshot_to_prometheus(snapshot)
        wrote_any = False
        for line in text.splitlines():
            parsed = MetricsConverter.prometheus_to_sqlite(line)
            if not parsed:
                continue
            wrote_any = (
                await self.write_metric(
                    parsed["name"],
                    parsed["value"],
                    parsed.get("labels", {}),
                    parsed.get("timestamp"),
                )
            ) or wrote_any
        return wrote_any

    def get_stats(self) -> Dict[str, Any]:
        """
        Get dual-write statistics

        Returns:
            Statistics dictionary
        """
        return {
            "victoria_metrics_enabled": self.victoria_metrics_enabled,
            "fallback_on_error": self.fallback_on_error,
            "async_write": self.async_write,
            **self._stats,
        }

    def enable_victoriametrics(self) -> None:
        """Enable VictoriaMetrics writes"""
        self.victoria_metrics_enabled = True
        logger.info("VictoriaMetrics dual-write enabled")

    def disable_victoriametrics(self) -> None:
        """Disable VictoriaMetrics writes"""
        self.victoria_metrics_enabled = False
        logger.info("VictoriaMetrics dual-write disabled")


# Global dual-write instance
_dual_write_strategy: Optional[DualWriteStrategy] = None


def get_dual_write_strategy() -> DualWriteStrategy:
    """Get global dual-write strategy instance"""
    global _dual_write_strategy
    if _dual_write_strategy is None:
        _dual_write_strategy = DualWriteStrategy(
            victoria_metrics_enabled=False,  # Start disabled
            fallback_on_error=True,
            async_write=True,
        )
    return _dual_write_strategy


async def init_dual_write_strategy(enabled: bool = False) -> DualWriteStrategy:
    """
    Initialize global dual-write strategy

    Args:
        enabled: Whether to enable VictoriaMetrics from start

    Returns:
        DualWriteStrategy instance
    """
    global _dual_write_strategy
    _dual_write_strategy = DualWriteStrategy(
        victoria_metrics_enabled=enabled, fallback_on_error=True, async_write=True
    )
    await _dual_write_strategy.initialize()
    return _dual_write_strategy
