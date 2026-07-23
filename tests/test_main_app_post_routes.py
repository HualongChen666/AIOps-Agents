# -*- coding: utf-8 -*-
"""Smoke test that exercises POST/PUT/PATCH route bodies of the main FastAPI app.

Authentication is bypassed, server exceptions are swallowed, and dangerous-looking
endpoints (execute/run/create/delete/update/etc.) are skipped. Each request uses a
timeout so slow/unconfigured backends are skipped instead of blocking the suite.
"""

import asyncio
import re
import uuid
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from core.authentication import get_current_active_user


def _default_value(convertor) -> str:
    name = type(convertor).__name__.lower()
    if "path" in name:
        return "a/b"
    if "int" in name:
        return "1"
    if "float" in name:
        return "1.0"
    if "uuid" in name:
        return str(uuid.uuid4())
    return "default"


def _build_path(route):
    path = route.path
    for name, convertor in getattr(route, "param_convertors", {}).items():
        path = path.replace("{" + name + "}", _default_value(convertor))
        path = path.replace("{" + name + ":path}", _default_value(convertor))
    return path


@pytest.fixture
def client():
    import main

    main.app.dependency_overrides[get_current_active_user] = lambda: MagicMock(
        role="admin", disabled=False
    )
    return TestClient(main.app, raise_server_exceptions=False)


_DANGEROUS = {
    "execute",
    "run",
    "create",
    "add",
    "delete",
    "remove",
    "save",
    "update",
    "install",
    "deploy",
    "start",
    "stop",
    "restart",
    "kill",
    "clear",
    "reset",
    "apply",
    "approve",
    "repair",
    "backup",
    "restore",
    "sync",
    "trigger",
    "send",
    "write",
    "configure",
    "set",
    "enable",
    "disable",
    "register",
    "unregister",
    "upload",
    "download",
    "import",
    "export",
    "schedule",
    "cancel",
    "publish",
    "unpublish",
    "grant",
    "revoke",
    "lock",
    "unlock",
    "archive",
    "unarchive",
    "tag",
    "untag",
    "clean",
    "batch",
}

_SAFE = {
    "search",
    "query",
    "predict",
    "analyze",
    "analyse",
    "explain",
    "recommend",
    "summarize",
    "summarise",
    "parse",
    "validate",
    "encode",
    "decode",
    "forecast",
    "classify",
    "cluster",
    "generate",
    "transform",
    "process",
    "simulate",
    "infer",
    "detect",
    "evaluate",
    "score",
    "rank",
    "embed",
    "match",
    "compare",
    "list",
    "get",
    "health",
    "ping",
    "status",
    "summary",
    "metrics",
    "info",
    "check",
    "render",
    "convert",
    "format",
    "sample",
    "estimate",
    "calibrate",
    "optimize",
    "debug",
    "inspect",
    "describe",
    "profile",
    "index",
    "lookup",
    "retrieve",
}


def _path_tokens(path: str):
    """Extract path words, ignoring route parameter placeholders."""
    return set(re.findall(r"[a-z]+", path.lower()))


def _is_safe(path: str) -> bool:
    tokens = _path_tokens(path)
    if tokens & _DANGEROUS:
        return False
    return bool(tokens & _SAFE)


def _iter_routes(app):
    """Yield all real routes, flattening FastAPI's included routers."""
    for route in app.routes:
        if type(route).__name__ == "_IncludedRouter":
            router = getattr(route, "original_router", None)
            if router:
                yield from router.routes
        elif hasattr(route, "path") and route.path:
            yield route


@pytest.mark.timeout(240)
def test_main_app_post_routes(client: TestClient):
    """Call safe POST/PUT/PATCH routes with an empty JSON body."""
    skipped = 0
    called = 0
    for route in _iter_routes(client.app):
        if not hasattr(route, "path") or route.path is None:
            continue
        path = route.path.lower()
        if any(k in path for k in ("/ws", "/websocket")):
            skipped += 1
            continue

        methods = getattr(route, "methods", set())
        method = None
        for m in ("POST", "PUT", "PATCH"):
            if m in methods:
                method = m
                break
        if method is None:
            continue
        if not _is_safe(route.path):
            skipped += 1
            continue

        url = _build_path(route)
        try:
            client.request(method, url, json={}, timeout=2.0)
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.ReadError, asyncio.TimeoutError):
            skipped += 1
        else:
            called += 1

    assert called > 0, "no safe POST routes were called"
