# -*- coding: utf-8 -*-
"""Unit tests for error handling modules."""

import pytest  # noqa: F401  # Imported for test setup

from core.error_codes.manager import get_error_code_manager, get_error_message
from core.error_logging.logger import get_structured_error_logger, log_error
from core.error_recovery.core import (
    CircuitBreaker,
    CircuitBreakerConfig,
    ErrorRecoveryManager,
    RetryConfig,
)
from core.exception_handler import setup_exception_handlers
from core.exceptions.base import AIOpsBaseException
from core.exceptions.business import BusinessException, ValidationException
from core.exceptions.critical import CriticalException
from core.exceptions.security import SecurityException
from core.exceptions.system import DatabaseException, SystemException
from core.exceptions.third_party import ThirdPartyException


def test_exception_classes_can_be_raised():
    classes = [
        AIOpsBaseException,
        ValidationException,
        BusinessException,
        DatabaseException,
        SystemException,
        SecurityException,
        CriticalException,
        ThirdPartyException,
    ]
    for exc_cls in classes:
        with pytest.raises(exc_cls):
            raise exc_cls("test message")


def test_error_code_manager():
    manager = get_error_code_manager()
    assert manager is not None
    # Unknown codes return a generic message
    message = get_error_message("ERR_UNKNOWN")
    assert isinstance(message, str)


def test_structured_error_logger():
    logger = get_structured_error_logger()
    assert logger is not None
    log_error("ERR_TEST", "test error", context={"test": True})


def test_error_recovery_manager():
    manager = ErrorRecoveryManager()
    assert manager is not None


def test_circuit_breaker():
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1)
    cb = CircuitBreaker(config)
    assert cb.config.failure_threshold == 3
    assert cb.state.name == "CLOSED"


def test_retry_config():
    config = RetryConfig(max_attempts=2, base_delay=0.1)
    assert config.max_attempts == 2


def test_setup_exception_handlers_runs():
    class FakeApp:
        def add_exception_handler(self, *args, **kwargs):
            pass

    app = FakeApp()
    setup_exception_handlers(app)
