# -*- coding: utf-8 -*-
"""gRPC servicer implementation for the ``aiops.AIOpsService`` proto.

The servicer is a thin, real adapter over existing core subsystems:

* metrics / processes -> :mod:`core.collector`
* alerts              -> :class:`core.alert_service.AlertService`
* repairs             -> :data:`core.auto_heal.CROSS_PLATFORM_EXECUTOR`
* analysis            -> :mod:`core.root_cause_intelligence` when available

Blocking collectors are dispatched to a worker thread so the asyncio gRPC
server is never blocked.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import grpc
from loguru import logger

from proto import aiops_pb2, aiops_pb2_grpc


def _to_epoch(value: Any) -> int:
    """Normalise the many timestamp shapes used across the core into Unix epoch.

    ``core.collector`` reports ISO-8601 strings, the alert service reports
    ISO-8601 strings as well, and some producers already use ints. The proto
    field is ``int64``, so everything must be converted - never cast blindly.
    """
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        try:
            return int(float(text))
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return 0
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    return 0


class AIOpsServiceServicer(aiops_pb2_grpc.AIOpsServiceServicer):
    """Concrete implementation of the AIOps gRPC service."""

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    async def GetMetrics(  # noqa: N802 - proto method name
        self, request: aiops_pb2.MetricsRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.MetricsResponse:
        """Return current host metrics collected from the local probe."""
        try:
            from core.collector import collect_system_metrics

            snapshot = await asyncio.to_thread(collect_system_metrics)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an error
            logger.error(f"GetMetrics failed: {exc}")
            await context.abort(grpc.StatusCode.INTERNAL, f"metrics collection failed: {exc}")

        metrics = aiops_pb2.SystemMetrics(
            cpu_usage=float(snapshot.get("cpu_percent") or 0.0),
            memory_usage=float(snapshot.get("memory_percent") or 0.0),
            disk_usage=float(snapshot.get("disk_percent") or self._max_disk_percent(snapshot)),
            network_rx=int(snapshot.get("net_bytes_recv") or 0),
            network_tx=int(snapshot.get("net_bytes_sent") or 0),
            timestamp=_to_epoch(snapshot.get("timestamp")),
        )
        return aiops_pb2.MetricsResponse(metrics=metrics)

    @staticmethod
    def _max_disk_percent(snapshot: Dict[str, Any]) -> float:
        """Derive a disk figure when the probe reports per-partition data."""
        disks = snapshot.get("disks")
        if isinstance(disks, list) and disks:
            percents = [float(d.get("percent") or 0.0) for d in disks if isinstance(d, dict)]
            if percents:
                return max(percents)
        return 0.0

    # ------------------------------------------------------------------
    # Processes
    # ------------------------------------------------------------------
    async def GetTopProcesses(  # noqa: N802
        self, request: aiops_pb2.ProcessRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.ProcessResponse:
        """Return the top resource-consuming processes."""
        limit = request.limit or 10
        try:
            from core.collector import get_top_processes

            processes = await asyncio.to_thread(get_top_processes, limit)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"GetTopProcesses failed: {exc}")
            await context.abort(grpc.StatusCode.INTERNAL, f"process collection failed: {exc}")

        return aiops_pb2.ProcessResponse(
            processes=[
                aiops_pb2.ProcessInfo(
                    pid=int(p.get("pid") or 0),
                    name=str(p.get("name") or ""),
                    cpu_percent=float(p.get("cpu_percent") or 0.0),
                    memory_percent=float(p.get("memory_percent") or 0.0),
                    status=str(p.get("status") or ""),
                )
                for p in processes
            ]
        )

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _list_alert_dicts(self, limit: int) -> List[Dict[str, Any]]:
        from core.alert_service import alert_service

        result = alert_service.get_alerts(limit=limit)
        alerts = result.get("alerts") if isinstance(result, dict) else result
        return list(alerts or [])

    @staticmethod
    def _to_proto_alert(alert: Dict[str, Any]) -> aiops_pb2.Alert:
        return aiops_pb2.Alert(
            id=str(alert.get("id") or alert.get("alert_id") or ""),
            level=str(alert.get("level") or alert.get("severity") or ""),
            title=str(alert.get("title") or alert.get("message") or ""),
            description=str(alert.get("description") or alert.get("message") or ""),
            platform=str(alert.get("platform") or alert.get("source") or ""),
            timestamp=_to_epoch(alert.get("timestamp") or alert.get("created_at")),
            resolved=str(alert.get("status") or "").lower() in {"resolved", "closed"},
        )

    async def ListAlerts(  # noqa: N802
        self, request: aiops_pb2.AlertRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.AlertsResponse:
        """List alerts, optionally filtered by level/platform/resolved."""
        limit = request.limit or 20
        alerts = await asyncio.to_thread(self._list_alert_dicts, limit)

        filtered = []
        for alert in alerts:
            proto = self._to_proto_alert(alert)
            if request.level and proto.level != request.level:
                continue
            if request.platform and proto.platform != request.platform:
                continue
            if request.resolved and not proto.resolved:
                continue
            filtered.append(proto)
        return aiops_pb2.AlertsResponse(alerts=filtered)

    async def GetAlert(  # noqa: N802
        self, request: aiops_pb2.AlertRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.AlertResponse:
        """Fetch a single alert by id."""
        if not request.id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "alert id is required")
        alerts = await asyncio.to_thread(self._list_alert_dicts, 1000)
        for alert in alerts:
            proto = self._to_proto_alert(alert)
            if proto.id == request.id:
                return aiops_pb2.AlertResponse(alert=proto)
        await context.abort(grpc.StatusCode.NOT_FOUND, f"alert not found: {request.id}")

    async def CreateAlert(  # noqa: N802
        self, request: aiops_pb2.CreateAlertRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.AlertResponse:
        """Create a new alert through the alert service."""
        if not request.title:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "title is required")

        from core.alert_service import alert_service

        created = await alert_service.create_alert(
            severity=request.level or "warning",
            message=request.title,
            source=request.platform or "grpc",
        )
        if request.description:
            created["description"] = request.description
        return aiops_pb2.AlertResponse(alert=self._to_proto_alert(created))

    async def ResolveAlert(  # noqa: N802
        self, request: aiops_pb2.ResolveAlertRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.Empty:
        """Mark an alert as resolved."""
        if not request.alert_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "alert_id is required")

        from core.alert_service import alert_service

        updated = await alert_service.update_alert_status(request.alert_id, "resolved")
        if not updated:
            await context.abort(grpc.StatusCode.NOT_FOUND, f"alert not found: {request.alert_id}")
        return aiops_pb2.Empty()

    # ------------------------------------------------------------------
    # Repairs
    # ------------------------------------------------------------------
    async def ExecuteRepair(  # noqa: N802
        self, request: aiops_pb2.RepairRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.RepairResponse:
        """Execute a registered repair script."""
        if not request.script_key:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "script_key is required")

        from core.auto_heal import CROSS_PLATFORM_EXECUTOR, repair_script_library

        script = repair_script_library.get_script(request.script_key)
        if script is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND, f"unknown repair script: {request.script_key}"
            )

        result = await asyncio.to_thread(
            CROSS_PLATFORM_EXECUTOR.execute_script,
            request.script_key,
            dict(request.parameters),
        )
        if result.get("requires_approval"):
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"script '{request.script_key}' requires human approval",
            )

        return aiops_pb2.RepairResponse(
            repair=aiops_pb2.RepairAction(
                id=request.script_key,
                script_key=request.script_key,
                success=bool(result.get("success")),
                duration_ms=int(result.get("duration") or 0),
                error_message=str(result.get("error") or ""),
            )
        )

    async def ListRepairs(  # noqa: N802
        self, request: aiops_pb2.RepairRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.RepairsResponse:
        """List the repair scripts available on this host."""
        from core.auto_heal import CROSS_PLATFORM_EXECUTOR

        scripts = await asyncio.to_thread(CROSS_PLATFORM_EXECUTOR.get_available_scripts)
        actions = [
            aiops_pb2.RepairAction(
                id=s["script_key"],
                script_key=s["script_key"],
                success=True,
            )
            for s in scripts
        ]
        return aiops_pb2.RepairsResponse(repairs=actions)

    # ------------------------------------------------------------------
    # AI analysis
    # ------------------------------------------------------------------
    async def Analyze(  # noqa: N802
        self, request: aiops_pb2.AIAnalysisRequest, context: grpc.aio.ServicerContext
    ) -> aiops_pb2.AIAnalysisResponse:
        """Run root-cause analysis for a natural-language query."""
        if not request.query:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "query is required")

        engine = self._load_analyzer()
        if engine is None:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "no AI analysis engine is available in this deployment",
            )

        analyzed = await asyncio.to_thread(
            engine, request.query, request.platform, dict(request.context)
        )
        return aiops_pb2.AIAnalysisResponse(
            analysis=aiops_pb2.AIAnalysis(
                id=str(analyzed.get("id") or ""),
                query=request.query,
                result=str(analyzed.get("result") or analyzed.get("root_cause") or ""),
                model_used=str(analyzed.get("model_used") or analyzed.get("model") or "rules"),
                tokens_used=int(analyzed.get("tokens_used") or 0),
                timestamp=_to_epoch(analyzed.get("timestamp")),
            )
        )

    @staticmethod
    def _load_analyzer() -> Optional[Any]:
        """Resolve a callable ``(query, platform, context) -> dict`` analyzer."""
        try:
            from core.root_cause_intelligence import RootCauseIntelligence  # type: ignore

            engine = RootCauseIntelligence()

            def _analyze(query: str, platform: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
                return engine.analyze(query=query, platform=platform, context=ctx)

            return lambda q, p, c: _analyze(q, p, c)
        except Exception:  # noqa: BLE001 - optional dependency
            return None

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------
    async def StreamMetrics(  # noqa: N802
        self, request: aiops_pb2.StreamRequest, context: grpc.aio.ServicerContext
    ) -> Any:
        """Stream system metrics once per subscribed interval."""
        interval = float(dict(request.filters).get("interval_seconds", 5) or 5)
        while context.is_active():
            response = await self.GetMetrics(aiops_pb2.MetricsRequest(), context)
            yield aiops_pb2.StreamResponse(status="metrics")
            yield aiops_pb2.StreamResponse(metrics=response.metrics)
            await asyncio.sleep(interval)

    async def StreamAlerts(  # noqa: N802
        self, request: aiops_pb2.StreamRequest, context: grpc.aio.ServicerContext
    ) -> Any:
        """Stream newly observed alerts."""
        filters = dict(request.filters)
        interval = float(filters.get("interval_seconds", 5) or 5)
        seen: set[str] = set()
        while context.is_active():
            alerts = await asyncio.to_thread(self._list_alert_dicts, 200)
            for alert in alerts:
                proto = self._to_proto_alert(alert)
                if proto.id in seen:
                    continue
                seen.add(proto.id)
                yield aiops_pb2.StreamResponse(alert=proto)
            await asyncio.sleep(interval)
