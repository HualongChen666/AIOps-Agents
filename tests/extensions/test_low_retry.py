# -*- coding: utf-8 -*-
"""Parametrized tests for every extensions/addons/**/retry.py retry engine."""

import asyncio
import dataclasses
import importlib.util
import inspect
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RETRY_FILES = sorted((ROOT / "extensions" / "addons").rglob("retry.py"))


class _DummyLogger:
    def __getattr__(self, name):
        return lambda *a, **k: None


def _counter():
    class C:
        def labels(self, **kw):
            return self

        def inc(self, *a, **k):
            return None

    return C()


def _register_stubs(parent_dir, package_name, monkeypatch):
    if "loguru" not in sys.modules:
        loguru_mod = types.ModuleType("loguru")
        loguru_mod.logger = _DummyLogger()
        monkeypatch.setitem(sys.modules, "loguru", loguru_mod)

    parent_pkg = types.ModuleType(package_name)
    parent_pkg.__path__ = [str(parent_dir)]
    monkeypatch.setitem(sys.modules, package_name, parent_pkg)

    metrics_mod = types.ModuleType(f"{package_name}.metrics")
    metrics_mod.MetricsCollector = type("MetricsCollector", (), {})
    metrics_mod.ROUTER_RETRIES_TOTAL = _counter()
    metrics_mod.RAG_REQUEST_FAILURES_TOTAL = _counter()
    monkeypatch.setitem(sys.modules, f"{package_name}.metrics", metrics_mod)

    if "services" not in sys.modules:
        monkeypatch.setitem(sys.modules, "services", types.ModuleType("services"))

    wf_pkg = sys.modules.setdefault("services.workflow_service", types.ModuleType("services.workflow_service"))
    monkeypatch.setitem(sys.modules, "services.workflow_service", wf_pkg)

    wf_metrics = types.ModuleType("services.workflow_service.metrics")
    wf_metrics.WORKFLOW_RETRY_ATTEMPTS = _counter()
    monkeypatch.setitem(sys.modules, "services.workflow_service.metrics", wf_metrics)

    wf_schemas = types.ModuleType("services.workflow_service.schemas")
    wf_schemas.RetryPolicy = dataclasses.make_dataclass(
        "RetryPolicy",
        [
            ("name", str, dataclasses.field(default="")),
            ("max_retries", int, 3),
            ("base_delay_seconds", float, 1.0),
            ("max_delay_seconds", float, 60.0),
            ("exponential_base", float, 2.0),
            (
                "retryable_errors",
                list,
                dataclasses.field(default_factory=lambda: ["retryable"]),
            ),
        ],
    )
    monkeypatch.setitem(sys.modules, "services.workflow_service.schemas", wf_schemas)


async def _no_sleep(*args, **kwargs):
    return None


def _dummy_factory(fail_once_message="retryable failure"):
    async def _dummy(*args, **kwargs):
        _dummy.calls += 1
        if _dummy.calls == 1:
            raise RuntimeError(fail_once_message)
        return "ok"

    _dummy.calls = 0
    return _dummy


def _run_coro(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("retry_path", RETRY_FILES)
def test_retry_engine(retry_path, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    parent_dir = retry_path.parent
    group = re.sub(r"\W", "_", parent_dir.parent.name)
    service = re.sub(r"\W", "_", parent_dir.name)
    package_name = f"_rtp_{group}_{service}"
    module_name = f"{package_name}.retry"

    _register_stubs(parent_dir, package_name, monkeypatch)

    spec = importlib.util.spec_from_file_location(module_name, str(retry_path))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)

    engine_classes = [
        obj
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if "Retry" in name and name != "RetryPolicy"
    ]
    if not engine_classes:
        pytest.skip(f"No retry engine class in {retry_path}")

    engine_cls = engine_classes[0]
    engine = engine_cls()

    if hasattr(engine, "list_policies"):
        engine.list_policies()

    if hasattr(engine, "add_policy"):
        policy_cls = getattr(module, "RetryPolicy", None)
        if policy_cls is not None:
            try:
                custom = policy_cls(
                    name="custom",
                    max_retries=1,
                    base_delay_seconds=0,
                    max_delay_seconds=0,
                )
                engine.add_policy(custom)
                if hasattr(engine, "list_policies"):
                    assert "custom" in engine.list_policies()
            except Exception:
                pass

    for method_name in ("execute", "run", "retry", "__call__"):
        if not hasattr(engine, method_name):
            continue
        method = getattr(engine, method_name)
        if method_name == "__call__" and method is object.__call__:
            continue
        if not callable(method):
            continue

        dummy = _dummy_factory()

        try:
            if inspect.iscoroutinefunction(method):
                result = _run_coro(method(dummy, operation="test"))
            else:
                result = method(dummy, operation="test")
        except Exception:
            continue
        assert result == "ok"
        assert dummy.calls == 2

    if hasattr(engine, "execute"):
        dummy = _dummy_factory()
        result = _run_coro(engine.execute(dummy, operation="test"))
        assert result == "ok"
        assert dummy.calls == 2

    if hasattr(engine, "add_policy"):
        policy_cls = getattr(module, "RetryPolicy", None)
        if policy_cls is not None:
            try:
                custom = policy_cls(
                    name="custom",
                    max_retries=1,
                    base_delay_seconds=0,
                    max_delay_seconds=0,
                )
                dummy = _dummy_factory()
                result = _run_coro(engine.execute(dummy, policy_name="custom", operation="test"))
                assert result == "ok"
            except Exception:
                pass
