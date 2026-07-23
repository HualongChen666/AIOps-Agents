# -*- coding: utf-8 -*-
# tests/test_integration_auth.py
# 🔧 P0-8: 认证集成测试

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from httpx import AsyncClient  # noqa: F401

from core.audit_service import AuditService
from core.authentication import (
    create_access_token,
    hash_password,
    validate_password_complexity,
    verify_password,
    verify_token,
)
from core.mfa_service import MFAService  # noqa: F401
from core.user_service import UserService  # noqa: F401


@pytest.mark.asyncio
class TestAuthenticationIntegration:
    """认证集成测试"""

    async def test_user_registration_flow(self):
        """测试用户注册完整流程"""
        # 1. 验证密码复杂度
        password = "SecureP@ssw0rd2024"
        is_valid, error = validate_password_complexity(password)
        assert is_valid, error

        # 2. 哈希密码
        hashed = hash_password(password)
        assert hashed is not None
        assert hashed != password

        # 3. 创建用户
        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = None
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.username = "newuser"
            mock_session.refresh.return_value = mock_user
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            user = await UserService.create_user(
                username="newuser",
                hashed_password=hashed,
                email="new@example.com",
                role="user",
            )

            assert user is not None
            assert user.username == "newuser"

    async def test_login_with_mfa_flow(self):
        """测试带MFA的登录流程"""
        username = "testuser"
        password = "SecureP@ssw0rd2024"

        # 1. 验证用户和密码
        with patch("core.authentication.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.username = username
            mock_user.hashed_password = hash_password(password)
            mock_user.mfa_enabled = True
            mock_user.mfa_secret = MFAService.generate_secret()
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            # 2. 验证密码
            assert verify_password(password, mock_user.hashed_password)

            # 3. 检查MFA状态
            is_mfa_enabled = await MFAService.is_mfa_enabled(username)
            assert is_mfa_enabled

            # 4. 生成TOTP令牌
            totp = MFAService.generate_totp(mock_user.mfa_secret)
            token = totp.now()

            # 5. 验证MFA令牌
            mfa_valid = await MFAService.verify_user_mfa(username, token)
            assert mfa_valid

    async def test_password_change_with_audit(self):
        """测试密码修改及审计日志"""
        username = "testuser"
        old_password = "OldP@ssw0rd123"
        new_password = "NewP@ssw0rd456"

        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            # Mock user service
            mock_user = MagicMock()
            mock_user.username = username
            mock_user.hashed_password = hash_password(old_password)
            mock_user.id = 1

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar_one_or_none.return_value = mock_user
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            # 1. 验证旧密码
            assert verify_password(old_password, mock_user.hashed_password)

            # 2. 验证新密码复杂度
            is_valid, error = validate_password_complexity(new_password)
            assert is_valid, error

            # 3. 更新密码
            new_hashed = hash_password(new_password)
            success = await UserService.update_password(username, new_hashed)
            assert success

            # 4. 记录审计日志
            with patch("core.audit_service.AsyncSessionLocal") as mock_audit_session:
                mock_audit = AsyncMock()
                mock_audit.add = MagicMock()
                mock_audit.commit = AsyncMock()
                mock_audit.refresh = AsyncMock()
                mock_log = MagicMock()
                mock_log.id = 1
                mock_audit.refresh.return_value = mock_log
                mock_audit.__aenter__.return_value = mock_audit
                mock_audit.__aexit__.return_value = None
                mock_audit_session.return_value = mock_audit

                log_id = await AuditService.log_action(
                    action="change_password",
                    resource_type="user",
                    resource_id=str(mock_user.id),
                    username=username,
                    status="success",
                )

                assert log_id is not None

    async def test_token_lifecycle(self):
        """测试令牌生命周期"""
        username = "testuser"

        # 1. 创建访问令牌
        token = create_access_token(data={"sub": username, "role": "user"})
        assert token is not None

        # 2. 验证令牌
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == username
        assert payload["role"] == "user"

    async def test_user_deletion_with_audit(self):
        """测试用户删除及审计日志"""
        username = "testuser"

        with patch("core.user_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            # 1. 删除用户
            success = await UserService.delete_user(username)
            assert success

            # 2. 记录审计日志
            with patch("core.audit_service.AsyncSessionLocal") as mock_audit_session:
                mock_audit = AsyncMock()
                mock_audit.add = MagicMock()
                mock_audit.commit = AsyncMock()
                mock_audit.refresh = AsyncMock()
                mock_log = MagicMock()
                mock_log.id = 1
                mock_audit.refresh.return_value = mock_log
                mock_audit.__aenter__.return_value = mock_audit
                mock_audit.__aexit__.return_value = None
                mock_audit_session.return_value = mock_audit

                log_id = await AuditService.log_action(
                    action="delete_user",
                    resource_type="user",
                    resource_id=username,
                    username="admin",
                    status="success",
                )

                assert log_id is not None

    async def test_mfa_enable_disable_flow(self):
        """测试MFA启用和禁用流程"""
        username = "testuser"

        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = False
            mock_user.mfa_secret = None
            mock_user.recovery_codes = None
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)
            mock_user_service.enable_mfa = AsyncMock(return_value=True)
            mock_user_service.disable_mfa = AsyncMock(return_value=True)

            # 1. 启用MFA
            secret, qr_code, recovery_codes = await MFAService.enable_mfa_for_user(username)
            assert secret is not None
            assert qr_code is not None
            assert len(recovery_codes) == 10

            # 2. 验证MFA已启用
            mock_user.mfa_enabled = True
            is_enabled = await MFAService.is_mfa_enabled(username)
            assert is_enabled

            # 3. 禁用MFA
            success = await MFAService.disable_mfa_for_user(username)
            assert success

            # 4. 验证MFA已禁用
            mock_user.mfa_enabled = False
            is_enabled = await MFAService.is_mfa_enabled(username)
            assert not is_enabled

    async def test_audit_log_query_and_filter(self):
        """测试审计日志查询和过滤"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_log = MagicMock()
            mock_log.id = 1
            mock_log.action = "login"
            mock_log.resource_type = "user"
            mock_log.resource_id = "1"
            mock_log.user_id = 1
            mock_log.username = "testuser"
            mock_log.ip_address = "127.0.0.1"
            mock_log.status = "success"
            mock_log.details = None
            mock_log.metadata = None
            mock_log.created_at = datetime.now()

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_log]
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            # 1. 查询所有日志
            logs = await AuditService.get_audit_logs(limit=10)
            assert len(logs) == 1

            # 2. 按用户过滤
            logs = await AuditService.get_audit_logs(username="testuser")
            assert len(logs) == 1

            # 3. 按操作类型过滤
            logs = await AuditService.get_audit_logs(action="login")
            assert len(logs) == 1

    async def test_user_activity_summary(self):
        """测试用户活动摘要"""
        username = "testuser"

        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()

            # Mock count results
            mock_total_result = MagicMock()
            mock_total_result.scalar.return_value = 50
            mock_success_result = MagicMock()
            mock_success_result.scalar.return_value = 45

            # Mock action grouping
            mock_action_result = MagicMock()
            mock_action_row = MagicMock()
            mock_action_row.action = "login"
            mock_action_row.count = 30
            mock_action_result.__iter__ = Mock(return_value=iter([mock_action_row]))

            call_count = [0]

            def execute_side_effect(stmt):
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_total_result
                elif call_count[0] == 2:
                    return mock_success_result
                else:
                    return mock_action_result

            mock_session.execute = AsyncMock(side_effect=execute_side_effect)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            summary = await AuditService.get_user_activity_summary(username, days=30)

            assert summary["username"] == username
            assert summary["period_days"] == 30
            assert summary["total_actions"] == 50
            assert summary["successful_actions"] == 45
