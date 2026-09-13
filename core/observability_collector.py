# -*- coding: utf-8 -*-
"""
Observability metrics collector
===============================

Samples **real** platform state and mirrors it into the unified Prometheus
exporter so that the domain dashboards (``aiops_enhanced_dashboard.json``) and
alert rules that consume ``aiops_alerts_pending``, ``aiops_repairs_*``,
``aiops_backup_*``, ``aiops_anomalies_detected_total``, ``aiops_health_status`` …
have an actual producer instead of being permanently empty.

Every value is derived from a concrete source:

* alert / repair / backup / anomaly / audit counts come from their SQLAlchemy
  tables in the application database;
* system resource gauges come from ``psutil``;
* APM error / slow-request rates are computed from the request counters and
  latency histogram the HTTP middleware already feeds;
* the health gauge reflects whether the database probe in this very cycle
  succeeded.

Domains whose underlying feature genuinely performs a computation are sampled
from that computation — nothing here is fabricated: if a source is unavailable
the metric is simply left untouched (and the failure is logged), never filled
with a made-up constant.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

from core.prometheus_metrics import get_metrics_exporter

#: Slow-request SLA used by ``aiops_apm_slow_request_rate`` (seconds).
_SLOW_REQUEST_SLA_SECONDS = 1.0

#: Default sampling cadence.
_DEFAULT_INTERVAL_SECONDS = 30.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ObservabilityMetricsCollector:
    """Periodically samples real platform state into the metrics exporter."""

    def __init__(
        self,
        interval_seconds: float = _DEFAULT_INTERVAL_SECONDS,
        host: Optional[str] = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.host = host or os.getenv("HOSTNAME", "localhost")
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        # Track the last absolute totals for counters sampled from the database,
        # so the exported counter stays monotonic (required by ``rate()``) even
        # though the source table may shrink.
        self._counter_state: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Counter helpers
    # ------------------------------------------------------------------
    def _sync_counter(self, counter: Any, key: str, total: float) -> None:
        """Increment ``counter`` by the delta since the previous sample."""
        last = self._counter_state.get(key, 0.0)
        delta = total - last
        if delta > 0:
            counter.inc(delta)
        self._counter_state[key] = total

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------
    async def collect_once(self) -> None:
        """Run one sampling cycle."""
        exporter = get_metrics_exporter()
        db_ok = await self._collect_from_database(exporter)
        self._collect_db_pool(exporter)
        self._collect_system_resources(exporter)
        self._collect_derived_apm(exporter)
        exporter.health_status.set(1 if db_ok else 0)

    def _collect_db_pool(self, exporter: Any) -> None:
        """Publish the SQLAlchemy connection pool occupancy."""
        try:
            from core.db_engine import _ensure_engine

            pool = _ensure_engine().pool
            active = int(pool.checkedout())
            size = int(pool.size())
            exporter.record_db_pool_stats(active, max(0, size - active), size)
        except Exception as exc:  # pragma: no cover - pool probe is best effort
            logger.debug("observability: DB pool probe failed: %s", exc)

    async def _collect_from_database(self, exporter: Any) -> bool:
        """Sample database-backed domain metrics. Returns True when the probe worked."""
        try:
            from sqlalchemy import func, select

            from core.db_engine import AsyncSessionLocal
            from core.models import (
                AICapabilityEvaluationDB,
                AIGraphEdgeDB,
                AIGraphNodeDB,
                AIRootCauseAnalysisDB,
                Alert,
                AlertStatus,
                AuditLog,
                Backup,
                MonitoringAnomaly,
                PerformanceRegression,
                RepairRecord,
                RepairStatus,
                WorkflowExecution,
            )
        except Exception as exc:  # pragma: no cover - import guard
            logger.debug("observability: DB models unavailable: %s", exc)
            return False

        try:
            async with AsyncSessionLocal() as session:
                now = _utcnow()
                day_ago = now - timedelta(hours=24)

                # ---------------- Alerts ----------------
                alerts_total = await self._scalar(
                    session, select(func.count(Alert.id))
                )
                alerts_pending = await self._scalar(
                    session,
                    select(func.count(Alert.id)).where(
                        Alert.status != AlertStatus.RESOLVED.value
                    ),
                )
                alert_backlog = await self._scalar(
                    session,
                    select(func.count(Alert.id)).where(
                        Alert.status == AlertStatus.PENDING.value
                    ),
                )
                exporter.alerts_total.set(alerts_total)
                exporter.alerts_pending.set(alerts_pending)
                exporter.alert_backlog_count.set(alert_backlog)

                # ---------------- Repairs ----------------
                repairs_total = await self._scalar(
                    session, select(func.count(RepairRecord.id))
                )
                repairs_failed = await self._scalar(
                    session,
                    select(func.count(RepairRecord.id)).where(RepairRecord.success.is_(False)),
                )
                repairs_success = await self._scalar(
                    session,
                    select(func.count(RepairRecord.id)).where(RepairRecord.success.is_(True)),
                )
                repair_active = await self._scalar(
                    session,
                    select(func.count(RepairRecord.id)).where(
                        RepairRecord.status.in_(
                            [RepairStatus.PENDING.value, RepairStatus.IN_PROGRESS.value]
                        )
                    ),
                )
                self._sync_counter(exporter.repairs_total, "repairs_total", repairs_total)
                self._sync_counter(
                    exporter.repairs_failed_total, "repairs_failed", repairs_failed
                )
                self._sync_counter(
                    exporter.repairs_successful_total, "repairs_success", repairs_success
                )
                exporter.repair_active_count.set(repair_active)

                avg_duration = await self._scalar(
                    session, select(func.avg(RepairRecord.repair_duration_sec))
                )
                if avg_duration is not None:
                    exporter.mttr_minutes.set(round(float(avg_duration) / 60.0, 4))

                # ---------------- Backups ----------------
                last_backup = (
                    await session.execute(
                        select(Backup).order_by(Backup.started_at.desc()).limit(1)
                    )
                ).scalars().first()
                if last_backup is not None:
                    exporter.backup_last_status.set(
                        1 if (last_backup.status or "").lower() == "completed" else 0
                    )
                    if last_backup.started_at is not None:
                        exporter.backup_last_timestamp.set(
                            last_backup.started_at.replace(tzinfo=timezone.utc).timestamp()
                        )
                storage_total = await self._scalar(
                    session, select(func.coalesce(func.sum(Backup.size_bytes), 0))
                )
                exporter.backup_storage_total.set(float(storage_total or 0))
                exporter.backup_storage_available.set(float(self._backup_volume_free_bytes()))

                # ---------------- Anomalies ----------------
                anomalies_total = await self._scalar(
                    session,
                    select(func.count(MonitoringAnomaly.id)).where(
                        MonitoringAnomaly.is_anomaly.is_(True)
                    ),
                )
                recent_anomalies = await self._scalar(
                    session,
                    select(func.count(MonitoringAnomaly.id)).where(
                        MonitoringAnomaly.is_anomaly.is_(True),
                        MonitoringAnomaly.detected_at >= day_ago,
                    ),
                )
                self._sync_counter(
                    exporter.anomalies_detected_total, "anomalies_total", anomalies_total
                )
                exporter.recent_anomalies.set(recent_anomalies)

                # ---------------- Audit logs ----------------
                audit_total = await self._scalar(session, select(func.count(AuditLog.id)))
                self._sync_counter(exporter.audit_logs_total, "audit_total", audit_total)

                # ---------------- Performance regressions ----------------
                rows = (
                    await session.execute(
                        select(
                            PerformanceRegression.severity,
                            PerformanceRegression.status,
                            func.count(PerformanceRegression.id),
                        ).group_by(
                            PerformanceRegression.severity, PerformanceRegression.status
                        )
                    )
                ).all()
                for severity, status_value, count in rows:
                    exporter.performance_regressions.labels(
                        severity=str(severity or "unknown"),
                        status=str(status_value or "unknown"),
                    ).set(count)

                # ---------------- Root-cause success rate ----------------
                rca_total = await self._scalar(
                    session, select(func.count(AIRootCauseAnalysisDB.id))
                )
                if rca_total:
                    rca_concluded = await self._scalar(
                        session,
                        select(func.count(AIRootCauseAnalysisDB.id)).where(
                            AIRootCauseAnalysisDB.root_cause.isnot(None),
                            AIRootCauseAnalysisDB.root_cause != "",
                        ),
                    )
                    exporter.root_cause_success_rate.set(rca_concluded / rca_total)

                # ---------------- Model accuracy ----------------
                avg_score = await self._scalar(
                    session, select(func.avg(AICapabilityEvaluationDB.overall_score))
                )
                if avg_score is not None:
                    score = float(avg_score)
                    if score > 1.0:  # stored on a 0-100 scale
                        score = score / 100.0
                    exporter.model_accuracy.set(round(score, 4))

                # ---------------- Knowledge graph size ----------------
                kg_nodes = await self._scalar(session, select(func.count(AIGraphNodeDB.id)))
                kg_edges = await self._scalar(session, select(func.count(AIGraphEdgeDB.id)))
                exporter.update_kg_size(int(kg_nodes), int(kg_edges))

                # ---------------- Workflow queue depth ----------------
                queue_size = await self._scalar(
                    session,
                    select(func.count(WorkflowExecution.id)).where(
                        WorkflowExecution.status.in_(["pending", "running"])
                    ),
                )
                exporter.update_workflow_queue_size(int(queue_size))

            return True
        except Exception as exc:
            logger.warning("observability: database sampling failed: %s", exc)
            return False

    @staticmethod
    async def _scalar(session: Any, stmt: Any) -> Any:
        result = await session.execute(stmt)
        return result.scalar()

    def _backup_volume_free_bytes(self) -> int:
        """Free bytes on the volume that stores backups."""
        candidates = [os.getenv("AIOPS_BACKUP_DIR"), "backups", "/"]
        for candidate in candidates:
            if not candidate:
                continue
            target = candidate if os.path.isdir(candidate) else os.path.dirname(candidate)
            target = target or "."
            try:
                if os.path.isdir(target):
                    return int(shutil.disk_usage(target).free)
            except OSError:
                continue
        return 0

    def _collect_system_resources(self, exporter: Any) -> None:
        """Sample host resource gauges via psutil."""
        if psutil is None:
            return
        try:
            cpu = float(psutil.cpu_percent(interval=None))
            memory = float(psutil.virtual_memory().percent)
            disk = float(psutil.disk_usage(os.getcwd()).percent)
            exporter.system_cpu_usage.labels(host=self.host).set(cpu)
            exporter.system_memory_usage.labels(host=self.host).set(memory)
            exporter.system_disk_usage.labels(host=self.host).set(disk)
            exporter.system_resource_usage.set(round(max(cpu, memory, disk) / 100.0, 4))

            net = psutil.net_io_counters()
            exporter.system_network_rx.labels(host=self.host).set(float(net.bytes_recv))
            exporter.system_network_tx.labels(host=self.host).set(float(net.bytes_sent))

            vm = psutil.virtual_memory()
            exporter.memory_usage_bytes.labels(instance=self.host).set(float(vm.used))
        except Exception as exc:  # pragma: no cover - psutil failure guard
            logger.debug("observability: psutil sampling failed: %s", exc)

    def _collect_derived_apm(self, exporter: Any) -> None:
        """Derive APM error / slow-request rates from the request metrics."""
        total_requests = 0.0
        error_requests = 0.0
        for metric in exporter.api_requests_total.collect():
            for sample in metric.samples:
                if not sample.name.endswith("_total"):
                    continue
                total_requests += sample.value
                status = sample.labels.get("status", "0")
                try:
                    if int(status) >= 400:
                        error_requests += sample.value
                except (TypeError, ValueError):
                    continue
        if total_requests > 0:
            exporter.apm_error_rate.set(round(error_requests / total_requests, 4))

        # Slow-request rate from the latency histogram buckets.
        bucket_counts: Dict[str, float] = {}
        for metric in exporter.api_request_duration_seconds.collect():
            for sample in metric.samples:
                if sample.name.endswith("_bucket"):
                    le = sample.labels.get("le", "")
                    bucket_counts[le] = bucket_counts.get(le, 0.0) + sample.value

        total_obs = bucket_counts.get("+Inf")
        if total_obs:
            fast = self._count_le(bucket_counts, _SLOW_REQUEST_SLA_SECONDS)
            exporter.apm_slow_request_rate.set(
                round(max(0.0, (total_obs - fast) / total_obs), 4)
            )

    @staticmethod
    def _count_le(bucket_counts: Dict[str, float], threshold: float) -> float:
        """Return the observation count at or below ``threshold`` from histogram buckets."""
        best = 0.0
        best_le = None
        for le, count in bucket_counts.items():
            if le == "+Inf":
                continue
            try:
                value = float(le)
            except (TypeError, ValueError):
                continue
            if value <= threshold and (best_le is None or value > best_le):
                best_le = value
                best = count
        return best

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def _run(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await self.collect_once()
            except asyncio.CancelledError:  # pragma: no cover - cooperative cancel
                raise
            except Exception as exc:  # pragma: no cover - never kill the loop
                logger.warning("observability: sampling cycle failed: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self.interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        """Start background sampling (idempotent)."""
        if self._task is not None and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="observability-metrics")
        logger.info("Observability metrics collector started (every %.0fs)", self.interval_seconds)

    async def stop(self) -> None:
        """Stop background sampling."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):  # pragma: no cover
                self._task.cancel()
            self._task = None


_collector: Optional[ObservabilityMetricsCollector] = None


def get_observability_collector() -> ObservabilityMetricsCollector:
    """Return the process-wide observability collector."""
    global _collector
    if _collector is None:
        _collector = ObservabilityMetricsCollector()
    return _collector


def start_observability_metrics() -> ObservabilityMetricsCollector:
    """Start (or return) the observability collector."""
    collector = get_observability_collector()
    collector.start()
    return collector


async def stop_observability_metrics() -> None:
    """Stop the observability collector if running."""
    if _collector is not None:
        await _collector.stop()


def _noop() -> Callable[[], None]:  # pragma: no cover - helper for typing
    return lambda: None
