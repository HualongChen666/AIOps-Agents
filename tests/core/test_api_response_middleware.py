# -*- coding: utf-8 -*-
"""Tests for core/api_response_middleware.py."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from core.api_response_middleware import (
    APIResponseMiddleware,
    setup_api_response_middleware,
)


def test_setup_api_response_middleware():
    app = FastAPI()

    @app.get("/api/test")
    def test_endpoint():
        return {"key": "value"}

    @app.get("/api/raw")
    def raw_endpoint():
        return JSONResponse(content={"data": 1})

    setup_api_response_middleware(app)
    client = TestClient(app)
    resp = client.get("/api/test")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)

    raw = client.get("/api/raw")
    assert raw.status_code == 200
    assert isinstance(raw.json(), dict)


def test_exclude_paths():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    app.add_middleware(APIResponseMiddleware)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
