# -*- coding: utf-8 -*-
# tests/test_user_service.py
# 🔧 P0-7: 用户服务单元测试

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import User
from core.user_service import UserService


@pytest.fixture
def mock_session():
    """Mock database session"""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Mock user object"""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        role="user",
        disabled=False,
        mfa_enabled=False,
    )
    return user


class TestUserService:
    """用户服务测试"""

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, mock_user):
        """测试根据用户名获取用户 - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = mock_user
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            user = await UserService.get_user_by_username("testuser")

            assert user is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self):
        """测试根据用户名获取用户 - 未找到"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = None
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            user = await UserService.get_user_by_username("nonexistent")

            assert user is None

    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_user):
        """测试创建用户 - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = None  # No existing user
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            user = await UserService.create_user(
                username="newuser",
                hashed_password="hashed_password",
                email="new@example.com",
                full_name="New User",
                role="user",
            )

            assert user is not None
            assert user.username == "newuser"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self):
        """测试创建用户 - 用户名已存在"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            # First call returns existing user
            with patch.object(UserService, "get_user_by_username") as mock_get:
                mock_get.return_value = MagicMock()  # User exists

                user = await UserService.create_user(
                    username="existing",
                    hashed_password="hashed_password",
                )

                assert user is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, mock_user):
        """测试更新用户 - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = mock_user
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            success = await UserService.update_user(
                username="testuser",
                full_name="Updated Name",
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """测试更新用户 - 用户不存在"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = None
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            success = await UserService.update_user(
                username="nonexistent",
                full_name="Name",
            )

            assert success is False

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """测试删除用户 - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            success = await UserService.delete_user("testuser")

            assert success is True

    @pytest.mark.asyncio
    async def test_list_users(self, mock_user):
        """测试列出用户"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalars.return_value.all.return_value = [mock_user]
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            users = await UserService.list_users()

            assert len(users) == 1
            assert users[0].username == "testuser"

    @pytest.mark.asyncio
    async def test_update_password_success(self, mock_user):
        """测试更新密码 - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = mock_user
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            success = await UserService.update_password("testuser", "new_hashed_password")

            assert success is True

    @pytest.mark.asyncio
    async def test_enable_mfa_success(self, mock_user):
        """测试启用MFA - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = mock_user
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            success = await UserService.enable_mfa("testuser", "secret", ["code1", "code2"])

            assert success is True

    @pytest.mark.asyncio
    async def test_disable_mfa_success(self, mock_user):
        """测试禁用MFA - 成功"""
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = mock_user
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            success = await UserService.disable_mfa("testuser")

            assert success is True

    def test_user_to_dict(self, mock_user):
        """测试用户对象转字典"""
        mock_user.created_at = datetime.now()
        mock_user.updated_at = datetime.now()
        mock_user.last_login_at = datetime.now()

        user_dict = UserService.user_to_dict(mock_user)

        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"
        assert "created_at" in user_dict
        assert "updated_at" in user_dict
