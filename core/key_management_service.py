# -*- coding: utf-8 -*-

"""
密钥管理服务
Key Management Service

为AIOps Agent提供统一的密钥管理服务，支持多种后端：
- 环境变量（默认）
- 文件存储
- 未来可扩展：AWS Secrets Manager、Azure Key Vault、HashiCorp Vault
"""

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class KeyBackend(ABC):
    """密钥后端抽象基类"""

    @abstractmethod
    def get_key(self, key_name: str) -> Optional[str]:
        """获取密钥"""

    @abstractmethod
    def set_key(self, key_name: str, value: str) -> bool:
        """设置密钥"""

    @abstractmethod
    def delete_key(self, key_name: str) -> bool:
        """删除密钥"""

    @abstractmethod
    def key_exists(self, key_name: str) -> bool:
        """检查密钥是否存在"""


class EnvironmentKeyBackend(KeyBackend):
    """环境变量密钥后端"""

    def __init__(self):
        self._prefix = "AIOPS_"

    def get_key(self, key_name: str) -> Optional[str]:
        """从环境变量获取密钥"""
        # 尝试带前缀和不带前缀的键名
        env_key = f"{self._prefix}{key_name.upper()}"
        value = os.getenv(env_key) or os.getenv(key_name)

        if value:
            logger.debug(f"Retrieved key from environment: {env_key}")

        return value

    def set_key(self, key_name: str, value: str) -> bool:
        """设置环境变量密钥（仅在当前进程有效）"""
        env_key = f"{self._prefix}{key_name.upper()}"
        os.environ[env_key] = value
        logger.debug(f"Set key in environment: {env_key}")
        return True

    def delete_key(self, key_name: str) -> bool:
        """删除环境变量密钥（仅在当前进程有效）"""
        env_key = f"{self._prefix}{key_name.upper()}"
        if env_key in os.environ:
            del os.environ[env_key]
            logger.debug(f"Deleted key from environment: {env_key}")
            return True
        return False

    def key_exists(self, key_name: str) -> bool:
        """检查环境变量密钥是否存在"""
        env_key = f"{self._prefix}{key_name.upper()}"
        return env_key in os.environ or key_name in os.environ


class FileKeyBackend(KeyBackend):
    """文件存储密钥后端"""

    def __init__(self, file_path: str = "secrets.json"):
        self.file_path = Path(file_path)
        self._keys: Dict[str, str] = {}
        self._load_keys()

    def _load_keys(self):
        """从文件加载密钥"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._keys = json.load(f)
                logger.info(f"Loaded {len(self._keys)} keys from {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to load keys from {self.file_path}: {e}")
                self._keys = {}
        else:
            logger.info(f"Key file {self.file_path} does not exist, starting with empty key store")
            self._keys = {}

    def _save_keys(self) -> bool:
        """保存密钥到文件"""
        try:
            # 确保目录存在
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # 设置文件权限（仅所有者可读写）
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._keys, f, indent=2)

            # 在Unix系统上设置文件权限为600（仅所有者可读写）
            try:
                import stat

                os.chmod(self.file_path, stat.S_IRUSR | stat.S_IWUSR)
                logger.debug(f"Set file permissions to 600 for {self.file_path}")
            except (OSError, AttributeError) as e:
                # chmod may fail on Windows or non-Unix systems
                logger.debug(f"chmod not supported on this platform: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error setting file permissions: {e}")

            logger.debug(f"Saved {len(self._keys)} keys to {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save keys to {self.file_path}: {e}")
            return False

    def get_key(self, key_name: str) -> Optional[str]:
        """从文件获取密钥"""
        value = self._keys.get(key_name)
        if value:
            logger.debug(f"Retrieved key from file: {key_name}")
        return value

    def set_key(self, key_name: str, value: str) -> bool:
        """设置密钥到文件"""
        self._keys[key_name] = value
        return self._save_keys()

    def delete_key(self, key_name: str) -> bool:
        """从文件删除密钥"""
        if key_name in self._keys:
            del self._keys[key_name]
            return self._save_keys()
        return False

    def key_exists(self, key_name: str) -> bool:
        """检查文件中密钥是否存在"""
        return key_name in self._keys


class KeyManagementService:
    """
    统一密钥管理服务

    支持多后端密钥管理，提供统一的密钥访问接口
    支持密钥轮换和缓存机制
    """

    def __init__(self, backend_type: str = "environment", **backend_config):
        """
        初始化密钥管理服务

        Args:
            backend_type: 后端类型 (environment, file)
            backend_config: 后端配置参数
        """
        self.backend = self._create_backend(backend_type, **backend_config)
        self._cache: Dict[str, Dict[str, Any]] = {}  # Key cache with metadata
        self._cache_ttl = backend_config.get("cache_ttl", 300)  # Default 5 minutes
        self._rotation_schedule: Dict[str, datetime] = {}  # Key rotation schedule
        logger.info(f"Key management service initialized with {backend_type} backend")

    def _create_backend(self, backend_type: str, **config) -> KeyBackend:
        """创建密钥后端"""
        if backend_type == "environment":
            return EnvironmentKeyBackend()
        elif backend_type == "file":
            file_path = config.get("file_path", "secrets.json")
            return FileKeyBackend(file_path)
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")

    def get_key(
        self, key_name: str, default: Optional[str] = None, required: bool = False
    ) -> Optional[str]:
        """
        获取密钥

        Args:
            key_name: 密钥名称
            default: 默认值（如果密钥不存在）
            required: 是否必需（如果为True且密钥不存在，抛出异常）

        Returns:
            密钥值

        Raises:
            ValueError: 如果密钥不存在且required=True
        """
        value = self.backend.get_key(key_name)

        if value is None:
            if required:
                raise ValueError(f"Required key '{key_name}' not found in key store")
            return default

        return value

    def set_key(self, key_name: str, value: str) -> bool:
        """设置密钥"""
        return self.backend.set_key(key_name, value)

    def delete_key(self, key_name: str) -> bool:
        """删除密钥"""
        return self.backend.delete_key(key_name)

    def key_exists(self, key_name: str) -> bool:
        """检查密钥是否存在"""
        return self.backend.key_exists(key_name)

    def get_jwt_secret_key(self, required: bool = True) -> str:
        """获取JWT密钥"""
        key = self.get_key("JWT_SECRET_KEY", required=required)
        if key is None and required:
            raise ValueError("JWT_SECRET_KEY is required but not found")
        return key or ""

    def get_database_password(self, required: bool = True) -> str:
        """获取数据库密码"""
        key = self.get_key("DATABASE_PASSWORD", required=required)
        if key is None and required:
            raise ValueError("DATABASE_PASSWORD is required but not found")
        return key or ""

    def get_api_key(self, service_name: str, required: bool = False) -> Optional[str]:
        """获取API密钥"""
        return self.get_key(f"{service_name.upper()}_API_KEY", required=required)

    def _get_cached_key(self, key_name: str) -> Optional[str]:
        """Get key from cache if still valid."""
        if key_name in self._cache:
            cached_data = self._cache[key_name]
            if time.time() < cached_data["expires_at"]:
                logger.debug(f"Retrieved key from cache: {key_name}")
                return str(cached_data["value"])
            else:
                # Cache expired, remove it
                del self._cache[key_name]
        return None

    def _cache_key(self, key_name: str, value: str):
        """Cache a key with TTL."""
        self._cache[key_name] = {
            "value": value,
            "cached_at": time.time(),
            "expires_at": time.time() + self._cache_ttl,
        }
        logger.debug(f"Cached key: {key_name} (TTL: {self._cache_ttl}s)")

    def get_key_with_cache(
        self,
        key_name: str,
        default: Optional[str] = None,
        required: bool = False,
        use_cache: bool = True,
    ) -> Optional[str]:
        """
        Get key with caching support.

        Args:
            key_name: 密钥名称
            default: 默认值（如果密钥不存在）
            required: 是否必需（如果为True且密钥不存在，抛出异常）
            use_cache: 是否使用缓存

        Returns:
            密钥值
        """
        # Try cache first
        if use_cache:
            cached_value = self._get_cached_key(key_name)
            if cached_value is not None:
                return cached_value

        # Get from backend
        value = self.get_key(key_name, default=default, required=required)

        # Cache the value
        if value is not None and use_cache:
            self._cache_key(key_name, value)

        return value

    def rotate_key(self, key_name: str, new_value: str, old_value_retention: int = 86400) -> bool:
        """
        Rotate a key to a new value while keeping the old value for a grace period.

        Args:
            key_name: 密钥名称
            new_value: 新的密钥值
            old_value_retention: 旧密钥保留时间（秒），默认24小时

        Returns:
            是否成功轮换
        """
        try:
            # Get current value
            current_value = self.get_key(key_name)

            if current_value:
                # Store old value with timestamp for grace period
                old_key_name = f"{key_name}_old_{int(time.time())}"
                self.set_key(old_key_name, current_value)

                # Schedule cleanup of old key
                cleanup_time = datetime.now() + timedelta(seconds=old_value_retention)
                self._rotation_schedule[old_key_name] = cleanup_time

                logger.info(
                    f"Key rotation scheduled: {old_key_name} will be cleaned up at {cleanup_time}"
                )

            # Set new value
            success = self.set_key(key_name, new_value)

            if success:
                # Clear cache to force refresh
                if key_name in self._cache:
                    del self._cache[key_name]

                logger.info(f"Key rotated successfully: {key_name}")

            return success

        except Exception as e:
            logger.error(f"Key rotation failed for {key_name}: {e}")
            return False

    def cleanup_old_keys(self) -> int:
        """
        Clean up expired old keys from rotation.

        Returns:
            清理的密钥数量
        """
        cleaned_count = 0
        current_time = datetime.now()

        # Find expired keys
        expired_keys = [
            old_key_name
            for old_key_name, cleanup_time in self._rotation_schedule.items()
            if current_time >= cleanup_time
        ]

        # Clean up expired keys
        for old_key_name in expired_keys:
            try:
                self.delete_key(old_key_name)
                del self._rotation_schedule[old_key_name]
                cleaned_count += 1
                logger.info(f"Cleaned up expired old key: {old_key_name}")
            except Exception as e:
                logger.error(f"Failed to clean up old key {old_key_name}: {e}")

        return cleaned_count

    def clear_cache(self):
        """Clear all cached keys."""
        self._cache.clear()
        logger.info("Key cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_keys": len(self._cache),
            "cache_ttl": self._cache_ttl,
            "scheduled_rotations": len(self._rotation_schedule),
            "cached_key_names": list(self._cache.keys()),
        }


# 全局密钥管理服务实例
_global_key_service: Optional[KeyManagementService] = None


def get_key_service(backend_type: str = "environment", **config) -> KeyManagementService:
    """
    获取全局密钥管理服务实例

    Args:
        backend_type: 后端类型
        config: 后端配置

    Returns:
        密钥管理服务实例
    """
    global _global_key_service

    if _global_key_service is None:
        _global_key_service = KeyManagementService(backend_type, **config)

    return _global_key_service


def initialize_key_management(backend_type: str = "environment", **config):
    """
    初始化全局密钥管理服务

    Args:
        backend_type: 后端类型
        config: 后端配置
    """
    global _global_key_service
    _global_key_service = KeyManagementService(backend_type, **config)
    logger.info(f"Global key management service initialized with {backend_type} backend")


# 导出便捷函数
__all__ = [
    "KeyBackend",
    "EnvironmentKeyBackend",
    "FileKeyBackend",
    "KeyManagementService",
    "get_key_service",
    "initialize_key_management",
]
