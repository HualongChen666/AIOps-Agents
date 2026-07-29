# -*- coding: utf-8 -*-
"""测试用户服务模块"""

from collections import deque
from typing import Any, List, Optional

import pytest

from core.models import User


class FakeResult:
    """Minimal SQLAlchemy result component for UserService tests."""

    def __init__(
        self,
        scalar: Any = None,
        scalars: Optional[List[Any]] = None,
        rowcount: int = 0,
    ):
        self._scalar = scalar
        self._scalars = scalars or []
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._scalars


class FakeSession:
    """Minimal async session component driven by a queue of FakeResult objects."""

    def __init__(self, result: FakeResult = None):
        self._result = result if result is not None else FakeResult()

    async def execute(self, stmt):
        return self._result

    def add(self, obj):
        if not getattr(obj, "id", None):
            obj.id = 1

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class FakeSessionLocal:
    """Replacement for AsyncSessionLocal used by UserService."""

    results: deque = deque()

    def __call__(self):
        result = self.results.popleft() if self.results else FakeResult()
        return FakeSession(result)


@pytest.fixture(autouse=True)
def patch_session(monkeypatch):
    from core import user_service

    monkeypatch.setattr(user_service, "AsyncSessionLocal", FakeSessionLocal())
    FakeSessionLocal.results.clear()


def _user(username="alice", email="alice@example.com", user_id=1):
    return User(
        id=user_id,
        username=username,
        email=email,
        full_name="Alice",
        hashed_password="hash",
        role="user",
        disabled=False,
    )


@pytest.mark.asyncio
async def test_get_user_by_username():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    user = await UserService.get_user_by_username("alice")
    assert user is not None
    assert user.username == "alice"


@pytest.mark.asyncio
async def test_get_user_by_email():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    user = await UserService.get_user_by_email("alice@example.com")
    assert user is not None
    assert user.username == "alice"


@pytest.mark.asyncio
async def test_get_user_by_id():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    user = await UserService.get_user_by_id(1)
    assert user is not None
    assert user.id == 1


@pytest.mark.asyncio
async def test_create_user_success():
    from core.user_service import UserService

    # get_user_by_username, get_user_by_email, outer session
    FakeSessionLocal.results.extend([FakeResult(), FakeResult(), FakeResult()])
    user = await UserService.create_user(
        username="bob",
        hashed_password="h",
        email="bob@example.com",
        full_name="Bob",
    )
    assert user is not None
    assert user.username == "bob"


@pytest.mark.asyncio
async def test_create_user_duplicate_username():
    from core.user_service import UserService

    # create_user calls AsyncSessionLocal() for the outer session first,
    # then get_user_by_username inside that block.
    FakeSessionLocal.results.extend([FakeResult(), FakeResult(scalar=_user())])
    result = await UserService.create_user(
        username="alice",
        hashed_password="h",
        email="new@example.com",
    )
    assert result is None


@pytest.mark.asyncio
async def test_update_user():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    assert await UserService.update_user("alice", full_name="Alice Updated") is True


@pytest.mark.asyncio
async def test_update_user_not_found():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=None))
    assert await UserService.update_user("missing", full_name="X") is False


@pytest.mark.asyncio
async def test_update_password():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    assert await UserService.update_password("alice", "newhash") is True


@pytest.mark.asyncio
async def test_delete_user():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(rowcount=1))
    assert await UserService.delete_user("alice") is True


@pytest.mark.asyncio
async def test_list_users():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalars=[_user(), _user(user_id=2)]))
    users = await UserService.list_users()
    assert len(users) == 2


@pytest.mark.asyncio
async def test_update_last_login():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    assert await UserService.update_last_login("alice") is True


@pytest.mark.asyncio
async def test_enable_mfa():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    assert await UserService.enable_mfa("alice", "secret", ["rc1"]) is True


@pytest.mark.asyncio
async def test_disable_mfa():
    from core.user_service import UserService

    FakeSessionLocal.results.append(FakeResult(scalar=_user()))
    assert await UserService.disable_mfa("alice") is True


def test_user_to_dict():
    from core.user_service import UserService

    user = _user()
    data = UserService.user_to_dict(user)
    assert data["username"] == "alice"
    assert "id" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
