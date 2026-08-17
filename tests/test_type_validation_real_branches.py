# -*- coding: utf-8 -*-
"""Branch-coverage tests for core/type_validation.py using real values."""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

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


# ---------------------------------------------------------------------------
# Real-world fixtures / data classes
# ---------------------------------------------------------------------------


class Color(Enum):
    RED = "red"
    GREEN = "green"


class Plain:
    """A non-dataclass used for the default validation fallback."""

    pass


@dataclass
class Inner:
    value: int


@dataclass
class Outer:
    inner: Inner
    label: Optional[str] = None


# ---------------------------------------------------------------------------
# validate_type -- basic types
# ---------------------------------------------------------------------------


def test_validate_type_int_valid_and_invalid():
    assert RuntimeTypeValidator.validate_type(5, int) == 5
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("5", int)


def test_validate_type_float_valid_and_invalid():
    assert RuntimeTypeValidator.validate_type(3.14, float) == 3.14
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type(3, float)


def test_validate_type_str_valid_and_invalid():
    assert RuntimeTypeValidator.validate_type("ok", str) == "ok"
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type(b"ok", str)


def test_validate_type_bool_edge():
    assert RuntimeTypeValidator.validate_type(True, bool) is True
    assert RuntimeTypeValidator.validate_type(False, bool) is False
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type(1, bool)


def test_validate_type_datetime_and_date():
    now = datetime.now(timezone.utc)
    assert RuntimeTypeValidator.validate_type(now, datetime) is now
    today = date.today()
    assert RuntimeTypeValidator.validate_type(today, date) is today
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("2026-01-01", datetime)
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("2026-01-01", date)


# ---------------------------------------------------------------------------
# validate_type -- Optional and None
# ---------------------------------------------------------------------------


def test_validate_type_optional_none():
    assert RuntimeTypeValidator.validate_type(None, get_optional_type(int)) is None


def test_validate_type_none_for_non_optional_raises():
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type(None, int)


def test_is_optional_type_variations():
    assert RuntimeTypeValidator._is_optional_type(get_optional_type(int)) is True
    assert RuntimeTypeValidator._is_optional_type(int) is False
    assert RuntimeTypeValidator._is_optional_type(Union[int, str]) is False
    assert RuntimeTypeValidator._is_optional_type(Union[int, None]) is True
    assert RuntimeTypeValidator._is_optional_type(type(None)) is True
    assert RuntimeTypeValidator.validate_type(None, type(None)) is None


# ---------------------------------------------------------------------------
# validate_type -- collections
# ---------------------------------------------------------------------------


def test_validate_type_list_valid_and_invalid():
    assert RuntimeTypeValidator.validate_type([1, 2, 3], get_list_type(int)) == [1, 2, 3]
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("not a list", get_list_type(int))
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type([1, "x"], get_list_type(int))


def test_validate_type_list_unparameterized():
    # Bare typing.List has no item type args; item validation is skipped.
    assert RuntimeTypeValidator.validate_type([1, "a", None], List) == [1, "a", None]


def test_validate_type_list_nested():
    nested = [[1, 2], [3, 4]]
    assert RuntimeTypeValidator.validate_type(nested, List[List[int]]) == nested
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type([[1, "x"]], List[List[int]])


def test_validate_type_dict_valid_and_invalid():
    assert RuntimeTypeValidator.validate_type({"a": 1, "b": 2}, Dict[str, int]) == {"a": 1, "b": 2}
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("not a dict", Dict[str, int])
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type({1: 1}, Dict[str, int])
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type({"a": "x"}, Dict[str, int])


def test_validate_type_dict_unparameterized():
    # Bare typing.Dict has no key/value type args; key/value validation is skipped.
    assert RuntimeTypeValidator.validate_type({1: "a"}, Dict) == {1: "a"}


def test_validate_type_dict_nested():
    data = {"x": {"a": 1}, "y": {"b": 2}}
    assert RuntimeTypeValidator.validate_type(data, Dict[str, Dict[str, int]]) == data


# ---------------------------------------------------------------------------
# validate_type -- dataclasses
# ---------------------------------------------------------------------------


def test_validate_type_dataclass_valid():
    inner = Inner(value=10)
    outer = Outer(inner=inner, label="test")
    assert RuntimeTypeValidator.validate_type(outer, Outer) is outer


def test_validate_type_dataclass_invalid_instance():
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type("not an outer", Outer)


def test_validate_type_dataclass_invalid_field():
    inner = Inner(value="not an int")
    outer = Outer(inner=inner)
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.validate_type(outer, Outer)


def test_validate_type_dataclass_missing_field():
    inner = Inner(value=10)
    # Delete the field so the hasattr branch is exercised.
    del inner.value
    # Should not raise because missing fields are skipped.
    RuntimeTypeValidator.validate_type(inner, Inner)


# ---------------------------------------------------------------------------
# validate_type -- default / unknown expected type
# ---------------------------------------------------------------------------


def test_validate_type_unknown_expected_type_returns_value():
    obj = Plain()
    assert RuntimeTypeValidator.validate_type(obj, Plain) is obj


# ---------------------------------------------------------------------------
# coerce_type
# ---------------------------------------------------------------------------


def test_coerce_type_int():
    assert RuntimeTypeValidator.coerce_type("42", int) == 42
    assert RuntimeTypeValidator.coerce_type(3.14, int) == 3
    assert RuntimeTypeValidator.coerce_type(7, int) == 7
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.coerce_type("abc", int)


def test_coerce_type_float():
    assert RuntimeTypeValidator.coerce_type("2.5", float) == 2.5
    assert RuntimeTypeValidator.coerce_type(5, float) == 5.0
    with pytest.raises(TypeValidationError):
        RuntimeTypeValidator.coerce_type("n/a", float)


def test_coerce_type_str():
    assert RuntimeTypeValidator.coerce_type(123, str) == "123"


def test_coerce_type_bool():
    assert RuntimeTypeValidator.coerce_type("true", bool) is True
    assert RuntimeTypeValidator.coerce_type("false", bool) is False
    assert RuntimeTypeValidator.coerce_type("yes", bool) is True
    assert RuntimeTypeValidator.coerce_type("on", bool) is True
    assert RuntimeTypeValidator.coerce_type("1", bool) is True
    assert RuntimeTypeValidator.coerce_type(1, bool) is True
    assert RuntimeTypeValidator.coerce_type(0, bool) is False


def test_coerce_type_none_and_fallback():
    assert RuntimeTypeValidator.coerce_type(None, int) is None
    obj = Plain()
    assert RuntimeTypeValidator.coerce_type(obj, Plain) is obj
    # Unknown target type with a value that is not an instance of it.
    assert RuntimeTypeValidator.coerce_type("something", Plain) == "something"


# ---------------------------------------------------------------------------
# validate_types decorator
# ---------------------------------------------------------------------------


def test_validate_types_positional_and_kwargs():
    @validate_types(a=int, c=str)
    def sample(a, b, c="default"):
        return (a, b, c)

    # a validated positionally, b has no hint, c supplied as kwarg.
    assert sample(1, 2, c="ok") == (1, 2, "ok")


def test_validate_types_invalid_positional():
    @validate_types(a=int)
    def sample(a):
        return a

    with pytest.raises(TypeValidationError):
        sample("not an int")


def test_validate_types_invalid_kwarg():
    @validate_types(name=str)
    def sample(name=""):
        return name

    with pytest.raises(TypeValidationError):
        sample(name=123)


def test_validate_types_kwarg_not_in_hints():
    @validate_types(a=int)
    def sample(a, b=0):
        return (a, b)

    # `b` is passed as a keyword but has no type hint, exercising the skip branch.
    assert sample(1, b=2) == (1, 2)


# ---------------------------------------------------------------------------
# validate_return_type decorator
# ---------------------------------------------------------------------------


def test_validate_return_type_valid_and_invalid():
    @validate_return_type(int)
    def good():
        return 42

    assert good() == 42

    @validate_return_type(str)
    def bad():
        return 123

    with pytest.raises(TypeValidationError):
        bad()


# ---------------------------------------------------------------------------
# TypeSafeAPI
# ---------------------------------------------------------------------------


def test_validate_request_data_valid_and_missing_and_invalid():
    schema = {"name": str, "count": int}
    data = {"name": "alice", "count": 3}
    assert TypeSafeAPI.validate_request_data(data, schema) == data

    with pytest.raises(TypeValidationError, match="Missing required field"):
        TypeSafeAPI.validate_request_data({"name": "alice"}, schema)

    with pytest.raises(TypeValidationError, match="Validation failed"):
        TypeSafeAPI.validate_request_data({"name": "alice", "count": "x"}, schema)


def test_validate_request_data_nested_collection():
    schema = {"items": List[int]}
    data = {"items": [1, 2, 3]}
    assert TypeSafeAPI.validate_request_data(data, schema) == data


def test_sanitize_response_data_dicts_lists_and_other():
    payload = {
        "when": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "items": [1, {"key": "value"}],
        "tuple": (1, 2),
        "color": Color.RED,
        "raw": object(),  # should fall through as-is
    }
    sanitized = TypeSafeAPI.sanitize_response_data(payload)
    assert sanitized["when"] == "2026-01-01T00:00:00+00:00"
    assert sanitized["items"] == [1, {"key": "value"}]
    assert sanitized["tuple"] == [1, 2]
    assert sanitized["color"] == "red"
    assert sanitized["raw"] is payload["raw"]


def test_sanitize_response_data_date_and_enum():
    assert TypeSafeAPI.sanitize_response_data(date(2026, 1, 2)) == "2026-01-02"
    assert TypeSafeAPI.sanitize_response_data(Color.GREEN) == "green"


def test_sanitize_response_data_max_depth():
    assert isinstance(
        TypeSafeAPI.sanitize_response_data({"a": {"b": {"c": 1}}}, max_depth=0), str
    )
    depth_one = TypeSafeAPI.sanitize_response_data({"a": {"b": {"c": 1}}}, max_depth=1)
    assert depth_one == {"a": "{'b': {'c': 1}}"}


# ---------------------------------------------------------------------------
# Async request/response decorators
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_request_valid_and_invalid():
    @validate_request({"x": int, "y": str})
    async def handler(data):
        return data

    result = await handler({"x": 5, "y": "ok"})
    assert result == {"x": 5, "y": "ok"}

    with pytest.raises(TypeValidationError):
        await handler({"x": "bad"})

    with pytest.raises(TypeValidationError):
        await handler({"y": "ok"})


@pytest.mark.asyncio
async def test_validate_request_first_arg_not_dict():
    @validate_request({"x": int})
    async def handler(a, b):
        return (a, b)

    # First arg is not a dict, so validation is skipped and the function is called directly.
    result = await handler(1, 2)
    assert result == (1, 2)


@pytest.mark.asyncio
async def test_sanitize_response_decorator():
    @sanitize_response
    async def handler():
        return {
            "when": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "color": Color.RED,
            "items": (1, 2),
        }

    result = await handler()
    assert result["when"] == "2026-01-01T00:00:00+00:00"
    assert result["color"] == "red"
    assert result["items"] == [1, 2]


# ---------------------------------------------------------------------------
# Typing helpers
# ---------------------------------------------------------------------------


def test_get_optional_type():
    assert get_optional_type(int) == Optional[int]


def test_get_list_type():
    assert get_list_type(int) == List[int]


def test_get_dict_type():
    assert get_dict_type(str, int) == Dict[str, int]
