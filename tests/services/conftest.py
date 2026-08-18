# -*- coding: utf-8 -*-
"""Conftest for services tests to disable database fixtures."""

import pytest


# Override the ensure_database fixture to do nothing
@pytest.fixture(scope="module", autouse=True)
def ensure_database():
    """No-op database fixture for services tests."""
    pass


# Override any other database-related fixtures
@pytest.fixture
def db_session():
    """No-op db session fixture."""
    yield None


@pytest.fixture
def async_db_session():
    """No-op async db session fixture."""
    yield None
