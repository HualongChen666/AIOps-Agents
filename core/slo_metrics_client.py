# -*- coding: utf-8 -*-
"""SLO metric client adapters.

Provides a pluggable ``MetricsClient`` abstraction for fetching time-series
samples used by the SLA/SLO engine.  Two built-in implementations are included:

* ``LocalMetricsHistoryAdapter`` - reads from the in-memory ``MetricsHistory``.
* ``VictoriaMetricsClient`` - queries a VictoriaMetrics / Prometheus endpoint.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricPoint:
    """A single time-series sample."""

    timestamp: datetime
    value: float


class MetricsClient(ABC):
    """Abstract client for fetching SLO time-series data."""

    @abstractmethod
    def query_time_series(
        self,
        metric: str,
        service: str,
        start: datetime,
        end: datetime,
    ) -> list[MetricPoint]:
        """Return metric samples for ``service`` between ``start`` and ``end``."""
        raise NotImplementedError


def _to_naive(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to a naive UTC datetime."""
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class LocalMetricsHistoryAdapter(MetricsClient):
    """Adapter that reads time-series samples from ``core.metrics_history``."""

    def __init__(self, history: Any = None) -> None:
        if history is None:
            from core.metrics_history import METRICS_HISTORY as metrics_history

            history = metrics_history
        self._history = history

    def query_time_series(
        self,
        metric: str,
        service: str,
        start: datetime,
        end: datetime,
    ) -> list[MetricPoint]:
        """Fetch samples from the local in-memory metric history.

        ``metrics_history`` currently exposes ``to_dict()`` rather than a
        dedicated ``query()`` method, so this adapter builds ``MetricPoint``
        objects from that snapshot.
        """
        raw = self._history.to_dict()
        values = raw.get(metric, [])
        timestamps = raw.get("timestamps", [])

        if len(values) != len(timestamps):
            logger.warning(
                "LocalMetricsHistoryAdapter: mismatched lengths for metric %r "
                "(values=%d, timestamps=%d)",
                metric,
                len(values),
                len(timestamps),
            )
            return []

        start_n = _to_naive(start)
        end_n = _to_naive(end)

        points: list[MetricPoint] = []
        for ts_raw, val in zip(timestamps, values):
            ts = _parse_local_timestamp(ts_raw)
            if ts is None:
                continue
            if start_n <= ts <= end_n:
                try:
                    points.append(MetricPoint(timestamp=ts, value=float(val)))
                except (TypeError, ValueError):
                    continue
        return points


def _parse_local_timestamp(ts_raw: Any) -> datetime | None:
    """Best-effort parse of a timestamp emitted by ``MetricsHistory``."""
    if isinstance(ts_raw, datetime):
        return _to_naive(ts_raw)
    if not isinstance(ts_raw, str) or not ts_raw:
        return None
    ts_raw = ts_raw.strip()
    try:
        t = datetime.strptime(ts_raw, "%H:%M:%S").time()
        return datetime.combine(date.today(), t)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_raw, fmt)
        except ValueError:
            continue
    return None


class VictoriaMetricsClient(MetricsClient):
    """Sync VictoriaMetrics / Prometheus query_range client."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        step: int = 60,
    ) -> None:
        if base_url is None:
            try:
                from config import VICTORIAMETRICS_URL

                base_url = VICTORIAMETRICS_URL
            except Exception:
                base_url = "http://localhost:8428"
        if timeout is None:
            try:
                from config import VICTORIAMETRICS_TIMEOUT

                timeout = VICTORIAMETRICS_TIMEOUT
            except Exception:
                timeout = 30

        self.base_url = str(base_url).rstrip("/")
        self.timeout = int(timeout)
        self.step = int(step)

    def query_time_series(
        self,
        metric: str,
        service: str,
        start: datetime,
        end: datetime,
    ) -> list[MetricPoint]:
        """Query VictoriaMetrics ``/api/v1/query_range`` for a metric series."""
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            logger.warning("requests not installed, VictoriaMetrics client disabled: %s", exc)
            return []

        promql = f'{metric}{{service="{_escape_label(service)}"}}'
        params = {
            "query": promql,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": self.step,
        }

        try:
            # Use environment variable to control SSL verification (default: True for security)
            ssl_verify = os.environ.get("SLO_METRICS_SSL_VERIFY", "true").lower() == "true"
            if not ssl_verify:
                logger.warning(
                    "SSL verification is disabled in slo_metrics_client - this is a security risk!"
                )
            response = requests.get(
                f"{self.base_url}/api/v1/query_range",
                params=params,
                timeout=self.timeout,
                verify=ssl_verify,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("VictoriaMetrics query failed: %s", exc)
            return []

        if data.get("status") != "success":
            logger.warning("VictoriaMetrics query returned non-success: %s", data)
            return []

        return _parse_matrix(data.get("data", {}).get("result", []))


def _escape_label(value: str) -> str:
    """Escape a label value for PromQL double-quoted strings."""
    value = value.replace("\\", "\\\\")
    return value.replace('"', '\\"')


def _parse_matrix(result: list[dict[str, Any]]) -> list[MetricPoint]:
    """Convert a Prometheus / VictoriaMetrics matrix response to ``MetricPoint``s."""
    points: list[MetricPoint] = []
    for series in result:
        values = series.get("values")
        if values is None and "value" in series:
            values = [series.get("value")]
        if not values:
            continue
        for entry in values:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue
            ts_raw, val_raw = entry[0], entry[1]
            try:
                ts = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc)
                val = float(val_raw)
            except (TypeError, ValueError):
                continue
            points.append(MetricPoint(timestamp=ts, value=val))
    return points
