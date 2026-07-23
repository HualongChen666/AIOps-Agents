# -*- coding: utf-8 -*-
# core/test/test_factory.py
# 测试数据工厂 - 横向测试支持层
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AlertData:
    """告警数据"""

    metric: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    level: str = "warning"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SSHLogData:
    """SSH日志数据"""

    host_name: str
    failed_logins: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: str = "127.0.0.1"
    username: str = "root"


class TestFactory:
    """测试数据工厂"""

    @staticmethod
    def create_alert(**kwargs) -> AlertData:
        """创建测试告警数据"""
        defaults: Dict[str, Any] = {
            "metric": "cpu.usage",
            "value": 90.0,
            "threshold": 80.0,
            "level": "warning",
        }
        defaults.update(kwargs)
        return AlertData(**defaults)

    @staticmethod
    def create_ssh_log(**kwargs) -> SSHLogData:
        """创建测试SSH日志数据"""
        defaults: Dict[str, Any] = {
            "host_name": "test-host",
            "failed_logins": 5,
            "ip_address": "192.168.1.1",
            "username": "root",
        }
        defaults.update(kwargs)
        return SSHLogData(**defaults)

    @staticmethod
    def create_alert_dict(**kwargs) -> Dict[str, Any]:
        """创建测试告警字典"""
        alert = TestFactory.create_alert(**kwargs)
        return {
            "metric": alert.metric,
            "value": alert.value,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp.isoformat(),
            "level": alert.level,
            "metadata": alert.metadata,
        }

    @staticmethod
    def create_ssh_log_dict(**kwargs) -> Dict[str, Any]:
        """创建测试SSH日志字典"""
        log = TestFactory.create_ssh_log(**kwargs)
        return {
            "host_name": log.host_name,
            "failed_logins": log.failed_logins,
            "timestamp": log.timestamp.isoformat(),
            "ip_address": log.ip_address,
            "username": log.username,
        }

    @staticmethod
    def create_batch_alerts(count: int, **kwargs) -> List[Dict[str, Any]]:
        """创建批量测试告警"""
        alerts = []
        for i in range(count):
            alert = TestFactory.create_alert(
                metric=f"test.metric.{i}", value=80.0 + i, threshold=80.0, **kwargs
            )
            alerts.append(
                {
                    "metric": alert.metric,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "timestamp": alert.timestamp.isoformat(),
                    "level": alert.level,
                    "metadata": alert.metadata,
                }
            )
        return alerts
