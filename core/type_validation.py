# -*- coding: utf-8 -*-
"""
Runtime Type Validation Module
============================

Provides runtime type checking and validation capabilities for enhanced type safety.
This complements static type checking with runtime validation for critical paths.

Key Features:
- Runtime type validation decorators
- Type-safe API interfaces
- Runtime type coercion
- Type validation for data structures
"""

import functools
import inspect
import logging
from dataclasses import is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class TypeValidationError(Exception):
    """Raised when runtime type validation fails"""


class RuntimeTypeValidator:
    """
    Runtime type validator for Python objects
    """

    @staticmethod
    def validate_type(value: Any, expected_type: Type[T], field_name: str = "value") -> Optional[T]:
        """
        Validate that a value matches the expected type

        Args:
            value: Value to validate
            expected_type: Expected type
            field_name: Name of the field (for error messages)

        Returns:
            The validated value

        Raises:
            TypeValidationError: If validation fails
        """
        if value is None:
            # Allow None for Optional types
            if RuntimeTypeValidator._is_optional_type(expected_type):
                return value
            raise TypeValidationError(f"{field_name} cannot be None for type {expected_type}")

        # Handle basic types
        if expected_type in (int, float, str, bool):
            if not isinstance(value, expected_type):
                raise TypeValidationError(
                    f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}"
                )
            return value

        # Handle datetime
        if expected_type in (datetime, date):
            if not isinstance(value, expected_type):
                raise TypeValidationError(
                    f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}"
                )
            return value

        # Handle lists
        origin = get_origin(expected_type)
        if origin is list:
            if not isinstance(value, list):
                raise TypeValidationError(
                    f"{field_name} must be a list, got {type(value).__name__}"
                )
            args = get_args(expected_type)
            if args:
                item_type = args[0]
                for i, item in enumerate(value):
                    RuntimeTypeValidator.validate_type(item, item_type, f"{field_name}[{i}]")
            return cast(T, value)

        # Handle dicts
        if origin is dict:
            if not isinstance(value, dict):
                raise TypeValidationError(
                    f"{field_name} must be a dict, got {type(value).__name__}"
                )
            args = get_args(expected_type)
            if args and len(args) == 2:
                key_type, value_type = args
                for key, val in value.items():
                    RuntimeTypeValidator.validate_type(key, key_type, f"{field_name} key")
                    RuntimeTypeValidator.validate_type(val, value_type, f"{field_name}[{key}]")
            return cast(T, value)

        # Handle dataclasses
        if is_dataclass(expected_type):
            if not isinstance(value, expected_type):
                raise TypeValidationError(
                    f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}"
                )
            # Validate dataclass fields
            type_hints = get_type_hints(expected_type)
            for field_name, field_type in type_hints.items():
                if hasattr(value, field_name):
                    field_value = getattr(value, field_name)
                    RuntimeTypeValidator.validate_type(
                        field_value, field_type, f"{field_name}.{field_name}"
                    )
            return value

        # Default: just return the value
        return cast(T, value)

    @staticmethod
    def _is_optional_type(type_hint: Type) -> bool:
        """Check if a type is Optional (Union with None)"""
        if type_hint is type(None):  # type(None) is the same as NoneType
            return True
        origin = get_origin(type_hint)
        if origin is not None and getattr(origin, "__name__", None) == "Union":
            args = get_args(type_hint)
            return type(None) in args
        return False

    @staticmethod
    def coerce_type(value: Any, target_type: Type[T]) -> Optional[T]:
        """
        Coerce a value to the target type if possible

        Args:
            value: Value to coerce
            target_type: Target type

        Returns:
            Coerced value

        Raises:
            TypeValidationError: If coercion fails
        """
        if value is None:
            return value

        # If already the right type, return as-is
        if isinstance(value, target_type):
            return value

        # Try common coercions
        if target_type == int:
            try:
                return cast(T, int(value))
            except (ValueError, TypeError):
                raise TypeValidationError(f"Cannot coerce {value} to int")

        if target_type == float:
            try:
                return cast(T, float(value))
            except (ValueError, TypeError):
                raise TypeValidationError(f"Cannot coerce {value} to float")

        if target_type == str:
            return cast(T, str(value))

        if target_type == bool:
            if isinstance(value, str):
                return cast(T, value.lower() in ("true", "1", "yes", "on"))
            return cast(T, bool(value))

        # If coercion not possible, return original value
        return cast(T, value)


def validate_types(**type_hints):
    """
    Decorator to validate function argument types at runtime

    Args:
        **type_hints: Type hints for function arguments
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            parameters = sig.parameters

            # Validate positional arguments
            args_list = list(args)
            for i, (name, param) in enumerate(parameters.items()):
                if i < len(args_list):
                    if name in type_hints:
                        try:
                            validated = RuntimeTypeValidator.validate_type(
                                args_list[i], type_hints[name], name
                            )
                            args_list[i] = validated
                        except TypeValidationError as e:
                            logger.error(f"Type validation failed for {func.__name__}.{name}: {e}")
                            raise

            # Validate keyword arguments
            for name, value in kwargs.items():
                if name in type_hints:
                    try:
                        validated = RuntimeTypeValidator.validate_type(
                            value, type_hints[name], name
                        )
                        kwargs[name] = validated
                    except TypeValidationError as e:
                        logger.error(f"Type validation failed for {func.__name__}.{name}: {e}")
                        raise

            return func(*args_list, **kwargs)

        return wrapper

    return decorator


def validate_return_type(return_type: Type[T]):
    """
    Decorator to validate function return type at runtime

    Args:
        return_type: Expected return type
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            try:
                validated = RuntimeTypeValidator.validate_type(result, return_type, "return_value")
                return validated
            except TypeValidationError as e:
                logger.error(f"Return type validation failed for {func.__name__}: {e}")
                raise

        return wrapper

    return decorator


class TypeSafeAPI:
    """
    Base class for type-safe API interfaces
    """

    @staticmethod
    def validate_request_data(data: Dict[str, Any], schema: Dict[str, Type]) -> Dict[str, Any]:
        """
        Validate API request data against a schema

        Args:
            data: Request data to validate
            schema: Schema mapping field names to types

        Returns:
            Validated data

        Raises:
            TypeValidationError: If validation fails
        """
        validated_data = {}

        for field_name, field_type in schema.items():
            if field_name not in data:
                raise TypeValidationError(f"Missing required field: {field_name}")

            try:
                validated_data[field_name] = RuntimeTypeValidator.validate_type(
                    data[field_name], field_type, field_name
                )
            except TypeValidationError as e:
                raise TypeValidationError(f"Validation failed for {field_name}: {e}")

        return validated_data

    @staticmethod
    def sanitize_response_data(data: Any, max_depth: int = 3) -> Any:
        """
        Sanitize response data for safe serialization

        Args:
            data: Data to sanitize
            max_depth: Maximum recursion depth

        Returns:
            Sanitized data
        """
        if max_depth <= 0:
            return str(data)

        if isinstance(data, dict):
            return {
                key: TypeSafeAPI.sanitize_response_data(value, max_depth - 1)
                for key, value in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return [TypeSafeAPI.sanitize_response_data(item, max_depth - 1) for item in data]
        elif isinstance(data, (datetime, date)):
            return data.isoformat()
        elif isinstance(data, Enum):
            return data.value
        else:
            return data


# Type-safe API decorators for common use cases
def validate_request(schema: Dict[str, Type]):
    """
    Decorator for validating API request data

    Args:
        schema: Schema for request validation
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract request data from first argument if it's a dict
            args_list = list(args)
            if args_list and isinstance(args_list[0], dict):
                try:
                    validated = TypeSafeAPI.validate_request_data(args_list[0], schema)
                    args_list[0] = validated
                except TypeValidationError as e:
                    logger.error(f"Request validation failed for {func.__name__}: {e}")
                    raise

            return await func(*args_list, **kwargs)

        return wrapper

    return decorator


def sanitize_response(func):
    """
    Decorator for sanitizing API response data
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return TypeSafeAPI.sanitize_response_data(result)

    return wrapper


# Type hint utilities for common patterns
def get_optional_type(base_type: Type[T]) -> Type[Optional[T]]:
    """Get Optional type for a base type"""
    try:
        from typing import Optional

        return Optional[base_type]  # type: ignore
    except ImportError:
        # Python 3.10+ syntax
        return base_type | None  # type: ignore


def get_list_type(item_type: Type[T]) -> Type[List[T]]:
    """Get List type for an item type"""
    try:
        from typing import List

        return List[item_type]  # type: ignore
    except ImportError:
        # Python 3.9+ syntax
        return list[item_type]  # type: ignore


def get_dict_type(key_type: Type[K], value_type: Type[V]) -> Type[Dict[K, V]]:
    """Get Dict type for key and value types"""
    try:
        from typing import Dict

        return Dict[key_type, value_type]  # type: ignore
    except ImportError:
        # Python 3.9+ syntax
        return dict[key_type, value_type]  # type: ignore
