# -*- coding: utf-8 -*-
# core/test/test_config.py
# 测试配置管理器 - 横向测试支持层
from typing import Any, Dict


class TestConfig:
    """测试配置管理器"""

    def __init__(self):
        """初始化测试配置"""
        self._overrides: Dict[str, Any] = {}
        self._real_config: Dict[str, Any] = {}

    def set_real_config(self, config: Dict[str, Any]):
        """设置真实配置"""
        self._real_config = config

    def override(self, key: str, value: Any):
        """覆盖配置值"""
        self._overrides[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置（优先使用测试覆盖）"""
        if key in self._overrides:
            return self._overrides[key]
        return self._real_config.get(key, default)

    def reset_overrides(self):
        """重置所有覆盖"""
        self._overrides.clear()

    def set_test_mode(self):
        """进入测试模式，设置测试友好的默认值"""
        self._overrides = {
            "SSH_WINDOW_SEC": 10,  # 测试时使用短窗口
            "SSH_FAIL_THRESHOLD": 2,  # 测试时使用低阈值
            "ALERT_RETENTION_DAYS": 1,  # 测试时保留1天
            "CACHE_TTL": 1,  # 测试时缓存1秒
            "RETRY_MAX_ATTEMPTS": 2,  # 测试时重试2次
            "TIMEOUT_SECONDS": 1,  # 测试时超时1秒
        }

    def restore_production_mode(self):
        """恢复生产模式"""
        self._overrides.clear()


# 全局测试配置实例
_test_config = TestConfig()


def get_test_config() -> TestConfig:
    """获取全局测试配置实例"""
    return _test_config
