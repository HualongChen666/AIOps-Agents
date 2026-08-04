# -*- coding: utf-8 -*-
"""
错误告警模块

提供错误告警功能，支持多种告警渠道。
"""

import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from core.error_logging.handler import ErrorLogHandler

logger = logging.getLogger(__name__)


class AlertChannel(ABC):
    """
    告警渠道抽象基类
    """

    @abstractmethod
    def send_alert(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        发送告警

        Args:
            message: 告警消息
            context: 上下文信息
        """


class EmailAlertChannel(AlertChannel):
    """
    邮件告警渠道
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
    ):
        """
        初始化邮件告警渠道

        Args:
            smtp_host: SMTP服务器地址
            smtp_port: SMTP服务器端口
            username: 用户名
            password: 密码
            from_addr: 发件人地址
            to_addrs: 收件人地址列表
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send_alert(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        发送邮件告警

        Args:
            message: 告警消息
            context: 上下文信息
        """
        try:
            msg = MIMEText(message)
            msg["Subject"] = "AIOps Agent 错误告警"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
        except Exception as e:
            logger.error("发送邮件告警失败: %s", e)


class SlackAlertChannel(AlertChannel):
    """
    Slack告警渠道
    """

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        """
        初始化Slack告警渠道

        Args:
            webhook_url: Slack Webhook URL
            channel: Slack频道
        """
        self.webhook_url = webhook_url
        self.channel = channel

    def send_alert(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        发送Slack告警

        Args:
            message: 告警消息
            context: 上下文信息
        """
        import requests

        try:
            payload = {
                "channel": self.channel,
                "text": message,
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {"title": k, "value": str(v), "short": True}
                            for k, v in (context or {}).items()
                        ],
                    }
                ],
            }
            requests.post(
                self.webhook_url,
                json=payload,  # type: ignore[arg-type]
                timeout=10,
            )
        except Exception as e:
            logger.error("发送Slack告警失败: %s", e)


class ErrorAlertManager:
    """
    错误告警管理器

    负责监控错误统计并在超过阈值时发送告警。
    """

    def __init__(self, error_handler: ErrorLogHandler):
        """
        初始化错误告警管理器

        Args:
            error_handler: 错误日志处理器
        """
        self.error_handler = error_handler
        self.alert_channels: List[AlertChannel] = []
        self.thresholds: Dict[str, int] = {
            "total_errors": 100,  # 总错误数阈值
            "error_rate": 10,  # 错误率阈值（错误/分钟）
            "specific_error": 50,  # 特定错误码阈值
        }

    def add_alert_channel(self, channel: AlertChannel):
        """
        添加告警渠道

        Args:
            channel: 告警渠道
        """
        self.alert_channels.append(channel)

    def set_threshold(self, metric: str, value: int):
        """
        设置告警阈值

        Args:
            metric: 指标名称
            value: 阈值
        """
        self.thresholds[metric] = value

    def check_alerts(self):
        """
        检查告警条件并发送告警
        """
        # 检查总错误数
        total_errors = self.error_handler.get_error_count()
        if total_errors > self.thresholds.get("total_errors", 100):
            self._send_alert(
                f"总错误数超过阈值: {total_errors} > {self.thresholds['total_errors']}",
                {"metric": "total_errors", "value": total_errors},
            )

        # 检查错误率
        error_rate = self.error_handler.get_error_rate(hours=1)
        if error_rate > self.thresholds.get("error_rate", 10):
            self._send_alert(
                f"错误率超过阈值: {error_rate:.2f} > {self.thresholds['error_rate']}",
                {"metric": "error_rate", "value": error_rate},
            )

        # 检查特定错误码
        top_errors = self.error_handler.get_top_errors(limit=10)
        for error_code, count in top_errors:
            if count > self.thresholds.get("specific_error", 50):
                self._send_alert(
                    f"错误码 {error_code} 频繁出现: {count} > {self.thresholds['specific_error']}",
                    {"metric": "specific_error", "error_code": error_code, "value": count},
                )

    def _send_alert(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        发送告警到所有渠道

        Args:
            message: 告警消息
            context: 上下文信息
        """
        for channel in self.alert_channels:
            channel.send_alert(message, context)


# 全局错误告警管理器实例
_error_alert_manager: Optional[ErrorAlertManager] = None


def get_error_alert_manager() -> ErrorAlertManager:
    """
    获取错误告警管理器实例

    Returns:
        错误告警管理器实例
    """
    global _error_alert_manager
    if _error_alert_manager is None:
        from core.error_logging import get_error_log_handler

        _error_alert_manager = ErrorAlertManager(get_error_log_handler())
    return _error_alert_manager


def check_error_alerts():
    """
    检查错误告警（便捷函数）
    """
    manager = get_error_alert_manager()
    manager.check_alerts()
