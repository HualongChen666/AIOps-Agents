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

The store is intentionally a thin *document* layer: the routers' business logic
(what a release is, how a repair is verified, …) is unchanged, only its
durability is fixed.  Values may be plain ``dict``/``list`` payloads, Pydantic
models or dataclasses — all are normalised to JSON on the way in and returned as
plain structures on the way out (Pydantic models are reconstructed when a
``decoder`` is supplied).

The table is created on first use if it is missing, so the store works in unit
tests that never run the full Alembic chain, while still being a normal Alembic
managed table (revision ``030``) in production.
"""

from __future__ import annotations

import json
import logging
from collections.abc import MutableMapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal, engine
from core.models import PersistentRecordDB

logger = logging.getLogger(__name__)

#: Cache of ``(domain, kind)`` tables already ensured in this process.
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
        normalised dict/list is returned.
    """

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
        self._cache: Dict[str, Any] = {}
        _ensure_table()
        self.load()

    # ------------------------------------------------------------------ #
    # persistence helpers
    # ------------------------------------------------------------------ #
    def _row_id(self, key: str) -> str:
        return f"{self.domain}:{self.kind}:{self.tenant_id}:{key}"

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
                self._cache[row.record_key] = self._decode(payload)
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

    def _decode(self, payload: Dict[str, Any]) -> Any:
        if self._decoder is not None:
            return self._decoder(payload)
        if set(payload.keys()) == {"__value__"}:
            return payload["__value__"]
        return payload

    def _persist(self, key: str, value: Any) -> None:
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
                    record_key=key,
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

    def _delete(self, key: str) -> None:
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
    def __getitem__(self, key: str) -> Any:
        return self._cache[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._persist(key, value)
        self._cache[key] = value

    def __delitem__(self, key: str) -> None:
        if key not in self._cache:
            raise KeyError(key)
        self._delete(key)
        del self._cache[key]

    def __iter__(self) -> Iterator[str]:
        return iter(list(self._cache.keys()))

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: object) -> bool:
        return key in self._cache

    def clear(self) -> None:  # type: ignore[override]
        for key in list(self._cache.keys()):
            self._delete(key)
        self._cache.clear()

    def flush(self, key: Optional[str] = None) -> None:
        """Re-persist entries after in-place mutation.

        ``store["id"]["status"] = "done"`` mutates the cached object without
        going through ``__setitem__``.  Call ``store.flush("id")`` (or
        ``store.flush()`` for the whole store) to write those changes back.
        """
        if key is None:
            for k, value in list(self._cache.items()):
                self._persist(k, value)
        else:
            self._persist(key, self._cache[key])

    def as_dict(self) -> Dict[str, Any]:
        """Return a plain ``dict`` copy (used by response models)."""
        return dict(self._cache)

    def values_list(self) -> List[Any]:
        return list(self._cache.values())
