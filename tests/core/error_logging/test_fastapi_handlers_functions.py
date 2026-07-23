# -*- coding: utf-8 -*-
"""Targeted tests for core.error_logging.fastapi_handlers."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from core.error_logging.fastapi_handlers import (
    ai_model_exception_handler,
    authentication_exception_handler,
    authorization_exception_handler,
    database_exception_handler,
    external_service_exception_handler,
    generic_exception_handler,
    network_exception_handler,
    permission_denied_exception_handler,
    quota_exceeded_exception_handler,
    resource_not_found_exception_handler,
    setup_exception_handlers,
    system_fatal_exception_handler,
    validation_exception_handler,
    version_mismatch_exception_handler,
)
from core.exceptions import (
    AIModelException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    ExternalServiceException,
    NetworkException,
    PermissionDeniedException,
    QuotaExceededException,
    ResourceNotFoundException,
    SystemFatalException,
    ValidationException,
    VersionMismatchException,
)


@pytest.fixture
def request_fixture() -> Request:
    return MagicMock(spec=Request)


@pytest.fixture(autouse=True)
def _noop_log_exception(monkeypatch) -> None:
    """Disable structured logging during handler tests."""
    monkeypatch.setattr("core.error_logging.logger.log_exception", lambda *a, **k: None)


HANDLERS = [
    (validation_exception_handler, ValidationException("invalid"), 400),
    (resource_not_found_exception_handler, ResourceNotFoundException("missing"), 404),
    (authentication_exception_handler, AuthenticationException("unauth"), 401),
    (authorization_exception_handler, AuthorizationException("forbidden"), 403),
    (permission_denied_exception_handler, PermissionDeniedException("denied"), 403),
    (database_exception_handler, DatabaseException("db error"), 500),
    (network_exception_handler, NetworkException("network error"), 502),
    (external_service_exception_handler, ExternalServiceException("ext error"), 502),
    (ai_model_exception_handler, AIModelException("ai error"), 500),
    (quota_exceeded_exception_handler, QuotaExceededException("quota"), 429),
    (version_mismatch_exception_handler, VersionMismatchException("version"), 409),
    (system_fatal_exception_handler, SystemFatalException("fatal"), 503),
    (generic_exception_handler, RuntimeError("generic"), 500),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("handler,exc,expected_status", HANDLERS)
async def test_exception_handlers(handler, exc, expected_status, request_fixture) -> None:
    response = await handler(request_fixture, exc)
    assert response.status_code == expected_status
    assert "error_code" in response.body.decode()


def test_setup_exception_handlers() -> None:
    app = MagicMock()
    setup_exception_handlers(app)
    assert app.add_exception_handler.call_count == len(HANDLERS)
