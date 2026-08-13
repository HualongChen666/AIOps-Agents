# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.idempotent, core.input_validator,
core.i18n, core.multi_tenant and core.metadata_engine."""
import asyncio
import json
import sys
import types
from contextvars import ContextVar
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import core.idempotent as idem
import core.i18n as i18n
import core.input_validator as iv
import core.metadata_engine as me
import core.multi_tenant as mt

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# Fixtures / helpers
# -----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _patch_idempotent_typing_dict(monkeypatch):
    """typing.Dict is not callable; replace it with the builtin dict so the
    in-memory store can actually return dictionaries."""
    monkeypatch.setattr("core.idempotent.Dict", dict)


@pytest.fixture
def clean_messages_dir(tmp_path, monkeypatch):
    """Provide a temporary messages directory and reset i18n globals."""
    messages_dir = tmp_path / "messages"
    messages_dir.mkdir()
    (messages_dir / "zh.json").write_text(
        json.dumps(
            {
                "alert.not_found": "未找到待审批记录: {alert_id}",
                "greeting": "你好",
                "fallback_only": "仅中文",
            }
        ),
        encoding="utf-8",
    )
    (messages_dir / "en.json").write_text(
        json.dumps(
            {
                "alert.not_found": "Pending approval not found: {alert_id}",
                "greeting": "Hello",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("core.i18n._MESSAGES_DIR", messages_dir)
    monkeypatch.setattr("core.i18n._messages", {})
    monkeypatch.setattr("core.i18n._loaded", False)
    new_ctx = ContextVar("i18n_locale_test", default=i18n._FALLBACK_LOCALE)
    monkeypatch.setattr("core.i18n._current_locale", new_ctx)
    yield messages_dir


@pytest.fixture(autouse=True)
def _clean_tenant_globals(monkeypatch):
    """Reset multi-tenant in-memory state for each test."""
    monkeypatch.setattr("core.multi_tenant._tenant_configs", {})
    monkeypatch.setattr("core.multi_tenant._tenant_users", {})
    monkeypatch.setattr(
        "core.multi_tenant._current_tenant",
        ContextVar("current_tenant_test", default=None),
    )


# -----------------------------------------------------------------------------
# core.idempotent
# -----------------------------------------------------------------------------
def test_idempotency_store_get_set_delete():
    store = idem.IdempotencyStore(ttl=3600)
    assert store.get("missing") is None
    assert store.exists("missing") is False
    store.set("k1", {"status": "ok"})
    assert store.exists("k1") is True
    assert store.get("k1") == {"status": "ok"}
    assert store.delete("k1") is True
    assert store.delete("k1") is False


def test_idempotency_store_expiration():
    store = idem.IdempotencyStore(ttl=-1)
    store.set("expired", {"x": 1})
    assert store.get("expired") is None
    assert store.exists("expired") is False


def test_idempotency_store_clear_expired():
    store = idem.IdempotencyStore(ttl=-1)
    store.set("a", {})
    store.set("b", {})
    assert store.clear_expired() == 2


def test_redis_store_with_fake_client():
    store = idem.RedisIdempotencyStore(redis_url="redis://fake", ttl=60)
    calls = {"get": [], "setex": [], "delete": [], "exists": []}

    class FakeClient:
        def __init__(self):
            self.data = {"idemp:k": json.dumps({"cached": True})}

        def get(self, key):
            calls["get"].append(key)
            return self.data.get(key)

        def setex(self, key, ttl, value):
            calls["setex"].append((key, ttl, value))
            self.data[key] = value

        def delete(self, key):
            calls["delete"].append(key)
            return 1 if self.data.pop(key, None) is not None else 0

        def exists(self, key):
            calls["exists"].append(key)
            return 1 if key in self.data else 0

    store._redis_client = FakeClient()
    assert store.get("k") == {"cached": True}
    assert store.get("k2") is None
    store.set("k3", {"x": 1})
    assert store.delete("k3") is True
    assert store.exists("k3") is False


def test_redis_store_get_invalid_json():
    store = idem.RedisIdempotencyStore(redis_url="redis://fake")

    class FakeClient:
        def get(self, key):
            return "not-json"

    store._redis_client = FakeClient()
    assert store.get("k") is None


def test_redis_store_exception_paths():
    store = idem.RedisIdempotencyStore(redis_url="redis://fake")

    class BoomClient:
        def get(self, key):
            raise RuntimeError("boom")

        def setex(self, key, ttl, value):
            raise RuntimeError("boom")

        def delete(self, key):
            raise RuntimeError("boom")

        def exists(self, key):
            raise RuntimeError("boom")

    store._redis_client = BoomClient()
    assert store.get("k") is None
    store.set("k", {})  # should not raise
    assert store.delete("k") is False
    assert store.exists("k") is False


def test_redis_store_falls_back_to_memory(monkeypatch):
    """Simulate redis import failure and verify in-memory fallback works."""
    monkeypatch.setitem(sys.modules, "redis", None)
    store = idem.RedisIdempotencyStore(redis_url="redis://fake")
    store._redis_client = None
    store.set("key", {"value": 1})
    assert store.get("key") == {"value": 1}


def test_generate_idempotency_key_variations():
    base = idem.generate_idempotency_key("POST", "/api/orders")
    assert len(base) == 64

    with_body = idem.generate_idempotency_key(
        "post",
        "/api/orders",
        body={"id": 1, "items": ["a", "b"]},
        headers={"Authorization": "secret", "X-Request-Id": "abc"},
        user_id="u123",
    )
    # auth/cookie must be filtered out; different headers should not affect key
    with_filtered = idem.generate_idempotency_key(
        "post",
        "/api/orders",
        body={"id": 1, "items": ["a", "b"]},
        headers={"Cookie": "session=x", "X-Request-Id": "abc"},
        user_id="u123",
    )
    assert with_body == with_filtered
    assert with_body != base


def test_idempotent_sync_decorator_caches():
    store = idem.IdempotencyStore(ttl=3600)
    calls = []

    @idem.idempotent(store=store, key_generator=lambda *a, **k: "key1")
    def create_resource(data):
        calls.append(data)
        return {"id": 1, "data": data}

    assert create_resource({"x": 1}) == {"id": 1, "data": {"x": 1}}
    assert create_resource({"x": 1}) == {"id": 1, "data": {"x": 1}}
    assert len(calls) == 1  # second call should be served from cache


def test_idempotent_sync_decorator_explicit_key():
    store = idem.IdempotencyStore(ttl=3600)

    @idem.idempotent(store=store)
    def update(x):
        return {"x": x + 1}

    assert update(1, idempotency_key="abc") == {"x": 2}
    assert update(5, idempotency_key="abc") == {"x": 2}  # cached


def test_idempotent_sync_decorator_no_key():
    store = idem.IdempotencyStore(ttl=3600)

    @idem.idempotent(store=store)
    def plain(a, b):
        return a + b

    assert plain(1, 2) == 3
    assert plain(1, 2) == 3


def test_idempotent_async_decorator():
    store = idem.IdempotencyStore(ttl=3600)
    calls = []

    @idem.idempotent(store=store, key_generator=lambda *a, **k: "async-key")
    async def async_create(payload):
        calls.append(payload)
        return {"ok": True, "payload": payload}

    assert asyncio.run(async_create({"a": 1})) == {"ok": True, "payload": {"a": 1}}
    assert asyncio.run(async_create({"a": 2})) == {"ok": True, "payload": {"a": 1}}
    assert len(calls) == 1


def test_idempotency_middleware_bypasses_non_mutating_methods():
    middleware = idem.IdempotencyMiddleware()

    async def call_next(request):
        return types.SimpleNamespace(status_code=200)

    class FakeRequest:
        method = "GET"
        headers = {}

    async def run():
        return await middleware(FakeRequest(), call_next)

    resp = asyncio.run(run())
    assert resp.status_code == 200


def test_idempotency_middleware_returns_cached_response(monkeypatch):
    # Avoid a hard dependency on fastapi for this unit test.
    fastapi_mod = types.ModuleType("fastapi")
    responses_mod = types.ModuleType("fastapi.responses")

    class FakeJSONResponse:
        def __init__(self, content):
            self.content = content

    responses_mod.JSONResponse = FakeJSONResponse
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "fastapi.responses", responses_mod)

    store = idem.IdempotencyStore(ttl=3600)
    store.set("idem-key", {"cached": True})
    middleware = idem.IdempotencyMiddleware(store=store)

    calls = []

    async def call_next(request):
        calls.append(request)
        return types.SimpleNamespace(status_code=200)

    class FakeRequest:
        method = "POST"
        headers = {"Idempotency-Key": "idem-key"}

    async def run():
        return await middleware(FakeRequest(), call_next)

    resp = asyncio.run(run())
    assert calls == []
    assert resp.content == {"cached": True}


def test_idempotency_middleware_caches_success_response(monkeypatch):
    fastapi_mod = types.ModuleType("fastapi")
    responses_mod = types.ModuleType("fastapi.responses")
    responses_mod.JSONResponse = lambda content: types.SimpleNamespace(content=content)
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "fastapi.responses", responses_mod)

    store = idem.IdempotencyStore(ttl=3600)
    middleware = idem.IdempotencyMiddleware(store=store)

    class FakeResponse:
        status_code = 200

        async def body(self):
            return json.dumps({"ok": True}).encode()

    class FakeRequest:
        method = "POST"
        headers = {"Idempotency-Key": "idem-key"}

    async def call_next(request):
        return FakeResponse()

    async def run():
        return await middleware(FakeRequest(), call_next)

    resp = asyncio.run(run())
    assert store.get("idem-key") == {"ok": True}


def test_idempotency_middleware_ignores_error_responses(monkeypatch):
    fastapi_mod = types.ModuleType("fastapi")
    responses_mod = types.ModuleType("fastapi.responses")
    responses_mod.JSONResponse = lambda content: types.SimpleNamespace(content=content)
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "fastapi.responses", responses_mod)

    store = idem.IdempotencyStore(ttl=3600)
    middleware = idem.IdempotencyMiddleware(store=store)

    class FakeResponse:
        status_code = 500

    class FakeRequest:
        method = "POST"
        headers = {"Idempotency-Key": "error-key"}

    async def call_next(request):
        return FakeResponse()

    async def run():
        return await middleware(FakeRequest(), call_next)

    asyncio.run(run())
    assert store.get("error-key") is None


def test_idempotency_middleware_unparseable_body(monkeypatch):
    fastapi_mod = types.ModuleType("fastapi")
    responses_mod = types.ModuleType("fastapi.responses")
    responses_mod.JSONResponse = lambda content: types.SimpleNamespace(content=content)
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "fastapi.responses", responses_mod)

    store = idem.IdempotencyStore(ttl=3600)
    middleware = idem.IdempotencyMiddleware(store=store)

    class FakeResponse:
        status_code = 200

        async def body(self):
            return b"not-json"

    class FakeRequest:
        method = "POST"
        headers = {"Idempotency-Key": "bad-body"}

    async def call_next(request):
        return FakeResponse()

    async def run():
        return await middleware(FakeRequest(), call_next)

    asyncio.run(run())
    assert store.get("bad-body") is None


# -----------------------------------------------------------------------------
# core.input_validator
# -----------------------------------------------------------------------------
def test_sanitize_string():
    assert iv.InputValidator.sanitize_string("<script>alert(1)</script>") == (
        "&lt;script&gt;alert(1)&lt;/script&gt;"
    )
    assert iv.InputValidator.sanitize_string(123) == ""
    long = "x" * 2000
    assert len(iv.InputValidator.sanitize_string(long, max_length=100)) == 100


def test_validate_sql_safe():
    assert iv.InputValidator.validate_sql_safe("normal_text")[0] is True
    assert iv.InputValidator.validate_sql_safe("SELECT * FROM users")[0] is False
    assert iv.InputValidator.validate_sql_safe(123)[0] is False


def test_validate_xss_safe():
    assert iv.InputValidator.validate_xss_safe("hello")[0] is True
    assert iv.InputValidator.validate_xss_safe("<script>alert(1)</script>")[0] is False
    assert iv.InputValidator.validate_xss_safe("javascript:alert(1)")[0] is False
    assert iv.InputValidator.validate_xss_safe(123)[0] is False


def test_validate_command_safe():
    assert iv.InputValidator.validate_command_safe("hostname")[0] is True
    assert iv.InputValidator.validate_command_safe("rm -rf /; echo pwn")[0] is False
    assert iv.InputValidator.validate_command_safe("../etc/passwd")[0] is False
    assert iv.InputValidator.validate_command_safe(123)[0] is False


def test_validate_path_safe():
    assert iv.InputValidator.validate_path_safe("files/report.pdf")[0] is True
    assert iv.InputValidator.validate_path_safe("../etc/passwd")[0] is False
    assert iv.InputValidator.validate_path_safe("/etc/passwd")[0] is False
    assert iv.InputValidator.validate_path_safe("C:\\Windows\\cmd.exe")[0] is False
    assert iv.InputValidator.validate_path_safe(123)[0] is False


def test_validate_email():
    assert iv.InputValidator.validate_email("user@example.com")[0] is True
    assert iv.InputValidator.validate_email("invalid-email")[0] is False
    assert iv.InputValidator.validate_email(123)[0] is False


def test_validate_username():
    assert iv.InputValidator.validate_username("alice_01")[0] is True
    assert iv.InputValidator.validate_username("ab")[0] is False
    assert iv.InputValidator.validate_username("a" * 51)[0] is False
    assert iv.InputValidator.validate_username("bad@name")[0] is False
    assert iv.InputValidator.validate_username(123)[0] is False


def test_sanitize_dict_and_list():
    raw = {
        "name": '<script>alert(1)</script>',
        "nested": {"tag": "<b>"},
        "items": ["<div>", {"inner": "<span>"}],
        "count": 42,
    }
    clean = iv.InputValidator.sanitize_dict(raw)
    assert clean["name"] == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert clean["nested"]["tag"] == "&lt;b&gt;"
    assert clean["items"][0] == "&lt;div&gt;"
    assert clean["items"][1]["inner"] == "&lt;span&gt;"
    assert clean["count"] == 42
    assert iv.InputValidator.sanitize_dict("not-a-dict") == "not-a-dict"
    assert iv.InputValidator.sanitize_list("not-a-list") == "not-a-list"


def test_validate_json():
    valid = '{"a": 1, "b": [1, 2]}'
    ok, err, parsed = iv.InputValidator.validate_json(valid)
    assert ok is True
    assert err == ""
    assert parsed == {"a": 1, "b": [1, 2]}

    ok, err, parsed = iv.InputValidator.validate_json("not-json")
    assert ok is False
    assert parsed is None
    assert "Invalid JSON" in err

    ok, err, parsed = iv.InputValidator.validate_json(123)
    assert ok is False


def test_sanitize_input_convenience():
    assert iv.sanitize_input("<b>") == "&lt;b&gt;"
    assert iv.sanitize_input({"k": "<b>"}) == {"k": "&lt;b&gt;"}
    assert iv.sanitize_input(["<b>"]) == ["&lt;b&gt;"]
    assert iv.sanitize_input(42) == 42


def test_validate_and_clean_input():
    dirty = "<script>alert(1)</script> SELECT * FROM users; -- ../path & more"
    cleaned = iv.validate_and_clean_input(dirty)
    assert "<script>" not in cleaned
    assert "SELECT" not in cleaned
    assert ".." not in cleaned
    # html.escape turns '&' into '&amp;'
    assert "&amp;" in cleaned
    assert iv.validate_and_clean_input(123) == ""


def test_validate_safe_input():
    assert iv.validate_safe_input("safe-string")[0] is True
    assert iv.validate_safe_input("SELECT * FROM t")[0] is False
    assert iv.validate_safe_input("<script>alert(1)</script>")[0] is False
    assert iv.validate_safe_input("`id`")[0] is False
    assert iv.validate_safe_input("../etc")[0] is False
    assert iv.validate_safe_input(123)[0] is False


# -----------------------------------------------------------------------------
# core.i18n
# -----------------------------------------------------------------------------
def test_set_and_get_locale():
    i18n.set_locale("en")
    assert i18n.get_locale() == "en"
    i18n.set_locale("EN_US")
    assert i18n.get_locale() == "zh"
    i18n.set_locale(123)
    assert i18n.get_locale() == "zh"


def test_msg_translation_and_interpolation(clean_messages_dir):
    i18n.set_locale("en")
    assert i18n.msg("alert.not_found", alert_id="CPU-123") == (
        "Pending approval not found: CPU-123"
    )
    i18n.set_locale("zh")
    assert i18n.msg("greeting") == "你好"


def test_msg_fallback_chain(clean_messages_dir):
    i18n.set_locale("en")
    # key exists only in zh fallback
    assert i18n.msg("fallback_only") == "仅中文"
    # key does not exist in any language pack
    assert i18n.msg("missing_key") == "missing_key"


def test_get_supported_locales():
    assert i18n.get_supported_locales() == ["en", "zh"]


def test_get_messages_stats(clean_messages_dir):
    stats = i18n.get_messages_stats()
    assert stats["loaded"] is True
    assert stats["supported_locales"] == ["en", "zh"]
    assert stats["locale_stats"]["zh"] >= 1
    assert stats["locale_stats"]["en"] >= 1


def test_reload_messages(clean_messages_dir):
    stats = i18n.reload_messages()
    assert stats["loaded"] is True
    assert "locale_stats" in stats


def test_load_messages_missing_file(clean_messages_dir, monkeypatch):
    (clean_messages_dir / "en.json").unlink()
    i18n._loaded = False
    i18n._messages.clear()
    i18n._load_messages(force=False)
    assert i18n._messages.get("en") == {}
    # zh still works
    i18n.set_locale("zh")
    assert i18n.msg("greeting") == "你好"


def test_load_messages_invalid_json(clean_messages_dir):
    (clean_messages_dir / "en.json").write_text("{bad json", encoding="utf-8")
    i18n._load_messages(force=True)
    assert i18n._messages.get("en") == {}


def test_load_messages_non_dict_root(clean_messages_dir):
    (clean_messages_dir / "zh.json").write_text("[1, 2, 3]", encoding="utf-8")
    i18n._load_messages(force=True)
    assert i18n._messages.get("zh") == {}


# -----------------------------------------------------------------------------
# core.multi_tenant
# -----------------------------------------------------------------------------
def test_tenant_create_and_get():
    assert mt.create_tenant("t1", "Alpha", "first", {"plan": "pro"}) is True
    assert mt.create_tenant("t1", "Alpha") is False  # duplicate
    tenant = mt.get_tenant("t1")
    assert tenant["name"] == "Alpha"
    assert tenant["config"]["plan"] == "pro"
    assert mt.get_tenant("missing") is None


def test_tenant_update_and_delete():
    mt.create_tenant("t2", "Beta")
    assert mt.update_tenant("t2", name="Beta2", is_active=False) is True
    assert mt.get_tenant("t2")["name"] == "Beta2"
    assert mt.get_tenant("t2")["is_active"] is False
    assert mt.update_tenant("missing") is False
    assert mt.delete_tenant("t2") is True
    assert mt.delete_tenant("t2") is False


def test_list_tenants_and_stats():
    mt.create_tenant("t3", "Active")
    mt.create_tenant("t4", "Inactive")
    mt.update_tenant("t4", is_active=False)
    assert len(mt.list_tenants()) == 2
    assert len(mt.list_tenants(active_only=True)) == 1
    stats = mt.get_tenant_stats()
    assert stats["total_tenants"] == 2
    assert stats["active_tenants"] == 1
    assert stats["inactive_tenants"] == 1


def test_tenant_context_management():
    mt.create_tenant("t5", "Ctx")
    mt.set_tenant_context("t5")
    assert mt.get_tenant_context() == "t5"
    mt.clear_tenant_context()
    assert mt.get_tenant_context() is None
    mt.set_tenant_context("missing")  # not found
    mt.create_tenant("inactive", "X")
    mt.update_tenant("inactive", is_active=False)
    mt.set_tenant_context("inactive")  # not active


def test_tenant_user_management():
    mt.create_tenant("t6", "Users")
    assert mt.add_user_to_tenant("t6", "u1") is True
    assert mt.add_user_to_tenant("t6", "u1") is False  # duplicate
    assert mt.add_user_to_tenant("missing", "u1") is False
    assert mt.get_tenant_users("t6") == ["u1"]
    assert mt.is_user_in_tenant("u1", "t6") is True
    assert mt.get_user_tenants("u1") == ["t6"]
    assert mt.remove_user_from_tenant("t6", "u1") is True
    assert mt.remove_user_from_tenant("t6", "u1") is False
    assert mt.remove_user_from_tenant("missing", "u1") is False


def test_get_tenant_config_and_missing():
    mt.create_tenant("t7", "Cfg", config={"retention": 7})
    assert mt.get_tenant_config("t7") == {"retention": 7}
    assert mt.get_tenant_config("missing") == {}


def test_tenant_stats_empty():
    stats = mt.get_tenant_stats()
    assert stats["total_tenants"] == 0
    assert stats["avg_users_per_tenant"] == 0


def test_tenant_to_dict():
    t = mt.Tenant("tx", "Name", "desc", {"k": "v"})
    d = t.to_dict()
    assert d["tenant_id"] == "tx"
    assert d["name"] == "Name"
    assert d["config"] == {"k": "v"}
    assert "created_at" in d


# -----------------------------------------------------------------------------
# core.metadata_engine
# -----------------------------------------------------------------------------
@pytest.fixture
def datahub_fakes(monkeypatch):
    """Provide deterministic DataHub classes and monkeypatch metadata_engine."""
    mce = types.ModuleType("datahub.emitter.mce_builder")
    schema = types.ModuleType("datahub.metadata.schema_classes")

    class DatasetPropertiesClass:
        def __init__(self, description, customProperties):
            self.description = description
            self.customProperties = customProperties

    class DatasetSnapshot:
        def __init__(self, urn, aspects):
            self.urn = urn
            self.aspects = aspects

    class LineagePatchBuilder:
        def add_edge(self, up, down):
            self._edge = (up, down)
            return self

        def build(self):
            return self._edge

    class CorpUserUrn:
        def __init__(self, urn):
            self.urn = urn

    class OwnerClass:
        def __init__(self, owner, type):
            self.owner = owner
            self.type = type

    class OwnershipClass:
        def __init__(self, owners):
            self.owners = owners

    mce.DatasetPropertiesClass = DatasetPropertiesClass
    mce.DatasetSnapshot = DatasetSnapshot
    mce.LineagePatchBuilder = LineagePatchBuilder
    mce.make_dataset_urn = lambda platform, name, env: f"urn:dataset:{env}:{platform}.{name}"

    schema.CorpUserUrn = CorpUserUrn
    schema.OwnerClass = OwnerClass
    schema.OwnershipClass = OwnershipClass

    monkeypatch.setitem(sys.modules, "datahub.emitter.mce_builder", mce)
    monkeypatch.setitem(sys.modules, "datahub.metadata.schema_classes", schema)
    monkeypatch.setattr("core.metadata_engine.DATAHUB_REST_URL", "http://test-datahub")
    monkeypatch.setattr("core.metadata_engine.make_dataset_urn", mce.make_dataset_urn)

    emitted = []

    class FakeEmitter:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def emit(self, event):
            emitted.append(event)

    monkeypatch.setattr("core.metadata_engine.DatahubRestEmitter", FakeEmitter)
    yield {"emitted": emitted, "FakeEmitter": FakeEmitter}


def test_get_datahub_emitter_none():
    old = me.DatahubRestEmitter
    me.DatahubRestEmitter = None
    try:
        assert me._get_datahub_emitter() is None
    finally:
        me.DatahubRestEmitter = old


def test_register_dataset_no_datahub_support():
    # make_dataset_urn is None -> returns False without network
    old_make = me.make_dataset_urn
    me.make_dataset_urn = None
    try:
        assert me.register_dataset("mysql", "customers") is False
    finally:
        me.make_dataset_urn = old_make


def test_register_dataset_emitter_none():
    old_make = me.make_dataset_urn
    old_cls = me.DatahubRestEmitter
    me.make_dataset_urn = lambda platform, name, env: "urn:dataset:PROD:mysql.customers"
    me.DatahubRestEmitter = lambda **kwargs: None
    try:
        assert me.register_dataset("mysql", "customers") is False
    finally:
        me.make_dataset_urn = old_make
        me.DatahubRestEmitter = old_cls


def test_register_dataset_success(datahub_fakes):
    assert me.register_dataset("mysql", "customers", description="customers table") is True
    assert len(datahub_fakes["emitted"]) == 1
    snapshot = datahub_fakes["emitted"][0]
    assert snapshot.urn == "urn:dataset:PROD:mysql.customers"


def test_register_dataset_emit_error(datahub_fakes, monkeypatch):
    class FailingEmitter(datahub_fakes["FakeEmitter"]):
        def emit(self, event):
            raise RuntimeError("emit failed")

    monkeypatch.setattr("core.metadata_engine.DatahubRestEmitter", FailingEmitter)
    assert me.register_dataset("mysql", "customers") is False


def test_register_lineage_success(datahub_fakes):
    assert me.register_lineage(
        {"platform": "mysql", "name": "orders"},
        {"platform": "snowflake", "name": "orders_agg"},
        description="daily aggregation",
    ) is True
    assert len(datahub_fakes["emitted"]) == 1
    assert datahub_fakes["emitted"][0] == (
        "urn:dataset:PROD:mysql.orders",
        "urn:dataset:PROD:snowflake.orders_agg",
    )


def test_register_lineage_emit_error(datahub_fakes, monkeypatch):
    class FailingEmitter(datahub_fakes["FakeEmitter"]):
        def emit(self, event):
            raise RuntimeError("lineage failed")

    monkeypatch.setattr("core.metadata_engine.DatahubRestEmitter", FailingEmitter)
    assert me.register_lineage(
        {"platform": "a", "name": "a1"},
        {"platform": "b", "name": "b1"},
    ) is False


def test_amundsen_register_table():
    # default branch: AmundsenTable is None
    assert me.amundsen_register_table("users") is True
    # force non-None branch
    old = me.AmundsenTable
    me.AmundsenTable = object
    try:
        assert me.amundsen_register_table("orders") is True
    finally:
        me.AmundsenTable = old
