# -*- coding: utf-8 -*-
"""
Observability query guardrail utilities.

Provides reusable safety primitives for querying Prometheus/VictoriaMetrics,
Elasticsearch, Loki, Tempo, ClickHouse and Kubernetes API data sources before
feeding results to an LLM:

- timeouts / concurrency / cache / fallback
- query validation and parameterization helpers
- PII redaction and token-aware truncation for LLM prompts
- time window alignment with scrape/index delay offset
"""

import asyncio
import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

MAX_QUERY_TIMEOUT = 30.0
DEFAULT_MAX_CONCURRENT_QUERIES = 10
DEFAULT_CACHE_TTL_SECONDS = 60.0
DEFAULT_MAX_LLM_TOKENS = 12000
DEFAULT_MAX_LLM_ITEMS = 1000
DEFAULT_MAX_PROMQL_SAMPLES = 40320  # 7 days @ 15s
DEFAULT_MAX_ES_HITS = 1000
DEFAULT_MAX_K8S_OBJECTS = 1000
DEFAULT_LATENCY_OFFSET_SECONDS = 30.0

SQL_KEYWORDS = {
    "union",
    "drop",
    "delete",
    "insert",
    "update",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
}
SQL_KEYWORDS_RE = re.compile(r"\b(" + "|".join(SQL_KEYWORDS) + r")\b", re.IGNORECASE)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Character allow-lists for simple syntax-aware validation.
PROMQL_ALLOWED = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "_:.,+-*/%=<>|&(){}[]\"'~` \t\n\r"
)
LOGQL_ALLOWED = set(PROMQL_ALLOWED) | {"|"}
ES_ALLOWED = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" "_:.,+-*?\"'()|&![]{}<> \t\n\r"
)

SENSITIVE_KEY_RE = re.compile(
    r"password|passwd|token|secret|api_?key|access_?key|private_?key|credential|auth",
    re.IGNORECASE,
)
SENSITIVE_PAIR_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api_?key|access_?key|private_?key|credential|auth)\b\s*[:=]\s*[^\s,;]+",  # noqa: E501
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?86)?1[3-9]\d{9}(?!\d)")
ID_RE = re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_query_semaphore: Optional[asyncio.Semaphore] = None


def get_query_semaphore(max_concurrent: int = DEFAULT_MAX_CONCURRENT_QUERIES) -> asyncio.Semaphore:
    """Return a shared observability query semaphore (lazy init)."""
    global _query_semaphore
    if _query_semaphore is None:
        _query_semaphore = asyncio.Semaphore(max_concurrent)
    return _query_semaphore


class QueryCache:
    """Simple in-memory TTL cache for observability query results."""

    def __init__(self, ttl: float = DEFAULT_CACHE_TTL_SECONDS, max_size: int = 1000):
        self.ttl = ttl
        self.max_size = max_size
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._order: List[str] = []

    def _delete(self, key: str) -> None:
        self._store.pop(key, None)
        if key in self._order:
            self._order.remove(key)

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        if key not in self._store:
            return None, False
        value, ts = self._store[key]
        if time.monotonic() - ts > self.ttl:
            self._delete(key)
            return None, False
        return value, True

    def set(self, key: str, value: Any) -> None:
        now = time.monotonic()
        if key in self._store:
            self._delete(key)
        while len(self._order) >= self.max_size:
            oldest = self._order.pop(0)
            self._delete(oldest)
        self._store[key] = (value, now)
        self._order.append(key)

    def clear(self) -> None:
        self._store.clear()
        self._order.clear()


def make_cache_key(*parts: Any) -> str:
    """Build a deterministic cache key from arbitrary parts."""
    payload = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


async def with_query_concurrency(coro):
    """Run a coroutine under the shared observability query semaphore."""
    async with get_query_semaphore():
        return await coro


async def with_query_timeout(coro, timeout: float = MAX_QUERY_TIMEOUT):
    """Wrap a coroutine in a hard timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)


async def cached_query(
    cache: QueryCache,
    key: str,
    coro,
    *,
    ttl: Optional[float] = None,
) -> Any:
    """
    Return cached value if fresh; otherwise run ``coro`` with concurrency guard
    and cache the result. On failure, return a stale cached value if available
    and annotate it with ``_stale=True``.
    """
    cached, ok = cache.get(key)
    if ok:
        logger.debug("observability cache hit | key=%s", key)
        return cached

    try:
        result = await with_query_concurrency(coro)
    except Exception as exc:
        cached, ok = cache.get(key)
        if ok:
            logger.warning(
                "observability query failed, returning stale cached result | key=%s error=%s",
                key,
                exc,
            )
            if isinstance(cached, dict):
                cached = {**cached, "_stale": True}
            elif isinstance(cached, list):
                cached = {"_stale": True, "_partial": cached}
            return cached
        raise

    if ttl is None:
        ttl = cache.ttl
    cache.set(key, result)
    return result


def _raise_if_disallowed(query: str, label: str) -> None:
    if not query or not isinstance(query, str):
        raise ValueError(f"{label} must be a non-empty string")
    if len(query) > 2000:
        raise ValueError(f"{label} too long (max 2000 characters)")
    if CONTROL_CHAR_RE.search(query):
        raise ValueError(f"{label} contains control characters")
    if "--" in query or ";" in query or "/*" in query or "*/" in query:
        raise ValueError(f"{label} contains comment or statement separator characters")
    if SQL_KEYWORDS_RE.search(query):
        raise ValueError(f"{label} contains SQL-like keywords")


def validate_promql(query: str) -> None:
    """Validate a PromQL string against a safe character set."""
    _raise_if_disallowed(query, "PromQL query")
    bad_chars = {c for c in query if c not in PROMQL_ALLOWED}
    if bad_chars:
        raise ValueError(f"PromQL query contains invalid characters: {sorted(bad_chars)[:5]}")


def validate_logql(query: str) -> None:
    """Validate a LogQL string against a safe character set and balanced braces."""
    _raise_if_disallowed(query, "LogQL query")
    bad_chars = {c for c in query if c not in LOGQL_ALLOWED}
    if bad_chars:
        raise ValueError(f"LogQL query contains invalid characters: {sorted(bad_chars)[:5]}")
    if query.count("{") != query.count("}"):
        raise ValueError("LogQL query has unbalanced stream selector braces")


def validate_es_query_string(query: str) -> None:
    """Validate an Elasticsearch query_string query."""
    if not isinstance(query, str):
        raise ValueError("Elasticsearch query must be a string")
    if len(query) > 2000:
        raise ValueError("Elasticsearch query too long")
    if CONTROL_CHAR_RE.search(query):
        raise ValueError("Elasticsearch query contains control characters")
    if (
        ";" in query
        or "--" in query
        or "{" in query
        or "}" in query
        or "=" in query
        or "~" in query
        or "\\" in query
        or "^" in query
        or "$" in query
    ):
        raise ValueError("Elasticsearch query contains disallowed characters")
    if SQL_KEYWORDS_RE.search(query):
        raise ValueError("Elasticsearch query contains SQL-like keywords")
    bad_chars = {c for c in query if c not in ES_ALLOWED}
    if bad_chars:
        raise ValueError(
            f"Elasticsearch query contains invalid characters: {sorted(bad_chars)[:5]}"
        )


def validate_clickhouse_identifier(name: str) -> None:
    """Validate a ClickHouse database/table/column identifier."""
    if not name or not isinstance(name, str):
        raise ValueError("ClickHouse identifier required")
    if not re.fullmatch(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(f"Invalid ClickHouse identifier: {name}")


def validate_clickhouse_metric_name(metric_name: str) -> None:
    """Validate a metric name used in ClickHouse queries."""
    if not metric_name or not isinstance(metric_name, str):
        raise ValueError("Metric name required")
    if not re.fullmatch(r"^[A-Za-z_:][A-Za-z0-9_:.-]*$", metric_name):
        raise ValueError(f"Invalid metric name: {metric_name}")


def build_clickhouse_query(
    table: str,
    columns: List[str],
    where_columns: List[str],
    where_values: List[Any],
    order_by: str,
    limit: int = DEFAULT_MAX_LLM_ITEMS,
) -> Tuple[str, List[Any]]:
    """
    Build a parameterized ClickHouse SELECT query.

    Returns (sql_template_with_question_mark_placeholders, parameter_values).
    """
    validate_clickhouse_identifier(table)
    for col in columns + where_columns + [order_by]:
        validate_clickhouse_identifier(col)

    cols = ", ".join(columns)
    where_clauses = [f"{col} = ?" for col in where_columns]
    where_sql = " AND ".join(where_clauses) if where_clauses else "1 = 1"
    safe_limit = max(1, min(limit, DEFAULT_MAX_LLM_ITEMS))

    sql = " ".join(
        [
            "SELECT",
            cols,
            "FROM",
            table,
            "WHERE",
            where_sql,
            "ORDER BY",
            order_by,
            "LIMIT",
            str(safe_limit),
        ]
    )
    return sql, list(where_values)


def redact_text(value: str) -> str:
    """Redact sensitive tokens / PII in a single string."""
    if not isinstance(value, str):
        return value
    value = SENSITIVE_PAIR_RE.sub(lambda m: f"{m.group(1)}=<REDACTED>", value)
    value = EMAIL_RE.sub("<EMAIL_REDACTED>", value)
    value = PHONE_RE.sub("<PHONE_REDACTED>", value)
    value = ID_RE.sub("<ID_REDACTED>", value)
    value = IP_RE.sub("<IP_REDACTED>", value)
    return value


def _redact_recursive(obj: Any) -> Any:
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if isinstance(v, str):
                if SENSITIVE_KEY_RE.search(k):
                    result[k] = "<REDACTED>"
                else:
                    result[k] = redact_text(v)
            else:
                result[k] = _redact_recursive(v)
        return result
    if isinstance(obj, list):
        return [_redact_recursive(i) for i in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj


def approx_token_count(obj: Any) -> int:
    """Rough token count (characters / 4) for JSON-serializable objects."""
    try:
        text = json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(obj)
    return len(text) // 4 + 1


def _truncate(
    obj: Any,
    max_items: int,
    max_string_chars: int,
) -> Any:
    if isinstance(obj, dict):
        truncated = {}
        for idx, (k, v) in enumerate(obj.items()):
            if idx >= max_items:
                truncated["..."] = "<TRUNCATED>"
                break
            truncated[k] = _truncate(v, max_items, max_string_chars)
        return truncated
    if isinstance(obj, list):
        total = len(obj)
        if total > max_items:
            step = max(1, total // max_items)
            sampled = obj[::step][:max_items]
        else:
            sampled = obj
        return [_truncate(i, max_items, max_string_chars) for i in sampled]
    if isinstance(obj, str):
        if len(obj) > max_string_chars:
            return obj[:max_string_chars] + "...<TRUNCATED>"
        return obj
    return obj


def prepare_for_llm(
    data: Any,
    max_tokens: int = DEFAULT_MAX_LLM_TOKENS,
    max_items: int = DEFAULT_MAX_LLM_ITEMS,
) -> Any:
    """
    Redact PII and truncate ``data`` so it fits in an LLM context window.

    The result is annotated with ``_llm_meta`` containing approximate token
    count and a truncation flag.
    """
    redacted = _redact_recursive(data)

    current_max_items = max_items
    current_max_string = max_tokens * 4  # rough char budget for a single string
    truncated = redacted

    for _ in range(10):
        truncated = _truncate(redacted, current_max_items, current_max_string)
        if approx_token_count(truncated) <= max_tokens:
            break
        current_max_items = max(1, current_max_items // 2)
        current_max_string = max(20, current_max_string // 2)

    if isinstance(truncated, dict):
        truncated.setdefault("_llm_meta", {})
        truncated["_llm_meta"]["approx_tokens"] = approx_token_count(truncated)
        truncated["_llm_meta"]["truncated"] = approx_token_count(redacted) > max_tokens
        truncated["_llm_meta"]["redacted"] = True
    return truncated


def align_time_window(
    end: Optional[datetime] = None,
    duration_seconds: float = 3600.0,
    latency_offset_seconds: float = DEFAULT_LATENCY_OFFSET_SECONDS,
) -> Tuple[datetime, datetime]:
    """Return a (start, end) window with a latency offset applied to ``end``."""
    if end is None:
        end = datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    end = end - timedelta(seconds=latency_offset_seconds)
    start = end - timedelta(seconds=duration_seconds)
    return start, end


def parse_duration_to_seconds(value: Any) -> float:
    """Parse a duration string like '15s', '1m', '5h' to seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 60.0
    s = str(value).strip().lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    if s[-1] in multipliers:
        number_part = s[:-1]
        try:
            return float(number_part) * multipliers[s[-1]]
        except ValueError:
            return float(s)
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Invalid duration value: {value!r}")


def limit_range_samples(
    start: datetime,
    end: datetime,
    step_seconds: float,
    max_samples: int = DEFAULT_MAX_PROMQL_SAMPLES,
) -> float:
    """Coarsen ``step_seconds`` so the number of samples stays under ``max_samples``."""
    if step_seconds <= 0:
        step_seconds = 60.0
    span = (end - start).total_seconds()
    if span <= 0:
        return step_seconds
    needed = span / step_seconds
    if needed > max_samples:
        new_step = span / max_samples
        logger.warning(
            "step coarsened from %ss to %ss to keep samples under %s",
            step_seconds,
            new_step,
            max_samples,
        )
        return new_step
    return step_seconds


def sanitize_error_for_llm(exc: Exception) -> str:
    """Return a safe, non-verbose error message suitable for an LLM prompt."""
    return f"query_failed: {type(exc).__name__}"


def validate_tempoql(query: str) -> None:
    """Validate a Tempo trace query string using the same guard as LogQL."""
    validate_logql(query)
