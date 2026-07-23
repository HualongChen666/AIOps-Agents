# -*- coding: utf-8 -*-
"""
linux_service.py
--------------
Linux 主机配置服务层

从 API 路由层提取的业务逻辑，提供主机配置查找等服务。
遵循分层架构原则：Controller → Service → Repository/Engine。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from config import LINUX_HOSTS  # type: ignore

logger = logging.getLogger(__name__)


# ============================================================
# 模块级常量
# ============================================================
_VALID_HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._\-:]+$")


# ============================================================
# Linux 主机配置服务
# ============================================================
class LinuxHostService:
    """Linux 主机配置服务"""

    def find_host_config(self, host_name: str) -> Optional[dict]:
        """
        根据主机名或 IP 查找配置

        Args:
            host_name: 主机名或 IP

        Returns:
            匹配的配置字典 / None（找不到）
        """
        if not host_name or not isinstance(host_name, str):
            return None

        # 防御：host_name 字符校验
        cleaned = host_name.strip()
        if not cleaned or not _VALID_HOSTNAME_PATTERN.match(cleaned):
            return None

        for h in LINUX_HOSTS:  # type: ignore
            if isinstance(h, dict) and (h.get("name") == cleaned or h.get("host") == cleaned):
                return h
        return None


# 默认服务实例
linux_host_service = LinuxHostService()
