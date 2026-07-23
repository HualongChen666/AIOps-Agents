# -*- coding: utf-8 -*-
"""
config_service.py
-----------------
配置服务

提供统一的配置访问接口，替代直接从 config 模块导入。
支持配置的动态加载、验证和类型转换。
"""

from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Any, Dict, List, Optional

from config import (
    POSTGRES_URL,
    QDRANT_URL,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_URL,
)

logger = logging.getLogger(__name__)


class ConfigService:
    """配置服务类"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._lock = Lock()
        self._load_config()

    def _load_config(self) -> None:
        """加载配置到缓存"""
        try:
            # 从环境变量加载配置
            self._cache.update(
                {
                    # JWT 配置
                    "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me"),
                    "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
                    "JWT_ACCESS_EXPIRE_MINUTES": self._parse_int("JWT_ACCESS_EXPIRE_MINUTES", 30),
                    "JWT_ISSUER": os.getenv("JWT_ISSUER", "aiops-agent"),
                    "JWT_AUDIENCE": os.getenv("JWT_AUDIENCE", "aiops-api"),
                    # Redis 配置（使用 config 模块统一配置）
                    "REDIS_HOST": REDIS_HOST,
                    "REDIS_PORT": REDIS_PORT,
                    "REDIS_DB": REDIS_DB,
                    "REDIS_URL": REDIS_URL,
                    # 数据库配置（使用 config 模块统一配置）
                    "POSTGRES_URL": POSTGRES_URL,
                    # Qdrant 配置（使用 config 模块统一配置）
                    "QDRANT_URL": QDRANT_URL,
                    # Slack 配置
                    "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN", ""),
                    "SLACK_SIGNING_SECRET": os.getenv("SLACK_SIGNING_SECRET", ""),
                    "SLACK_DEFAULT_CHANNEL": os.getenv("SLACK_DEFAULT_CHANNEL", "#general"),
                    # 内部 API 配置
                    "INTERNAL_API_KEY": os.getenv("INTERNAL_API_KEY", ""),
                    "TRUST_PROXY_HEADER": os.getenv("TRUST_PROXY_HEADER", "X-Forwarded-For"),
                    # 基础目录
                    "BASE_DIR": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                }
            )
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")

    def _parse_int(self, key: str, default: int) -> int:
        """安全解析整型配置"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid {key}, using default {default}")
            return default

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值，如果不存在返回默认值
        """
        with self._lock:
            return self._cache.get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段

        Args:
            section: 配置段名称（如 "JWT", "REDIS"）

        Returns:
            配置段字典
        """
        with self._lock:
            section_upper = section.upper()
            return {k: v for k, v in self._cache.items() if k.startswith(section_upper)}

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值（运行时动态配置）

        Args:
            key: 配置键
            value: 配置值
        """
        with self._lock:
            self._cache[key] = value
            logger.debug(f"Configuration updated: {key}")

    def get_int(self, key: str, default: int = 0) -> int:
        """
        获取整型配置

        Args:
            key: 配置键
            default: 默认值

        Returns:
            整型配置值
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for {key}, using default {default}")
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        获取布尔型配置

        Args:
            key: 配置键
            default: 默认值

        Returns:
            布尔型配置值
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_list(
        self, key: str, default: Optional[List[str]] = None, separator: str = ","
    ) -> List[str]:
        """
        获取列表型配置

        Args:
            key: 配置键
            default: 默认值
            separator: 分隔符

        Returns:
            列表型配置值
        """
        value = self.get(key, "")
        if not value:
            return default or []
        return [item.strip() for item in str(value).split(separator) if item.strip()]

    def reload(self) -> None:
        """重新加载配置"""
        with self._lock:
            self._cache.clear()
            self._load_config()
            logger.info("Configuration reloaded")

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            所有配置字典
        """
        with self._lock:
            return self._cache.copy()


# 全局配置服务实例
config_service = ConfigService()


# 便捷函数
def get_config(key: str, default: Optional[Any] = None) -> Any:
    """获取配置值的便捷函数"""
    return config_service.get(key, default)


def get_config_section(section: str) -> Dict[str, Any]:
    """获取配置段的便捷函数"""
    return config_service.get_section(section)
