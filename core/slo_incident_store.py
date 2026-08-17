# -*- coding: utf-8 -*-
"""In-memory incident store and downtime calculator for SLA reporting."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Incident:
    """A service incident with a start/end window and a severity label."""

    service: str
    start: datetime
    end: datetime
    severity: str


# Global in-memory incident store.  A real deployment would replace this with a
# persistence-backed store (e.g. core.repositories.alert_repository).
_incidents: list[Incident] = []


def add_incident(service: str, start: datetime, end: datetime, severity: str) -> Incident:
    """Register a new incident in the global in-memory store."""
    incident = Incident(service=service, start=start, end=end, severity=severity)
    _incidents.append(incident)
    logger.debug("Recorded incident for %s from %s to %s", service, start, end)
    return incident


def list_incidents(service: str | None = None) -> list[Incident]:
    """Return all recorded incidents, optionally filtered by service."""
    if service is None:
        return list(_incidents)
    return [inc for inc in _incidents if inc.service == service]


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize a datetime to a naive UTC value for comparisons."""
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _overlapping_interval(
    inc: Incident, start: datetime, end: datetime
) -> tuple[datetime, datetime] | None:
    """Return the overlap between an incident and the query window, if any."""
    a = _to_naive_utc(inc.start)
    b = _to_naive_utc(inc.end)
    lo = _to_naive_utc(start)
    hi = _to_naive_utc(end)

    if b <= lo or a >= hi:
        return None
    return (max(a, lo), min(b, hi))


def compute_downtime(service: str, start: datetime, end: datetime) -> float:
    """Sum the overlapping incident durations (in seconds) for ``service``.

    Overlapping incidents are merged so that the same wall-clock period is not
    counted twice.  If the store is empty or there are no overlapping incidents,
    ``0.0`` is returned.
    """
    if not _incidents or start >= end:
        return 0.0

    intervals: list[tuple[datetime, datetime]] = []
    for inc in _incidents:
        if inc.service != service:
            continue
        overlap = _overlapping_interval(inc, start, end)
        if overlap is not None:
            intervals.append(overlap)

    if not intervals:
        return 0.0

    intervals.sort(key=lambda pair: pair[0])
    merged: list[tuple[datetime, datetime]] = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1]:
            # Extend the previous interval if it overlaps the current one.
            prev_lo, prev_hi = merged[-1]
            merged[-1] = (prev_lo, max(prev_hi, hi))
        else:
            merged.append((lo, hi))

    total = sum((hi - lo).total_seconds() for lo, hi in merged)
    return float(total)
