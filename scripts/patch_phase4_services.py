#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch phase-4 services with gRPC tests, distributed locks, idempotency and performance benchmarks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path("C:/AIOps_Agent_bak")

# Load the original generator to reuse service metadata and helpers.
spec = importlib.util.spec_from_file_location(
    "gen",
    ROOT / "scripts" / "generate_phase4_monitoring_services.py",
)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


LOCK_PY = '''\
# -*- coding: utf-8 -*-
"""Distributed lock and idempotency helpers.

Provides a Redis-backed distributed lock with an in-process fallback,
and an idempotency manager backed by the service cache.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from loguru import logger

from .cache import CacheManager
from .config import settings


try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore[misc, assignment]


class LockManager:
    """Distributed lock with in-process asyncio.Lock fallback."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._local_locks: Dict[str, asyncio.Lock] = {}
        self._redis: Any = None
        if (
            settings.enable_distributed_lock
            and self._redis_url
            and aioredis is not None
        ):
            try:
                self._redis = aioredis.from_url(
                    self._redis_url, decode_responses=True
                )
                logger.info("Connected to Redis for distributed locking")
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Redis lock unavailable: {exc}")

    def _lock_name(self, resource: str, request_id: Optional[str] = None) -> str:
        return f"{resource}:{request_id}" if request_id else resource

    @asynccontextmanager
    async def acquire(
        self, resource: str, request_id: Optional[str] = None
    ) -> Any:
        """Acquire a lock for *resource* and optional *request_id*."""
        name = self._lock_name(resource, request_id)
        if self._redis:
            token = f"{settings.service_name}:{uuid.uuid4().hex}"
            lock_key = f"{settings.service_name}:lock:{name}"
            acquired = False
            for _ in range(20):
                try:
                    ok = await self._redis.set(
                        lock_key,
                        token,
                        nx=True,
                        ex=settings.lock_ttl_seconds or 30,
                    )
                    if ok:
                        acquired = True
                        break
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"Redis lock acquire failed: {exc}")
                await asyncio.sleep(0.05)
            if not acquired:
                raise RuntimeError(f"Could not acquire lock for {resource}")
            try:
                yield
            finally:
                try:
                    current = await self._redis.get(lock_key)
                    if current == token:
                        await self._redis.delete(lock_key)
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"Redis lock release failed: {exc}")
        else:
            lock = self._local_locks.setdefault(name, asyncio.Lock())
            async with lock:
                yield


class IdempotencyManager:
    """Idempotency manager using the service cache with in-memory fallback."""

    def __init__(self, cache: Optional[CacheManager] = None) -> None:
        self.cache = cache or CacheManager(settings.redis_url)
        self._memory: Dict[str, Any] = {}

    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, default=str, separators=(",", ":")
        )

    def _key(self, request_id: str) -> str:
        return f"{settings.service_name}:idempotency:{request_id}"

    def get_key(self, request: Any, operation: str) -> str:
        """Build an idempotency key for *request* and *operation*."""
        data: Any = {}
        if request is None:
            data = {}
        elif hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            data = {}
        if not isinstance(data, dict):
            data = {}
        explicit = data.get("idempotency_key")
        if not explicit and isinstance(data.get("config"), dict):
            explicit = data["config"].get("idempotency_key")
        if explicit:
            return f"{operation}:{explicit}"
        payload = {
            "op": operation,
            "config": data.get("config", data) if "config" in data else data,
        }
        digest = hashlib.sha256(
            self._serialize(payload).encode()
        ).hexdigest()[:16]
        return f"{operation}:{digest}"

    async def is_processed(self, request_id: str) -> bool:
        cached = await self.cache.get(self._key(request_id))
        if cached is not None:
            return True
        return self._memory.get(request_id) is not None

    async def mark_processed(self, request_id: str, result: Any = None) -> None:
        record = {"processed": True, "timestamp": time.time(), "result": result}
        ttl = settings.idempotency_ttl_seconds or 3600
        await self.cache.set(self._key(request_id), record, ttl=ttl)
        self._memory[request_id] = record
'''


OP_METHOD_TEMPLATE = '''\
    async def <<OP_SNAKE>>(self, request: Any = None) -> Dict[str, Any]:
        """<<OP_TITLE>>."""
        self.metrics.inc_request("<<OP_SNAKE>>")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "<<OP_SNAKE>>")
        async with self.lock_manager.acquire("<<OP_SNAKE>>", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "<<OP_SNAKE>>",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": <<SERVICE_REF>>, "display": "<<DISPLAY>>"},
                    "message": "<<OP_SNAKE>> already processed",
                }
            await self.cache.set(f"<<SERVICE_FSTRING>>:<<OP_SNAKE>>", config)
            self._state["<<OP_SNAKE>>"] = config
            self._operations["<<OP_SNAKE>>"] = self._operations.get("<<OP_SNAKE>>", 0) + 1
            self.metrics.inc_operation("<<OP_SNAKE>>")
            result = {
                "feature": "<<OP_SNAKE>>",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": <<SERVICE_REF>>, "display": "<<DISPLAY>>"},
                "message": "<<OP_SNAKE>> completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result
'''


SERVICE_PY = '''\
# -*- coding: utf-8 -*-
"""Core service logic for the <<DISPLAY>> microservice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .config import settings
from .lock import IdempotencyManager, LockManager
from .metrics import MetricsCollector
from .retry import RetryEngine


BASE_METHODS: List[str] = ["get_state", "backup_state", "restore_state", "get_stats", "list_methods"]
OPERATIONS: List[str] = [
<<OPERATIONS_LIST>>
]


class <<CLASS>>:
    """Domain service for <<DISPLAY>>."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector(settings.service_name)
        self.cache = cache or CacheManager(redis_url or settings.redis_url, self.metrics)
        self.retry_engine = RetryEngine("exponential_fast", self.metrics)
        self.lock_manager = LockManager(redis_url or settings.redis_url)
        self.idempotency = IdempotencyManager(self.cache)
        self._state: Dict[str, Any] = {}
        self._backups: Dict[str, Any] = {}
        self._operations: Dict[str, int] = {}
        self._feature_count = len(OPERATIONS)

    @staticmethod
    def _get_config(request: Any) -> Dict[str, Any]:
        if request is None:
            return {}
        if hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            return {}
        if not isinstance(data, dict):
            return {}
        return data.get("config", data) if "config" in data else data

    async def get_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_state")
        config = self._get_config(request)
        feature = config.get("feature") if isinstance(config, dict) else None
        if feature and feature in self._state:
            return {
                "feature": "get_state",
                "success": True,
                "status": "found",
                "config": {"feature": feature},
                "result": {"state": self._state[feature]},
                "message": f"State for {feature}",
            }
        return {
            "feature": "get_state",
            "success": False,
            "status": "not_found",
            "config": config,
            "result": {},
            "message": "State not found",
        }

    async def backup_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("backup_state")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "backup_state")
        async with self.lock_manager.acquire("backup_state", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "backup_state",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"snapshot": config.get("name", "default") if isinstance(config, dict) else "default"},
                    "message": "backup_state already processed",
                }
            name = config.get("name", "default") if isinstance(config, dict) else "default"
            self._backups[name] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "state": self._state.copy(),
            }
            self.metrics.inc_operation("backup_state")
            result = {
                "feature": "backup_state",
                "success": True,
                "status": "backed_up",
                "config": {"name": name},
                "result": {"snapshot": name},
                "message": f"Backup {name} created",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("restore_state")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "restore_state")
        async with self.lock_manager.acquire("restore_state", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "restore_state",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"snapshot": config.get("name", "default") if isinstance(config, dict) else "default"},
                    "message": "restore_state already processed",
                }
            name = config.get("name", "default") if isinstance(config, dict) else "default"
            data = self._backups.get(name)
            if not data:
                return {
                    "feature": "restore_state",
                    "success": False,
                    "status": "not_found",
                    "config": {"name": name},
                    "result": {},
                    "message": f"Backup {name} not found",
                }
            self._state = data["state"].copy()
            self.metrics.inc_operation("restore_state")
            result = {
                "feature": "restore_state",
                "success": True,
                "status": "restored",
                "config": {"name": name},
                "result": {"snapshot": name},
                "message": f"Backup {name} restored",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def get_stats(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_stats")
        return {
            "feature": "get_stats",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {
                "total_requests": self.metrics.request_count,
                "cache_hits": self.metrics.cache_hits_count,
                "cache_misses": self.metrics.cache_misses_count,
                "operations": self._operations.copy(),
                "index_size": len(self._state),
                "feature_count": self._feature_count,
            },
            "message": "Statistics",
        }

    async def list_methods(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("list_methods")
        return {
            "feature": "list_methods",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {"methods": OPERATIONS + BASE_METHODS},
            "message": "Methods listed",
        }

<<OPERATION_METHODS>>

    async def call(self, method: str, **kwargs: Any) -> Any:
        self.metrics.inc_request("call")
        if method == "list_methods":
            return await self.list_methods(**kwargs)
        if method == "get_stats":
            return await self.get_stats(**kwargs)
        if method == "get_state":
            return await self.get_state(**kwargs)
        if method == "backup_state":
            return await self.backup_state(**kwargs)
        if method == "restore_state":
            return await self.restore_state(**kwargs)
        if method in OPERATIONS:
            fn = getattr(self, method, None)
            if fn is None:
                raise ValueError(f"Unknown method: {method}")
            return await fn(**kwargs)
        raise ValueError(f"Unknown method: {method}")


Service = <<CLASS>>
'''


CONFIG_PY = '''\
# -*- coding: utf-8 -*-
"""Configuration for the <<DISPLAY>> microservice."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class <<CLASS>>Settings(BaseSettings):
    """Settings for the <<DISPLAY>> microservice."""

    service_name: str = "<<NAME_DASH>>-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = <<PORT>>
    redis_url: str = ""
    database_url: str = ""
    qdrant_url: str = ""
    enable_prometheus: bool = True
    max_retries: int = 3
    cache_ttl_seconds: int = 300
    request_timeout: float = 60.0
    enable_distributed_lock: bool = True
    lock_ttl_seconds: int = 30
    idempotency_ttl_seconds: int = 3600

    class Config:  # type: ignore[misc]
        env_prefix = "<<NAME_UPPER>>_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = <<CLASS>>Settings()
'''


SCHEMAS_PY = '''\
# -*- coding: utf-8 -*-
"""Pydantic schemas for the <<DISPLAY>> microservice."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    index_size: int = 0


class StatsResponse(BaseModel):
    """Service statistics response."""

    total_requests: int
    cache_hits: int
    cache_misses: int
    operations: Dict[str, int] = Field(default_factory=dict)
    index_size: int = 0
    feature_count: int = 0


class FeatureRequest(BaseModel):
    """Feature request."""

    config: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class FeatureResponse(BaseModel):
    """Feature response."""

    feature: str
    success: bool
    status: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
'''


TEST_GRPC_PY = '''\
# -*- coding: utf-8 -*-
"""gRPC client/server tests for the <<DISPLAY>> microservice."""

from __future__ import annotations

from unittest import mock

import httpx
import pytest

from services.<<NAME>>_service.grpc.client import <<CLASS>>RPCClient
from services.<<NAME>>_service.grpc.server import <<CLASS>>RPCServer


@pytest.mark.asyncio
async def test_rpc_server_register_and_call():
    server = <<CLASS>>RPCServer()

    async def handler(x):
        return {"ok": True, "x": x}

    server.register("echo", handler)
    assert "echo" in server.list_methods()
    result = await server.call("echo", x=1)
    assert result == {"ok": True, "x": 1}


@pytest.mark.asyncio
async def test_rpc_server_unknown_method():
    server = <<CLASS>>RPCServer()
    with pytest.raises(ValueError):
        await server.call("missing")


@pytest.mark.asyncio
async def test_rpc_client_call():
    client = <<CLASS>>RPCClient(base_url="http://test")
    fake_response = mock.Mock()
    fake_response.raise_for_status = mock.Mock()
    fake_response.json = mock.Mock(return_value={"success": True})
    fake_post = mock.AsyncMock(return_value=fake_response)
    fake_client = mock.AsyncMock()
    fake_client.post = fake_post
    fake_cm = mock.AsyncMock()
    fake_cm.__aenter__ = mock.AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = mock.AsyncMock(return_value=False)
    with mock.patch.object(httpx, "AsyncClient", return_value=fake_cm):
        result = await client.call("list_methods", payload={})
    assert result == {"success": True}
    fake_post.assert_called_once_with("http://test/rpc/list_methods", json={})
'''


TEST_LOCK_PY = '''\
# -*- coding: utf-8 -*-
"""Lock and idempotency tests for the <<DISPLAY>> microservice."""

from __future__ import annotations

import uuid

import pytest

from services.<<NAME>>_service.lock import LockManager
from services.<<NAME>>_service.metrics import MetricsCollector
from services.<<NAME>>_service.service import OPERATIONS, Service


@pytest.mark.asyncio
async def test_idempotency_manager():
    metrics = MetricsCollector(f"<<NAME>>_idemp_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    key = service.idempotency.get_key(
        {"config": {"x": 1}, "idempotency_key": "abc"}, "op1"
    )
    assert key == "op1:abc"
    assert await service.idempotency.is_processed(key) is False
    await service.idempotency.mark_processed(key, {"result": 1})
    assert await service.idempotency.is_processed(key) is True


@pytest.mark.asyncio
async def test_lock_manager_fallback():
    lock = LockManager(redis_url="")
    async with lock.acquire("resource", "req-1"):
        pass


@pytest.mark.asyncio
async def test_service_idempotent_request():
    metrics = MetricsCollector(f"<<NAME>>_idemp_req_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    op = OPERATIONS[0]
    req = {"config": {"test": True}, "idempotency_key": "dup-1"}
    result1 = await getattr(service, op)(req)
    assert result1["success"] is True
    result2 = await getattr(service, op)(req)
    assert result2["success"] is True
    assert result2["status"] == "idempotent"
'''


TEST_PERFORMANCE_PY = '''\
# -*- coding: utf-8 -*-
"""Performance benchmark for the <<DISPLAY>> microservice."""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest

import services.<<NAME>>_service.config as config_module
from services.<<NAME>>_service.metrics import MetricsCollector
from services.<<NAME>>_service.service import OPERATIONS, Service


MIN_OPS_PER_SEC = 8000


@pytest.mark.asyncio
@pytest.mark.performance
async def test_operation_throughput():
    """Benchmark in-memory operation throughput."""
    n = 1000
    op = OPERATIONS[0]
    config_module.settings.redis_url = ""
    metrics = MetricsCollector(f"<<NAME>>_perf_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    start = time.perf_counter()
    await asyncio.gather(*[
        getattr(service, op)({
            "config": {"i": i},
            "idempotency_key": f"perf-{i}",
        })
        for i in range(n)
    ])
    elapsed = time.perf_counter() - start
    ops_per_sec = n / elapsed
    assert ops_per_sec >= MIN_OPS_PER_SEC, (
        f"{op} throughput {ops_per_sec:.0f} ops/s below {MIN_OPS_PER_SEC}"
    )
'''


def build_operation_methods(service: Dict[str, Any]) -> str:
    service_fstring = "{settings.service_name}"
    service_ref = "settings.service_name"
    display = service["display"]
    methods = []
    for op in service["operations"]:
        op_snake = gen.to_snake(op)
        op_title = op.replace("-", " ").replace("_", " ").title()
        method = OP_METHOD_TEMPLATE.replace("<<SERVICE_FSTRING>>", service_fstring)
        method = method.replace("<<SERVICE_REF>>", service_ref)
        method = method.replace("<<OP_SNAKE>>", op_snake)
        method = method.replace("<<OP_TITLE>>", op_title)
        method = method.replace("<<DISPLAY>>", display)
        methods.append(method)
    return "\n\n".join(methods)


def build_info(service: Dict[str, Any]) -> Dict[str, Any]:
    info = gen.build_info(service)
    info["operation_methods"] = build_operation_methods(service)
    return info


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def patch() -> None:
    for service in gen.SERVICES:
        info = build_info(service)
        name = info["name"]
        service_dir = ROOT / "services" / f"{name}_service"
        test_dir = ROOT / "tests" / "services" / f"{name}_service"

        write_file(service_dir / "lock.py", LOCK_PY)
        write_file(service_dir / "config.py", gen.apply_placeholders(CONFIG_PY, info))
        write_file(service_dir / "schemas.py", gen.apply_placeholders(SCHEMAS_PY, info))
        write_file(service_dir / "service.py", gen.apply_placeholders(SERVICE_PY, info))

        write_file(test_dir / "test_grpc.py", gen.apply_placeholders(TEST_GRPC_PY, info))
        write_file(test_dir / "test_lock.py", gen.apply_placeholders(TEST_LOCK_PY, info))
        write_file(test_dir / "test_performance.py", gen.apply_placeholders(TEST_PERFORMANCE_PY, info))

        print(f"Patched {service_dir} and {test_dir}")


if __name__ == "__main__":
    patch()
