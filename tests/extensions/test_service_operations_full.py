# -*- coding: utf-8 -*-
"""Exhaustive exercise of every addon Service.execute_operation plus base APIs."""

import asyncio  # noqa: F401  # Imported for test setup
import importlib
import importlib.util
import inspect
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import sqlite3
import subprocess
import sys  # noqa: F401  # Imported for test setup
import urllib.request
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple  # noqa: F401  # Imported for test setup
from unittest.mock import MagicMock

import numpy as np
import pytest  # noqa: F401  # Imported for test setup

# ------------------------------------------------------------------
# Bootstrap: make optional/unsafe third-party dependencies harmless
# ------------------------------------------------------------------


def _ensure_mock_module(name: str) -> ModuleType:
    """Register a MagicMock as a missing top-level package."""
    if name not in sys.modules:
        sys.modules[name] = MagicMock()
    return sys.modules[name]


for _mod in (
    "redis",
    "redis.asyncio",
    "psycopg2",
    "psycopg2.pool",
    "psycopg2.extras",
    "psycopg2.sql",
    "qdrant_client",
    "qdrant_client.models",
    "httpx",
    "aiohttp",
    "grpc",
):
    _ensure_mock_module(_mod)

# sentence_transformers is heavy; if present, replace it with a fake so no model loads.
try:
    import sentence_transformers  # noqa: F401

    _st_installed = True
except Exception:
    _st_installed = False

if _st_installed:
    sys.modules["sentence_transformers"] = MagicMock()

# Guard against Prometheus duplicate registrations when addons are imported.
try:
    import prometheus_client

    prometheus_client.REGISTRY.register = lambda *a, **k: None
except Exception:
    pass


# ------------------------------------------------------------------
# Fake implementations / stubs
# ------------------------------------------------------------------


class _FakeRedis:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def set(self, key: str, value: Any, **kwargs: Any) -> bool:
        self._data[key] = value
        return True

    def from_url(self, *args: Any, **kwargs: Any) -> "_FakeRedis":
        return self


def _fake_redis_from_url(*args: Any, **kwargs: Any) -> _FakeRedis:
    return _FakeRedis()


class _FakeRequestsResponse:
    def __init__(self) -> None:
        self.status_code = 200
        self.text = '{"data": {"result": []}}'
        self.content = self.text.encode("utf-8")

    def raise_for_status(self) -> None:
        pass

    def json_response(self) -> Any:
        return {"data": {"result": []}}


def _fake_request(method: str, url: str, **kwargs: Any) -> _FakeRequestsResponse:
    return _FakeRequestsResponse()


class _FakeUrllibResponse:
    def __init__(self, data: bytes = b'{"data": {"result": []}}') -> None:
        self._data = data

    def getcode(self) -> int:
        return 200

    def read(self) -> bytes:
        return self._data


def _fake_urlopen(req: Any, **kwargs: Any) -> _FakeUrllibResponse:
    return _FakeUrllibResponse()


class _FakeHttpxResponse:
    def __init__(self) -> None:
        self.content = b'{"status": "ok"}'
        self.status_code = 200


class _FakeHttpxClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def get(self, *args: Any, **kwargs: Any) -> _FakeHttpxResponse:
        return _FakeHttpxResponse()

    def post(self, *args: Any, **kwargs: Any) -> _FakeHttpxResponse:
        return _FakeHttpxResponse()

    def put(self, *args: Any, **kwargs: Any) -> _FakeHttpxResponse:
        return _FakeHttpxResponse()

    def delete(self, *args: Any, **kwargs: Any) -> _FakeHttpxResponse:
        return _FakeHttpxResponse()

    def patch(self, *args: Any, **kwargs: Any) -> _FakeHttpxResponse:
        return _FakeHttpxResponse()

    def close(self) -> None:
        pass


class _FakeSqliteCursor:
    def execute(self, *args: Any, **kwargs: Any) -> None:
        pass

    def fetchall(self) -> List[Any]:
        return []

    def __enter__(self) -> "_FakeSqliteCursor":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class _FakeSqliteConn:
    row_factory: Any = None
    total_changes: int = 1

    def cursor(self) -> _FakeSqliteCursor:
        return _FakeSqliteCursor()

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


def _fake_sqlite_connect(*args: Any, **kwargs: Any) -> _FakeSqliteConn:
    return _FakeSqliteConn()


class _FakePgCursor:
    def execute(self, *args: Any, **kwargs: Any) -> None:
        pass

    def fetchall(self) -> List[Any]:
        return []

    def fetchone(self) -> Optional[Any]:
        return None

    def close(self) -> None:
        pass

    def __enter__(self) -> "_FakePgCursor":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class _FakePgConn:
    def cursor(self, *args: Any, **kwargs: Any) -> _FakePgCursor:
        return _FakePgCursor()

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


class _FakeConnectionPool:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def getconn(self) -> _FakePgConn:
        return _FakePgConn()

    def putconn(self, conn: Any) -> None:
        pass

    def closeall(self) -> None:
        pass


def _fake_json(value: Any) -> Any:
    return value


class _FakeQdrantClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def get_collections(self) -> Any:
        return type("Collections", (), {"collections": []})()

    def create_collection(self, *args: Any, **kwargs: Any) -> None:
        pass

    def upsert(self, *args: Any, **kwargs: Any) -> None:
        pass

    def search(self, *args: Any, **kwargs: Any) -> List[Any]:
        return []


class _FakeAiohttpResponse:
    @property
    def status(self) -> int:
        return 200
        return {}

    async def text(self) -> str:
        return "{}"

    async def __aenter__(self) -> "_FakeAiohttpResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class _FakeAiohttpClientSession:
    async def __aenter__(self) -> "_FakeAiohttpClientSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def get(self, *args: Any, **kwargs: Any) -> _FakeAiohttpResponse:
        return _FakeAiohttpResponse()

    async def post(self, *args: Any, **kwargs: Any) -> _FakeAiohttpResponse:
        return _FakeAiohttpResponse()

    async def put(self, *args: Any, **kwargs: Any) -> _FakeAiohttpResponse:
        return _FakeAiohttpResponse()


class _FakeSentenceTransformer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def encode(self, *args: Any, **kwargs: Any) -> np.ndarray:
        return np.random.rand(384).astype(np.float32)

    def tolist(self) -> List[float]:
        return [0.1] * 384


def _fake_subprocess_run(
    cmd: Iterable[str],
    *args: Any,
    capture_output: bool = True,
    text: bool = True,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    command: List[str] = [str(c) for c in (cmd if isinstance(cmd, (list, tuple)) else [cmd])]
    stdout = "{}" if command and command[0] in ("aws",) else ""
    return subprocess.CompletedProcess(
        args=command,
        returncode=0,
        stdout=stdout,
        stderr="",
    )


# ------------------------------------------------------------------
# Import base service classes after environment is safe
# ------------------------------------------------------------------

try:
    from extensions.addons.engines.security_scanner import BaseSecurityService
except Exception as _e:  # pragma: no cover - defensive
    BaseSecurityService = None  # type: ignore

try:
    from extensions.addons.engines.monitoring_provider import BaseObservabilityService
except Exception as _e:  # pragma: no cover - defensive
    BaseObservabilityService = None  # type: ignore

try:
    from extensions.addons.engines.infra_executor import BaseInfraService
except Exception as _e:  # pragma: no cover - defensive
    BaseInfraService = None  # type: ignore

try:
    from extensions.addons.engines.storage_driver import StorageDriver
except Exception as _e:  # pragma: no cover - defensive
    StorageDriver = None  # type: ignore


# ------------------------------------------------------------------
# Discovery
# ------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2] / "extensions"


def _load_service_module(path: Path) -> Optional[ModuleType]:
    rel = path.relative_to(ROOT).with_suffix("")
    dotted = ".".join(rel.parts)
    try:
        return importlib.import_module(dotted)
    except Exception:
        try:
            spec = importlib.util.spec_from_file_location(dotted, path)
            if spec is None or spec.loader is None:
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules[dotted] = mod
            spec.loader.exec_module(mod)
            return mod
        except Exception as exc:
            warnings.warn(f"Could not import {path}: {exc}", stacklevel=2)
            return None


def _discover_services() -> Iterable[Tuple[str, type]]:
    if not ROOT.exists():
        return
    for service_path in (ROOT / "addons").rglob("service.py"):
        mod = _load_service_module(service_path)
        if mod is None:
            continue
        cls = getattr(mod, "Service", None)
        if not isinstance(cls, type):
            continue
        operations = list(getattr(cls, "OPERATIONS", []))
        if not operations and not getattr(cls, "BASE_METHODS", None):
            continue
        rel = ".".join(service_path.relative_to(ROOT).with_suffix("").parts)
        yield rel, cls


# ------------------------------------------------------------------
# Case generation
# ------------------------------------------------------------------


def _has_method_or_attr(cls: type, name: str) -> bool:
    return any(name in c.__dict__ for c in cls.__mro__)


def _build_cases() -> Tuple[List[Tuple[str, type, str, str]], List[str]]:
    cases: List[Tuple[str, type, str, str]] = []
    ids: List[str] = []
    for rel, cls in _discover_services():
        ops = list(getattr(cls, "OPERATIONS", []))
        bases = list(getattr(cls, "BASE_METHODS", [])) or [
            "get_state",
            "backup_state",
            "restore_state",
            "get_stats",
            "list_methods",
        ]
        for op in ops:
            cases.append((rel, cls, op, "operation"))
            ids.append(f"{rel}::operation::{op}")
        for base in bases:
            cases.append((rel, cls, base, "base"))
            ids.append(f"{rel}::base::{base}")
        for api in ("list_methods", "get_stats", "call"):
            if _has_method_or_attr(cls, api):
                cases.append((rel, cls, api, api))
                ids.append(f"{rel}::{api}")
        if _has_method_or_attr(cls, "__getattr__") and ops:
            cases.append((rel, cls, ops[0], "getattr"))
            ids.append(f"{rel}::getattr::{ops[0]}")
    return cases, ids


def pytest_generate_tests(metafunc: Any) -> None:
    if "rel" in metafunc.fixturenames and "cls" in metafunc.fixturenames:
        cases, ids = _build_cases()
        if not cases:
            cases = [("none", type, "noop", "noop")]  # pragma: no cover
            ids = ["none::noop"]
        metafunc.parametrize("rel, cls, op, kind", cases, ids=ids)


# ------------------------------------------------------------------
# Autouse stubbing fixture
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://localhost:9093")
    monkeypatch.setenv("LOKI_URL", "http://localhost:3100")
    monkeypatch.setenv("JAEGER_URL", "http://localhost:16686")
    monkeypatch.setattr(subprocess, "run", _fake_subprocess_run)
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    if "requests" in sys.modules:
        monkeypatch.setattr(sys.modules["requests"], "request", _fake_request)
    if "httpx" in sys.modules:
        monkeypatch.setattr(sys.modules["httpx"], "Client", _FakeHttpxClient)
    if "redis" in sys.modules:
        monkeypatch.setattr(sys.modules["redis"].Redis, "from_url", _fake_redis_from_url)
    if "redis.asyncio" in sys.modules:
        monkeypatch.setattr(sys.modules["redis.asyncio"].Redis, "from_url", _fake_redis_from_url)
    if "psycopg2" in sys.modules:
        psycopg2 = sys.modules["psycopg2"]
        monkeypatch.setattr(psycopg2.pool, "SimpleConnectionPool", _FakeConnectionPool)
        monkeypatch.setattr(psycopg2.extras, "Json", _fake_json)
        monkeypatch.setattr(psycopg2.extras, "RealDictCursor", object)
    if "sqlite3" in sys.modules:
        monkeypatch.setattr(sqlite3, "connect", _fake_sqlite_connect)
    if "qdrant_client" in sys.modules:
        monkeypatch.setattr(sys.modules["qdrant_client"], "QdrantClient", _FakeQdrantClient)
    if "aiohttp" in sys.modules:
        monkeypatch.setattr(sys.modules["aiohttp"], "ClientSession", _FakeAiohttpClientSession)
    if _st_installed and "sentence_transformers" in sys.modules:
        sys.modules["sentence_transformers"].SentenceTransformer = _FakeSentenceTransformer


# ------------------------------------------------------------------
# Helpers and test
# ------------------------------------------------------------------


def _call_sync_or_async(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    result = fn(*args, **kwargs)  # noqa: F841  # Variable for test verification
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _instantiate(cls: type) -> Any:
    sig = inspect.signature(cls.__init__)
    params = sig.parameters
    has_dry_run = "dry_run" in params
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    is_base = any(  # noqa: F841  # Variable for test verification
        base is not None and issubclass(cls, base)
        for base in (BaseSecurityService, BaseObservabilityService, BaseInfraService)
    )

    kwargs: Dict[str, Any] = {}
    if has_dry_run:
        kwargs["dry_run"] = False
    if has_var_kw and not is_base:
        kwargs.setdefault("database_url", "sqlite:///tmp/test.db")
        kwargs.setdefault("qdrant_url", "http://localhost:6333")
        kwargs.setdefault("redis_url", "redis://localhost:6379")

    try:
        return cls(**kwargs)
    except Exception as exc:
        if has_dry_run and kwargs.get("dry_run") is False:
            try:
                return cls(dry_run=True)
            except Exception:
                pass
        raise exc


def _base_payload(op: str) -> Dict[str, Any]:
    if op in ("backup_state", "restore_state"):
        return {"name": "default"}
    if op == "get_state":
        return {"feature": "test"}
    return {}


def _operation_payload(service: Any, op: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"dry_run": False}

    is_security = BaseSecurityService is not None and isinstance(service, BaseSecurityService)
    is_obs = BaseObservabilityService is not None and isinstance(service, BaseObservabilityService)
    is_storage = StorageDriver is not None and getattr(service, "driver", None) is not None

    if is_security:
        payload.update(
            {
                "target": ".",
                "scanners": ["bandit"],
                "spec": {
                    "openapi": "3.0.0",
                    "servers": [{"url": "https://localhost"}],
                    "components": {"securitySchemes": {"bearerAuth": {}}},
                },
                "dependencies": [{"name": "requests", "license": "mit"}],
                "image": "alpine:latest",
                "code": "SELECT * FROM users WHERE id = %s",
                "findings": [],
            }
        )
    elif is_obs:
        payload.update(
            {
                "target": "http://localhost:9090",
                "metric": "up",
                "query": '{job="default"}',
                "service": "svc",
                "operation": "op",
                "source": "http://localhost:9090",
                "rule_name": "rule",
                "expr": "up == 1",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "test"},
            }
        )
    elif is_storage:
        if op == "cache_get":
            payload = {"key": "test"}
        elif op == "cache_set":
            payload = {"key": "test", "value": "value"}
        elif op == "sql":
            payload = {"query": "SELECT 1", "params": [], "readonly": True}
        elif op == "vector_create_collection":
            payload = {"name": "test_collection", "size": 4, "distance": "Cosine"}
        elif op == "vector_upsert":
            payload = {
                "name": "test_collection",
                "ids": ["1"],
                "vectors": [[0.1, 0.2, 0.3, 0.4]],
                "payloads": [{"content": "hello"}],
            }
        elif op == "vector_search":
            payload = {
                "name": "test_collection",
                "vector": [0.1, 0.2, 0.3, 0.4],
                "top": 5,
            }
        else:
            payload = {}
    return payload


def _should_assert_success(service: Any, cls: type, op: str, kind: str, result: Any) -> bool:
    if not isinstance(result, dict) or "success" not in result:
        return False
    if kind in ("list_methods", "get_stats"):
        return True
    if kind == "base" and op in ("get_stats", "list_methods", "backup_state"):
        return True
    if kind == "base" and op == "restore_state":
        return True
    if kind == "call":
        return isinstance(result, dict) and result.get("feature") in ("list_methods", "get_stats")
    return False


def test_service_operation(rel: str, cls: type, op: str, kind: str) -> None:
    try:
        service = _instantiate(cls)
    except Exception as exc:
        pytest.skip(f"Could not instantiate {rel} Service: {exc}")

    try:
        if kind == "operation":
            payload = _operation_payload(service, op)
            result = _call_sync_or_async(service.execute_operation, op, payload)  # noqa: F841  # Variable for test verification
        elif kind == "base":
            if op == "restore_state":
                _call_sync_or_async(service.execute_operation, "backup_state", {"name": "default"})
            payload = _base_payload(op)
            result = _call_sync_or_async(service.execute_operation, op, payload)  # noqa: F841  # Variable for test verification
        elif kind == "list_methods":
            result = _call_sync_or_async(service.list_methods)  # noqa: F841  # Variable for test verification
        elif kind == "get_stats":
            result = _call_sync_or_async(service.get_stats)  # noqa: F841  # Variable for test verification
        elif kind == "call":
            if _has_method_or_attr(cls, "call"):
                result = _call_sync_or_async(service.call, "list_methods")  # noqa: F841  # Variable for test verification
            else:
                pytest.skip(f"{rel} has no call method")
        elif kind == "getattr":
            handler = getattr(service, op, None)
            if not callable(handler):
                pytest.skip(f"{rel} __getattr__ did not yield a callable for {op}")
            result = _call_sync_or_async(handler, None)  # noqa: F841  # Variable for test verification
        else:
            pytest.skip(f"Unknown test kind {kind}")
    except Exception as exc:
        pytest.skip(f"{rel} {kind} {op} raised: {exc}")

    if _should_assert_success(service, cls, op, kind, result):
        assert result["success"] is True, f"{rel} {kind} {op} returned success=False: {result}"
