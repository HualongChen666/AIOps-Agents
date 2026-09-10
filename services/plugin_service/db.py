# -*- coding: utf-8 -*-
"""Database wiring for the plugin microservice.

The plugin repository layer is synchronous, so this module builds a sync
engine/sessionmaker. When ``PLUGIN_SERVICE_USE_IN_MEMORY`` is true an in-memory
SQLite database backed by a ``StaticPool`` is used (a single connection is
shared so the schema survives across requests); otherwise the configured
PostgreSQL URL is used.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.models import Plugin, PluginConfig, PluginExecution
from services.plugin_service.config import settings

_PLUGIN_TABLES = [Plugin.__table__, PluginExecution.__table__, PluginConfig.__table__]


def build_engine() -> Engine:
    """Create the engine and ensure the plugin tables exist."""
    if settings.use_in_memory:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
    # Only the three plugin-owned tables live here; core.models owns the rest.
    Plugin.__table__.metadata.create_all(engine, tables=_PLUGIN_TABLES)
    return engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide engine (created on first use)."""
    return build_engine()


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped ORM session."""
    session: Session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
