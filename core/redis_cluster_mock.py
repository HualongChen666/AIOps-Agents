# -*- coding: utf-8 -*-
# core/redis_cluster_mock.py
# Redis集群管理器的Mock实现
# 用于测试目的，提供基本的Redis功能

import time
from typing import Any, Dict, Optional


class RedisClusterManager:
    """Redis集群管理器的Mock实现"""

    def __init__(self):
        self._data_store: Dict[str, Any] = {}
        self._lock_store: Dict[str, bool] = {}

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置键值"""
        self._data_store[key] = {"value": value, "expires_at": time.time() + ttl if ttl else None}
        return True

    def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        if key in self._data_store:
            data = self._data_store[key]
            if data["expires_at"] is None or time.time() < data["expires_at"]:
                return data["value"]
            else:
                # 过期了，删除
                del self._data_store[key]
        return None

    def delete(self, key: str) -> bool:
        """删除键"""
        if key in self._data_store:
            del self._data_store[key]
            return True
        return False

    def distributed_lock(self, lock_key: str, ttl: int = 10) -> bool:
        """获取分布式锁"""
        if lock_key not in self._lock_store:
            self._lock_store[lock_key] = True
            return True
        return False

    def release_lock(self, lock_key: str) -> bool:
        """释放分布式锁"""
        if lock_key in self._lock_store:
            del self._lock_store[lock_key]
            return True
        return False
