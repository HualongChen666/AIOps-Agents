# -*- coding: utf-8 -*-
"""tests/api/conftest.py

Prevent any test in tests/api from opening a real database connection.
All calls into core.db_engine are replaced with safe async stubs so that
endpoint tests can execute to completion without a running PostgreSQL.
"""

import sys
import types
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock


def _make_fake_db_engine():
    fake_db = types.ModuleType("core.db_engine")

    @asynccontextmanager
    async def _fake_session_ctx():
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.scalar = AsyncMock(return_value=None)
        session.scalars = AsyncMock(return_value=MagicMock())
        session.commit = AsyncMock(return_value=None)
        session.rollback = AsyncMock(return_value=None)
        yield session

    def _db_getattr(name: str):
        if name == "async_get_session":
            return _fake_session_ctx
        return AsyncMock(return_value=None)

    fake_db.__getattr__ = _db_getattr
    return fake_db


# This runs before api router test modules are imported, so we can pre-seed
# core.db_engine with a safe fake module.
if "core.db_engine" not in sys.modules or not hasattr(
    sys.modules["core.db_engine"], "__getattr__"
):
    sys.modules["core.db_engine"] = _make_fake_db_engine()

# Also expose it as core.db_engine so monkeypatch.setattr("core.db_engine.", ...) works.
import core  # noqa: E402

core.db_engine = sys.modules["core.db_engine"]
