# -*- coding: utf-8 -*-
"""
Common Validation Helpers
=========================

Provides reusable validation functions to reduce code duplication
across API routers.

This module addresses the following code duplication issues:
- Repeated parameter validation patterns
- Repeated string validation patterns
- Repeated numeric range validation
- Repeated hostname/IP validation
"""

import re
from typing import Any, Optional

from fastapi import HTTPException, status

# Common validation patterns
VALID_HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]+$")
VALID_IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def validate_string_not_empty(
    value: Any,
    field_name: str,
    allow_whitespace: bool = False,
    max_length: Optional[int] = None,
) -> str:
    """
    Validate that a value is a non-empty string.

    This function reduces duplication of string validation patterns.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        allow_whitespace: Whether to allow whitespace-only strings
        max_length: Maximum allowed length

    Returns:
        Validated and cleaned string

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        keyword = validate_string_not_empty(
            keyword,
            "keyword",
            allow_whitespace=False,
            max_length=200
        )
    """
    if not value or not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} 不能为空"
        )

    cleaned = value.strip()

    if not cleaned and not allow_whitespace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} 不能为纯空白"
        )

    if max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def validate_numeric_range(
    value: Any,
    field_name: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    default: Optional[float] = None,
) -> float:
    """
    Validate that a value is within a numeric range.

    This function reduces duplication of numeric validation patterns.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        default: Default value if validation fails

    Returns:
        Validated numeric value

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        limit = validate_numeric_range(
            limit,
            "limit",
            min_val=1,
            max_val=500,
            default=20
        )
    """
    try:
        num_value = float(value)
    except (TypeError, ValueError):
        if default is not None:
            return default
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} 必须是数字"
        )

    if min_val is not None and num_value < min_val:
        if default is not None:
            return default
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 必须大于或等于 {min_val}",
        )

    if max_val is not None and num_value > max_val:
        if default is not None:
            return default
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 必须小于或等于 {max_val}",
        )

    return num_value


def validate_hostname_or_ip(
    value: str,
    field_name: str = "host_name",
    allow_localhost: bool = True,
) -> str:
    """
    Validate that a value is a valid hostname or IP address.

    This function reduces duplication of hostname/IP validation patterns.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        allow_localhost: Whether to allow localhost addresses

    Returns:
        Validated hostname or IP

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        host = validate_hostname_or_ip(host_name, "host_name")
    """
    cleaned = validate_string_not_empty(value, field_name)

    if not VALID_HOSTNAME_PATTERN.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 仅允许字母数字和 '._-:'",
        )

    # Optionally check if it's a valid IP
    if "." in cleaned and not VALID_IP_PATTERN.match(cleaned):
        # It looks like an IP but doesn't match the pattern
        # This is not necessarily an error, as it could be a hostname with dots
        pass

    return cleaned


def validate_list_length(
    value: Any,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> list:
    """
    Validate that a value is a list within length constraints.

    This function reduces duplication of list validation patterns.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Validated list

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        metrics = validate_list_length(
            metrics,
            "metrics",
            min_length=1,
            max_length=50
        )
    """
    if not isinstance(value, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} 必须是列表"
        )

    if min_length is not None and len(value) < min_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 长度必须至少为 {min_length}",
        )

    if max_length is not None and len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 长度不能超过 {max_length}",
        )

    return value


def validate_dict_fields(
    value: Any,
    field_name: str,
    required_fields: Optional[list[str]] = None,
    optional_fields: Optional[list[str]] = None,
) -> dict:
    """
    Validate that a value is a dict with required/optional fields.

    This function reduces duplication of dict validation patterns.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        required_fields: List of required field names
        optional_fields: List of optional field names

    Returns:
        Validated dictionary

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        params = validate_dict_fields(
            params,
            "params",
            required_fields=["service_name"],
            optional_fields=["timeout"]
        )
    """
    if not isinstance(value, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} 必须是字典"
        )

    if required_fields:
        missing = [f for f in required_fields if f not in value]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} 缺少必填字段: {', '.join(missing)}",
            )

    if optional_fields:
        # Check for unknown fields
        known_fields = set(required_fields or []) | set(optional_fields)
        unknown = [f for f in value.keys() if f not in known_fields]
        if unknown:
            # This is a warning, not an error
            # Log it but don't raise an exception
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"{field_name} 包含未知字段: {', '.join(unknown)}")

    return value


def sanitize_string(
    value: str,
    allowed_chars: Optional[str] = None,
    max_length: Optional[int] = None,
) -> str:
    """
    Sanitize a string by removing disallowed characters.

    This function reduces duplication of string sanitization patterns.

    Args:
        value: String to sanitize
        allowed_chars: String of allowed characters (if None, keeps alphanumeric)
        max_length: Maximum length after sanitization

    Returns:
        Sanitized string

    Example:
        safe_keyword = sanitize_string(
            keyword,
            allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
            max_length=200
        )
    """
    if allowed_chars is None:
        # Default to alphanumeric and common safe characters
        allowed_chars = "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789" "_-"

    allowed_set = set(allowed_chars)
    sanitized = "".join(c for c in value if c in allowed_set)

    if max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def validate_enum_value(
    value: Any,
    field_name: str,
    allowed_values: list[Any],
    case_sensitive: bool = True,
) -> Any:
    """
    Validate that a value is one of the allowed enum values.

    This function reduces duplication of enum validation patterns.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        allowed_values: List of allowed values
        case_sensitive: Whether comparison is case-sensitive

    Returns:
        Validated value

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        log_name = validate_enum_value(
            log_name,
            "log_name",
            allowed_values=["System", "Application", "Security"],
            case_sensitive=True
        )
    """
    if not case_sensitive and isinstance(value, str):
        # Case-insensitive comparison
        normalized_value = value.lower()
        normalized_allowed = [v.lower() if isinstance(v, str) else v for v in allowed_values]
        if normalized_value not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} 必须是以下值之一: {', '.join(map(str, allowed_values))}",
            )
        # Return the original case version
        for allowed in allowed_values:
            if isinstance(allowed, str) and allowed.lower() == normalized_value:
                return allowed
        return value
    else:
        # Case-sensitive comparison
        if value not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} 必须是以下值之一: {', '.join(map(str, allowed_values))}",
            )
        return value
