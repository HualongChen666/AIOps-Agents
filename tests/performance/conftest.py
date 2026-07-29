# -*- coding: utf-8 -*-
"""Performance test fixtures and helpers.

Provides an isolated ASGI client with a lightweight `/api/test` endpoint
and disables the production rate limiter so performance assertions are
not affected by 429 responses.
"""

from typing import Any

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def performance_app() -> FastAPI:
    """Wrap the real app with a test-only `/api/test` echo endpoint."""
    from main import app as real_app

    wrapper = FastAPI()

    @wrapper.get("/api/test")
    async def test_get() -> dict[str, Any]:
        """Return a 1KB payload for download/throughput tests."""
        return {"data": "x" * 1024}

    @wrapper.post("/api/test")
    async def test_post(request: Request) -> Any:
        """Echo JSON payload for upload/serialization tests."""
        return await request.json()

    wrapper.mount("/", real_app)
    return wrapper


@pytest.fixture
async def client(performance_app: FastAPI) -> AsyncClient:
    """Async test client using the wrapped performance app."""
    async with AsyncClient(
        transport=ASGITransport(app=performance_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def disable_rate_limit():
    """Disable the global rate limiter for all performance tests."""
    import core.security_middleware as sm

    original = sm.rate_limiter.check_rate_limit
    sm.rate_limiter.check_rate_limit = lambda client_id: (True, None)
    yield
    sm.rate_limiter.check_rate_limit = original
