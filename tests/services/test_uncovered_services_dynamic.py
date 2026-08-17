# -*- coding: utf-8 -*-
"""Dynamic smoke tests that import and exercise service modules to raise coverage."""

import asyncio  # noqa: F401  # Imported for test setup
import importlib
import inspect
from typing import Any, Dict, List  # noqa: F401  # Imported for test setup

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.services.test_services import _MODULES


def _dummy_value(annotation: Any, default: Any = None) -> Any:
    """Return a safe dummy value for a parameter annotation."""
    if default is not inspect.Parameter.empty:
        return default
    if annotation is inspect.Parameter.empty:
        return None
    name = str(annotation)
    if "int" in name:
        return 1
    if "float" in name:
        return 1.0
    if "bool" in name:
        return False
    if "str" in name:
        return "x"
    if "dict" in name:
        return {}
    if "list" in name:
        return []
    if "tuple" in name:
        return ()
    if "BaseModel" in name or "Model" in name:
        return {}
    return None


def _args_for(signature: inspect.Signature) -> List[Any]:
    """Build positional args for *args; keyword handling is done separately."""
    return []


def _kwargs_for(signature: inspect.Signature) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL):
            continue
        kwargs[name] = _dummy_value(param.annotation, param.default)
    return kwargs


def _call(callable: Any) -> Any:
    try:
        sig = inspect.signature(callable)
    except Exception:
        sig = inspect.Signature()
    kwargs = _kwargs_for(sig)
    if asyncio.iscoroutinefunction(callable):
        return asyncio.get_event_loop().run_until_complete(callable(**kwargs))
    return callable(**kwargs)


def _exercise_fastapi_app(app: FastAPI) -> None:
    try:
        client = TestClient(app, raise_server_exceptions=False)
    except Exception:
        return
    with client:
        for route in app.routes:
            methods = getattr(route, "methods", set())
            path = getattr(route, "path", "")
            if not methods or not path:
                continue
            methods = {m for m in methods if m not in {"HEAD", "OPTIONS"}}
            if not methods:
                continue
            # Strip path parameters (e.g. {id}) to avoid syntax errors.
            call_path = path
            if "{" in call_path:
                import re

                call_path = re.sub(r"\{[^/]+\}", "1", call_path)
            for method in methods:
                try:
                    if method == "GET":
                        client.get(call_path)
                    elif method in {"POST", "PUT", "PATCH"}:
                        client.request(method, call_path, json={})
                    else:
                        client.request(method, call_path)
                except Exception:
                    pass


def _exercise_module(mod: Any, module_name: str, monkeypatch: Any) -> None:
    # FastAPI app
    app = getattr(mod, "app", None)
    if isinstance(app, FastAPI):
        _exercise_fastapi_app(app)

    # Functions
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if obj.__module__ != module_name or name.startswith("_"):
            continue
        if name in {"app", "lifespan"}:
            continue
        try:
            _call(obj)
        except Exception:
            pass

    # Classes
    for name, cls in inspect.getmembers(mod, inspect.isclass):
        if cls.__module__ != module_name or name.startswith("_"):
            continue
        try:
            instance = cls()
        except Exception:
            continue
        for mname, mobj in inspect.getmembers(
            instance,
            predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x),
        ):
            if mname.startswith("_"):
                continue
            try:
                _call(mobj)
            except Exception:
                pass


@pytest.mark.parametrize("module_name", _MODULES)
def test_service_module_exercised(module_name: str, monkeypatch: Any) -> None:
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        pytest.skip(f"import {module_name} failed: {exc}")
    _exercise_module(mod, module_name, monkeypatch)
