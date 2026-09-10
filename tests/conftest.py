# -*- coding: utf-8 -*-
"""
Pytest配置文件
包含共享的fixtures和配置
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# --- Wave2 #25: endpoints protected by X-Internal-Key now fail closed when
# INTERNAL_API_KEY is unset.  The suite needs a configured key
# (tests/test_security_audit.py already asserts INTERNAL_API_KEY != "").
try:
    import config as _config

    if not _config.INTERNAL_API_KEY:
        _config.INTERNAL_API_KEY = "test-internal-key"
except Exception:  # pragma: no cover - config problems surface elsewhere
    pass


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _ensure_database_schema():
    """Ensure the test database schema exists before DB-backed tests run.

    Several API test suites (change/repair/database advanced routers, …) talk
    to the real SQLAlchemy metadata; without this the first ``DELETE FROM`` in
    their setup fixtures fails with ``no such table``.  Creating the schema is
    idempotent and mirrors what ``alembic upgrade head`` does in production.
    """
    try:
        from core.database import Base, engine
        import core.models  # noqa: F401  (register all mapped tables)

        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as exc:  # pragma: no cover - schema problems surface in tests
        import logging

        logging.getLogger(__name__).warning("Could not pre-create test schema: %s", exc)
    yield


# 配置pytest标记
def pytest_configure(config):
    """配置pytest自定义标记"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
