# -*- coding: utf-8 -*-
"""Tests for core/type_validation.py."""

import pytest

from core.type_validation import (
    RuntimeTypeValidator,
    TypeSafeAPI,
    TypeValidationError,
    get_dict_type,
    get_list_type,
    get_optional_type,
    sanitize_response,
    validate_request,
    validate_return_type,
    validate_types,
)


def test_validate_type_basic():
    assert RuntimeTypeValidator.validate_type(5, int) == 5
    assert RuntimeTypeValidator.validate_type("x", str) == "x"
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("5", int)


def test_validate_optional():
    assert RuntimeTypeValidator.validate_type(None, get_optional_type(str)) is None


def test_validate_collection():
    assert RuntimeTypeValidator.validate_type([1, 2], get_list_type(int)) == [1, 2]
    assert RuntimeTypeValidator.validate_type({"a": 1}, get_dict_type(str, int)) == {"a": 1}
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type(["x"], get_list_type(int))


def test_validate_types_decorator():
    @validate_types(name=str, age=int)
    def greet(name, age):
        return f"{name} is {age}"

    assert greet("alice", 30) == "alice is 30"
    with pytest.raises(TypeValidationError):
        greet("alice", "30")


def test_validate_return_type():
    @validate_return_type(int)
    def get_number():
        return 42

    assert get_number() == 42

    @validate_return_type(str)
    def bad():
        return 123

    with pytest.raises(TypeValidationError):
        bad()


def test_validate_request_data():
    data = {"name": "alice", "age": 30}
    schema = {"name": str, "age": int}
    assert TypeSafeAPI.validate_request_data(data, schema) == data
    with pytest.raises(TypeValidationError):
        TypeSafeAPI.validate_request_data({"name": "alice"}, schema)


def test_sanitize_response_data():
    from datetime import datetime, timezone

    sanitized = TypeSafeAPI.sanitize_response_data(
        {
            "created": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "items": [1, 2],
        }
    )
    assert isinstance(sanitized["created"], str)
    assert sanitized["items"] == [1, 2]


@pytest.mark.asyncio
async def test_validate_request_and_sanitize_response_decorators():
    @validate_request({"x": int})
    @sanitize_response
    async def handler(data):
        return {"x": data["x"] * 2}

    result = await handler({"x": 5})
    assert result == {"x": 10}
