# -*- coding: utf-8 -*-
"""Durable, domain-scoped document store for advanced API routers.

Several "advanced" API routers historically kept their business entities in
module-level ``dict``/``list`` objects.  That made the endpoints stateless and
lossy — every process restart silently discarded releases, optimization tasks,
repair executions, ….

:class:`PersistentStore` keeps the very same mapping interface the routers
already use (``store[key] = value`` / ``del store[key]`` / ``store.items()`` /
``len(store)`` …) but writes every mutation through to the ``persistent_records``
table.  Each row stores one entity serialised as JSON, scoped by
``(domain, kind, tenant_id)`` so unrelated routers never collide.

Design highlights
-----------------
* **In-place mutations are durable.**  Values that are plain ``dict``/``list``
  are wrapped in lightweight tracking containers, so ``store[k]["status"] = "x"``
  or ``store[k].append(v)`` are written back automatically — the router code
  does not have to change.
* **Rich objects survive restarts.**  When a ``decoder`` is supplied the stored
  JSON is reconstructed (e.g. back into a Pydantic model) on load.
* **``defaultdict`` semantics.**  ``default_factory`` reproduces
  ``defaultdict(list)`` behaviour for stores keyed by parent id.
* **Non-string keys.**  ``key_type=int`` supports stores keyed by user/tenant id.

The table is created on first use if it is missing, so the store works in unit
tests that never run the full Alembic chain, while still being a normal Alembic
managed table (revision ``030``) in production.
"""

from __future__ import annotations

import json
import logging
from collections.abc import MutableMapping, MutableSequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal, engine
from core.models import PersistentRecordDB

logger = logging.getLogger(__name__)

#: Cache of the "table ensured" flag for this process.
_ENSURED_TABLES = False


def _ensure_table() -> None:
    """Create ``persistent_records`` if it does not exist yet (idempotent)."""
    global _ENSURED_TABLES
    if _ENSURED_TABLES:
        return
    try:
        PersistentRecordDB.__table__.create(bind=engine, checkfirst=True)
        _ENSURED_TABLES = True
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        logger.warning("Could not ensure persistent_records table: %s", exc)


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of *value* into JSON-serialisable structures."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, MutableMapping) or isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return _jsonable(dump())
    dict_fn = getattr(value, "dict", None)
    if callable(dict_fn):
        try:
            return _jsonable(dict_fn())
        except Exception:  # pragma: no cover - defensive
            pass
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _jsonable(to_dict())
        except Exception:  # pragma: no cover - defensive
            pass
    # Fallback: stringify so that nothing silently disappears.
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


# --------------------------------------------------------------------------- #
# Tracking containers — make in-place mutations durable
# --------------------------------------------------------------------------- #
def _wrap(value: Any, on_change: Callable[[], None]) -> Any:
    """Recursively wrap dict/list values so nested mutations trigger *on_change*."""
    if isinstance(value, _TrackedDict):
        value._on_change = on_change
        value._rebind_children(on_change)
        return value
    if isinstance(value, _TrackedList):
        value._on_change = on_change
        value._rebind_children(on_change)
        return value
    if isinstance(value, dict):
        return _TrackedDict(value, on_change)
    if isinstance(value, list):
        return _TrackedList(value, on_change)
    return value


class _TrackedDict(dict):
    """A ``dict`` that reports every mutation through ``_on_change``."""

    __slots__ = ("_on_change",)

    def __init__(self, data: Optional[dict] = None, on_change: Optional[Callable[[], None]] = None):
        super().__init__()
        object.__setattr__(self, "_on_change", on_change or (lambda: None))
        if data:
            for key, value in data.items():
                dict.__setitem__(self, key, _wrap(value, object.__getattribute__(self, "_on_change")))

    def _rebind_children(self, on_change: Callable[[], None]) -> None:
        for key in list(dict.keys(self)):
            dict.__setitem__(self, key, _wrap(dict.__getitem__(self, key), on_change))

    def _changed(self) -> None:
        object.__getattribute__(self, "_on_change")()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, _wrap(value, object.__getattribute__(self, "_on_change")))
        self._changed()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._changed()

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            dict.__setitem__(self, key, _wrap(value, object.__getattribute__(self, "_on_change")))
        self._changed()

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return dict.__getitem__(self, key)

    def pop(self, *args):
        result = dict.pop(self, *args)
        self._changed()
        return result

    def popitem(self):
        result = dict.popitem(self)
        self._changed()
        return result

    def clear(self):
        dict.clear(self)
        self._changed()


class _TrackedList(list):
    """A ``list`` that reports every mutation through ``_on_change``."""

    __slots__ = ("_on_change",)

    def __init__(self, data: Optional[list] = None, on_change: Optional[Callable[[], None]] = None):
        super().__init__()
        object.__setattr__(self, "_on_change", on_change or (lambda: None))
        if data:
            for item in data:
                list.append(self, _wrap(item, object.__getattribute__(self, "_on_change")))

    def _rebind_children(self, on_change: Callable[[], None]) -> None:
        for index in range(len(self)):
            list.__setitem__(self, index, _wrap(list.__getitem__(self, index), on_change))

    def _changed(self) -> None:
        object.__getattribute__(self, "_on_change")()

    def append(self, item):
        list.append(self, _wrap(item, object.__getattribute__(self, "_on_change")))
        self._changed()

    def insert(self, index, item):
        list.insert(self, index, _wrap(item, object.__getattribute__(self, "_on_change")))
        self._changed()

    def extend(self, items):
        for item in items:
            list.append(self, _wrap(item, object.__getattribute__(self, "_on_change")))
        self._changed()

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            list.__setitem__(
                self,
                index,
                [_wrap(v, object.__getattribute__(self, "_on_change")) for v in value],
            )
        else:
            list.__setitem__(self, index, _wrap(value, object.__getattribute__(self, "_on_change")))
        self._changed()

    def __delitem__(self, index):
        list.__delitem__(self, index)
        self._changed()

    def __iadd__(self, other):
        self.extend(other)
        return self

    def pop(self, *args):
        result = list.pop(self, *args)
        self._changed()
        return result

    def remove(self, item):
        list.remove(self, item)
        self._changed()

    def reverse(self):
        list.reverse(self)
        self._changed()

    def sort(self, *args, **kwargs):
        list.sort(self, *args, **kwargs)
        self._changed()

    def clear(self):
        list.clear(self)
        self._changed()


# --------------------------------------------------------------------------- #
# PersistentStore
# --------------------------------------------------------------------------- #
class PersistentStore(MutableMapping):
    """A ``dict``-like mapping whose entries live in ``persistent_records``.

    Parameters
    ----------
    domain, kind:
        Scope used to isolate this store's rows from every other store.
    tenant_id:
        Tenant scope (defaults to ``"default"``).
    decoder:
        Optional ``callable(payload_dict) -> value`` used to rebuild rich
        objects (e.g. Pydantic models) on read.  When omitted the raw
        normalised dict/list is returned (as a tracking container).
    key_type:
        Coercion applied to keys (``str`` by default, ``int`` for id-keyed
        stores).
    default_factory:
        When set, reading a missing key creates (and persists) the default,
        reproducing ``defaultdict(default_factory)`` semantics.
    """

    def __init__(
        self,
        domain: str,
        kind: str,
        tenant_id: str = "default",
        decoder: Optional[Callable[[Dict[str, Any]], Any]] = None,
        key_type: Callable[[Any], Any] = str,
        default_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.domain = domain
        self.kind = kind
        self.tenant_id = tenant_id
        self._decoder = decoder
        self._key_type = key_type
        self._default_factory = default_factory
        self._cache: Dict[Any, Any] = {}
        _ensure_table()
        self.load()

    # ------------------------------------------------------------------ #
    # key handling
    # ------------------------------------------------------------------ #
    def _coerce_key(self, key: Any) -> Any:
        return self._key_type(key)

    def _row_id(self, key: Any) -> str:
        return f"{self.domain}:{self.kind}:{self.tenant_id}:{key}"

    # ------------------------------------------------------------------ #
    # persistence helpers
    # ------------------------------------------------------------------ #
    def load(self) -> "PersistentStore":
        """(Re)hydrate the in-memory view from the database."""
        self._cache.clear()
        db = SessionLocal()
        try:
            rows = (
                db.query(PersistentRecordDB)
                .filter(
                    PersistentRecordDB.domain == self.domain,
                    PersistentRecordDB.kind == self.kind,
                    PersistentRecordDB.tenant_id == self.tenant_id,
                )
                .all()
            )
            for row in rows:
                payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
                key = self._coerce_key(row.record_key)
                self._cache[key] = self._wrap(key, self._decode(payload))
        except SQLAlchemyError as exc:
            logger.error("Failed to load %s/%s from database: %s", self.domain, self.kind, exc)
        finally:
            db.close()
        return self

    def _encode(self, value: Any) -> Dict[str, Any]:
        encoded = _jsonable(value)
        if not isinstance(encoded, dict):
            # Wrap scalars/lists so the JSON column always gets an object.
            return {"__value__": encoded}
        return encoded

    @staticmethod
    def _unwrap(payload: Dict[str, Any]) -> Any:
        if set(payload.keys()) == {"__value__"}:
            return payload["__value__"]
        return payload

    def _decode(self, payload: Dict[str, Any]) -> Any:
        value = self._unwrap(payload)
        if self._decoder is not None and isinstance(value, dict):
            return self._decoder(value)
        return value

    def _wrap(self, key: Any, value: Any) -> Any:
        """Wrap containers so in-place mutations write back through."""
        if isinstance(value, (dict, list)) and not isinstance(value, (str, bytes)):
            return _wrap(value, lambda: self._persist(key, self._cache[key]))
        return value

    def _persist(self, key: Any, value: Any) -> None:
        db = SessionLocal()
        try:
            row_id = self._row_id(key)
            row = db.query(PersistentRecordDB).filter(PersistentRecordDB.id == row_id).first()
            payload = self._encode(value)
            if row is None:
                row = PersistentRecordDB(
                    id=row_id,
                    domain=self.domain,
                    kind=self.kind,
                    record_key=str(key),
                    tenant_id=self.tenant_id,
                    payload=payload,
                )
                db.add(row)
            else:
                row.payload = payload
                row.updated_at = datetime.utcnow()
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to persist %s/%s[%s]: %s", self.domain, self.kind, key, exc)
            raise
        finally:
            db.close()

    def _delete(self, key: Any) -> None:
        db = SessionLocal()
        try:
            db.query(PersistentRecordDB).filter(
                PersistentRecordDB.id == self._row_id(key)
            ).delete(synchronize_session=False)
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to delete %s/%s[%s]: %s", self.domain, self.kind, key, exc)
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # Mapping protocol
    # ------------------------------------------------------------------ #
    def __getitem__(self, key: Any) -> Any:
        key = self._coerce_key(key)
        if key not in self._cache:
            if self._default_factory is not None:
                default = self._default_factory()
                self[key] = default
            else:
                raise KeyError(key)
        return self._cache[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        key = self._coerce_key(key)
        self._persist(key, value)
        self._cache[key] = self._wrap(key, value)

    def __delitem__(self, key: Any) -> None:
        key = self._coerce_key(key)
        if key not in self._cache:
            raise KeyError(key)
        self._delete(key)
        del self._cache[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(list(self._cache.keys()))

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: object) -> bool:
        try:
            return self._coerce_key(key) in self._cache
        except (TypeError, ValueError):
            return False

    def get(self, key: Any, default: Any = None) -> Any:
        """``dict.get`` semantics — never triggers ``default_factory``."""
        try:
            return self._cache.get(self._coerce_key(key), default)
        except (TypeError, ValueError):
            return default

    def clear(self) -> None:  # type: ignore[override]
        for key in list(self._cache.keys()):
            self._delete(key)
        self._cache.clear()

    def flush(self, key: Optional[Any] = None) -> None:
        """Re-persist entries after in-place mutation of non-tracked values.

        ``store["id"]["status"] = "done"`` on a plain dict is written back
        automatically; this helper exists for in-place mutation of rich values
        (e.g. Pydantic models) that the tracking layer cannot observe.
        """
        if key is None:
            for k, value in list(self._cache.items()):
                self._persist(k, value)
        else:
            self._persist(self._coerce_key(key), self._cache[self._coerce_key(key)])

    def as_dict(self) -> Dict[Any, Any]:
        """Return a plain ``dict`` copy (used by response models)."""
        return dict(self._cache)

    def values_list(self) -> List[Any]:
        return list(self._cache.values())


# --------------------------------------------------------------------------- #
# PersistentList
# --------------------------------------------------------------------------- #
class PersistentList(MutableSequence):
    """A ``list``-like sequence persisted as a single ``persistent_records`` row.

    Order is preserved by keeping the whole sequence in one JSON document under
    the ``"__items__"`` record key.  In-place mutations of ``dict``/``list``
    elements are tracked, so ``store[0]["x"] = 1`` is durable without extra
    calls.
    """

    _RECORD_KEY = "__items__"

    def __init__(
        self,
        domain: str,
        kind: str,
        tenant_id: str = "default",
        decoder: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        self.domain = domain
        self.kind = kind
        self.tenant_id = tenant_id
        self._decoder = decoder
        self._items: List[Any] = []
        _ensure_table()
        self.load()

    # ------------------------------------------------------------------ #
    def _row_id(self) -> str:
        return f"{self.domain}:{self.kind}:{self.tenant_id}:{self._RECORD_KEY}"

    def _decode_item(self, raw: Any) -> Any:
        if self._decoder is not None and isinstance(raw, dict):
            return self._decoder(raw)
        return raw

    def load(self) -> "PersistentList":
        self._items = []
        db = SessionLocal()
        try:
            row = (
                db.query(PersistentRecordDB)
                .filter(PersistentRecordDB.id == self._row_id())
                .first()
            )
            if row is not None:
                payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
                for raw in payload.get("__items__", []):
                    decoded = self._decode_item(raw)
                    self._items.append(_wrap(decoded, self._persist_all))
        except SQLAlchemyError as exc:
            logger.error("Failed to load list %s/%s: %s", self.domain, self.kind, exc)
        finally:
            db.close()
        return self

    def _persist_all(self) -> None:
        db = SessionLocal()
        try:
            payload = {"__items__": [_jsonable(item) for item in self._items]}
            row = db.query(PersistentRecordDB).filter(PersistentRecordDB.id == self._row_id()).first()
            if row is None:
                row = PersistentRecordDB(
                    id=self._row_id(),
                    domain=self.domain,
                    kind=self.kind,
                    record_key=self._RECORD_KEY,
                    tenant_id=self.tenant_id,
                    payload=payload,
                )
                db.add(row)
            else:
                row.payload = payload
                row.updated_at = datetime.utcnow()
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to persist list %s/%s: %s", self.domain, self.kind, exc)
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # MutableSequence protocol
    # ------------------------------------------------------------------ #
    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            self._items[index] = [_wrap(v, self._persist_all) for v in value]
        else:
            self._items[index] = _wrap(value, self._persist_all)
        self._persist_all()

    def __delitem__(self, index):
        del self._items[index]
        self._persist_all()

    def __len__(self) -> int:
        return len(self._items)

    def insert(self, index, value):
        self._items.insert(index, _wrap(value, self._persist_all))
        self._persist_all()

    def append(self, value):
        self._items.append(_wrap(value, self._persist_all))
        self._persist_all()

    def extend(self, values):
        for value in values:
            self._items.append(_wrap(value, self._persist_all))
        self._persist_all()

    def clear(self):
        self._items.clear()
        self._persist_all()

    def values_list(self) -> List[Any]:
        return list(self._items)

    def copy(self) -> List[Any]:
        """Return a shallow ``list`` copy (``list.copy`` compatibility)."""
        return list(self._items)
