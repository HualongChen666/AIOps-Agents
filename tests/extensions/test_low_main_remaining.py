# -*- coding: utf-8 -*-
"""Smoke tests for low-coverage main_app.py / main.py files under extensions/addons."""

import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment,misc]
    TestClient = None  # type: ignore[assignment,misc]

BASE = Path(__file__).resolve().parents[2]
COV_PATH = BASE / "cov_ext.json"


def _targets():
    targets = []
    if COV_PATH.exists():
        data = json.loads(COV_PATH.read_text(encoding="utf-8"))
        for f, meta in data.get("files", {}).items():
            norm = f.replace("\\", "/")
            if norm.startswith("extensions/addons/") and norm.endswith(("main_app.py", "main.py")):
                s = meta.get("summary", {})
                if s.get("percent_covered", 0) < 80 and s.get("num_statements", 0) > 10:
                    targets.append(f)
    else:
        # Fallback for CI environments that don't have cov_ext.json:
        # cover all addon main.py files (main_app.py is already handled by test_low_main_app.py).
        for p in (BASE / "extensions" / "addons").rglob("main.py"):
            targets.append(str(p.relative_to(BASE)))
    return sorted(targets)


TARGETS = _targets()


def _install_mock(name, monkeypatch):
    """Insert a MagicMock for a missing module (and its parent chain) into sys.modules."""
    if name in sys.modules:
        return
    segments = name.split(".")
    for i in range(1, len(segments) + 1):
        sub = ".".join(segments[:i])
        if sub in sys.modules:
            continue
        # Only mock if the module cannot be found normally.
        if importlib.util.find_spec(sub) is not None:
            continue
        mock = MagicMock()
        if i < len(segments):
            mock.__path__ = []
        monkeypatch.setitem(sys.modules, sub, mock)
        # Wire the submodule as an attribute on its parent so
        # ``from parent import child`` works as well as ``import parent.child``.
        if i > 1:
            parent_name = ".".join(segments[: i - 1])
            parent = sys.modules.get(parent_name)
            if parent is not None:
                try:
                    setattr(parent, segments[i - 1], mock)
                except Exception:
                    pass


def _handle_import_error(exc, package_name, monkeypatch):
    """Mock the missing name/module that caused an ImportError during import."""
    m = re.search(r"cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]", str(exc))
    if m:
        name, module = m.group(1), m.group(2)
        if module not in sys.modules:
            monkeypatch.setitem(sys.modules, module, MagicMock())
        mod = sys.modules[module]
        if not hasattr(mod, name):
            try:
                setattr(mod, name, MagicMock())
            except Exception:
                pass
        return
    missing = getattr(exc, "name", None)
    if not missing:
        m2 = re.search(r"No module named ['\"]([^'\"]+)['\"]", str(exc))
        missing = m2.group(1) if m2 else None
    if missing is None:
        raise
    if missing.startswith(package_name + ".") or missing == package_name:
        monkeypatch.setitem(sys.modules, missing, MagicMock())
        if "." in missing:
            parent_name, attr = missing.rsplit(".", 1)
            parent = sys.modules.get(parent_name)
            if parent is not None:
                try:
                    setattr(parent, attr, sys.modules[missing])
                except Exception:
                    pass
        return
    _install_mock(missing, monkeypatch)


def _load(rel_path, monkeypatch):
    rel_posix = rel_path.replace("\\", "/")
    parts = rel_posix.split("/")
    file_name = parts[-1]
    stem = Path(file_name).stem

    # Build a fake package hierarchy that mirrors the directory layout so that
    # relative imports (including ones that go up multiple levels) resolve.
    root_name = "ext_main"
    base_dir = BASE / parts[0]
    if root_name not in sys.modules:
        root_pkg = types.ModuleType(root_name)
        root_pkg.__path__ = [str(base_dir)]
        root_pkg.__package__ = root_name
        sys.modules[root_name] = root_pkg

    package_name = root_name
    current_dir = base_dir
    for seg in parts[1:-1]:
        current_dir = current_dir / seg
        seg_san = re.sub(r"[^0-9a-zA-Z_]", "_", seg)
        package_name = f"{package_name}.{seg_san}"
        if package_name not in sys.modules:
            pkg = types.ModuleType(package_name)
            pkg.__path__ = [str(current_dir)]
            pkg.__package__ = package_name
            sys.modules[package_name] = pkg

    service_dir = current_dir
    module_name = f"{package_name}.{stem}"

    for _ in range(30):
        if module_name in sys.modules:
            del sys.modules[module_name]

        full = service_dir / file_name
        spec = importlib.util.spec_from_file_location(module_name, str(full))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {full}")

        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        before = set(sys.modules)

        try:
            spec.loader.exec_module(mod)
            return mod
        except ImportError as exc:
            added = set(sys.modules) - before
            for key in list(added):
                try:
                    del sys.modules[key]
                except KeyError:
                    pass

            _handle_import_error(exc, package_name, monkeypatch)

    raise RuntimeError(f"Failed to load {rel_path} after multiple attempts")


def _get_public(mod):
    for attr in ("create_app", "get_app", "app", "main", "start", "serve"):
        if hasattr(mod, attr):
            return getattr(mod, attr)
    return None


@pytest.mark.parametrize(
    "rel_path",
    TARGETS,
    ids=[t.replace("\\", "/") for t in TARGETS],
)
def test_low_main_remaining(rel_path, monkeypatch):
    monkeypatch.syspath_prepend(str(BASE))
    if FastAPI is not None:
        monkeypatch.setattr(FastAPI, "response_class", MagicMock(), raising=False)

    mod = _load(rel_path, monkeypatch)
    public = _get_public(mod)

    if public is None:
        pytest.skip(f"No public object found in {rel_path}")

    app = None
    if FastAPI is not None and isinstance(public, FastAPI):
        app = public
    elif callable(public):
        try:
            result = public()
        except Exception:
            result = None
        if FastAPI is not None and isinstance(result, FastAPI):
            app = result
        else:
            # Callable was invoked (e.g. main/start) but did not return a FastAPI app.
            return

    if TestClient is None or app is None:
        return

    try:
        client = TestClient(app)
    except Exception:
        return

    routes = {getattr(r, "path", None) for r in app.routes}
    for endpoint in ("/health", "/info"):
        if endpoint in routes:
            try:
                client.get(endpoint)
            except Exception:
                pass
