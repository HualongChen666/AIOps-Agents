# -*- coding: utf-8 -*-
"""Tests for core/error_handling.py."""

from fastapi import status

from core.error_handling import (
    AIEngineError,
    AIOpsException,
    AIOpsHTTPException,
    AuthenticationError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    create_error_response,
    handle_aiops_exception,
    handle_generic_exception,
    log_error,
)


def test_exceptions():
    assert str(AIOpsException("msg")) == "msg"
    exc = AIOpsHTTPException("not found", status_code=status.HTTP_404_NOT_FOUND)
    assert exc.status_code == 404
    assert isinstance(ValidationError("bad"), AIOpsException)
    assert isinstance(NotFoundError("x"), AIOpsException)
    assert isinstance(PermissionDeniedError("x"), AIOpsException)
    assert isinstance(AIEngineError("x"), AIOpsException)
    assert isinstance(DatabaseError("x"), AIOpsException)
    assert isinstance(AuthenticationError("x"), AIOpsException)


def test_handlers():
    exc = AIOpsException("boom")
    response = handle_aiops_exception(exc)
    assert "error_code" in response
    assert response["message"] == "boom"

    generic = handle_generic_exception(ValueError("bad"))
    assert "error_type" in generic["details"]

    resp = create_error_response(ErrorCode.INVALID_REQUEST, "detail", status_code=400)
    assert resp.status_code == 400

    log_error(ErrorCode.INTERNAL_ERROR, "test error")
