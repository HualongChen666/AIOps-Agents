# -*- coding: utf-8 -*-
"""测试数据生命周期操作模块"""

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


class FakeResult:
    def __init__(self, rowcount=3):
        self.rowcount = rowcount


@pytest.fixture
def fake_session(monkeypatch):
    """提供一个可复用的 FakeSession 用于测试 core/db_engine 接口。"""
    session = MagicMock()
    session.execute = AsyncMock(return_value=FakeResult(3))
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", MagicMock(return_value=session))
    return session


@pytest.mark.asyncio
async def test_archive_alerts(fake_session):
    from core.data_lifecycle_operations import archive_alerts

    count = await archive_alerts(datetime.datetime.now())
    assert count == 3


@pytest.mark.asyncio
async def test_archive_alerts_exception(fake_session):
    from core.data_lifecycle_operations import archive_alerts

    fake_session.execute = AsyncMock(side_effect=RuntimeError("db fail"))
    count = await archive_alerts(datetime.datetime.now())
    assert count == 0


@pytest.mark.asyncio
async def test_archive_metrics(fake_session):
    from core.data_lifecycle_operations import archive_metrics

    count = await archive_metrics(datetime.datetime.now())
    assert count == 3


@pytest.mark.asyncio
async def test_archive_metrics_exception(fake_session):
    from core.data_lifecycle_operations import archive_metrics

    fake_session.execute = AsyncMock(side_effect=RuntimeError("db fail"))
    count = await archive_metrics(datetime.datetime.now())
    assert count == 0


@pytest.mark.asyncio
async def test_cleanup_temporary_files_no_temp_dir(monkeypatch):
    from core.data_lifecycle_operations import cleanup_temporary_files

    monkeypatch.setattr("os.path.exists", lambda _path: False)
    count = await cleanup_temporary_files(datetime.datetime.now())
    assert count == 0


@pytest.mark.asyncio
async def test_cleanup_temporary_files_deletes_old_files(monkeypatch):
    from core.data_lifecycle_operations import cleanup_temporary_files

    now = datetime.datetime.now()
    old_time = (now - datetime.timedelta(days=2)).timestamp()
    new_time = now.timestamp()

    def fake_exists(path):
        return True

    def fake_glob(pattern):
        return ["temp/old.txt", "temp/new.txt"]

    def fake_getmtime(path):
        return old_time if "old" in path else new_time

    removed = []

    def fake_remove(path):
        removed.append(path)

    monkeypatch.setattr("os.path.exists", fake_exists)
    monkeypatch.setattr("glob.glob", fake_glob)
    monkeypatch.setattr("os.path.getmtime", fake_getmtime)
    monkeypatch.setattr("os.remove", fake_remove)

    count = await cleanup_temporary_files(now - datetime.timedelta(days=1))
    assert count == 1
    assert removed == ["temp/old.txt"]


@pytest.mark.asyncio
async def test_cleanup_temporary_cache(monkeypatch):
    from core.data_lifecycle_operations import cleanup_temporary_cache

    mock_redis = MagicMock()
    mock_redis.keys.return_value = ["temp:a", "temp:b"]
    mock_redis.delete.return_value = 2

    monkeypatch.setattr("redis.Redis", lambda **kw: mock_redis)
    result = await cleanup_temporary_cache(datetime.datetime.now())
    assert result is True


@pytest.mark.asyncio
async def test_cleanup_temporary_cache_no_keys(monkeypatch):
    from core.data_lifecycle_operations import cleanup_temporary_cache

    mock_redis = MagicMock()
    mock_redis.keys.return_value = []

    monkeypatch.setattr("redis.Redis", lambda **kw: mock_redis)
    result = await cleanup_temporary_cache(datetime.datetime.now())
    assert result is False


@pytest.mark.asyncio
async def test_cleanup_temporary_cache_exception(monkeypatch):
    from core.data_lifecycle_operations import cleanup_temporary_cache

    monkeypatch.setattr(
        "redis.Redis", lambda **kw: (_ for _ in ()).throw(RuntimeError("redis down"))
    )
    result = await cleanup_temporary_cache(datetime.datetime.now())
    assert result is False
