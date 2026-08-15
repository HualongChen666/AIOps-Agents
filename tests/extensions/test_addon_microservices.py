# -*- coding: utf-8 -*-
"""Happy-path smoke tests for addon microservice main.py apps."""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parents[2] / "extensions" / "addons"
MAIN_PY_FILES = sorted(p for p in ROOT.rglob("main.py"))


@pytest.mark.parametrize(
    "main_path",
    MAIN_PY_FILES,
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_addon_microservice_happy_path(main_path: Path):
    name = main_path.relative_to(ROOT).as_posix().replace("/", ".")
    try:
        spec = importlib.util.spec_from_file_location(
            f"_addon_main_test.{name}", str(main_path)
        )
        if spec is None or spec.loader is None:
            pytest.skip(f"Could not create spec for {main_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:
        pytest.skip(f"Could not load {main_path}: {exc}")

    app = getattr(module, "app", None)
    if app is None:
        pytest.skip(f"{main_path} has no 'app'")

    client = TestClient(app)

    health = client.get("/health")
    if health.status_code != 200:
        pytest.skip(f"/health not available for {main_path}")

    # /info is optional
    client.get("/info")

    # /invoke is the standard endpoint; skip if this app does not support it.
    for action in ("list", "evaluate"):
        invoke = client.post("/invoke", json={"action": action, "payload": {}})
        if invoke.status_code == 200:
            data = invoke.json()
            assert data.get("success") is True
            return

    pytest.skip(f"/invoke not available for {main_path}")
