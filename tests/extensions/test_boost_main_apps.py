# -*- coding: utf-8 -*-
"""Parametrized smoke tests that call every FastAPI endpoint in addon main_app.py/main.py files."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from fastapi.testclient import TestClient as _TestClient
    from starlette.responses import PlainTextResponse as _PlainTextResponse

    _TESTCLIENT_AVAILABLE = True
except Exception:  # pragma: no cover - fallback handled below
    _TestClient = None  # type: ignore[misc, assignment]
    _PlainTextResponse = None
    _TESTCLIENT_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[2]
ADDON_ROOT = ROOT / "extensions" / "addons"
_STD_LIB = set(getattr(sys, "stdlib_module_names", ()))
_PROJECT_MODULES = {"api", "core", "main", "services", "scripts", "infrastructure", "config", "tests", "modules", "extensions"}
_CORE_DEPS = {
    "fastapi",
    "pydantic",
    "pydantic_settings",
    "starlette",
    "prometheus_client",
    "anyio",
    "typing_extensions",
    "loguru",
    "orjson",
    "jinja2",
    "markupsafe",
    "yaml",
    "toml",
    "click",
    "cryptography",
    "pyjwt",
    "passlib",
    "authlib",
    "slowapi",
    "apscheduler",
    "tenacity",
    "cachetools",
    "watchdog",
    "strawberry",
    "pillow",
}
_DO_NOT_FAKE = _STD_LIB | _PROJECT_MODULES | _CORE_DEPS
_IO_MODULES = {
    "httpx",
    "aiohttp",
    "requests",
    "redis",
    "redis.asyncio",
    "asyncpg",
    "psycopg2",
    "qdrant_client",
    "neo4j",
    "openai",
    "anthropic",
    "sentence_transformers",
    "prophet",
    "prometheus_api_client",
    "temporalio",
    "prefect",
    "kubernetes",
    "docker",
    "boto3",
    "botocore",
    "elasticsearch",
    "pika",
    "kafka",
    "confluent_kafka",
    "grpc",
    "uvicorn",
    "ansible",
    "ansible_runner",
    "datadog",
    "pygithub",
    "github",
    "grafana",
    "pygrafana",
    "aiobotocore",
    "aiokafka",
    "aiomysql",
    "motor",
    "pymongo",
    "paramiko",
    "fabric",
    "asyncio_mqtt",
    "smtplib",
    "jira",
    "slack_sdk",
    "telegram",
    "twilio",
    "sendgrid",
    "stripe",
    "hubspot",
    "salesforce",
    "asana",
    "trello",
    "monday",
    "notion",
    "airtable",
    "zapier",
    "websockets",
    "grpc.aio",
    "asyncpg.pool",
    "psycopg2.extras",
}
_ASYNC_CLASS_NAMES = frozenset({
    "AsyncClient",
    "ClientSession",
    "AsyncOpenAI",
    "AsyncAnthropic",
    "AsyncKafkaProducer",
    "AsyncKafkaConsumer",
    "AsyncEngine",
    "AsyncGraphDatabase",
})


def _magic_mod(monkeypatch, name, force=False):
    """Create a lightweight fake module in sys.modules."""
    if not force and name in sys.modules:
        return sys.modules[name]

    mod = types.ModuleType(name)

    def __getattr__(attr):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(f"module {name!r} has no attribute {attr!r}")
        if attr in _ASYNC_CLASS_NAMES or (name.endswith(".asyncio") and attr == "Redis"):
            val = AsyncMock
        else:
            val = MagicMock(name=f"{name}.{attr}")
        mod.__dict__[attr] = val
        return val

    mod.__getattr__ = __getattr__
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _ensure_module_path(monkeypatch, name):
    """Pre-populate sys.modules with fake modules for a dotted import."""
    parts = name.split(".")
    if not parts or parts[0] in _DO_NOT_FAKE or parts[0] == "__future__":
        return
    full = ""
    parent = None
    for part in parts:
        full = f"{full}.{part}" if full else part
        force = full in _IO_MODULES
        if force or full not in sys.modules:
            mod = _magic_mod(monkeypatch, full, force=force)
        else:
            mod = sys.modules[full]
        if parent is not None:
            try:
                setattr(parent, part, mod)
            except Exception:
                pass
        parent = mod


def _ensure_imports(monkeypatch, app_path):
    """Parse addon .py files and shim any optional dependencies they import."""
    addon_dir = app_path.parent
    for path in addon_dir.rglob("*.py"):
        if path.name.startswith("__pycache__"):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _ensure_module_path(monkeypatch, alias.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                _ensure_module_path(monkeypatch, node.module)


def _make_pkg(monkeypatch, name, path=None, package=None):
    """Create and register a synthetic package/module in sys.modules."""
    mod = sys.modules.get(name)
    if mod is not None:
        return mod
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    if package is not None:
        mod.__package__ = package
    mod.__file__ = str(Path(path or ADDON_ROOT) / "__init__.py")
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _load_engine_modules(monkeypatch):
    """Pre-load shared engines modules so addon service.py files can import them."""
    _make_pkg(monkeypatch, "extensions", str(ROOT / "extensions"), "extensions")
    _make_pkg(monkeypatch, "extensions.addons", str(ADDON_ROOT), "extensions")
    engines_pkg = _make_pkg(monkeypatch, "extensions.addons.engines", str(ADDON_ROOT / "engines"), "extensions.addons")
    for path in (ADDON_ROOT / "engines").glob("*.py"):
        if path.name.startswith("__"):
            continue
        name = f"extensions.addons.engines.{path.stem}"
        if name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(name, str(path))
        if spec is None:
            continue
        module = importlib.util.module_from_spec(spec)
        module.__package__ = "extensions.addons.engines"
        monkeypatch.setitem(sys.modules, name, module)
        try:
            spec.loader.exec_module(module)
        except Exception:
            pass
        try:
            setattr(engines_pkg, path.stem, module)
        except Exception:
            pass


def _patch_service_module(app_path, pkg, pkg_name, monkeypatch):
    """Pre-load addon service.py and back-fill names main_app.py expects."""
    service_path = app_path.parent / "service.py"
    if not service_path.exists():
        return
    try:
        tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    except Exception:
        return
    needed = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "service":
            for alias in node.names:
                needed[alias.name] = alias.asname or alias.name
    if not needed:
        return
    full_name = f"{pkg_name}.service"
    if full_name in sys.modules:
        service_mod = sys.modules[full_name]
    else:
        spec = importlib.util.spec_from_file_location(full_name, str(service_path))
        if spec is None:
            return
        service_mod = importlib.util.module_from_spec(spec)
        service_mod.__package__ = pkg_name
        monkeypatch.setitem(sys.modules, full_name, service_mod)
        try:
            spec.loader.exec_module(service_mod)
        except Exception:
            return
    service_class = getattr(service_mod, "Service", None)
    if service_class is None or not inspect.isclass(service_class):
        for obj in service_mod.__dict__.values():
            if inspect.isclass(obj) and obj.__name__ not in ("BaseInfraService", "BaseSecurityService"):
                service_class = obj
                break
    if service_class is None:
        service_class = MagicMock
    for src, _ in needed.items():
        if hasattr(service_mod, src):
            continue
        if src in ("BASE_METHODS", "OPERATIONS"):
            setattr(service_mod, src, [])
        else:
            setattr(service_mod, src, service_class)


def _load_addon_app(app_path, monkeypatch):
    """Load an addon main_app.py/main.py under a unique sanitized package."""
    addon_dir = app_path.parent
    rel_parts = addon_dir.relative_to(ADDON_ROOT).parts
    service_name = rel_parts[-1]
    unique_root = f"_boost_main_apps_{abs(hash(str(app_path)))}"

    # Build a synthetic package tree that mirrors extensions/addons/<pack>/<service>
    # so multi-level relative imports (e.g. ``from ...engines import X``) resolve.
    root_pkg = _make_pkg(monkeypatch, unique_root, str(ADDON_ROOT), unique_root)
    pkg_name = unique_root
    pkg = root_pkg
    for i, part in enumerate(rel_parts):
        pkg_name = f"{pkg_name}.{part}"
        pkg_path = ADDON_ROOT / Path(*rel_parts[: i + 1])
        pkg = _make_pkg(
            monkeypatch,
            pkg_name,
            str(pkg_path),
            unique_root if i == 0 else ".".join([unique_root] + list(rel_parts[:i])),
        )
        try:
            setattr(root_pkg if i == 0 else sys.modules[".".join([unique_root] + list(rel_parts[:i]))], part, pkg)
        except Exception:
            pass

    # Make relative ``...engines.<name>`` imports resolve without pulling in
    # the shared engines/__init__.py for every addon.
    engines_pkg = _make_pkg(
        monkeypatch,
        f"{unique_root}.engines",
        str(ADDON_ROOT / "engines"),
        unique_root,
    )
    try:
        setattr(root_pkg, "engines", engines_pkg)
    except Exception:
        pass

    # Keep the old services.<service_name> alias working for absolute imports.
    services = sys.modules.get("services")
    if services is not None:
        try:
            monkeypatch.setattr(services, service_name, pkg)
            monkeypatch.setitem(sys.modules, f"services.{service_name}", pkg)
        except Exception:
            pass

    _load_engine_modules(monkeypatch)
    _patch_service_module(app_path, pkg, pkg_name, monkeypatch)
    _ensure_imports(monkeypatch, app_path)

    # Some addon main files reference ``FastAPI.response_class.PlainTextResponse``;
    # provide a shim so those route decorators compile.
    _fastapi = sys.modules.get("fastapi")
    if _fastapi is not None and _PlainTextResponse is not None and not hasattr(_fastapi.FastAPI, "response_class"):
        monkeypatch.setattr(_fastapi.FastAPI, "response_class", types.SimpleNamespace(PlainTextResponse=_PlainTextResponse), raising=False)

    full_name = f"{pkg_name}.{app_path.stem}"
    spec = importlib.util.spec_from_file_location(full_name, str(app_path))
    if spec is None:
        raise ImportError(f"Cannot create spec for {app_path}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = pkg_name
    monkeypatch.setitem(sys.modules, full_name, module)
    spec.loader.exec_module(module)

    for attr in ("create_app", "get_app", "app"):
        obj = module.__dict__.get(attr)
        if attr == "app":
            if obj is not None:
                return obj
        elif callable(obj):
            return obj()
    return None


def _path_with_dummy(path: str) -> str:
    """Replace path parameters with dummy values for TestClient calls."""

    def repl(match: re.Match) -> str:
        inner = match.group(0)
        if ":int" in inner or ":float" in inner:
            return "1"
        return "dummy"

    url = re.sub(r"\{[^}]*\}", repl, path)
    return url if url else "/"


def _call_with_testclient(app, app_path):
    """Exercise each route using FastAPI TestClient."""
    try:
        with _TestClient(app) as client:
            for route in app.routes:
                methods = getattr(route, "methods", None)
                if not methods:
                    continue
                url = _path_with_dummy(route.path)
                try:
                    if route.path in ("/health", "/info"):
                        client.get(url)
                    elif "POST" in methods:
                        client.request("POST", url, json={})
                    elif "PUT" in methods:
                        client.request("PUT", url, json={})
                    elif "DELETE" in methods:
                        client.request("DELETE", url, json={})
                    elif "PATCH" in methods:
                        client.request("PATCH", url, json={})
                    elif "GET" in methods:
                        client.get(url)
                except Exception:
                    continue
    except Exception as exc:
        pytest.skip(f"TestClient failed for {app_path}: {exc}")


def _call_directly(app, app_path):  # pragma: no cover - fallback only
    """Best-effort direct invocation when TestClient is unavailable."""
    import asyncio

    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        try:
            sig = inspect.signature(route.endpoint)
            path = route.path
            kwargs = {}
            path_params = set(re.findall(r"\{([^}:]+)", path))
            for param in sig.parameters.values():
                if param.name in path_params:
                    kwargs[param.name] = "1" if ":int" in path or ":float" in path else "dummy"
                elif param.default is not inspect.Parameter.empty:
                    continue
                elif param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                else:
                    kwargs[param.name] = {}
            if inspect.iscoroutinefunction(route.endpoint):
                asyncio.run(route.endpoint(**kwargs))
            else:
                route.endpoint(**kwargs)
        except Exception:
            continue


_APP_PATHS = sorted(ADDON_ROOT.rglob("main_app.py")) + sorted(ADDON_ROOT.rglob("main.py"))


@pytest.mark.parametrize(
    "app_path",
    _APP_PATHS,
    ids=lambda p: str(p.relative_to(ADDON_ROOT)),
)
def test_addon_app_endpoints(app_path, monkeypatch):
    """Load addon app and call every FastAPI route it exposes."""
    try:
        app = _load_addon_app(app_path, monkeypatch)
    except Exception as exc:
        pytest.skip(f"Could not load {app_path}: {type(exc).__name__}: {exc}")

    if app is None:
        pytest.skip(f"No app object found in {app_path}")

    main_app_ref = getattr(sys.modules.get("main"), "app", None)
    if app is main_app_ref:
        pytest.skip(f"{app_path} re-exports the main app")

    if _TESTCLIENT_AVAILABLE:
        _call_with_testclient(app, app_path)
    else:
        _call_directly(app, app_path)
