# -*- coding: utf-8 -*-
"""Tests for the durable document store backing the advanced routers.

These verify that :class:`core.persistent_store.PersistentStore` behaves like a
mapping *and* actually persists across process-level "reloads" (a fresh store
instance reading the same rows), which is the whole point of replacing the old
module-level dicts.
"""

from __future__ import annotations

import uuid

from core.persistent_store import PersistentStore, _jsonable


def _store(kind: str = "demo"):
    return PersistentStore("test_persistent_store", f"{kind}_{uuid.uuid4().hex[:8]}")


def test_setitem_persists_across_instances():
    store = _store()
    store["a"] = {"value": 1}

    reloaded = PersistentStore(store.domain, store.kind)
    assert reloaded["a"] == {"value": 1}
    assert len(reloaded) == 1


def test_delete_persists():
    store = _store()
    store["a"] = {"value": 1}
    del store["a"]

    reloaded = PersistentStore(store.domain, store.kind)
    assert "a" not in reloaded


def test_in_place_mutation_requires_flush():
    store = _store()
    store["a"] = {"items": [1]}

    store["a"]["items"].append(2)
    store.flush("a")

    reloaded = PersistentStore(store.domain, store.kind)
    assert reloaded["a"] == {"items": [1, 2]}


def test_flush_without_key_persists_all():
    store = _store()
    store["a"] = {"n": 1}
    store["b"] = {"n": 2}
    store["a"]["n"] = 10
    store.flush()

    reloaded = PersistentStore(store.domain, store.kind)
    assert reloaded["a"] == {"n": 10}
    assert reloaded["b"] == {"n": 2}


def test_clear_removes_persisted_rows():
    store = _store()
    store["a"] = {"value": 1}
    store.clear()

    reloaded = PersistentStore(store.domain, store.kind)
    assert len(reloaded) == 0


def test_decoder_reconstructs_rich_objects():
    class Model:
        def __init__(self, name, score):
            self.name = name
            self.score = score

    kind = f"model_{uuid.uuid4().hex[:8]}"
    store = PersistentStore(
        "test_persistent_store", kind, decoder=lambda p: Model(p["name"], p["score"])
    )
    store["m1"] = {"name": "alpha", "score": 3}

    reloaded = PersistentStore(
        "test_persistent_store", kind, decoder=lambda p: Model(p["name"], p["score"])
    )
    obj = reloaded["m1"]
    assert isinstance(obj, Model)
    assert obj.name == "alpha"
    assert obj.score == 3


def test_jsonable_handles_enum_datetime_and_rich_objects():
    import datetime
    from enum import Enum

    class Color(str, Enum):
        RED = "red"

    payload = _jsonable(
        {
            "enum": Color.RED,
            "when": datetime.datetime(2026, 1, 2, 3, 4, 5),
            "nested": [datetime.date(2026, 1, 2)],
        }
    )
    assert payload["enum"] == "red"
    assert payload["when"].startswith("2026-01-02T03:04:05")
    assert payload["nested"] == ["2026-01-02"]


def test_isolated_by_kind():
    a = PersistentStore("test_persistent_store", "isolation_a")
    b = PersistentStore("test_persistent_store", "isolation_b")
    a["x"] = {"v": 1}
    b["x"] = {"v": 2}
    assert a["x"] == {"v": 1}
    assert b["x"] == {"v": 2}
