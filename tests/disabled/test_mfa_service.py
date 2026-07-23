# -*- coding: utf-8 -*-
# tests/test_mfa_service.py
# 🔧 P0-7: MFA服务单元测试

from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest

from core.mfa_service import MFAService


class TestMFAService:
    """MFA服务测试"""

    def test_generate_secret(self):
        """测试生成MFA密钥"""
        secret = MFAService.generate_secret()

        assert secret is not None
        assert len(secret) > 0
        # Base32编码只包含特定字符
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_generate_totp(self):
        """测试生成TOTP对象"""
        secret = MFAService.generate_secret()
        totp = MFAService.generate_totp(secret)

        assert totp is not None
        assert isinstance(totp, pyotp.TOTP)

    def test_generate_qr_code(self):
        """测试生成QR码"""
        secret = MFAService.generate_secret()
        qr_code = MFAService.generate_qr_code(secret, "testuser")

        assert qr_code is not None
        assert qr_code.startswith("data:image/png;base64,")

    def test_verify_totp_success(self):
        """测试验证TOTP令牌 - 成功"""
        secret = MFAService.generate_secret()
        totp = MFAService.generate_totp(secret)
        token = totp.now()

        result = MFAService.verify_totp(secret, token)

        assert result is True

    def test_verify_totp_failure(self):
        """测试验证TOTP令牌 - 失败"""
        secret = MFAService.generate_secret()
        wrong_token = "000000"

        result = MFAService.verify_totp(secret, wrong_token)

        assert result is False

    def test_generate_recovery_codes(self):
        """测试生成恢复码"""
        codes = MFAService.generate_recovery_codes(count=10)

        assert len(codes) == 10
        for code in codes:
            assert "-" in code
            # 格式: XXXX-XXXX-XXXX
            parts = code.split("-")
            assert len(parts) == 3
            assert all(len(part) == 4 for part in parts)

    @pytest.mark.asyncio
    async def test_enable_mfa_for_user_success(self):
        """测试为用户启用MFA - 成功"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user_service.enable_mfa = AsyncMock(return_value=True)

            secret, qr_code, recovery_codes = await MFAService.enable_mfa_for_user("testuser")

            assert secret is not None
            assert qr_code is not None
            assert len(recovery_codes) == 10
            mock_user_service.enable_mfa.assert_called_once()

    @pytest.mark.asyncio
    async def test_enable_mfa_for_user_failure(self):
        """测试为用户启用MFA - 失败"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user_service.enable_mfa = AsyncMock(return_value=False)

            with pytest.raises(Exception):
                await MFAService.enable_mfa_for_user("testuser")

    @pytest.mark.asyncio
    async def test_disable_mfa_for_user_success(self):
        """测试为用户禁用MFA - 成功"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user_service.disable_mfa = AsyncMock(return_value=True)

            success = await MFAService.disable_mfa_for_user("testuser")

            assert success is True

    @pytest.mark.asyncio
    async def test_verify_user_mfa_with_totp(self):
        """测试验证用户MFA - 使用TOTP"""
        secret = MFAService.generate_secret()
        totp = MFAService.generate_totp(secret)
        token = totp.now()

        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = True
            mock_user.mfa_secret = secret
            mock_user.recovery_codes = None
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            result = await MFAService.verify_user_mfa("testuser", token)

            assert result is True

    @pytest.mark.asyncio
    async def test_verify_user_mfa_with_recovery_code(self):
        """测试验证用户MFA - 使用恢复码"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = True
            mock_user.mfa_secret = None
            mock_user.recovery_codes = '["ABCD-1234-EFGH"]'
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)
            mock_user_service.enable_mfa = AsyncMock()

            result = await MFAService.verify_user_mfa("testuser", "ABCD-1234-EFGH")

            assert result is True

    @pytest.mark.asyncio
    async def test_verify_user_mfa_mfa_disabled(self):
        """测试验证用户MFA - MFA未启用"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = False
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            result = await MFAService.verify_user_mfa("testuser", "123456")

            assert result is False

    @pytest.mark.asyncio
    async def test_is_mfa_enabled_true(self):
        """测试检查MFA是否启用 - 已启用"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = True
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            result = await MFAService.is_mfa_enabled("testuser")

            assert result is True

    @pytest.mark.asyncio
    async def test_is_mfa_enabled_false(self):
        """测试检查MFA是否启用 - 未启用"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = False
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            result = await MFAService.is_mfa_enabled("testuser")

            assert result is False

    @pytest.mark.asyncio
    async def test_is_mfa_enabled_user_not_found(self):
        """测试检查MFA是否启用 - 用户不存在"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user_service.get_user_by_username = AsyncMock(return_value=None)

            result = await MFAService.is_mfa_enabled("testuser")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_mfa_status_enabled(self):
        """测试获取MFA状态 - 已启用"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = True
            mock_user.mfa_secret = "secret"
            mock_user.recovery_codes = '["code1", "code2"]'
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            status = await MFAService.get_mfa_status("testuser")

            assert status["enabled"] is True
            assert status["has_secret"] is True
            assert status["has_recovery_codes"] is True

    @pytest.mark.asyncio
    async def test_get_mfa_status_disabled(self):
        """测试获取MFA状态 - 未启用"""
        with patch("core.mfa_service.user_service") as mock_user_service:
            mock_user = MagicMock()
            mock_user.mfa_enabled = False
            mock_user.mfa_secret = None
            mock_user.recovery_codes = None
            mock_user_service.get_user_by_username = AsyncMock(return_value=mock_user)

            status = await MFAService.get_mfa_status("testuser")

            assert status["enabled"] is False
            assert status["has_secret"] is False
            assert status["has_recovery_codes"] is False
