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
        """
        Execute single transformation

        Args:
            transformation: Transformation rule
            data: Data to transform

        Returns:
            Transformed data
        """
        # In real implementation, would execute actual transformation logic
        # For now, return data as-is
        await asyncio.sleep(0.1)  # Simulate transformation
        return data

    async def _store_to_knowledge_layer(self, stream_id: str, data: List[Dict[str, Any]]) -> None:
        """
        Store data to L5 Knowledge Layer

        Args:
            stream_id: Stream ID
            data: Data to store
        """
        # In real implementation, would store to knowledge graph or vector database
        await asyncio.sleep(0.2)  # Simulate storage
        logger.debug(f"Stored {len(data)} records to knowledge layer from stream: {stream_id}")

    async def query_data(
        self, stream_id: str, query: Dict[str, Any], time_range: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Query integrated data

        Args:
            stream_id: Stream ID
            query: Query parameters
            time_range: Optional time range filter

        Returns:
            Query results
        """
        if stream_id not in self.data_streams:
            return []

        # In real implementation, would query from knowledge layer
        # For now, return empty list
        return []

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
