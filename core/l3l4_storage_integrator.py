# -*- coding: utf-8 -*-
"""
L3-L4 Storage Integration (Phase 2)
Integration between L3 Processing Layer and L4 Storage Layer for optimized data persistence
"""

import asyncio
import json
import time
import uuid
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


class _L4BackendAdapter(StorageBackendAdapter):
    """Adapter wrapping a real ``core.storage.l4`` backend (VictoriaMetrics/Loki/Tempo).

    The wrapped object implements :class:`core.base.storage.BaseStorage`
    (``store``/``retrieve``/``delete``/``query``).  This adapter maps the
    integrator's :class:`StorageRequest` onto that real interface; every call
    performs an actual network operation against the configured endpoint and
    reports the true outcome (no simulated success).
    """

    def __init__(self, backend: StorageBackend, storage: Any):
        self.backend = backend
        self._storage = storage

    @staticmethod
    def _key(request: StorageRequest) -> Optional[str]:
        meta = request.metadata or {}
        return meta.get("key") or meta.get("id")

    async def store(self, request: StorageRequest) -> StorageResult:
        key = self._key(request)
        if not key:
            return StorageResult(
                success=False,
                backend=self.backend,
                error=Exception("StorageRequest.metadata requires 'key' or 'id'"),
            )
        try:
            ok = await self._storage.store(key, request.data, request.metadata)
            return StorageResult(
                success=bool(ok),
                backend=self.backend,
                data_id=key if ok else None,
                error=None if ok else Exception(f"{self.backend.value} rejected write"),
            )
        except Exception as e:  # noqa: BLE001 - surface real failure
            logger.error(f"{self.backend.value} store failed: {e}")
            return StorageResult(success=False, backend=self.backend, error=e)

    async def retrieve(self, data_id: str, data_type: DataType) -> Optional[Any]:
        try:
            return await self._storage.retrieve(data_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"{self.backend.value} retrieve failed: {e}")
            return None

    async def delete(self, data_id: str, data_type: DataType) -> bool:
        try:
            return bool(await self._storage.delete(data_id))
        except Exception as e:  # noqa: BLE001
            logger.error(f"{self.backend.value} delete failed: {e}")
            return False

    async def query(self, query: Dict[str, Any], data_type: DataType) -> List[Any]:
        try:
            return await self._storage.query(query)
        except Exception as e:  # noqa: BLE001
            logger.error(f"{self.backend.value} query failed: {e}")
            return []


class _RedisAdapter(StorageBackendAdapter):
    """Real Redis-backed adapter using ``redis.asyncio``."""

    def __init__(self, client: Any, ttl_seconds: int = 300):
        self.backend = StorageBackend.REDIS
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def _key(data_id: str, data_type: DataType) -> str:
        return f"l3l4:{data_type.value}:{data_id}"

    async def store(self, request: StorageRequest) -> StorageResult:
        meta = request.metadata or {}
        data_id = meta.get("id") or meta.get("key") or str(uuid.uuid4())
        payload = json.dumps({"data": request.data, "metadata": meta}, default=str)
        try:
            await self._client.set(self._key(data_id, request.data_type), payload, ex=self._ttl)
            return StorageResult(success=True, backend=self.backend, data_id=data_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Redis store failed: {e}")
            return StorageResult(success=False, backend=self.backend, error=e)

    async def retrieve(self, data_id: str, data_type: DataType) -> Optional[Any]:
        try:
            raw = await self._client.get(self._key(data_id, data_type))
            if raw is None:
                return None
            return json.loads(raw)["data"]
        except Exception as e:  # noqa: BLE001
            logger.error(f"Redis retrieve failed: {e}")
            return None

    async def delete(self, data_id: str, data_type: DataType) -> bool:
        try:
            return bool(await self._client.delete(self._key(data_id, data_type)))
        except Exception as e:  # noqa: BLE001
            logger.error(f"Redis delete failed: {e}")
            return False

    async def query(self, query: Dict[str, Any], data_type: DataType) -> List[Any]:
        pattern = self._key(query.get("id", "*"), data_type)
        try:
            keys = await self._client.keys(pattern)
            out = []
            for k in keys:
                raw = await self._client.get(k)
                if raw is not None:
                    out.append(json.loads(raw)["data"])
            return out
        except Exception as e:  # noqa: BLE001
            logger.error(f"Redis query failed: {e}")
            return []


class _PostgresAdapter(StorageBackendAdapter):
    """Real PostgreSQL adapter using SQLAlchemy over a JSONB key/value table."""

    DDL = (
        "CREATE TABLE IF NOT EXISTS l3l4_storage ("
        "data_type VARCHAR(64) NOT NULL, data_id VARCHAR(255) NOT NULL, "
        "payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "PRIMARY KEY (data_type, data_id))"
    )

    def __init__(self, engine: Any):
        self.backend = StorageBackend.POSTGRESQL
        self._engine = engine
        self._ensure_table()

    def _ensure_table(self) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            conn.execute(text(self.DDL))

    async def _run(self, fn):
        return await asyncio.to_thread(fn)

    async def store(self, request: StorageRequest) -> StorageResult:
        from sqlalchemy import text

        meta = request.metadata or {}
        data_id = meta.get("id") or meta.get("key") or str(uuid.uuid4())
        payload = json.dumps(request.data, default=str)

        def _write():
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO l3l4_storage (data_type, data_id, payload) "
                        "VALUES (:t, :i, CAST(:p AS JSONB)) "
                        "ON CONFLICT (data_type, data_id) DO UPDATE SET payload = EXCLUDED.payload"
                    ),
                    {"t": request.data_type.value, "i": data_id, "p": payload},
                )
            return data_id

        try:
            data_id = await self._run(_write)
            return StorageResult(success=True, backend=self.backend, data_id=data_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"PostgreSQL store failed: {e}")
            return StorageResult(success=False, backend=self.backend, error=e)

    async def retrieve(self, data_id: str, data_type: DataType) -> Optional[Any]:
        from sqlalchemy import text

        def _read():
            with self._engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT payload FROM l3l4_storage WHERE data_type = :t AND data_id = :i"
                    ),
                    {"t": data_type.value, "i": data_id},
                ).fetchone()
                return row[0] if row else None

        try:
            payload = await self._run(_read)
            return json.loads(payload) if isinstance(payload, str) else payload
        except Exception as e:  # noqa: BLE001
            logger.error(f"PostgreSQL retrieve failed: {e}")
            return None

    async def delete(self, data_id: str, data_type: DataType) -> bool:
        from sqlalchemy import text

        def _del():
            with self._engine.begin() as conn:
                res = conn.execute(
                    text("DELETE FROM l3l4_storage WHERE data_type = :t AND data_id = :i"),
                    {"t": data_type.value, "i": data_id},
                )
                return res.rowcount > 0

        try:
            return bool(await self._run(_del))
        except Exception as e:  # noqa: BLE001
            logger.error(f"PostgreSQL delete failed: {e}")
            return False

    async def query(self, query: Dict[str, Any], data_type: DataType) -> List[Any]:
        from sqlalchemy import text

        def _q():
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT payload FROM l3l4_storage WHERE data_type = :t"),
                    {"t": data_type.value},
                ).fetchall()
                return [r[0] for r in rows]

        try:
            rows = await self._run(_q)
            return [json.loads(r) if isinstance(r, str) else r for r in rows]
        except Exception as e:  # noqa: BLE001
            logger.error(f"PostgreSQL query failed: {e}")
            return []


class _ElasticsearchAdapter(StorageBackendAdapter):
    """Real Elasticsearch adapter.

    Uses the synchronous ``Elasticsearch`` client executed in a worker thread so
    the adapter has no dependency on the async transport (``aiohttp``), which is
    not always installed.
    """

    def __init__(self, client: Any):
        self.backend = StorageBackend.ELASTICSEARCH
        self._client = client

    @staticmethod
    def _index(data_type: DataType) -> str:
        return f"aiops-{data_type.value}".lower()

    async def store(self, request: StorageRequest) -> StorageResult:
        meta = request.metadata or {}
        data_id = meta.get("id") or meta.get("key") or str(uuid.uuid4())
        doc = request.data if isinstance(request.data, dict) else {"value": request.data}
        try:
            await asyncio.to_thread(
                self._client.index, index=self._index(request.data_type), id=data_id, document=doc
            )
            return StorageResult(success=True, backend=self.backend, data_id=data_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Elasticsearch store failed: {e}")
            return StorageResult(success=False, backend=self.backend, error=e)

    async def retrieve(self, data_id: str, data_type: DataType) -> Optional[Any]:
        try:
            res = await asyncio.to_thread(
                self._client.get, index=self._index(data_type), id=data_id
            )
            return res.get("_source")
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Elasticsearch retrieve missed: {e}")
            return None

    async def delete(self, data_id: str, data_type: DataType) -> bool:
        try:
            await asyncio.to_thread(self._client.delete, index=self._index(data_type), id=data_id)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Elasticsearch delete failed: {e}")
            return False

    async def query(self, query: Dict[str, Any], data_type: DataType) -> List[Any]:
        try:
            body = {"query": query.get("query", {"match_all": {}})}
            res = await asyncio.to_thread(
                self._client.search, index=self._index(data_type), body=body
            )
            return [h["_source"] for h in res["hits"]["hits"]]
        except Exception as e:  # noqa: BLE001
            logger.error(f"Elasticsearch query failed: {e}")
            return []


class _QdrantAdapter(StorageBackendAdapter):
    """Real Qdrant vector adapter (requires ``qdrant-client``)."""

    def __init__(self, client: Any):
        self.backend = StorageBackend.QDRANT
        self._client = client
        self._collection = "aiops_l3l4"

    def _ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

    async def store(self, request: StorageRequest) -> StorageResult:
        from qdrant_client.models import PointStruct

        meta = request.metadata or {}
        data_id = meta.get("id") or meta.get("key") or str(uuid.uuid4())
        vector = meta.get("vector")
        if not isinstance(vector, list):
            return StorageResult(
                success=False,
                backend=self.backend,
                error=Exception("Qdrant requires metadata['vector'] (list[float])"),
            )
        try:
            await asyncio.to_thread(self._ensure_collection)
            payload = {"data": request.data, "data_type": request.data_type.value}
            await asyncio.to_thread(
                self._client.upsert,
                collection_name=self._collection,
                points=[PointStruct(id=data_id, vector=vector, payload=payload)],
            )
            return StorageResult(success=True, backend=self.backend, data_id=data_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Qdrant store failed: {e}")
            return StorageResult(success=False, backend=self.backend, error=e)

    async def retrieve(self, data_id: str, data_type: DataType) -> Optional[Any]:
        try:
            pts = await asyncio.to_thread(
                self._client.retrieve, collection_name=self._collection, ids=[data_id]
            )
            if not pts:
                return None
            return pts[0].payload.get("data")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Qdrant retrieve failed: {e}")
            return None

    async def delete(self, data_id: str, data_type: DataType) -> bool:
        try:
            await asyncio.to_thread(
                self._client.delete, collection_name=self._collection, points_selector=[data_id]
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Qdrant delete failed: {e}")
            return False

    async def query(self, query: Dict[str, Any], data_type: DataType) -> List[Any]:
        vector = query.get("vector")
        if not isinstance(vector, list):
            return []
        try:
            hits = await asyncio.to_thread(
                self._client.search,
                collection_name=self._collection,
                query_vector=vector,
                limit=int(query.get("limit", 10)),
            )
            return [h.payload.get("data") for h in hits]
        except Exception as e:  # noqa: BLE001
            logger.error(f"Qdrant query failed: {e}")
            return []


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

        # Caching layer (configured before adapters so the Redis adapter can read TTL)
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl", 300)
        self.cache_max_entries = self.config.get("cache_max_entries", 4096)
        # key=(data_type, data_id) -> (value, expires_at_monotonic)
        self._cache: Dict[Any, Any] = {}

        # Backend adapters
        self.backend_adapters: Dict[StorageBackend, StorageBackendAdapter] = {}
        self._initialize_backend_adapters()

        # Data routing
        self.data_router_enabled = self.config.get("data_router_enabled", True)

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
        """Initialize storage backend adapters (real clients, honest failures)."""
        for backend in StorageBackend:
            try:
                adapter = self._create_backend_adapter(backend)
            except Exception as e:  # noqa: BLE001 - one backend must not break init
                logger.warning(f"Backend adapter init failed for {backend.value}: {e}")
                adapter = None
            if adapter:
                self.backend_adapters[backend] = adapter
                logger.info(f"Initialized backend adapter: {backend.value}")

    def _create_backend_adapter(self, backend: StorageBackend) -> Optional[StorageBackendAdapter]:
        """Create a *real* backend adapter for the given storage type.

        历史问题（已修复）：原实现无条件 ``return None``，导致 ``backend_adapters``
        恒空，store/retrieve/delete/query 对所有后端均返回 "Backend adapter not
        available"/空 —— L3-L4 存储层完全无落地。现按后端类型构造真实客户端适配器
        （VictoriaMetrics/Loki/Tempo 复用 ``core.storage.l4``；Redis 走
        ``redis.asyncio``；PostgreSQL 走 SQLAlchemy JSONB 表；Elasticsearch 走
        ``AsyncElasticsearch``）。后端不可用时返回 ``None``（跳过注册），由上层
        如实报告不可用，绝不伪造成功。
        """
        cfg = self.config.get("backends", {})

        try:
            return self._build_backend_adapter(backend, cfg)
        except ImportError as e:
            logger.warning(f"Backend {backend.value} client unavailable: {e}")
            return None
        except ModuleNotFoundError as e:
            logger.warning(f"Backend {backend.value} driver missing: {e}")
            return None
        except Exception as e:  # noqa: BLE001 - unavailable backend must not abort init
            logger.warning(f"Backend {backend.value} adapter unavailable: {e}")
            return None

    def _build_backend_adapter(
        self, backend: StorageBackend, cfg: Dict[str, Any]
    ) -> Optional[StorageBackendAdapter]:
        """Construct a real adapter for ``backend`` or return None if unsupported."""
        if backend == StorageBackend.VICTORIAMETRICS:
            from core.storage.l4.victoriametrics import VictoriaMetricsStorage

            storage = VictoriaMetricsStorage(cfg.get("victoriametrics", {}))
            storage.initialize()
            return _L4BackendAdapter(backend, storage)

        if backend == StorageBackend.LOKI:
            from core.storage.l4.loki import LokiStorage

            storage = LokiStorage(cfg.get("loki", {}))
            storage.initialize()
            return _L4BackendAdapter(backend, storage)

        if backend == StorageBackend.TEMPO:
            from core.storage.l4.tempo import TempoStorage

            storage = TempoStorage(cfg.get("tempo", {}))
            storage.initialize()
            return _L4BackendAdapter(backend, storage)

        if backend == StorageBackend.REDIS:
            import redis.asyncio as aioredis

            from config import REDIS_PASSWORD, REDIS_URL

            kwargs: Dict[str, Any] = {"decode_responses": True}
            if REDIS_PASSWORD:
                kwargs["password"] = REDIS_PASSWORD
            client = aioredis.from_url(REDIS_URL, **kwargs)
            return _RedisAdapter(client, ttl_seconds=self.cache_ttl)

        if backend == StorageBackend.POSTGRESQL:
            from sqlalchemy import create_engine

            from config import DATABASE_URL

            url = cfg.get("postgresql", {}).get("url", DATABASE_URL)
            engine = create_engine(url, pool_pre_ping=True, future=True)
            return _PostgresAdapter(engine)

        if backend == StorageBackend.ELASTICSEARCH:
            from elasticsearch import Elasticsearch

            from config import ELASTICSEARCH_URL

            client = Elasticsearch(cfg.get("elasticsearch", {}).get("url", ELASTICSEARCH_URL))
            return _ElasticsearchAdapter(client)

        if backend == StorageBackend.QDRANT:
            from core.qdrant_service import get_qdrant_client

            client = get_qdrant_client()
            if client is None:
                logger.warning("Qdrant client unavailable; skipping Qdrant adapter")
                return None
            return _QdrantAdapter(client)

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
        """Retrieve data from the in-process TTL cache.

        历史问题（已修复）：原实现仅 ``logging.info`` 后 ``return None``（空实现），
        缓存命中永远为 0。现为一款真实生效的带 TTL / LRU 淘汰的缓存。
        """
        key = (data_type.value, data_id)
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            self._cache.pop(key, None)
            return None
        return value

    async def _store_in_cache(self, data_id: str, data_type: DataType, data: Any) -> None:
        """Store data in the in-process TTL cache."""
        key = (data_type.value, data_id)
        expires_at = time.monotonic() + self.cache_ttl if self.cache_ttl else None
        self._cache[key] = (data, expires_at)
        # Bound the cache size with simple LRU-style eviction.
        if len(self._cache) > self.cache_max_entries:
            oldest = next(iter(self._cache))
            self._cache.pop(oldest, None)

    async def _remove_from_cache(self, data_id: str, data_type: DataType) -> None:
        """Remove data from the in-process TTL cache."""
        self._cache.pop((data_type.value, data_id), None)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return current cache size and TTL configuration."""
        return {
            "cached_entries": len(self._cache),
            "cache_ttl_seconds": self.cache_ttl,
            "cache_max_entries": self.cache_max_entries,
        }

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
