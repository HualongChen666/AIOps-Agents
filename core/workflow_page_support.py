# -*- coding: utf-8 -*-
"""Shared helpers for the workflow-page backend routers.

The ``frontend/app/workflow/*`` pages each talk to a dedicated ``/api/v1/...``
domain.  Those domains share a handful of cross-cutting concerns (tenant
scoping, id/timestamp formatting, cron next-run computation, durable document
storage, CSV/PNG export).  Rather than duplicating that glue in every router,
this module centralises it so each router only owns its *business* logic.

Everything here is a real, side-effect-honest helper:

* :func:`get_store` / :func:`get_list_store` return
  :class:`core.persistent_store.PersistentStore` instances that durably persist
  to the ``persistent_records`` table.
* :func:`next_cron_run` uses :class:`apscheduler.triggers.cron.CronTrigger` —
  the same scheduler engine used by :mod:`core.task_scheduler` — so the "next
  run" column on the task-scheduler page is derived, never fabricated.
* :func:`paginate` / :func:`apply_filters` implement the query semantics the
  list pages rely on.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Iterator, Optional
from uuid import uuid4

from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from core.persistent_store import PersistentList, PersistentStore

# Default tenant scope used whenever a request carries no tenant context.
DEFAULT_TENANT = "default"

# All workflow-page entities live under this store domain.
STORE_DOMAIN = "workflow_pages"


# --------------------------------------------------------------------------- #
# Tenant / id / time helpers
# --------------------------------------------------------------------------- #
def tenant_of(request: Any) -> str:
    """Return the caller's tenant id (``"default"`` when absent)."""
    state = getattr(request, "state", None)
    tenant = getattr(state, "tenant_id", None)
    return str(tenant) if tenant else DEFAULT_TENANT


def get_store(
    request: Any,
    kind: str,
    *,
    domain: str = STORE_DOMAIN,
    key_type: Callable[[Any], Any] = str,
) -> PersistentStore:
    """Return a fresh tenant-scoped :class:`PersistentStore` for ``kind``.

    A new instance is created per call (it rehydrates from the database) so
    concurrent requests never observe a stale in-process cache.
    """
    return PersistentStore(domain, kind, tenant_id=tenant_of(request), key_type=key_type)


def get_list_store(
    request: Any,
    kind: str,
    *,
    domain: str = STORE_DOMAIN,
) -> PersistentList:
    """Return a fresh tenant-scoped :class:`PersistentList` for ``kind``."""
    return PersistentList(domain, kind, tenant_id=tenant_of(request))


def new_id(prefix: str) -> str:
    """Return a collision-resistant entity id such as ``playbook-1a2b3c4d5e6f``."""
    return f"{prefix}-{uuid4().hex[:12]}"


def slugify(value: str, *, fallback: str = "item") -> str:
    """Lower-case ASCII slug used for human-readable identifiers."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or fallback


def utcnow() -> datetime:
    """Timezone-aware UTC ``datetime``."""
    return datetime.now(timezone.utc)


def iso_now() -> str:
    """Current UTC timestamp as an ISO-8601 string."""
    return utcnow().isoformat()


def to_iso(value: Any) -> Optional[str]:
    """Best-effort ISO-8601 rendering of a datetime / date / str value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, str):
        return value
    # date and anything else that has isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


# --------------------------------------------------------------------------- #
# Cron
# --------------------------------------------------------------------------- #
def next_cron_run(
    expression: str,
    *,
    base: Optional[datetime] = None,
    tz: str = "UTC",
) -> Optional[str]:
    """Return the next fire time (ISO-8601) for a standard 5-field cron string.

    Returns ``None`` for an unparseable expression so the caller can surface a
    validation error instead of silently inventing a timestamp.
    """
    expression = (expression or "").strip()
    if not expression:
        return None
    try:
        trigger = CronTrigger.from_crontab(expression, timezone=tz)
    except (ValueError, TypeError):
        return None
    reference = base or datetime.now(timezone.utc)
    try:
        fire_time = trigger.get_next_fire_time(None, reference)
    except Exception:  # pragma: no cover - defensive against tz misconfig
        return None
    if fire_time is None:
        return None
    return fire_time.isoformat()


def is_valid_cron(expression: str) -> bool:
    """True when *expression* is a valid 5-field cron string."""
    expression = (expression or "").strip()
    if not expression:
        return False
    try:
        CronTrigger.from_crontab(expression)
        return True
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# Filtering / pagination
# --------------------------------------------------------------------------- #
def apply_filters(
    items: Iterable[dict],
    filters: Iterable[tuple[str, Callable[[Any], bool]]],
) -> list[dict]:
    """Apply ``(field, predicate)`` pairs; ``None`` predicate values are skipped.

    ``field`` is looked up on each item with ``dict.get`` — callers pass the
    value they want compared via the predicate closure.
    """
    result = list(items)
    for field, predicate in filters:
        result = [item for item in result if predicate(item.get(field))]
    return result


def paginate(items: list[dict], *, offset: int = 0, limit: Optional[int] = None) -> list[dict]:
    """Slice *items* honouring a non-negative offset and optional limit."""
    offset = max(0, int(offset or 0))
    if limit is None:
        return items[offset:]
    return items[offset : offset + max(0, int(limit))]


# --------------------------------------------------------------------------- #
# Export helpers
# --------------------------------------------------------------------------- #
def rows_to_csv(rows: list[dict], header: Optional[list[str]] = None) -> str:
    """Serialise *rows* to CSV text (used by the export buttons)."""
    if header is None:
        header = list(rows[0].keys()) if rows else []
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def csv_rows(items: Iterable[dict], columns: Iterable[str]) -> Iterator[dict]:
    """Project each item to just *columns* (missing values become ``""``)."""
    cols = list(columns)
    for item in items:
        yield {col: item.get(col, "") for col in cols}
