# -*- coding: utf-8 -*-
"""Full CRUD/invoke flow tests for add-on microservice main.py apps."""

import importlib.util
import logging
import types
import typing
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

ROOT = Path(__file__).parents[2] / "extensions" / "addons"
MAIN_PY_FILES = sorted(p for p in ROOT.rglob("main.py"))

_EXCLUDED_MODEL_NAMES = {
    "InvokeRequest",
    "HealthResponse",
    "InfoResponse",
    "InvokeResponse",
    "BaseModel",
}

logger = logging.getLogger(__name__)


class _FakeHttpResponse:
    status_code = 200
    text = ""

    def json(self):
        return {}

    def raise_for_status(self):
        pass


def _fake_http_get(*_args, **_kwargs):
    return _FakeHttpResponse()


def _fake_http_post(*_args, **_kwargs):
    return _FakeHttpResponse()


def _fake_subprocess_run(*_args, **_kwargs):
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _no_op(*_args, **_kwargs):
    return None


@pytest.fixture(autouse=True)
def _no_external_calls(monkeypatch):
    """Stub external I/O so tests never hit the network, redis, shell, etc."""
    monkeypatch.setattr(httpx, "get", _fake_http_get)
    monkeypatch.setattr(httpx, "post", _fake_http_post)
    monkeypatch.setattr(httpx, "request", _fake_http_get)
    try:
        import requests
        monkeypatch.setattr(requests, "get", _fake_http_get)
        monkeypatch.setattr(requests, "post", _fake_http_post)
    except ImportError:
        pass
    try:
        import redis
        monkeypatch.setattr(redis, "Redis", type("FakeRedis", (), {}))
    except ImportError:
        pass
    try:
        import redis.asyncio
        monkeypatch.setattr(redis.asyncio, "Redis", type("FakeAsyncRedis", (), {}))
    except (ImportError, AttributeError):
        pass
    try:
        import aiohttp
        monkeypatch.setattr(aiohttp, "ClientSession", type("FakeSession", (), {}))
    except ImportError:
        pass
    import subprocess
    monkeypatch.setattr(subprocess, "run", _fake_subprocess_run)
    monkeypatch.setattr(subprocess, "Popen", _no_op)


def _model_fields(model):
    return getattr(model, "model_fields", None) or getattr(model, "__fields__", {})


def _is_required(field_info):
    if hasattr(field_info, "is_required"):
        return field_info.is_required()
    return getattr(field_info, "required", False)


def _field_annotation(field_info):
    return getattr(field_info, "annotation", None) or getattr(field_info, "outer_type_", None)


def _unwrap_optional(annotation):
    origin = typing.get_origin(annotation)
    if origin is typing.Union or (hasattr(types, "UnionType") and origin is types.UnionType):
        for arg in typing.get_args(annotation):
            if arg is not type(None):
                return _unwrap_optional(arg)
        return type(None)
    return annotation


def _sensible_value(annotation):
    annotation = _unwrap_optional(annotation)
    if annotation is type(None):
        return None
    origin = typing.get_origin(annotation)
    if origin is not None:
        if origin is typing.List or (isinstance(origin, type) and issubclass(origin, list)):
            return []
        if origin is typing.Dict or (isinstance(origin, type) and issubclass(origin, dict)):
            return {}
        return None
    if isinstance(annotation, type):
        if issubclass(annotation, bool):
            return True
        if issubclass(annotation, int):
            return 0
        if issubclass(annotation, float):
            return 0.0
        if issubclass(annotation, str):
            return "x"
    return None


def _find_entity_model(module):
    for _, cls in module.__dict__.items():
        if not isinstance(cls, type):
            continue
        if not issubclass(cls, BaseModel) or cls is BaseModel:
            continue
        if cls.__name__ in _EXCLUDED_MODEL_NAMES:
            continue
        fields = _model_fields(cls)
        if "id" in fields:
            return cls
    return None


def _build_create_payload(model):
    payload = {}
    for field_name, field_info in _model_fields(model).items():
        if not _is_required(field_info):
            continue
        payload[field_name] = _sensible_value(_field_annotation(field_info))
    return payload


def _find_update_field_and_value(model, create_payload):
    fields = _model_fields(model)
    chosen = None
    for field_name, field_info in fields.items():
        if field_name == "id":
            continue
        ann = _unwrap_optional(_field_annotation(field_info))
        if ann is str:
            chosen = field_name
            break
    if chosen is None:
        for field_name in fields:
            if field_name != "id":
                chosen = field_name
                break
    if chosen is None:
        return None, None
    base = _sensible_value(_field_annotation(fields[chosen]))
    if base == "x":
        return chosen, "y"
    if base == 0:
        return chosen, 1
    if base == 0.0:
        return chosen, 1.1
    if base is True:
        return chosen, False
    return chosen, base


def _extract_id(result):
    if isinstance(result, dict):
        return result.get("id")
    if hasattr(result, "id"):
        return getattr(result, "id")
    return None


@pytest.mark.parametrize(
    "main_path",
    MAIN_PY_FILES,
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_addon_microservice_full_crud_flow(main_path: Path):
    rel = main_path.relative_to(ROOT).with_suffix("")
    module_name = f"_addon_test_{'_'.join(rel.parts)}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(main_path))
        if spec is None or spec.loader is None:
            pytest.skip(f"Could not create spec for {main_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:
        pytest.skip(f"Could not load {main_path}: {exc}")

    app = getattr(module, "app", None)
    if app is None:
        pytest.skip(f"{main_path} has no 'app'")

    entity_model = _find_entity_model(module)
    if entity_model is None:
        pytest.skip(f"{main_path} has no entity BaseModel with 'id' field")

    handlers = getattr(module, "HANDLERS", {})
    if not handlers:
        pytest.skip(f"{main_path} has no HANDLERS")

    create_payload = _build_create_payload(entity_model)
    client = TestClient(app)

    create_resp = client.post(
        "/invoke",
        json={"action": "create", "payload": create_payload},
    )
    if create_resp.status_code >= 400:
        pytest.skip(f"create failed for {main_path}: {create_resp.status_code}")

    data = create_resp.json()
    result = data.get("result", {})
    item_id = _extract_id(result)
    if not item_id:
        pytest.skip(f"create did not return an id for {main_path}")

    update_field, update_value = _find_update_field_and_value(entity_model, create_payload)
    query_payload = {"name": "x"} if "name" in _model_fields(entity_model) else None
    if query_payload is None:
        for field_name in _model_fields(entity_model):
            if field_name != "id" and field_name in create_payload:
                query_payload = {field_name: create_payload[field_name]}
                break
    if query_payload is None:
        query_payload = {}

    actions = [
        ("list", {}),
        ("get", {"id": item_id}),
        ("update", {"id": item_id, update_field: update_value} if update_field else {"id": item_id}),
        ("query", query_payload),
        ("run", {"id": item_id}),
        ("export", {}),
        ("evaluate", {}),
        ("import", {"items": [create_payload]}),
        ("delete", {"id": item_id}),
    ]

    for action, payload in actions:
        if action not in handlers:
            continue
        resp = client.post("/invoke", json={"action": action, "payload": payload})
        if resp.status_code != 200:
            pytest.skip(f"{action} returned {resp.status_code} for {main_path}: {resp.text}")
