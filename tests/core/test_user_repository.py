# -*- coding: utf-8 -*-
# tests/core/test_user_repository.py
# 用户Repository层单元测试

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.db_engine import AsyncSessionLocal
from core.models import Base, User
from core.repositories.user_repository import UserRepository


@pytest.fixture
async def test_db():
    """创建测试数据库"""
    # 使用内存SQLite数据库进行测试
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield async_session_maker
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_user_repository_create(test_db):
    """测试创建用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com",
            full_name="Test User",
            role="user",
        )
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == "user"
        assert user.disabled is False
        assert user.mfa_enabled is False


@pytest.mark.asyncio
async def test_user_repository_create_duplicate_username(test_db):
    """测试创建重复用户名"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建第一个用户
        await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test1@example.com",
        )
        
        # 尝试创建重复用户名
        with pytest.raises(ValueError, match="用户名已存在"):
            await repo.create(
                username="testuser",
                hashed_password="hashed_password_456",
                email="test2@example.com",
            )


@pytest.mark.asyncio
async def test_user_repository_create_duplicate_email(test_db):
    """测试创建重复邮箱"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建第一个用户
        await repo.create(
            username="user1",
            hashed_password="hashed_password_123",
            email="test@example.com",
        )
        
        # 尝试创建重复邮箱
        with pytest.raises(ValueError, match="邮箱已存在"):
            await repo.create(
                username="user2",
                hashed_password="hashed_password_456",
                email="test@example.com",
            )


@pytest.mark.asyncio
async def test_user_repository_get_by_id(test_db):
    """测试根据ID获取用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        created_user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com",
        )
        
        # 根据ID获取
        user = await repo.get_by_id(created_user.id)
        
        assert user is not None
        assert user.id == created_user.id
        assert user.username == "testuser"


@pytest.mark.asyncio
async def test_user_repository_get_by_username(test_db):
    """测试根据用户名获取用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com",
        )
        
        # 根据用户名获取
        user = await repo.get_by_username("testuser")
        
        assert user is not None
        assert user.username == "testuser"


@pytest.mark.asyncio
async def test_user_repository_get_by_email(test_db):
    """测试根据邮箱获取用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com",
        )
        
        # 根据邮箱获取
        user = await repo.get_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_user_repository_update(test_db):
    """测试更新用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com",
            full_name="Test User",
            role="user",
        )
        
        # 更新用户
        updated_user = await repo.update(
            user_id=user.id,
            email="newemail@example.com",
            full_name="New Name",
            role="operator",
        )
        
        assert updated_user is not None
        assert updated_user.email == "newemail@example.com"
        assert updated_user.full_name == "New Name"
        assert updated_user.role == "operator"


@pytest.mark.asyncio
async def test_user_repository_update_password(test_db):
    """测试更新密码"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
        )
        
        # 更新密码
        success = await repo.update_password(user.id, "new_hashed_password_456")
        
        assert success is True
        
        # 验证密码已更新
        updated_user = await repo.get_by_id(user.id)
        assert updated_user.hashed_password == "new_hashed_password_456"


@pytest.mark.asyncio
async def test_user_repository_delete(test_db):
    """测试删除用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
        )
        
        # 删除用户
        success = await repo.delete(user.id)
        
        assert success is True
        
        # 验证用户已删除
        deleted_user = await repo.get_by_id(user.id)
        assert deleted_user is None


@pytest.mark.asyncio
async def test_user_repository_list_users(test_db):
    """测试列出用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建多个用户
        await repo.create(username="user1", hashed_password="hash1")
        await repo.create(username="user2", hashed_password="hash2")
        await repo.create(username="user3", hashed_password="hash3")
        
        # 列出用户
        users = await repo.list_users(limit=10, offset=0)
        
        assert len(users) == 3


@pytest.mark.asyncio
async def test_user_repository_count(test_db):
    """测试统计用户数量"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        await repo.create(username="user1", hashed_password="hash1", role="admin")
        await repo.create(username="user2", hashed_password="hash2", role="user")
        await repo.create(username="user3", hashed_password="hash3", role="user")
        
        # 统计总数
        total_count = await repo.count()
        assert total_count == 3
        
        # 统计特定角色
        user_count = await repo.count(role="user")
        assert user_count == 2


@pytest.mark.asyncio
async def test_user_repository_update_last_login(test_db):
    """测试更新最后登录时间"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
        )
        
        # 更新最后登录时间
        success = await repo.update_last_login(user.id)
        
        assert success is True
        
        # 验证最后登录时间已更新
        updated_user = await repo.get_by_id(user.id)
        assert updated_user.last_login_at is not None
        assert isinstance(updated_user.last_login_at, datetime)


@pytest.mark.asyncio
async def test_user_repository_enable_mfa(test_db):
    """测试启用MFA"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
        )
        
        # 启用MFA
        success = await repo.enable_mfa(
            user.id,
            secret="JBSWY3DPEHPK3PXP",
            recovery_codes=["code1", "code2", "code3"],
        )
        
        assert success is True
        
        # 验证MFA已启用
        updated_user = await repo.get_by_id(user.id)
        assert updated_user.mfa_enabled is True
        assert updated_user.mfa_secret == "JBSWY3DPEHPK3PXP"


@pytest.mark.asyncio
async def test_user_repository_disable_mfa(test_db):
    """测试禁用MFA"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户并启用MFA
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
        )
        await repo.enable_mfa(
            user.id,
            secret="JBSWY3DPEHPK3PXP",
            recovery_codes=["code1", "code2", "code3"],
        )
        
        # 禁用MFA
        success = await repo.disable_mfa(user.id)
        
        assert success is True
        
        # 验证MFA已禁用
        updated_user = await repo.get_by_id(user.id)
        assert updated_user.mfa_enabled is False
        assert updated_user.mfa_secret is None


@pytest.mark.asyncio
async def test_user_repository_batch_create(test_db):
    """测试批量创建用户"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 准备批量数据
        users_data = [
            {
                "username": f"user{i}",
                "hashed_password": f"hash{i}",
                "email": f"user{i}@example.com",
            }
            for i in range(10)
        ]
        
        # 批量创建
        created_users = await repo.batch_create(users_data, batch_size=5)
        
        assert len(created_users) == 10
        
        # 验证所有用户都已创建
        for user in created_users:
            assert user.username.startswith("user")


@pytest.mark.asyncio
async def test_user_repository_to_dict(test_db):
    """测试转换为字典"""
    async with test_db() as session:
        repo = UserRepository(session=session)
        
        # 创建用户
        user = await repo.create(
            username="testuser",
            hashed_password="hashed_password_123",
            email="test@example.com",
            full_name="Test User",
            role="user",
        )
        
        # 转换为字典
        user_dict = repo.to_dict(user)
        
        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["full_name"] == "Test User"
        assert user_dict["role"] == "user"
        assert "id" in user_dict
        assert "created_at" in user_dict
