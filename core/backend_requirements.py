# -*- coding: utf-8 -*-
"""Backend-requirement signalling helpers.

A number of API endpoints can only produce *meaningful* results when an
external backend is available: a cloud billing API, a Prometheus / Loki /
Tempo / Elasticsearch server, a remote host agent, a package registry, etc.

Historically those endpoints fabricated a plausible-looking number (a random
latency, a hard-coded cost, a made-up accuracy score) or slept to fake success.
That is unacceptable: it hides outages and produces un-actionable data.

Instead, an endpoint that cannot produce a real answer because its backend is
missing must say so explicitly, using the canonical marker string
``requires-backend`` carried in the ``detail`` payload of an HTTP 503 response
returned by :func:`requires_backend`.

The marker is intentionally machine-readable so clients (and the frontend) can
distinguish "no data because nothing is deployed" from "an error happened".
"""

from __future__ import annotations

from typing import Any, NoReturn, Optional

from fastapi import HTTPException, status

#: Canonical marker string returned in the ``error`` field of the detail body.
REQUIRES_BACKEND = "requires-backend"


def backend_required_detail(
    backend: str,
    *,
    capability: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Build the structured 503 ``detail`` payload for a missing backend."""
    detail: dict[str, Any] = {
        "error": REQUIRES_BACKEND,
        "backend": backend,
        "reason": reason or f"'{backend}' backend is not configured in this deployment",
    }
    if capability:
        detail["capability"] = capability
    return detail


def requires_backend(
    backend: str,
    *,
    capability: Optional[str] = None,
    reason: Optional[str] = None,
) -> NoReturn:
    """Raise an HTTP 503 that explicitly signals a required, missing backend."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=backend_required_detail(backend, capability=capability, reason=reason),
    )


def is_requires_backend(payload: Any) -> bool:
    """Return ``True`` when ``payload`` is a ``requires-backend`` marker body."""
    return isinstance(payload, dict) and payload.get("error") == REQUIRES_BACKEND


__all__ = [
    "REQUIRES_BACKEND",
    "backend_required_detail",
    "requires_backend",
    "is_requires_backend",
]
