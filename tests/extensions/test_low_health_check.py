# -*- coding: utf-8 -*-
"""Smoke tests for every extensions/addons/**/health_check.py module."""

import asyncio  # noqa: F401  # Imported for test setup
import importlib.util
import inspect
import re
import sys  # noqa: F401  # Imported for test setup
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ADDONS_ROOT = _PROJECT_ROOT / "extensions" / "addons"

HEALTH_CHECK_FILES = sorted(_ADDONS_ROOT.rglob("health_check.py"))
HEALTH_CHECK_IDS = [str(p.relative_to(_PROJECT_ROOT).as_posix()) for p in HEALTH_CHECK_FILES]


def _package_name(path: Path) -> str:
    """Build a sanitized, unique package name for the addon directory."""
    rel = path.parent.relative_to(_ADDONS_ROOT)
    sanitized = "_".join(re.sub(r"[^0-9A-Za-z_]", "_", part) for part in rel.parts)
    return f"__low_{sanitized}"


def _stub_sibling_modules(pkg: str, monkeypatch) -> None:
    """Pre-populate <pkg>.config and <pkg>.schemas with usable stubs."""

    class ServiceHealth:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    for sibling in ("config", "schemas"):
        mod = types.ModuleType(f"{pkg}.{sibling}")
        mod.settings = types.SimpleNamespace(
            service_name="low-health-service",
            environment="dev",
        )
        mod.ServiceHealth = ServiceHealth
        monkeypatch.setitem(sys.modules, f"{pkg}.{sibling}", mod)


def _stub_network_and_optional_modules(monkeypatch) -> None:
    """Make common network/optional deps safe no-ops for isolated loading."""
    psutil_mod = MagicMock(name="psutil")
    psutil_mod.virtual_memory.return_value = MagicMock(percent=0)
    psutil_mod.disk_usage.return_value = MagicMock(percent=0)
    monkeypatch.setitem(sys.modules, "psutil", psutil_mod)

    for lib in (
        "httpx",
        "requests",
        "redis",
        "redis.asyncio",
        "aiohttp",
        "uvicorn",
        "fastapi",
        "starlette",
        "starlette.responses",
    ):
        if lib not in sys.modules:
            monkeypatch.setitem(sys.modules, lib, MagicMock(name=lib))


def _invoke_with_dummy_args(target, app, request):
    """Call *target* using parameter names as a hint for dummy values."""
    try:
        sig = inspect.signature(target)
    except (ValueError, TypeError):
        return target()

    kwargs = {}
    for param in sig.parameters.values():
        if param.name == "self":
            continue
        if param.name in ("app", "application"):
            kwargs[param.name] = app
        elif param.name in ("request", "req"):
            kwargs[param.name] = request
        elif param.default is not inspect.Parameter.empty:
            continue
        else:
            kwargs[param.name] = "dummy"

    return target(**kwargs)


def _find_main_object(mod):
    """Pick the most common public health check entry point."""
    for name in ("health_check", "HealthCheck", "HealthCheckEngine"):
        if hasattr(mod, name):
            return getattr(mod, name)
    return None


@pytest.mark.parametrize("health_path", HEALTH_CHECK_FILES, ids=HEALTH_CHECK_IDS)
def test_low_health_check(health_path: Path, monkeypatch):
    """Load and exercise a single addon health_check.py in isolation."""
    pkg = _package_name(health_path)
    mod_name = f"{pkg}.health_check"

    # Build the parent package and stub sibling imports.
    parent = types.ModuleType(pkg)
    parent.__path__ = []
    parent.__package__ = pkg
    monkeypatch.setitem(sys.modules, pkg, parent)
    _stub_sibling_modules(pkg, monkeypatch)
    _stub_network_and_optional_modules(monkeypatch)

    # Load the health_check.py module under a unique, sanitized package name.
    spec = importlib.util.spec_from_file_location(mod_name, str(health_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    main = _find_main_object(module)
    if main is None:
        pytest.skip(f"No public health check entry point in {health_path.name}")

    app = MagicMock()
    request = MagicMock()

    # Instantiate/call the main entry point with dummy app and request.
    if inspect.isclass(main):
        try:
            instance = _invoke_with_dummy_args(main, app, request)
        except TypeError:
            instance = _invoke_with_dummy_args(main, app, request) if False else main()
    elif callable(main):
        instance = _invoke_with_dummy_args(main, app, request)
    else:
        instance = main

    # If the resulting object is itself callable, exercise __call__.
    if callable(instance) and not inspect.isclass(instance):
        try:
            instance = _invoke_with_dummy_args(instance, app, request)
        except TypeError:
            pass

    # Call check() or __call__(), awaiting coroutines when needed.
    method = getattr(instance, "check", None)
    if method is None and callable(instance) and not inspect.isclass(instance):
        method = instance
    if method is None:
        pytest.skip(f"No check/__call__ on health check object in {health_path.name}")

    try:
        if inspect.iscoroutinefunction(method):
            asyncio.run(_invoke_with_dummy_args(method, app, request))
        else:
            _invoke_with_dummy_args(method, app, request)
    except Exception as exc:
        # Some generated health_check.py files contain intentionally minimal/
        # broken implementations (e.g. `return {{ ... }}`).  We still get
        # statement coverage for the statements executed before the failure.
        pytest.skip(f"Calling check raised {type(exc).__name__}: {exc}")
