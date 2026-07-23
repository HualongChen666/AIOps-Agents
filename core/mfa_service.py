# -*- coding: utf-8 -*-
# core/mfa_service.py
# 🔧 P0-20: 多因素认证（MFA）服务
# 基于TOTP（Time-based One-Time Password）实现

from __future__ import annotations

import base64
import logging
import secrets
from io import BytesIO
from typing import List, Tuple

import pyotp
from qrcode import QRCode

from core.user_service import user_service

logger = logging.getLogger(__name__)


class MFAService:
    """多因素认证服务"""

    @staticmethod
    def generate_secret() -> str:
        """生成MFA密钥（Base32编码）"""
        return pyotp.random_base32()

    @staticmethod
    def generate_totp(secret: str) -> pyotp.TOTP:
        """根据密钥生成TOTP对象"""
        return pyotp.TOTP(secret, digits=6, interval=30)

    @staticmethod
    def generate_qr_code(secret: str, username: str, issuer: str = "AIOps Agent") -> str:
        """生成QR码的base64图像

        Args:
            secret: TOTP密钥
            username: 用户名
            issuer: 发行者名称

        Returns:
            base64编码的QR码图像（data URL格式）
        """
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=username, issuer_name=issuer)

        qr = QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """验证TOTP令牌

        Args:
            secret: TOTP密钥
            token: 用户输入的6位令牌

        Returns:
            验证是否成功
        """
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        return totp.verify(token, valid_window=1)  # 允许前后1个时间窗口的容错

    @staticmethod
    def generate_recovery_codes(count: int = 10) -> List[str]:
        """生成恢复码（用于MFA丢失时恢复）

        Args:
            count: 生成的恢复码数量

        Returns:
            恢复码列表
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            # 格式化为 XXXX-XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:12]}"
            codes.append(formatted_code)
        return codes

    @staticmethod
    async def enable_mfa_for_user(username: str) -> Tuple[str, str, List[str]]:
        """为用户启用MFA

        Args:
            username: 用户名

        Returns:
            (secret, qr_code_data_url, recovery_codes)
        """
        secret = MFAService.generate_secret()
        recovery_codes = MFAService.generate_recovery_codes()
        qr_code = MFAService.generate_qr_code(secret, username)

        # 保存到数据库
        success = await user_service.enable_mfa(username, secret, recovery_codes)
        if not success:
            raise Exception("启用MFA失败")

        logger.info(f"✅ MFA已为用户启用 | username={username}")
        return secret, qr_code, recovery_codes

    @staticmethod
    async def disable_mfa_for_user(username: str) -> bool:
        """为用户禁用MFA

        Args:
            username: 用户名

        Returns:
            是否成功
        """
        success = await user_service.disable_mfa(username)
        if success:
            logger.info(f"✅ MFA已为用户禁用 | username={username}")
        return success

    @staticmethod
    async def verify_user_mfa(username: str, token: str) -> bool:
        """验证用户的MFA令牌

        Args:
            username: 用户名
            token: TOTP令牌或恢复码

        Returns:
            验证是否成功
        """
        user = await user_service.get_user_by_username(username)
        if not user or not user.mfa_enabled:
            return False

        # 先检查是否为恢复码
        if "-" in token:  # 恢复码格式 XXXX-XXXX-XXXX
            import json

            recovery_codes_str = str(user.recovery_codes) if user.recovery_codes else "[]"
            recovery_codes = json.loads(recovery_codes_str)
            if token.upper() in recovery_codes:
                # 使用恢复码后需要移除
                recovery_codes.remove(token.upper())
                secret_str = str(user.mfa_secret) if user.mfa_secret else ""
                await user_service.enable_mfa(username, secret_str, recovery_codes)
                logger.info(f"✅ 用户使用恢复码登录成功 | username={username}")
                return True
            return False

        # 验证TOTP令牌
        if user.mfa_secret:
            secret_str = str(user.mfa_secret)
            return MFAService.verify_totp(secret_str, token)

        return False

    @staticmethod
    async def is_mfa_enabled(username: str) -> bool:
        """检查用户是否启用了MFA

        Args:
            username: 用户名

        Returns:
            是否启用MFA
        """
        user = await user_service.get_user_by_username(username)
        return bool(user.mfa_enabled) if user else False

    @staticmethod
    async def get_mfa_status(username: str) -> dict:
        """获取用户MFA状态

        Args:
            username: 用户名

        Returns:
            MFA状态字典
        """
        user = await user_service.get_user_by_username(username)
        if not user:
            return {"enabled": False}

        return {
            "enabled": user.mfa_enabled,
            "has_secret": bool(user.mfa_secret),
            "has_recovery_codes": bool(user.recovery_codes),
        }


# 默认MFA服务实例
mfa_service = MFAService()
