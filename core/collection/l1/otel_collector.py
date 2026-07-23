# -*- coding: utf-8 -*-
"""
L1 Collection Layer - OpenTelemetry Enhanced Collector
Enhanced collector that automatically exports to OpenTelemetry and L4 Storage Layer
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from core.base.collector import BaseCollector
from core.otel_exporter import export_snapshot, init_otel
from core.storage.l4.storage_manager import get_l4_storage_manager


class OTELEnhancedCollector(BaseCollector):
    """
    Enhanced collector with automatic OpenTelemetry and L4 Storage integration

    This collector extends the base collector to automatically:
    1. Export metrics to OpenTelemetry (for VictoriaMetrics/Tempo)
    2. Store logs to Loki via L4 Storage Layer
    3. Store metrics to VictoriaMetrics via L4 Storage Layer
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(name, config)

        self.enable_otel = config.get("enable_otel", True)
        self.enable_l4_storage = config.get("enable_l4_storage", True)
        self.otel_initialized = False

        if self.enable_otel:
            try:
                init_otel()
                self.otel_initialized = True
                logger.info(f"OpenTelemetry initialized for collector: {name}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenTelemetry: {e}")

    async def collect(self) -> Dict[str, Any]:
        """
        Collect data and automatically export to OpenTelemetry and L4 Storage

        Returns:
            Collected data dictionary
        """
        # Collect data from source (to be implemented by subclasses)
        snapshot = await self._collect_from_source()

        if not snapshot:
            return snapshot

        # Export to OpenTelemetry
        if self.enable_otel and self.otel_initialized:
            try:
                export_snapshot(snapshot)
                logger.debug(f"Exported snapshot to OpenTelemetry: {self.name}")
            except Exception as e:
                logger.error(f"Failed to export to OpenTelemetry: {e}")

        # Store to L4 Storage Layer
        if self.enable_l4_storage:
            await self._store_to_l4(snapshot)

        return snapshot

    async def _collect_from_source(self) -> Dict[str, Any]:
        """
        Override this method in subclasses to implement actual collection logic

        Returns:
            Collected data dictionary
        """
        raise NotImplementedError("Subclasses must implement _collect_from_source")

    async def _store_to_l4(self, snapshot: Dict[str, Any]) -> None:
        """
        Store snapshot to L4 Storage Layer (VictoriaMetrics, Loki, Tempo)

        Args:
            snapshot: Collected data snapshot
        """
        l4_manager = get_l4_storage_manager()
        if not l4_manager:
            return

        # Store metrics to VictoriaMetrics
        vm_storage = l4_manager.get_victoriametrics()
        if vm_storage:
            await self._store_metrics_to_vm(vm_storage, snapshot)

        # Store logs to Loki
        loki_storage = l4_manager.get_loki()
        if loki_storage:
            await self._store_logs_to_loki(loki_storage, snapshot)

    async def _store_metrics_to_vm(self, vm_storage, snapshot: Dict[str, Any]) -> None:
        """
        Store metrics to VictoriaMetrics

        Args:
            vm_storage: VictoriaMetrics storage instance
            snapshot: Collected data snapshot
        """
        try:
            timestamp = int(datetime.now().timestamp())
            labels = {"collector": self.name, "source": snapshot.get("source", "unknown")}

            # CPU metrics
            cpu = snapshot.get("cpu", {})
            if cpu:
                await vm_storage.store(
                    "cpu.usage_percent",
                    cpu.get("usage_percent", 0),
                    {"labels": labels, "timestamp": timestamp},
                )

            # Memory metrics
            memory = snapshot.get("memory", {})
            if memory:
                await vm_storage.store(
                    "memory.used_gb",
                    memory.get("used_gb", 0),
                    {"labels": labels, "timestamp": timestamp},
                )
                await vm_storage.store(
                    "memory.total_gb",
                    memory.get("total_gb", 0),
                    {"labels": labels, "timestamp": timestamp},
                )

            # Disk metrics
            disks = snapshot.get("disk", [])
            for idx, disk in enumerate(disks):
                disk_labels = {**labels, "device": disk.get("device", f"disk{idx}")}
                await vm_storage.store(
                    "disk.used_gb",
                    disk.get("used_gb", 0),
                    {"labels": disk_labels, "timestamp": timestamp},
                )

            # Network metrics
            network = snapshot.get("network", {})
            if network:
                await vm_storage.store(
                    "network.recv_speed_mb",
                    network.get("recv_speed_mb", 0),
                    {"labels": labels, "timestamp": timestamp},
                )
                await vm_storage.store(
                    "network.sent_speed_mb",
                    network.get("sent_speed_mb", 0),
                    {"labels": labels, "timestamp": timestamp},
                )

            logger.debug(f"Stored metrics to VictoriaMetrics: {self.name}")

        except Exception as e:
            logger.error(f"Failed to store metrics to VictoriaMetrics: {e}")

    async def _store_logs_to_loki(self, loki_storage, snapshot: Dict[str, Any]) -> None:
        """
        Store logs to Loki

        Args:
            loki_storage: Loki storage instance
            snapshot: Collected data snapshot
        """
        try:
            # Convert snapshot to log format
            log_message = f"[{self.name}] Collection snapshot: {snapshot.get('source', 'unknown')}"

            labels = {
                "collector": self.name,
                "source": snapshot.get("source", "unknown"),
                "level": "info",
            }

            await loki_storage.store(self.name, log_message, {"labels": labels})

            logger.debug(f"Stored logs to Loki: {self.name}")

        except Exception as e:
            logger.error(f"Failed to store logs to Loki: {e}")

    def close(self) -> None:
        """Close the collector"""
        if self.otel_initialized:
            try:
                from core.otel_exporter import shutdown

                shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown OpenTelemetry: {e}")

        super().close()  # type: ignore[safe-super]


class SystemMetricsCollector(OTELEnhancedCollector):
    """
    System metrics collector with OpenTelemetry and L4 Storage integration
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("system_metrics", config)

    async def _collect_from_source(self) -> Dict[str, Any]:
        """Collect system metrics"""
        try:
            from core.collector import get_cached_snapshot

            snapshot = get_cached_snapshot()

            if snapshot:
                snapshot["source"] = "system"
                snapshot["timestamp"] = datetime.now().isoformat()

            return snapshot or {}

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}
