# -*- coding: utf-8 -*-
"""
Performance Regression Notifier
性能回归通知服务
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.performance_regression_detector import PerformanceRegressionDetector

logger = logging.getLogger(__name__)


@dataclass
class NotificationChannel:
    """通知渠道"""

    name: str
    enabled: bool
    config: Dict[str, Any]


class PerformanceRegressionNotifier:
    """性能回归通知器"""

    def __init__(self):
        """初始化通知器"""
        self.regression_detector = PerformanceRegressionDetector()
        self.channels: Dict[str, NotificationChannel] = {}
        self._setup_default_channels()

    def _setup_default_channels(self):
        """设置默认通知渠道"""
        # 邮件通知
        self.channels["email"] = NotificationChannel(
            name="email",
            enabled=False,
            config={
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "smtp_username": "",
                "smtp_password": "",  # nosec B105
                "from_email": "aiops@example.com",
                "to_emails": ["admin@example.com"],
            },
        )

        # Slack通知
        self.channels["slack"] = NotificationChannel(
            name="slack",
            enabled=False,
            config={
                "webhook_url": "",
                "channel": "#performance-alerts",
            },
        )

        # 钉钉通知
        self.channels["dingtalk"] = NotificationChannel(
            name="dingtalk",
            enabled=False,
            config={
                "webhook_url": "",
                "secret": "",  # nosec B105
            },
        )

    def enable_channel(self, channel_name: str, config: Dict[str, Any]):
        """启用通知渠道"""
        if channel_name in self.channels:
            self.channels[channel_name].enabled = True
            self.channels[channel_name].config.update(config)
            logger.info(f"通知渠道已启用: {channel_name}")
        else:
            logger.warning(f"未知的通知渠道: {channel_name}")

    def disable_channel(self, channel_name: str):
        """禁用通知渠道"""
        if channel_name in self.channels:
            self.channels[channel_name].enabled = False
            logger.info(f"通知渠道已禁用: {channel_name}")

    async def send_email_notification(
        self,
        subject: str,
        content: str,
        to_emails: List[str],
    ):
        """发送邮件通知"""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            channel = self.channels["email"]
            if not channel.enabled:
                logger.debug("邮件通知未启用")
                return

            config = channel.config
            msg = MIMEMultipart()
            msg["From"] = config["from_email"]
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject

            msg.attach(MIMEText(content, "plain", "utf-8"))

            with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
                server.starttls()
                server.login(config["smtp_username"], config["smtp_password"])
                server.send_message(msg)

            logger.info(f"邮件通知已发送: {subject}")

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}", exc_info=True)

    async def send_slack_notification(
        self,
        message: str,
    ):
        """发送Slack通知"""
        try:
            import httpx

            channel = self.channels["slack"]
            if not channel.enabled:
                logger.debug("Slack通知未启用")
                return

            config = channel.config
            webhook_url = config["webhook_url"]

            payload = {
                "text": message,
                "channel": config["channel"],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()

            logger.info("Slack通知已发送")

        except Exception as e:
            logger.error(f"发送Slack通知失败: {e}", exc_info=True)

    async def send_dingtalk_notification(
        self,
        message: str,
    ):
        """发送钉钉通知"""
        try:
            import base64
            import hashlib
            import hmac
            import time
            import urllib.parse

            import httpx

            channel = self.channels["dingtalk"]
            if not channel.enabled:
                logger.debug("钉钉通知未启用")
                return

            config = channel.config
            webhook_url = config["webhook_url"]
            secret = config["secret"]

            # 生成签名
            timestamp = str(round(time.time() * 1000))
            secret_enc = bytes((secret + "\n" + timestamp).encode("utf-8"))
            secret_dec = base64.b64encode(
                hmac.new(secret.encode("utf-8"), secret_enc, digestmod=hashlib.sha256).digest()
            ).decode()

            sign = urllib.parse.quote_plus(secret_dec)

            # 构建完整URL
            url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            payload = {
                "msgtype": "text",
                "text": {
                    "content": message,
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            logger.info("钉钉通知已发送")

        except Exception as e:
            logger.error(f"发送钉钉通知失败: {e}", exc_info=True)

    async def notify_regression(
        self,
        regression: Dict[str, Any],
        channels: Optional[List[str]] = None,
    ):
        """通知性能回归"""
        if channels is None:
            channels = ["email", "slack"]

        # 构建通知消息
        severity = regression.get("severity", "warning")
        component = regression.get("component", "unknown")
        deviation = regression.get("deviation", 0)
        baseline_value = regression.get("baseline_value", 0)
        current_value = regression.get("current_value", 0)

        subject = f"[{severity.upper()}] 性能回归检测: {component}"

        message = f"""
性能回归检测告警

组件: {component}
严重程度: {severity.upper()}
偏差: {deviation:.2%}
基准值: {baseline_value}
当前值: {current_value}
检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请及时处理！
"""

        # 发送通知
        for channel_name in channels:
            if channel_name == "email":
                await self.send_email_notification(
                    subject=subject,
                    content=message,
                    to_emails=self.channels["email"].config.get("to_emails", []),
                )
            elif channel_name == "slack":
                await self.send_slack_notification(message)
            elif channel_name == "dingtalk":
                await self.send_dingtalk_notification(message)

    async def notify_report(
        self,
        report: Dict[str, Any],
        channels: Optional[List[str]] = None,
    ):
        """通知性能报告"""
        if channels is None:
            channels = ["email"]

        report_type = report.get("report_type", "unknown")
        date = report.get("date", datetime.now().strftime("%Y-%m-%d"))

        subject = f"性能报告: {report_type} - {date}"

        summary = report.get("summary", {})
        message = f"""
性能报告

报告类型: {report_type}
日期: {date}
总测试数: {summary.get('total_tests', 0)}
总组件数: {summary.get('total_components', 0)}
总回归数: {summary.get('total_regressions', 0)}

详情请查看性能数据库。
"""

        for channel_name in channels:
            if channel_name == "email":
                await self.send_email_notification(
                    subject=subject,
                    content=message,
                    to_emails=self.channels["email"].config.get("to_emails", []),
                )

    async def check_and_notify_regressions(
        self,
        environment: str = "dev",
    ):
        """检查并通知性能回归"""
        try:
            # 获取活跃的回归
            regressions = await self.regression_detector.get_active_regressions(
                environment=environment, severity="critical"
            )

            # 通知每个回归
            for regression in regressions:
                await self.notify_regression(regression)

            logger.info(f"已通知 {len(regressions)} 个性能回归")

        except Exception as e:
            logger.error(f"检查和通知性能回归失败: {e}", exc_info=True)


# 全局实例
notifier = PerformanceRegressionNotifier()


def get_notifier() -> PerformanceRegressionNotifier:
    """获取通知器实例"""
    return notifier
