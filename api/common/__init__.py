# -*- coding: utf-8 -*-
"""
Common API Helpers Module
=========================

Provides reusable helper functions and utilities for API routers
to reduce code duplication and improve maintainability.

Modules:
- error_handlers: Common error handling and response formatting
- cache_helpers: Common caching patterns and utilities
- validation_helpers: Common validation functions
- logging_helpers: Common logging patterns
"""

from .cache_helpers import (
    CacheStats,
    SimpleTTLCache,
    generate_cache_key,
    get_cached_or_execute,
    with_cache_response,
)
from .error_handlers import (
    check_feature_availability,
    create_error_response,
    create_list_response,
    create_success_response,
    create_timestamp_response,
    get_client_ip,
    handle_service_error,
    validate_and_raise_422,
)
from .logging_helpers import (
    OperationLogger,
    format_log_params,
    log_cache_hit,
    log_cache_miss,
    log_operation_complete,
    log_operation_start,
    log_request_error,
    log_request_received,
    log_request_success,
    log_security_event,
    log_warning,
)
from .validation_helpers import (
    VALID_HOSTNAME_PATTERN,
    VALID_IP_PATTERN,
    sanitize_string,
    validate_dict_fields,
    validate_enum_value,
    validate_hostname_or_ip,
    validate_list_length,
    validate_numeric_range,
    validate_string_not_empty,
)

__all__ = [
    # Error handlers
    "handle_service_error",
    "create_success_response",
    "create_list_response",
    "create_error_response",
    "validate_and_raise_422",
    "check_feature_availability",
    "get_client_ip",
    "create_timestamp_response",
    # Cache helpers
    "SimpleTTLCache",
    "CacheStats",
    "get_cached_or_execute",
    "generate_cache_key",
    "with_cache_response",
    # Validation helpers
    "VALID_HOSTNAME_PATTERN",
    "VALID_IP_PATTERN",
    "validate_string_not_empty",
    "validate_numeric_range",
    "validate_hostname_or_ip",
    "validate_list_length",
    "validate_dict_fields",
    "sanitize_string",
    "validate_enum_value",
    # Logging helpers
    "log_request_received",
    "log_request_success",
    "log_request_error",
    "log_cache_hit",
    "log_cache_miss",
    "log_operation_start",
    "log_operation_complete",
    "log_warning",
    "log_security_event",
    "format_log_params",
    "OperationLogger",
]
