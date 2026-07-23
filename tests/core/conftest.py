# -*- coding: utf-8 -*-
"""
Core database test configuration

Provides pytest fixtures for database testing to avoid SQLAlchemy metadata conflicts.
"""

import pytest
from sqlalchemy import create_engine, orm
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="session")
def test_base(test_engine):
    """Create a test SQLAlchemy Base with extend_existing=True."""
    from sqlalchemy import orm

    # Create a new Base with extend_existing=True to avoid conflicts
    TestBase = orm.declarative_base()
    return TestBase


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session."""
    Session = orm.sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def mock_async_session():
    """Mock async session for testing async functions."""
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    return mock_session
