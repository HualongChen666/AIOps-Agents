# -*- coding: utf-8 -*-
# core/config/config_manager.py
# 配置管理器 - 横向配置层
from typing import Any, Dict


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self._config: Dict[str, Any] = {}
        self._test_mode = False
        self._test_overrides: Dict[str, Any] = {}

    def load_config(self, config: Dict[str, Any]):
        """加载配置"""
        self._config = config.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置（测试模式下优先使用测试覆盖）"""
        if self._test_mode and key in self._test_overrides:
            return self._test_overrides[key]
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置"""
        self._config[key] = value

    def enable_test_mode(self):
        """启用测试模式"""
        self._test_mode = True
        # 设置测试友好的默认值
        self._test_overrides = {
            "SSH_WINDOW_SEC": 10,
            "SSH_FAIL_THRESHOLD": 2,
            "ALERT_RETENTION_DAYS": 1,
            "CACHE_TTL": 1,
            "RETRY_MAX_ATTEMPTS": 2,
            "TIMEOUT_SECONDS": 1,
            "MAX_CONCURRENT_TASKS": 5,
            "BATCH_SIZE": 10,
        }

    def disable_test_mode(self):
        """禁用测试模式"""
        self._test_mode = False
        self._test_overrides.clear()

    def override_for_test(self, key: str, value: Any):
        """测试时覆盖配置"""
        if not self._test_mode:
            self.enable_test_mode()
        self._test_overrides[key] = value

    def get_ssh_config(self) -> Dict[str, Any]:
        """获取SSH检测配置"""
        return {
            "window_sec": self.get("SSH_WINDOW_SEC", 300),
            "fail_threshold": self.get("SSH_FAIL_THRESHOLD", 10),
        }

    def get_alert_config(self) -> Dict[str, Any]:
        """获取告警配置"""
        return {
            "retention_days": self.get("ALERT_RETENTION_DAYS", 30),
            "max_alerts_per_host": self.get("MAX_ALERTS_PER_HOST", 100),
            "alert_levels": self.get("ALERT_LEVELS", ["warning", "error", "critical"]),
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return {
            "ttl": self.get("CACHE_TTL", 3600),
            "max_size": self.get("CACHE_MAX_SIZE", 10000),
        }

    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能配置"""
        return {
            "retry_max_attempts": self.get("RETRY_MAX_ATTEMPTS", 3),
            "timeout_seconds": self.get("TIMEOUT_SECONDS", 30),
            "max_concurrent_tasks": self.get("MAX_CONCURRENT_TASKS", 100),
            "batch_size": self.get("BATCH_SIZE", 100),
        }


# 全局配置管理器实例
_config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    return _config_manager
