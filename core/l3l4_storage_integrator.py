# -*- coding: utf-8 -*-
"""
L3-L4 Storage Integration (Phase 2)
Integration between L3 Processing Layer and L4 Storage Layer for optimized data persistence
"""

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from loguru import logger


class DataType(Enum):
    """Data type for storage"""

    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"
    ALERTS = "alerts"
    ANALYSIS_RESULTS = "analysis_results"
    WORKFLOW_STATE = "workflow_state"
    CONFIGURATION = "configuration"


class StorageBackend(Enum):
    """Storage backend type"""

    POSTGRESQL = "postgresql"
    REDIS = "redis"
    QDRANT = "qdrant"
    VICTORIAMETRICS = "victoriametrics"
    LOKI = "loki"
    TEMPO = "tempo"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class StoragePolicy:
    """Storage policy for data"""

    data_type: DataType
    primary_backend: StorageBackend
    secondary_backends: List[StorageBackend] = field(default_factory=list)
    retention_period: timedelta = timedelta(days=30)
    compression_enabled: bool = True
    indexing_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageRequest:
    """Storage request"""

    data_type: DataType
    data: Union[Dict[str, Any], List[Dict[str, Any]], str, bytes]
    metadata: Dict[str, Any] = field(default_factory=dict)
    policy: Optional[StoragePolicy] = None


@dataclass
class StorageResult:
    """Storage operation result"""

    success: bool
    backend: StorageBackend
    data_id: Optional[str] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StorageBackendAdapter(ABC):
    """Abstract base class for storage backend adapters"""

    @abstractmethod
    async def store(self, request: StorageRequest) -> StorageResult:
        """Store data"""

    @abstractmethod
    async def retrieve(self, data_id: str, data_type: DataType) -> Optional[Any]:
        """Retrieve data"""

    @abstractmethod
    async def delete(self, data_id: str, data_type: DataType) -> bool:
        """Delete data"""

    @abstractmethod
    async def query(self, query: Dict[str, Any], data_type: DataType) -> List[Any]:
        """Query data"""


class L3L4StorageIntegrator:
    """Integration between L3 Processing Layer and L4 Storage Layer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize L3-L4 storage integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Storage policies
        self.storage_policies: Dict[DataType, StoragePolicy] = {}
        self._initialize_storage_policies()

        # Backend adapters
        self.backend_adapters: Dict[StorageBackend, StorageBackendAdapter] = {}
        self._initialize_backend_adapters()

        # Data routing
        self.data_router_enabled = self.config.get("data_router_enabled", True)

        # Caching layer
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl", 300)

        # Statistics
        self.storage_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "failure": 0, "cache_hits": 0, "cache_misses": 0}
        )

        logger.info("L3-L4 storage integrator initialized")

    def _initialize_storage_policies(self):
        """Initialize default storage policies"""
        # Metrics policy - VictoriaMetrics + PostgreSQL
        self.storage_policies[DataType.METRICS] = StoragePolicy(
            data_type=DataType.METRICS,
            primary_backend=StorageBackend.VICTORIAMETRICS,
            secondary_backends=[StorageBackend.POSTGRESQL],
            retention_period=timedelta(days=90),
            compression_enabled=False,
            indexing_enabled=True,
        )

        # Logs policy - Loki + Elasticsearch
        self.storage_policies[DataType.LOGS] = StoragePolicy(
            data_type=DataType.LOGS,
            primary_backend=StorageBackend.LOKI,
            secondary_backends=[StorageBackend.ELASTICSEARCH],
            retention_period=timedelta(days=30),
            compression_enabled=True,
            indexing_enabled=True,
        )

        # Traces policy - Tempo + PostgreSQL
        self.storage_policies[DataType.TRACES] = StoragePolicy(
            data_type=DataType.TRACES,
            primary_backend=StorageBackend.TEMPO,
            secondary_backends=[StorageBackend.POSTGRESQL],
            retention_period=timedelta(days=7),
            compression_enabled=False,
            indexing_enabled=True,
        )

        # Alerts policy - PostgreSQL + Redis
        self.storage_policies[DataType.ALERTS] = StoragePolicy(
            data_type=DataType.ALERTS,
            primary_backend=StorageBackend.POSTGRESQL,
            secondary_backends=[StorageBackend.REDIS],
            retention_period=timedelta(days=365),
            compression_enabled=False,
            indexing_enabled=True,
        )

        # Analysis results policy - Qdrant + PostgreSQL
        self.storage_policies[DataType.ANALYSIS_RESULTS] = StoragePolicy(
            data_type=DataType.ANALYSIS_RESULTS,
            primary_backend=StorageBackend.QDRANT,
            secondary_backends=[StorageBackend.POSTGRESQL],
            retention_period=timedelta(days=180),
            compression_enabled=True,
            indexing_enabled=True,
        )

        # Workflow state policy - Redis + PostgreSQL
        self.storage_policies[DataType.WORKFLOW_STATE] = StoragePolicy(
            data_type=DataType.WORKFLOW_STATE,
            primary_backend=StorageBackend.REDIS,
            secondary_backends=[StorageBackend.POSTGRESQL],
            retention_period=timedelta(days=30),
            compression_enabled=False,
            indexing_enabled=False,
        )

        # Configuration policy - PostgreSQL + Redis
        self.storage_policies[DataType.CONFIGURATION] = StoragePolicy(
            data_type=DataType.CONFIGURATION,
            primary_backend=StorageBackend.POSTGRESQL,
            secondary_backends=[StorageBackend.REDIS],
            retention_period=timedelta(days=365),
            compression_enabled=False,
            indexing_enabled=True,
        )

    def _initialize_backend_adapters(self):
        """Initialize storage backend adapters"""
        try:
            # Initialize adapters for each backend
            # In a real implementation, these would be actual adapter classes
            for backend in StorageBackend:
                adapter = self._create_backend_adapter(backend)
                if adapter:
                    self.backend_adapters[backend] = adapter
                    logger.info(f"Initialized backend adapter: {backend.value}")
        except Exception as e:
            logger.error(f"Failed to initialize backend adapters: {e}")

    def _create_backend_adapter(self, backend: StorageBackend) -> Optional[StorageBackendAdapter]:
        """Create backend adapter for specific storage type"""
        import logging

        logging.getLogger(__name__).info(f"{__name__}._create_backend_adapter invoked")
        return None

    async def store_data(self, request: StorageRequest) -> StorageResult:
        """
        Store data using appropriate storage policy

        Args:
            request: Storage request

        Returns:
            StorageResult: Storage result
        """
        data_type = request.data_type
        policy = request.policy or self.storage_policies.get(data_type)

        if not policy:
            return StorageResult(
                success=False,
                backend=StorageBackend.POSTGRESQL,
                error=Exception(f"No storage policy for data type: {data_type.value}"),
            )

        # Update statistics
        self.storage_stats[data_type.value]["total"] += 1

        try:
            # Store in primary backend
            primary_result = await self._store_in_backend(request, policy.primary_backend)

            if primary_result.success:
                self.storage_stats[data_type.value]["success"] += 1

                # Store in secondary backends asynchronously
                for secondary_backend in policy.secondary_backends:
                    asyncio.create_task(self._store_in_backend(request, secondary_backend))

                return primary_result
            else:
                # Try secondary backends if primary fails
                for secondary_backend in policy.secondary_backends:
                    secondary_result = await self._store_in_backend(request, secondary_backend)
                    if secondary_result.success:
                        self.storage_stats[data_type.value]["success"] += 1
                        return secondary_result

                self.storage_stats[data_type.value]["failure"] += 1
                return primary_result

        except Exception as e:
            logger.error(f"Failed to store data: {e}")
            self.storage_stats[data_type.value]["failure"] += 1
            return StorageResult(success=False, backend=policy.primary_backend, error=e)

    async def _store_in_backend(
        self, request: StorageRequest, backend: StorageBackend
    ) -> StorageResult:
        """Store data in specific backend"""
        if backend not in self.backend_adapters:
            return StorageResult(
                success=False,
                backend=backend,
                error=Exception(f"Backend adapter not available: {backend.value}"),
            )

        adapter = self.backend_adapters[backend]
        return await adapter.store(request)

    async def retrieve_data(
        self, data_id: str, data_type: DataType, backend: Optional[StorageBackend] = None
    ) -> Optional[Any]:
        """
        Retrieve data from storage

        Args:
            data_id: Data identifier
            data_type: Data type
            backend: Specific backend to use (optional)

        Returns:
            Retrieved data or None
        """
        policy = self.storage_policies.get(data_type)
        if not policy:
            return None

        # Check cache first if enabled
        if self.cache_enabled and backend is None:
            cached_data = await self._retrieve_from_cache(data_id, data_type)
            if cached_data is not None:
                self.storage_stats[data_type.value]["cache_hits"] += 1
                return cached_data
            else:
                self.storage_stats[data_type.value]["cache_misses"] += 1

        # Determine backend to use
        target_backend = backend or policy.primary_backend

        if target_backend not in self.backend_adapters:
            # Try secondary backends
            for secondary_backend in policy.secondary_backends:
                if secondary_backend in self.backend_adapters:
                    target_backend = secondary_backend
                    break
            else:
                return None

        adapter = self.backend_adapters[target_backend]
        data = await adapter.retrieve(data_id, data_type)

        # Store in cache if enabled
        if self.cache_enabled and data is not None:
            await self._store_in_cache(data_id, data_type, data)

        return data

    async def delete_data(self, data_id: str, data_type: DataType) -> bool:
        """
        Delete data from storage

        Args:
            data_id: Data identifier
            data_type: Data type

        Returns:
            Success status
        """
        policy = self.storage_policies.get(data_type)
        if not policy:
            return False

        # Delete from all backends
        all_backends = [policy.primary_backend] + policy.secondary_backends
        success_count = 0

        for backend in all_backends:
            if backend in self.backend_adapters:
                adapter = self.backend_adapters[backend]
                if await adapter.delete(data_id, data_type):
                    success_count += 1

        # Remove from cache
        if self.cache_enabled:
            await self._remove_from_cache(data_id, data_type)

        return success_count > 0

    async def query_data(
        self, query: Dict[str, Any], data_type: DataType, backend: Optional[StorageBackend] = None
    ) -> List[Any]:
        """
        Query data from storage

        Args:
            query: Query parameters
            data_type: Data type
            backend: Specific backend to use (optional)

        Returns:
            Query results
        """
        policy = self.storage_policies.get(data_type)
        if not policy:
            return []

        target_backend = backend or policy.primary_backend

        if target_backend not in self.backend_adapters:
            return []

        adapter = self.backend_adapters[target_backend]
        return await adapter.query(query, data_type)

    async def _retrieve_from_cache(self, data_id: str, data_type: DataType) -> Optional[Any]:
        """Retrieve data from cache"""
        import logging

        logging.getLogger(__name__).info(f"{__name__}._retrieve_from_cache invoked")
        return None

    async def _store_in_cache(self, data_id: str, data_type: DataType, data: Any) -> None:
        """Store data in cache"""
        import logging

        logging.getLogger(__name__).info(f"{__name__}._store_in_cache invoked")
        return None
        # In real implementation, would use Redis or in-memory cache

    async def _remove_from_cache(self, data_id: str, data_type: DataType) -> None:
        """Remove data from cache"""
        import logging

        logging.getLogger(__name__).info(f"{__name__}._remove_from_cache invoked")
        return None
        # In real implementation, would use Redis or in-memory cache

    def register_storage_policy(self, policy: StoragePolicy) -> None:
        """
        Register custom storage policy

        Args:
            policy: Storage policy
        """
        self.storage_policies[policy.data_type] = policy
        logger.info(f"Registered storage policy for: {policy.data_type.value}")

    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        return {
            "data_type_stats": dict(self.storage_stats),
            "registered_policies": len(self.storage_policies),
            "available_backends": len(self.backend_adapters),
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
        }

    def get_storage_policy(self, data_type: DataType) -> Optional[StoragePolicy]:
        """
        Get storage policy for data type

        Args:
            data_type: Data type

        Returns:
            Storage policy or None
        """
        return self.storage_policies.get(data_type)


def get_l3l4_storage_integrator(config: Optional[Dict[str, Any]] = None) -> L3L4StorageIntegrator:
    """
    Factory function to get L3-L4 storage integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        L3L4StorageIntegrator: Integrator instance
    """
    return L3L4StorageIntegrator(config)
