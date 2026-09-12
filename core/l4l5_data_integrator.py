# -*- coding: utf-8 -*-
"""
L4-L5 Real-time Data Integration (Phase 3)
Integration between L4 Storage Layer and L5 Knowledge Layer for real-time data processing
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class DataType(Enum):
    """Data type for integration"""

    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"
    EVENTS = "events"
    ALERTS = "alerts"
    KNOWLEDGE = "knowledge"


class ProcessingMode(Enum):
    """Processing mode"""

    REALTIME = "realtime"
    BATCH = "batch"
    STREAMING = "streaming"
    HYBRID = "hybrid"


class DataQuality(Enum):
    """Data quality level"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class DataStream:
    """Data stream configuration"""

    stream_id: str
    data_type: DataType
    source: str
    destination: str
    processing_mode: ProcessingMode = ProcessingMode.REALTIME
    batch_size: int = 100
    flush_interval: int = 5
    quality_threshold: DataQuality = DataQuality.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataTransformation:
    """Data transformation rule"""

    transformation_id: str
    name: str
    transformation_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationMetrics:
    """Integration metrics"""

    stream_id: str
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    avg_processing_time: float = 0.0
    throughput: float = 0.0
    last_processed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class L4L5DataIntegrator:
    """Integration between L4 Storage Layer and L5 Knowledge Layer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize L4-L5 data integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Data streams
        self.data_streams: Dict[str, DataStream] = {}
        self.stream_metrics: Dict[str, IntegrationMetrics] = {}

        # Transformations
        self.transformations: Dict[str, DataTransformation] = {}

        # Data buffers
        self.data_buffers: Dict[str, List[Any]] = defaultdict(list)

        # Processing queues
        self.processing_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

        # Configuration
        self.max_buffer_size = self.config.get("max_buffer_size", 1000)
        self.auto_flush = self.config.get("auto_flush", True)

        # Statistics
        self.total_integrations = 0
        self.successful_integrations = 0

        logger.info("L4-L5 data integrator initialized")

    def register_data_stream(self, stream: DataStream) -> None:
        """
        Register data stream

        Args:
            stream: Data stream configuration
        """
        self.data_streams[stream.stream_id] = stream
        self.stream_metrics[stream.stream_id] = IntegrationMetrics(stream_id=stream.stream_id)
        logger.info(f"Registered data stream: {stream.stream_id}")

    def register_transformation(self, transformation: DataTransformation) -> None:
        """
        Register data transformation

        Args:
            transformation: Data transformation rule
        """
        self.transformations[transformation.transformation_id] = transformation
        logger.info(f"Registered transformation: {transformation.transformation_id}")

    async def ingest_data(
        self, stream_id: str, data: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ingest data into stream

        Args:
            stream_id: Stream ID
            data: Data to ingest
            metadata: Optional metadata

        Returns:
            Success status
        """
        if stream_id not in self.data_streams:
            logger.warning(f"Stream not found: {stream_id}")
            return False

        stream = self.data_streams[stream_id]

        try:
            # Add to buffer
            self.data_buffers[stream_id].append(
                {"data": data, "metadata": metadata or {}, "timestamp": datetime.now(timezone.utc)}
            )

            # Check buffer size
            if len(self.data_buffers[stream_id]) >= stream.batch_size:
                await self._flush_buffer(stream_id)

            # Update metrics
            metrics = self.stream_metrics[stream_id]
            metrics.total_records += 1

            logger.debug(f"Ingested data into stream: {stream_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to ingest data into stream {stream_id}: {e}")
            return False

    async def _flush_buffer(self, stream_id: str) -> None:
        """
        Flush data buffer for processing

        Args:
            stream_id: Stream ID
        """
        if stream_id not in self.data_buffers or not self.data_buffers[stream_id]:
            return

        buffer = self.data_buffers[stream_id]
        self.data_streams[stream_id]

        # Process batch
        await self._process_batch(stream_id, buffer)

        # Clear buffer
        self.data_buffers[stream_id].clear()

        logger.info(f"Flushed buffer for stream: {stream_id}")

    async def _process_batch(self, stream_id: str, batch: List[Dict[str, Any]]) -> None:
        """
        Process data batch

        Args:
            stream_id: Stream ID
            batch: Data batch
        """
        self.data_streams[stream_id]
        metrics = self.stream_metrics[stream_id]

        start_time = datetime.now(timezone.utc)

        try:
            # Apply transformations
            transformed_data = await self._apply_transformations(stream_id, batch)

            # Store to L5 Knowledge Layer
            await self._store_to_knowledge_layer(stream_id, transformed_data)

            # Update metrics
            metrics.processed_records += len(batch)
            metrics.last_processed_at = datetime.now(timezone.utc)

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            metrics.avg_processing_time = (
                metrics.avg_processing_time * (metrics.processed_records - len(batch))
                + processing_time
            ) / metrics.processed_records

            self.successful_integrations += 1

        except Exception as e:
            logger.error(f"Failed to process batch for stream {stream_id}: {e}")
            metrics.failed_records += len(batch)

    async def _apply_transformations(
        self, stream_id: str, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply data transformations

        Args:
            stream_id: Stream ID
            data: Data to transform

        Returns:
            Transformed data
        """
        transformed_data = data

        # Apply enabled transformations
        for transformation in self.transformations.values():
            if transformation.enabled:
                transformed_data = await self._execute_transformation(
                    transformation, transformed_data
                )

        return transformed_data

    async def _execute_transformation(
        self, transformation: DataTransformation, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute a single transformation rule (real logic).

        历史问题（已修复）：原实现仅 ``asyncio.sleep(0.1)`` 后原样返回数据（"Simulate
        transformation"），任何规则都不产生效果。现按 ``transformation_type`` 真实执行
        过滤/投影/重命名/去重/聚合/富化等算子。
        """
        t_type = (transformation.transformation_type or "").lower()
        cfg = transformation.config or {}

        if t_type in ("identity", "none", ""):
            return list(data)

        if t_type == "filter":
            field_name = cfg.get("field")
            expected = cfg.get("value")
            op = cfg.get("op", "eq")
            if field_name is None:
                raise ValueError("filter transformation requires 'field'")
            if op == "eq":
                return [r for r in data if r.get(field_name) == expected]
            if op == "ne":
                return [r for r in data if r.get(field_name) != expected]
            if op == "gt":
                return [r for r in data if r.get(field_name, 0) > expected]
            if op == "lt":
                return [r for r in data if r.get(field_name, 0) < expected]
            if op == "in":
                return [r for r in data if r.get(field_name) in (expected or [])]
            raise ValueError(f"unsupported filter op: {op}")

        if t_type in ("project", "map_fields"):
            fields = cfg.get("fields", [])
            return [{k: r.get(k) for k in fields} for r in data]

        if t_type in ("rename", "rename_fields"):
            mapping = cfg.get("mapping", {})
            out = []
            for r in data:
                new_r = dict(r)
                for old, new in mapping.items():
                    if old in new_r:
                        new_r[new] = new_r.pop(old)
                out.append(new_r)
            return out

        if t_type in ("deduplicate", "dedupe", "distinct"):
            key = cfg.get("key")
            seen = set()
            out = []
            for r in data:
                k = r.get(key) if key else tuple(sorted(r.items(), key=lambda kv: kv[0]))
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        if t_type == "aggregate":
            group_by = cfg.get("group_by")
            agg_field = cfg.get("agg_field")
            func = cfg.get("func", "sum")
            if not group_by or not agg_field:
                raise ValueError("aggregate transformation requires 'group_by' and 'agg_field'")
            groups: Dict[Any, List[float]] = defaultdict(list)
            for r in data:
                groups[r.get(group_by)].append(float(r.get(agg_field, 0) or 0))
            out = []
            for g, values in groups.items():
                if func == "sum":
                    val = sum(values)
                elif func == "avg":
                    val = sum(values) / len(values) if values else 0.0
                elif func == "count":
                    val = len(values)
                elif func == "max":
                    val = max(values) if values else 0.0
                elif func == "min":
                    val = min(values) if values else 0.0
                else:
                    raise ValueError(f"unsupported aggregate func: {func}")
                out.append({"group": g, f"{func}_{agg_field}": val, "count": len(values)})
            return out

        if t_type in ("enrich", "add_fields"):
            extra = cfg.get("add", {})
            return [{**r, **extra} for r in data]

        raise ValueError(f"unknown transformation type: {transformation.transformation_type}")

    async def _store_to_knowledge_layer(self, stream_id: str, data: List[Dict[str, Any]]) -> None:
        """Store data to L5 Knowledge Layer through real storage backends.

        历史问题（已修复）：原实现仅 ``asyncio.sleep(0.2)``（"would store to knowledge
        graph or vector database"），数据从未落地。现通过 ``L3L4StorageIntegrator`` 将
        批次数据真实写入 L4/L5 存储后端；写入失败时抛错由上层计入 failed_records。
        """
        if not data:
            return

        from core.l3l4_storage_integrator import (
            DataType as StorageDataType,
            StorageBackend,
            StorageRequest,
            get_l3l4_storage_integrator,
        )

        integrator = self._get_storage_integrator()
        request = StorageRequest(
            data_type=StorageDataType.ANALYSIS_RESULTS,
            data=data,
            metadata={"id": f"stream:{stream_id}", "stream_id": stream_id},
        )
        result = await integrator.store_data(request)
        if not result.success:
            raise RuntimeError(
                f"knowledge-layer store failed for stream {stream_id}: {result.error}"
            )
        logger.debug(
            f"Stored {len(data)} records to knowledge layer from stream {stream_id} "
            f"(backend={result.backend.value})"
        )
        self._last_knowledge_backend: StorageBackend = result.backend

    async def query_data(
        self, stream_id: str, query: Dict[str, Any], time_range: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Query integrated data from the real knowledge layer.

        历史问题（已修复）：原实现恒 ``return []``。现查询 L4/L5 存储后端并返回真实结果。
        """
        if stream_id not in self.data_streams:
            return []

        from core.l3l4_storage_integrator import (
            DataType as StorageDataType,
            get_l3l4_storage_integrator,
        )

        integrator = self._get_storage_integrator()
        backend = getattr(self, "_last_knowledge_backend", None)
        results = await integrator.query_data(
            query or {"stream_id": stream_id}, StorageDataType.ANALYSIS_RESULTS, backend=backend
        )
        return list(results)

    def _get_storage_integrator(self):
        """Lazily create a shared L3-L4 storage integrator."""
        if getattr(self, "_storage_integrator", None) is None:
            from core.l3l4_storage_integrator import get_l3l4_storage_integrator

            self._storage_integrator = get_l3l4_storage_integrator(
                self.config.get("storage_config")
            )
        return self._storage_integrator

    async def start_realtime_processing(self) -> None:
        """Start real-time data processing"""

        async def processing_loop():
            while True:
                try:
                    # Auto-flush buffers
                    if self.auto_flush:
                        for stream_id in self.data_streams.keys():
                            if self.data_buffers[stream_id]:
                                await self._flush_buffer(stream_id)

                    await asyncio.sleep(1)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Real-time processing error: {e}")
                    await asyncio.sleep(1)

        asyncio.create_task(processing_loop())
        logger.info("Real-time processing started")

    async def stop_realtime_processing(self) -> None:
        """Stop real-time data processing"""
        # Flush all buffers
        for stream_id in self.data_buffers.keys():
            if self.data_buffers[stream_id]:
                await self._flush_buffer(stream_id)

        logger.info("Real-time processing stopped")

    def get_stream_metrics(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stream metrics

        Args:
            stream_id: Stream ID

        Returns:
            Stream metrics dictionary
        """
        if stream_id not in self.stream_metrics:
            return None

        metrics = self.stream_metrics[stream_id]

        return {
            "stream_id": metrics.stream_id,
            "total_records": metrics.total_records,
            "processed_records": metrics.processed_records,
            "failed_records": metrics.failed_records,
            "avg_processing_time": metrics.avg_processing_time,
            "throughput": metrics.throughput,
            "last_processed_at": (
                metrics.last_processed_at.isoformat() if metrics.last_processed_at else None
            ),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            "total_streams": len(self.data_streams),
            "total_transformations": len(self.transformations),
            "total_integrations": self.total_integrations,
            "successful_integrations": self.successful_integrations,
            "active_streams": len(
                [
                    s
                    for s in self.data_streams.values()
                    if s.processing_mode == ProcessingMode.REALTIME
                ]
            ),
        }


def get_l4l5_data_integrator(config: Optional[Dict[str, Any]] = None) -> L4L5DataIntegrator:
    """
    Factory function to get L4-L5 data integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        L4L5DataIntegrator: Integrator instance
    """
    return L4L5DataIntegrator(config)
