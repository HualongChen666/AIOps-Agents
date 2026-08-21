# -*- coding: utf-8 -*-
"""
Pytest fixtures for workflow benchmark tests.
"""

import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest

# Add workflow_service to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "extensions" / "addons" / "operations" / "workflow_service"))

# Clear prometheus metrics registry to avoid duplicate registration errors
from prometheus_client import REGISTRY
try:
    REGISTRY._collector_to_names.clear()
    REGISTRY._names_to_collectors.clear()
except:
    pass  # Registry may not have these attributes in all versions


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async benchmark tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test."""
    from prometheus_client import REGISTRY
    try:
        # Clear all metrics
        for collector in list(REGISTRY._collector_to_names.keys()):
            REGISTRY.unregister(collector)
    except:
        pass
    yield
    # Cleanup after test
    try:
        for collector in list(REGISTRY._collector_to_names.keys()):
            REGISTRY.unregister(collector)
    except:
        pass


@pytest.fixture(autouse=True)
def gc_collect():
    """Force garbage collection before and after each test for accurate memory measurements."""
    gc.collect()
    yield
    gc.collect()


# Import gc
import gc
