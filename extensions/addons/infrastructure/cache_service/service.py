# -*- coding: utf-8 -*-
"""Cache microservice.

Two layers:
* ``execute_operation`` – thin dispatch to :class:`StorageDriver` (generic tooling).
* A **real** TTL cache API (get/set/delete/clear/preheat, cache-aside / write-through /
  write-behind / refresh-ahead strategies, cache-breakdown mutex protection and
  avalanche protection with jittered TTLs) as expected by ``main_app.py``.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any, Dict, List, Optional

from extensions.addons.engines.storage_driver import StorageDriver

OPERATIONS: List[str] = ["cache_get", "cache_set", "get_stats"]


class _Entry:
    __slots__ = ("value", "expires_at", "tags")

    def __init__(self, value: Any, expires_at: Optional[float], tags: List[str]) -> None:
        self.value = value
        self.expires_at = expires_at
        self.tags = tags


class Service:
    """TTL cache service (thin driver dispatch + real in-process cache)."""

    def __init__(self, dry_run: bool = True, **kwargs: Any) -> None:
        kwargs.pop("metrics", None)
        kwargs.pop("cache", None)
        self.dry_run = dry_run
        self.driver = StorageDriver(dry_run=dry_run, **kwargs)
        self._lock = threading.Lock()
        self._store: Dict[str, _Entry] = {}
        self._key_locks: Dict[str, threading.Lock] = {}
        self._hits = 0
        self._misses = 0
        self._total_requests = 0
        self._operations: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Thin driver dispatch (compatibility)
    # ------------------------------------------------------------------
    def execute_operation(self, name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if params is None:
            params = {}
        if hasattr(params, "model_dump"):
            params = params.model_dump()
        if name not in OPERATIONS:
            raise ValueError(f"Unknown operation: {name}")
        method = getattr(self.driver, name)
        return method(**params)

    # ------------------------------------------------------------------
    # Introspection / stats
    # ------------------------------------------------------------------
    def list_methods(self) -> List[str]:
        return sorted(
            [
                "get",
                "set",
                "delete",
                "clear",
                "preheat",
                "protect_breakdown",
                "protect_avalanche",
                "execute_strategy",
                "get_stats",
                "get_cache_stats",
            ]
        )

    def _touch(self, operation: str) -> None:
        self._total_requests += 1
        self._operations[operation] = self._operations.get(operation, 0) + 1

    def _live_size(self) -> int:
        now = time.monotonic()
        return sum(1 for entry in self._store.values() if entry.expires_at is None or entry.expires_at > now)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "operations": dict(self._operations),
            "index_size": self._live_size(),
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": self._live_size(),
            "total_requests": self._total_requests,
        }

    # ------------------------------------------------------------------
    # Core cache operations (real TTL)
    # ------------------------------------------------------------------
    def _get_entry(self, key: str) -> Optional[_Entry]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at <= time.monotonic():
            self._store.pop(key, None)
            return None
        return entry

    async def get(self, request: Any):
        from .schemas import CacheGetResponse

        self._touch("get")
        with self._lock:
            entry = self._get_entry(request.key)
            if entry is None:
                self._misses += 1
                return CacheGetResponse(key=request.key, value=None, hit=False)
            self._hits += 1
            return CacheGetResponse(key=request.key, value=entry.value, hit=True)

    async def set(self, request: Any) -> Dict[str, Any]:
        self._touch("set")
        expires_at = time.monotonic() + request.ttl if request.ttl else None
        with self._lock:
            self._store[request.key] = _Entry(request.value, expires_at, list(request.tags or []))
        return {"stored": True, "key": request.key, "ttl": request.ttl}

    async def delete(self, request: Any) -> Dict[str, bool]:
        self._touch("delete")
        with self._lock:
            existed = self._store.pop(request.key, None) is not None
        return {"deleted": existed}

    async def clear(self) -> Dict[str, bool]:
        self._touch("clear")
        with self._lock:
            self._store.clear()
        return {"cleared": True}

    async def preheat(self, request: Any):
        from .schemas import CachePreheatResponse

        self._touch("preheat")
        expires_at = time.monotonic() + request.ttl if request.ttl else None
        with self._lock:
            for key, value in (request.data or {}).items():
                self._store[key] = _Entry(value, expires_at, [])
        return CachePreheatResponse(keys_loaded=len(request.data or {}))

    # ------------------------------------------------------------------
    # Protection
    # ------------------------------------------------------------------
    async def protect_breakdown(self, request: Any):
        from .schemas import BreakdownProtectResponse

        self._touch("protect_breakdown")
        with self._lock:
            lock = self._key_locks.setdefault(request.key, threading.Lock())

        acquired = lock.acquire(blocking=False)
        try:
            if acquired:
                # First caller recomputes/stores the value.
                if request.value is not None:
                    expires_at = time.monotonic() + request.ttl if request.ttl else None
                    with self._lock:
                        self._store[request.key] = _Entry(request.value, expires_at, [])
                with self._lock:
                    entry = self._get_entry(request.key)
                return BreakdownProtectResponse(
                    key=request.key, locked=True, value=entry.value if entry else request.value
                )
            # Concurrent caller returns the cached (possibly stale) value.
            with self._lock:
                entry = self._get_entry(request.key)
            return BreakdownProtectResponse(
                key=request.key, locked=False, value=entry.value if entry else None
            )
        finally:
            if acquired:
                lock.release()

    async def protect_avalanche(self, request: Any):
        from .schemas import AvalancheProtectResponse

        self._touch("protect_avalanche")
        jitter = random.randint(0, max(0, request.jitter_seconds))
        ttl = request.base_ttl + jitter
        expires_at = time.monotonic() + ttl if ttl else None
        with self._lock:
            self._store[request.key] = _Entry(request.value, expires_at, [])
        return AvalancheProtectResponse(key=request.key, ttl=ttl, value=request.value)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------
    async def execute_strategy(self, request: Any):
        from .schemas import CacheStrategyResponse

        self._touch("execute_strategy")
        strategy = getattr(request.strategy, "value", request.strategy)
        expires_at = time.monotonic() + request.ttl if request.ttl else None
        backend_written = False

        with self._lock:
            self._store[request.key] = _Entry(request.value, expires_at, [])

        # Real backend interaction for write-through / write-behind / refresh-ahead.
        if strategy in ("write-through", "write-behind", "refresh-ahead"):
            result = self.driver.cache_set(key=request.key, value=request.value, ttl=request.ttl)
            backend_written = isinstance(result, dict) and "error" not in result

        return CacheStrategyResponse(
            strategy=str(strategy),
            key=request.key,
            value=request.value,
            status="applied",
            backend_written=backend_written,
        )

    # ------------------------------------------------------------------
    # Generic RPC
    # ------------------------------------------------------------------
    async def call(self, method: str, **payload: Any) -> Any:
        if method not in self.list_methods():
            raise ValueError(f"Unknown method: {method}")
        request = payload.pop("request", None)
        if request is not None:
            if isinstance(request, dict):
                schema_cls = self._schema_class(method)
                if schema_cls is not None:
                    request = schema_cls(**request)
            return await getattr(self, method)(request)
        return await getattr(self, method)(**payload)

    def _schema_class(self, method: str) -> Optional[Any]:
        mapping = {
            "get": "CacheGetRequest",
            "set": "CacheSetRequest",
            "delete": "CacheGetRequest",
            "preheat": "CachePreheatRequest",
            "protect_breakdown": "BreakdownProtectRequest",
            "protect_avalanche": "AvalancheProtectRequest",
            "execute_strategy": "CacheStrategyRequest",
        }
        attr = mapping.get(method)
        if not attr:
            return None
        try:
            from . import schemas
        except Exception:
            return None
        return getattr(schemas, attr, None)


Service.OPERATIONS = OPERATIONS


CacheService = Service
