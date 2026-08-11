# -*- coding: utf-8 -*-
"""Unit tests for previously uncovered core helper modules."""

import pytest

from core.api_resource_optimizer import (
    ResourceType,
    get_api_resource_optimizer,
)
from core.database_cache_optimizer import get_database_cache_optimizer
from core.database_connection_optimizer import get_database_connection_optimizer
from core.error_handler import ErrorHandler, ValidationError
from core.error_handling_logging import ErrorHandlingAndLogging, StructuredLogger
from core.log_router import LogRouterManager, create_log_router


def test_api_resource_optimizer():
    opt = get_api_resource_optimizer({})
    opt.track_resource_usage(ResourceType.CPU, "/api/test", "GET", 1.0)
    opt.set_resource_limit(ResourceType.CPU, "/api/test", 80.0)
    opt.check_resource_limit(ResourceType.CPU, "/api/test", "GET")
    opt.allocate_resource(ResourceType.CPU, "/api/test", 1.0)
    opt.release_resource(ResourceType.CPU, "/api/test", 1.0)
    stats = opt.get_statistics()
    assert isinstance(stats, dict)


def test_database_connection_optimizer():
    opt = get_database_connection_optimizer()
    stats = opt.get_pool_stats("default")
    assert isinstance(stats, dict)
    health = opt.check_pool_health("default")
    assert isinstance(health, dict)


def test_database_cache_optimizer():
    opt = get_database_cache_optimizer({})
    stats = opt.get_stats()
    assert isinstance(stats, dict)


def test_error_handler():
    handler = ErrorHandler({})
    handler.handle_exception(ValidationError("test error"))
    stats = handler.get_error_stats()
    assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_error_handling_and_logging():
    ehl = ErrorHandlingAndLogging()
    await ehl.initialize()
    await ehl.handle_exception(ValueError("test"))
    stats = await ehl.get_statistics()
    assert isinstance(stats, dict)


def test_structured_logger():
    logger = StructuredLogger()
    logger.info("test message")
    logger.debug("test debug")
    logger.error("test error")
    logger.warning("test warning")
    logger.critical("test critical")


def test_log_router_manager():
    manager = LogRouterManager()
    router = manager.add_router("default", {"enabled": True})
    assert router is not None
    assert manager.get_router("default") is not None
    manager.set_default_router("default")
    assert manager.remove_router("default") is True


def test_log_router_create():
    router = create_log_router({"enabled": True})
    entry = router.create_log_entry("INFO", "test message")
    assert entry is not None
    assert router.parse_fluent_bit_log('{"log":"test"}') is not None
    router.enable()
    router.disable()


@pytest.mark.asyncio
async def test_log_router_batch():
    router = create_log_router({"enabled": True})
    entry = router.create_log_entry("INFO", "test message")
    result = await router.batch_route_logs([entry])
    assert isinstance(result, dict)
