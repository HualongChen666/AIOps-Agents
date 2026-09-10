# -*- coding: utf-8 -*-
"""
gRPC Client SDK
Client library for connecting to AIOps gRPC service

Uses the generated stubs in ``proto/aiops_pb2_grpc.py`` (regenerate with
``python scripts/generate_proto.py``).
"""

from typing import Any, AsyncIterator, Dict, List, Optional

import grpc
from loguru import logger

from proto import aiops_pb2, aiops_pb2_grpc


class AIOpsGrpcClient:
    """
    gRPC client for AIOps Agent
    """

    def __init__(self, host: str = "localhost", port: int = 50051, timeout: float = 30.0):
        """
        Initialize gRPC client

        Args:
            host: Server host
            port: Server port
            timeout: Request timeout
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._channel: Optional[grpc.aio.Channel] = None
        self._grpc_client: Optional[aiops_pb2_grpc.AIOpsServiceStub] = None

    @property
    def target(self) -> str:
        """``host:port`` of the server this client talks to."""
        return f"{self.host}:{self.port}"

    async def connect(self) -> None:
        """Connect to gRPC server"""
        self._channel = grpc.aio.insecure_channel(self.target)
        await self._channel.channel_ready()
        self._grpc_client = aiops_pb2_grpc.AIOpsServiceStub(self._channel)
        logger.info(f"Connected to gRPC server at {self.target}")

    async def close(self) -> None:
        """Close client connection"""
        if self._channel:
            await self._channel.close()
            self._grpc_client = None
            logger.info("gRPC client closed")

    def _stub(self) -> aiops_pb2_grpc.AIOpsServiceStub:
        if self._grpc_client is None:
            raise RuntimeError("gRPC client not initialised: call connect() first")
        return self._grpc_client

    async def get_metrics(self) -> dict:
        """Get current system metrics"""
        stub = self._stub()
        response = await stub.GetMetrics(aiops_pb2.MetricsRequest(), timeout=self.timeout)
        return {
            "cpu_usage": response.metrics.cpu_usage,
            "memory_usage": response.metrics.memory_usage,
            "disk_usage": response.metrics.disk_usage,
            "network_rx": response.metrics.network_rx,
            "network_tx": response.metrics.network_tx,
            "timestamp": response.metrics.timestamp,
        }

    async def get_alerts(
        self, level: Optional[str] = None, platform: Optional[str] = None, limit: int = 10
    ) -> List[dict]:
        """Get alerts with filtering"""
        stub = self._stub()
        request = aiops_pb2.AlertRequest(
            level=level or "", platform=platform or "", limit=limit
        )
        response = await stub.ListAlerts(request, timeout=self.timeout)
        return [
            {
                "id": alert.id,
                "level": alert.level,
                "title": alert.title,
                "description": alert.description,
                "platform": alert.platform,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
            }
            for alert in response.alerts
        ]

    async def get_alert(self, alert_id: str) -> dict:
        """Get a single alert by id"""
        stub = self._stub()
        response = await stub.GetAlert(
            aiops_pb2.AlertRequest(id=alert_id), timeout=self.timeout
        )
        alert = response.alert
        return {
            "id": alert.id,
            "level": alert.level,
            "title": alert.title,
            "description": alert.description,
            "platform": alert.platform,
            "resolved": alert.resolved,
        }

    async def create_alert(
        self, level: str, title: str, description: str = "", platform: str = ""
    ) -> dict:
        """Create a new alert"""
        stub = self._stub()
        response = await stub.CreateAlert(
            aiops_pb2.CreateAlertRequest(
                level=level, title=title, description=description, platform=platform
            ),
            timeout=self.timeout,
        )
        return {"id": response.alert.id, "level": response.alert.level}

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        stub = self._stub()
        await stub.ResolveAlert(aiops_pb2.ResolveAlertRequest(alert_id=alert_id), timeout=self.timeout)
        return True

    async def get_top_processes(self, limit: int = 10) -> List[dict]:
        """Get the top resource-consuming processes"""
        stub = self._stub()
        response = await stub.GetTopProcesses(
            aiops_pb2.ProcessRequest(limit=limit), timeout=self.timeout
        )
        return [
            {
                "pid": p.pid,
                "name": p.name,
                "cpu_percent": p.cpu_percent,
                "memory_percent": p.memory_percent,
                "status": p.status,
            }
            for p in response.processes
        ]

    async def execute_repair(self, script_key: str, parameters: Optional[dict] = None) -> dict:
        """Execute a repair action"""
        stub = self._stub()
        response = await stub.ExecuteRepair(
            aiops_pb2.RepairRequest(script_key=script_key, parameters=parameters or {}),
            timeout=self.timeout,
        )
        return {
            "id": response.repair.id,
            "script_key": response.repair.script_key,
            "success": response.repair.success,
            "duration_ms": response.repair.duration_ms,
            "error_message": response.repair.error_message,
        }

    async def list_repairs(self) -> List[dict]:
        """List the repair scripts the server can execute"""
        stub = self._stub()
        response = await stub.ListRepairs(aiops_pb2.RepairRequest(), timeout=self.timeout)
        return [{"script_key": r.script_key} for r in response.repairs]

    async def analyze(
        self, query: str, platform: str = "", context: Optional[Dict[str, str]] = None
    ) -> dict:
        """Run root-cause analysis"""
        stub = self._stub()
        response = await stub.Analyze(
            aiops_pb2.AIAnalysisRequest(
                query=query, platform=platform, context=context or {}
            ),
            timeout=self.timeout,
        )
        return {
            "id": response.analysis.id,
            "result": response.analysis.result,
            "model_used": response.analysis.model_used,
            "tokens_used": response.analysis.tokens_used,
        }

    async def stream_metrics(self, interval_seconds: int = 5) -> AsyncIterator[Dict[str, Any]]:
        """Stream metrics updates"""
        stub = self._stub()
        request = aiops_pb2.StreamRequest(
            stream_type="metrics", filters={"interval_seconds": str(interval_seconds)}
        )
        async for response in stub.StreamMetrics(request):
            if response.WhichOneof("data") == "metrics":
                yield {
                    "cpu_usage": response.metrics.cpu_usage,
                    "memory_usage": response.metrics.memory_usage,
                    "disk_usage": response.metrics.disk_usage,
                    "timestamp": response.metrics.timestamp,
                }

    async def stream_alerts(self, interval_seconds: int = 5) -> AsyncIterator[Dict[str, Any]]:
        """Stream alerts updates"""
        stub = self._stub()
        request = aiops_pb2.StreamRequest(
            stream_type="alerts", filters={"interval_seconds": str(interval_seconds)}
        )
        async for response in stub.StreamAlerts(request):
            if response.WhichOneof("data") == "alert":
                yield {
                    "id": response.alert.id,
                    "level": response.alert.level,
                    "title": response.alert.title,
                }
