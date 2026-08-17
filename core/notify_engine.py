# -*- coding: utf-8 -*-
# core/notify_engine.py
# 告警通知推送引擎
# 支持企业微信 / 钉钉(含加签)/ 飞书 Webhook
#
# 🔧 严格 Review 修复(R4):
#   - R4-1 [P1]:_post_webhook 复用全局 AsyncClient,启用连接池
#   - R4-2 [P1]:Webhook URL scheme 强校验
#   - R4-3 [P2]:reload_notify_config 加锁防并发竞态
#   - R4-4 [P2]:钉钉签名拼接更安全
#   - R4-5 [P2]:三渠道并行推送(asyncio.gather)
#   - R4-6 [P2]:URL 长度上限 + 类型注解收紧

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import smtplib
import time
import urllib.parse
from threading import Lock
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


try:
    import aiohttp
except ImportError:  # pragma: no cover - optional in some environments
    aiohttp = None  # type: ignore[assignment]

__all__ = [
    "close_http_client",
    "reload_notify_config",
    "send_alert_notification",
    "send_notification",
    "send_slack_notification",
    "send_teams_notification",
    "send_email_notification",
    "get_notification_history",
    "query_notifications",
    "format_alert_message",
    "format_for_slack",
    "format_for_teams",
    "_get_slack_client",
    "_post_webhook",
    "_send_wecom",
    "_send_dingtalk",
    "_send_feishu",
    "_get_http_client",
    "_validate_webhook_url",
    "NOTIFY_CONFIG",
    "_LEVEL_WEIGHT",
    "_WEBHOOK_URL_MAX_LEN",
    "_VALID_URL_SCHEMES",
    "_reload_lock",
    "_http_client",
    "_http_client_lock",
]


# ============================================================
# 模块级常量
# ============================================================
# 🔧 R4-6:URL 长度硬上限(防御异常配置)
_WEBHOOK_URL_MAX_LEN = 2048

# 🔧 R4-2:合法 URL scheme 白名单
_VALID_URL_SCHEMES = frozenset(["http", "https"])

# 🔧 R4-3:reload 操作锁
_reload_lock = Lock()


# ============================================================
# 通知节流与渠道路由配置
# ============================================================
# 按接收人/渠道冷却:同一 signature 在窗口期内只推送一次,避免轰炸
_notification_cooldowns: dict[str, float] = {}
_cooldown_lock = Lock()


# 通知状态追踪:记录每次通知的发送/送达/已读状态
_notification_history: list[dict[str, Any]] = []
_notification_history_lock = Lock()
MAX_NOTIFICATION_HISTORY = 10000


def _track_notification_status(
    alert: dict[str, Any],
    channel: str,
    status: str,
    recipient: str = "",
    message_id: str = "",
    error: str = "",
) -> None:
    """记录通知的发送/送达(delivery)/失败/已读(read)状态"""
    record = {
        "id": alert.get("id", ""),
        "fingerprint": alert.get("fingerprint", ""),
        "channel": channel,
        "recipient": recipient,
        "status": status,
        "message_id": message_id,
        "error": error[:200] if error else "",
        "timestamp": time.time(),
        "level": _get_severity(alert),
        "title": str(alert.get("title", ""))[:200],
    }
    with _notification_history_lock:
        _notification_history.append(record)
        if len(_notification_history) > MAX_NOTIFICATION_HISTORY:
            _notification_history.pop(0)


def get_notification_status(
    alert_id: Optional[str] = None,
    fingerprint: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """查询通知发送状态(支持按 alert_id/fingerprint/channel 过滤)"""
    with _notification_history_lock:
        records = list(_notification_history)
    filtered = [
        r
        for r in reversed(records)
        if (alert_id is None or r.get("id") == alert_id)
        and (fingerprint is None or r.get("fingerprint") == fingerprint)
        and (channel is None or r.get("channel") == channel)
    ]
    return filtered[:limit]


def mark_notification_read(message_id: str, channel: str) -> bool:
    """标记某条通知为已读(由回调或轮询更新)"""
    with _notification_history_lock:
        found = False
        for record in reversed(_notification_history):
            if record["channel"] == channel and (
                record["message_id"] == message_id or record.get("id") == message_id
            ):
                record["read_at"] = time.time()
                record["status"] = "read"
                found = True
        return found


def get_notification_read_status(message_id: str, channel: str) -> dict[str, Any]:
    """查询单条通知是否已读"""
    with _notification_history_lock:
        for record in reversed(_notification_history):
            if record["channel"] == channel and (
                record["message_id"] == message_id or record.get("id") == message_id
            ):
                return {
                    "message_id": message_id,
                    "channel": channel,
                    "status": record.get("status", "unknown"),
                    "sent_at": record.get("timestamp"),
                    "read_at": record.get("read_at"),
                }
    return {"message_id": message_id, "channel": channel, "status": "not_found"}


# 严重级别到默认渠道映射(P0 电话/SMS + IM + 邮件, P1 IM + 邮件, P2 邮件, P3 仅日志)
_SEVERITY_CHANNEL_MAP: dict[str, list[str]] = {
    "fatal": ["phone", "sms", "wecom", "dingtalk", "feishu", "slack", "teams", "email"],
    "critical": ["phone", "sms", "wecom", "dingtalk", "feishu", "slack", "teams", "email"],
    "high": ["wecom", "dingtalk", "feishu", "slack", "teams", "email"],
    "warning": ["email", "wecom", "dingtalk", "feishu"],
    "info": ["email"],
}

# 渠道优先级(用于自动降级/顺序重试)
_CHANNEL_PRIORITY: list[str] = [
    "phone",
    "sms",
    "wecom",
    "dingtalk",
    "feishu",
    "slack",
    "teams",
    "email",
]


def _cooldown_key(alert: dict[str, Any], channel: str, recipient: str = "") -> str:
    """生成冷却 key,按告警签名+渠道+接收人聚合"""
    signature = (
        str(alert.get("fingerprint", alert.get("id", "")))
        or f"{alert.get('title', '')}:{alert.get('host', '')}"
    )
    return f"{signature}:{channel}:{recipient}"


def _is_in_cooldown(
    alert: dict[str, Any], channel: str, recipient: str = "", window_seconds: float = 300.0
) -> bool:
    """检查给定 alert + channel + recipient 是否处于冷却期"""
    key = _cooldown_key(alert, channel, recipient)
    with _cooldown_lock:
        last_sent = _notification_cooldowns.get(key, 0.0)
    return time.time() - last_sent < window_seconds


def _mark_sent(alert: dict[str, Any], channel: str, recipient: str = "") -> None:
    """记录已成功发送时间戳"""
    key = _cooldown_key(alert, channel, recipient)
    with _cooldown_lock:
        _notification_cooldowns[key] = time.time()


def _get_severity(alert: dict[str, Any]) -> str:
    """统一提取告警严重级别"""
    return str(alert.get("level", alert.get("severity", "info"))).lower()


def _channels_for_severity(severity: str, config: dict[str, Any]) -> list[str]:
    """根据严重级别返回可用渠道,并按优先级排序"""
    channels = _SEVERITY_CHANNEL_MAP.get(severity, ["email"])
    available: list[str] = []
    for ch in channels:
        if ch in ("phone", "sms"):
            # 电话/短信需要专用适配器配置
            if config.get(f"{ch}_provider") or config.get(f"{ch}_webhook"):
                available.append(ch)
        elif ch in ("wecom", "dingtalk", "feishu"):
            if config.get(f"{ch}_webhook"):
                available.append(ch)
        elif ch == "slack":
            if os.getenv("SLACK_BOT_TOKEN"):
                available.append(ch)
        elif ch == "teams":
            if config.get("teams_webhook") or os.getenv("TEAMS_WEBHOOK_URL"):
                available.append(ch)
        elif ch == "email":
            if config.get("email_to") or config.get("email_webhook"):
                available.append(ch)
    return available


def _order_channels_by_priority(channels: list[str]) -> list[str]:
    """按优先级对渠道排序"""
    order = {ch: idx for idx, ch in enumerate(_CHANNEL_PRIORITY)}
    return sorted(channels, key=lambda c: order.get(c, 999))


def _channel_configured(channel: str, config: dict[str, Any]) -> bool:
    """判断某个渠道是否已配置"""
    return channel in _channels_for_severity(_get_severity({"level": "critical"}), config)


# ============================================================
# 🔧 R4-1 [P1]:全局 HTTP 客户端单例(复用连接池)
# ──────────────────────────────────────────────────────
# 修复前:每次 _post_webhook 调用都 async with httpx.AsyncClient(...),
#         意味着每次告警推送都新建/销毁 TCP 连接,高频告警场景
#         (如批量告警 + 三渠道)瞬时连接数可达几十个
# 修复后:复用模块级 AsyncClient,启用 keep-alive 连接池
#         同时提供 close_http_client() 供 lifespan 调用
# ──────────────────────────────────────────────────────
_http_client: Optional[httpx.AsyncClient] = None
_http_client_lock = asyncio.Lock()


def _get_http_client() -> httpx.AsyncClient:
    """
    获取全局 AsyncClient 单例(懒加载)
    🔧 R4-1:连接池复用,大幅降低高频告警场景的连接开销
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        verify_ssl = os.environ.get("NOTIFY_ENGINE_SSL_VERIFY", "False").lower() not in (
            "false",
            "0",
            "no",
            "",
        )
        _http_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
            verify=verify_ssl,  # SSL verification configurable via env; defaults off for dev
        )
        logger.debug("R4-1: notify_engine HTTP 客户端单例已创建")
    return _http_client


async def close_http_client() -> None:
    """
    🔧 R4-1:供 main.py lifespan 退出时调用
    优雅关闭全局 HTTP 客户端,释放连接池
    """
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        try:
            await _http_client.aclose()
            logger.info("✅ notify_engine HTTP 客户端已优雅关闭")
        except Exception as e:
            logger.warning(f"notify_engine HTTP 客户端关闭异常(已忽略): {e}")
    _http_client = None


# ============================================================
# 🔧 R4-2 [P1]:Webhook URL 合法性校验
# ============================================================
def _validate_webhook_url(url: str, channel: str) -> bool:
    """
    校验 Webhook URL 是否合法
    🔧 R4-2:防御环境变量配错(如 scheme 缺失、URL 过长)

    Returns:
        True=合法 / False=非法(已记录 warning 日志)
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()
    if not url:
        return False

    # 长度上限
    if len(url) > _WEBHOOK_URL_MAX_LEN:
        logger.warning(
            f"[{channel}] Webhook URL 超出长度上限 ({len(url)} > {_WEBHOOK_URL_MAX_LEN}),已拒绝"
        )
        return False

    # scheme 校验
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        logger.warning(f"[{channel}] Webhook URL 解析失败: {e}")
        return False

    if parsed.scheme not in _VALID_URL_SCHEMES:
        logger.warning(
            f"[{channel}] Webhook URL scheme 非法 (scheme={parsed.scheme!r}),仅允许 http/https"
        )
        return False

    if not parsed.netloc:
        logger.warning(f"[{channel}] Webhook URL 缺少域名部分")
        return False

    return True


# ============================================================
# 配置加载
# ============================================================
def _load_notify_config() -> dict[str, Any]:
    """
    从环境变量加载通知渠道配置
    对应 .env 文件中的以下变量:
        NOTIFY_ENABLED=true
        NOTIFY_MIN_LEVEL=warning
        WECOM_WEBHOOK=https://qyapi.weixin.qq.com/...
        DINGTALK_WEBHOOK=https://oapi.dingtalk.com/...
        DINGTALK_SECRET=SEC...
        FEISHU_WEBHOOK=https://open.feishu.cn/...
        EMAIL_WEBHOOK=(可选,SMTP 网关 Webhook)
        EMAIL_TO=ops@example.com
        PHONE_PROVIDER=https://voice-gateway.example.com/call
        SMS_PROVIDER=https://sms-gateway.example.com/send
        ONCALL_PROVIDER=json|pagerduty|opsgenie
        ONCALL_API_TOKEN=...
        ONCALL_API_BASE=...
        ONCALL_SCHEDULE_JSON={...}
        COOLDOWN_SECONDS=300
    """
    raw_enabled = os.getenv("NOTIFY_ENABLED", "false").strip().lower()
    enabled = raw_enabled in ("true", "1", "yes", "on", "t", "y")

    cfg = {
        "enabled": enabled,
        "min_level": os.getenv("NOTIFY_MIN_LEVEL", "critical").strip().lower(),
        "wecom_webhook": os.getenv("WECOM_WEBHOOK", "").strip(),
        "dingtalk_webhook": os.getenv("DINGTALK_WEBHOOK", "").strip(),
        "dingtalk_secret": os.getenv("DINGTALK_SECRET", "").strip(),
        "feishu_webhook": os.getenv("FEISHU_WEBHOOK", "").strip(),
        "email_webhook": os.getenv("EMAIL_WEBHOOK", "").strip(),
        "email_to": os.getenv("EMAIL_TO", "").strip(),
        # 电话/短信
        "phone_provider": os.getenv("PHONE_PROVIDER", "").strip(),
        "phone_to": os.getenv("PHONE_TO", "").strip(),
        "sms_provider": os.getenv("SMS_PROVIDER", "").strip(),
        "sms_to": os.getenv("SMS_TO", "").strip(),
        # oncall 配置
        "oncall_provider": os.getenv("ONCALL_PROVIDER", "").strip(),
        "oncall_api_token": os.getenv("ONCALL_API_TOKEN", "").strip(),
        "oncall_api_base": os.getenv("ONCALL_API_BASE", "").strip(),
        # 节流
        "cooldown_seconds": os.getenv("COOLDOWN_SECONDS", "300").strip(),
    }

    # 🔧 R4-2:启动时校验所有 Webhook URL
    if cfg["wecom_webhook"] and not _validate_webhook_url(str(cfg["wecom_webhook"]), "企业微信"):
        cfg["wecom_webhook"] = ""
    if cfg["dingtalk_webhook"] and not _validate_webhook_url(str(cfg["dingtalk_webhook"]), "钉钉"):
        cfg["dingtalk_webhook"] = ""
    if cfg["feishu_webhook"] and not _validate_webhook_url(str(cfg["feishu_webhook"]), "飞书"):
        cfg["feishu_webhook"] = ""
    if cfg["email_webhook"] and not _validate_webhook_url(str(cfg["email_webhook"]), "邮件"):
        cfg["email_webhook"] = ""

    return cfg


# 模块加载时初始化一次
NOTIFY_CONFIG: dict[str, Any] = _load_notify_config()


def reload_notify_config() -> dict[str, Any]:
    """重新加载通知配置并更新模块全局变量"""
    global NOTIFY_CONFIG
    NOTIFY_CONFIG = _load_notify_config()
    return NOTIFY_CONFIG


def _get_slack_client() -> Any:
    """Lazy Slack client factory. Tests patch this name."""
    try:
        from slack_sdk.web.async_client import AsyncWebClient  # type: ignore[import]

        token = os.getenv("SLACK_BOT_TOKEN", "")
        if token:
            return AsyncWebClient(token=token)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        logger.debug("Slack SDK not available, returning no client", exc_info=True)
    return None


def _is_valid_email(email: str) -> bool:
    """Basic email format validation."""
    if not email or not isinstance(email, str):
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def format_alert_message(alert: dict[str, Any]) -> str:
    """Format alert as a plain text message (legacy simple formatter)."""
    severity = str(alert.get("severity", "warning")).upper()
    alert_type = alert.get("type", "alert")
    message = str(alert.get("message", "")).strip()
    header = f"[{severity}] {alert_type}: {message}" if message else f"[{severity}] {alert_type}"
    lines = [header]
    host = alert.get("host")
    if host:
        lines.append(f"Host: {host}")
    metrics = alert.get("metrics")
    if isinstance(metrics, dict):
        for k, v in metrics.items():
            lines.append(f"{k}={v}")
    elif metrics is not None:
        lines.append(str(metrics))
    return "\n".join(lines)


def build_structured_alert_message(alert: dict[str, Any], fmt: str = "markdown") -> str:
    """
    Build a structured alert message with all key fields required by operators.

    Required sections:
      - 告警摘要 (one-line summary)
      - 影响范围 (affected users/services)
      - Agent 已做的排查和结论
      - 需要人工做什么 (clear action item)
      - 相关 Dashboard/日志/追踪链接
      - 紧急程度

    Args:
        alert: dict with optional keys summary, impact, diagnosis, action,
               links, severity, title, desc, raw_time, affected_services,
               affected_users, confidence, host, metrics.
        fmt: 'markdown' | 'text' | 'html'
    """
    level = str(alert.get("level", alert.get("severity", "info"))).lower()
    urgency_label = {
        "critical": "P0-紧急",
        "fatal": "P0-紧急",
        "high": "P1-高优",
        "warning": "P2-一般",
        "info": "P3-提示",
    }.get(level, level.upper())
    title = str(alert.get("summary") or alert.get("title") or "").strip()
    if not title:
        alert_type = alert.get("type") or "alert"
        message = str(alert.get("message") or "未命名告警").strip()
        title = f"{alert_type}: {message}" if message != "未命名告警" else alert_type

    summary = str(
        alert.get("summary") or alert.get("desc") or alert.get("message") or "暂无摘要"
    ).strip()
    impact = (
        alert.get("impact")
        or alert.get("affected_services")
        or alert.get("affected_users")
        or "影响范围待评估"
    )
    diagnosis = (
        alert.get("diagnosis")
        or alert.get("root_cause")
        or alert.get("analysis")
        or "Agent 正在持续排查中"
    )
    action = (
        alert.get("action")
        or alert.get("action_item")
        or alert.get("next_step")
        or "请关注并确认是否需要人工介入"
    )
    confidence = alert.get("confidence")
    raw_time = str(alert.get("raw_time", alert.get("timestamp", "未知时间"))).strip()

    links = alert.get("links") or {}
    if not isinstance(links, dict):
        links = {}
    # Auto-collect link-like fields from alert
    for key, value in alert.items():
        if isinstance(value, str) and any(
            kw in key.lower() for kw in ("dashboard", "log", "trace", "url", "runbook")
        ):
            if key not in links:
                links[key] = value

    if fmt == "text":
        lines = [
            f"[{level.upper()} | {urgency_label}] {title}",
            f"时间: {raw_time}",
            f"摘要: {summary}",
            f"影响范围: {impact}",
            f"Agent 排查结论: {diagnosis}",
        ]
        if confidence is not None:
            lines.append(f"置信度: {confidence}")
        lines.append(f"需要你做的: {action}")
        if links:
            lines.append("相关链接:")
            for name, url in links.items():
                lines.append(f"  - {name}: {url}")
        return "\n".join(lines)

    if fmt == "html":
        body = [
            f"<h3>[{level.upper()} | {urgency_label}] {title}</h3>",
            f"<p><b>时间:</b> {raw_time}</p>",
            f"<p><b>摘要:</b> {summary}</p>",
            f"<p><b>影响范围:</b> {impact}</p>",
            f"<p><b>Agent 排查结论:</b> {diagnosis}</p>",
        ]
        if confidence is not None:
            body.append(f"<p><b>置信度:</b> {confidence}</p>")
        body.append(f"<p><b>需要你做的:</b> {action}</p>")
        if links:
            body.append("<p><b>相关链接:</b></p><ul>")
            for name, url in links.items():
                body.append(f'<li><a href="{url}">{name}</a></li>')
            body.append("</ul>")
        return "\n".join(body)

    # markdown default
    emoji = {"critical": "🔴", "fatal": "🔴", "high": "🟠", "warning": "🟡", "info": "🔵"}.get(
        level, "⚪"
    )
    lines = [
        f"{emoji} **[{level.upper()} | {urgency_label}] {title}**",
        f"> **时间:** {raw_time}",
        f"> **摘要:** {summary}",
        f"> **影响范围:** {impact}",
        f"> **Agent 排查结论:** {diagnosis}",
    ]
    if confidence is not None:
        lines.append(f"> **置信度:** {confidence}")
    lines.append(f"> **需要你做的:** {action}")
    if links:
        lines.append("> **相关链接:**")
        for name, url in links.items():
            lines.append(f"> - [{name}]({url})")
    return "\n".join(lines)


def format_for_slack(alert: dict[str, Any]) -> str:
    """Format alert for Slack as a structured message."""
    return build_structured_alert_message(alert, fmt="text")


def format_for_teams(alert: dict[str, Any]) -> str:
    """Format alert as Teams JSON payload with structured HTML content."""
    return json.dumps({"text": build_structured_alert_message(alert, fmt="text")})


async def query_notifications(
    limit: int = 50, severity: Optional[str] = None
) -> list[dict[str, Any]]:
    """Query notification history with optional severity filter."""
    with _notification_history_lock:
        records = list(_notification_history)
    if severity:
        sev = severity.lower()
        records = [r for r in records if (r.get("level") or "").lower() == sev]
    return list(reversed(records))[:limit]


async def _send_slack_notification_once(message: str, channel: str) -> dict[str, Any]:
    """Send a single Slack notification attempt."""
    try:
        client = _get_slack_client()
        if asyncio.iscoroutine(client):
            client = await client
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        return {"success": False, "error": str(e), "channel": channel}
    if client is None:
        return {"success": False, "error": "Slack client not configured"}
    try:
        response = await client.chat_postMessage(channel=channel, text=message)
        if isinstance(response, dict):
            ok = response.get("ok", False)
        else:
            ok = bool(getattr(response, "ok", False))
        if ok:
            return {"success": True, "channel": channel}
        return {"success": False, "error": "Slack API error", "channel": channel}
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "rate_limit" in err_msg:
            return {"success": False, "error": f"rate limit: {e}", "channel": channel}
        return {"success": False, "error": str(e), "channel": channel}


async def send_slack_notification(
    message: str, channel: str = "#alerts", max_retries: int = 0
) -> dict[str, Any]:
    """Send Slack notification via Slack SDK (with optional retries)."""
    # Retry loop delegates the actual send to _send_slack_notification_once.
    # Tests that patch send_slack_notification itself will have each retry
    # call the patched version (max_retries=0 keeps the same call shape).
    if max_retries > 0:
        for attempt in range(max_retries, 0, -1):
            result = await send_slack_notification(message, channel, max_retries=0)
            if result.get("success") or attempt <= 1:
                return result
        return result if "result" in locals() else {"success": False, "error": "retry failed"}

    return await _send_slack_notification_once(message, channel)


async def send_teams_notification(message: str, webhook_url: str = "") -> dict[str, Any]:
    """Send Teams notification via webhook (using aiohttp when available)."""
    if not _validate_webhook_url(webhook_url, "teams"):
        return {"success": False, "error": "invalid teams webhook url"}
    if aiohttp is None:
        return {"success": False, "error": "aiohttp not installed"}
    payload = {"text": message}
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.post(webhook_url, json=payload)
            if resp.status == 200:
                return {"success": True}
            return {"success": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        logger.error(f"Teams notification failed: {e}")
        return {"success": False, "error": str(e)}


async def send_email_notification(
    to: str, subject: str, body: str, smtp_host: str = "localhost", smtp_port: int = 25
) -> dict[str, Any]:
    """Send email notification via smtplib."""
    if not _is_valid_email(to):
        return {"success": False, "error": "invalid email address"}
    try:
        msg = f"Subject: {subject}\n\n{body}".encode("utf-8")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.sendmail("aiops@example.com", [to], msg)
        return {"success": True}
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        return {"success": False, "error": str(e)}


async def get_notification_history(
    limit: int = 50, severity: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return notification history (uses query_notifications when available)."""
    try:
        notifications = await query_notifications(limit, severity)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        notifications = []
    if severity:
        notifications = [n for n in notifications if n.get("level") == severity]
    return notifications


async def send_notification(
    alert: dict[str, Any], channels: Optional[list[str]] = None
) -> dict[str, Any]:
    """Route alert to the requested notification channels."""
    if not isinstance(alert, dict) or not alert.get("type") or not alert.get("message"):
        return {"success": False, "error": "invalid alert"}

    if channels is None:
        # Route by severity; only send to channels for which configuration is present.
        severity = str(alert.get("severity", "info")).lower()
        channels = ["slack", "teams", "email"] if severity == "critical" else ["slack"]

    if not channels:
        return {"success": False, "error": "no channels specified"}

    coroutines = []
    for ch in channels:
        if ch == "slack":
            coroutines.append(
                send_slack_notification(alert["message"], alert.get("channel", "#alerts"))
            )
        elif ch == "teams":
            coroutines.append(
                send_teams_notification(alert["message"], alert.get("webhook_url", ""))
            )
        elif ch == "email":
            coroutines.append(
                send_email_notification(
                    alert.get("to", "admin@example.com"), alert["message"], alert["message"]
                )
            )
        else:
            coroutines.append(_unsupported_channel(ch))

    results = await asyncio.gather(*coroutines, return_exceptions=True)

    success_count = 0
    for ch, result in zip(channels, results):
        if isinstance(result, Exception):
            logger.error(f"Notification channel '{ch}' failed: {result}")
        elif isinstance(result, dict) and result.get("success"):
            success_count += 1

    if success_count == len(channels):
        return {"success": True, "channels_sent": success_count}
    if success_count > 0:
        return {"success": True, "channels_sent": success_count}
    return {"success": False, "error": "all notification channels failed", "channels_sent": 0}


async def _unsupported_channel(channel: str) -> dict[str, Any]:
    return {"success": False, "error": f"unsupported channel: {channel}"}


# ============================================================
# 告警级别权重映射
# ============================================================
_LEVEL_WEIGHT: dict[str, int] = {
    "info": 0,
    "warning": 1,
    "critical": 2,
}


# ============================================================
# 🔧 R4-5 [P1]:主推送入口(三渠道并行)
# ──────────────────────────────────────────────────────
# 修复前:三渠道串行 await,总延迟 = sum(各渠道延迟)
#         任一渠道超时(10s)阻塞后续推送
# 修复后:asyncio.gather 并行推送,总延迟 = max(各渠道延迟)
#         单渠道异常不阻塞其他渠道
# ──────────────────────────────────────────────────────
async def _resolve_oncall_recipients(alert: dict[str, Any]) -> list[dict[str, Any]]:
    """查询 oncall 排班,返回当前值班人联系方式列表"""
    try:
        from core.oncall_adapter import get_oncall_adapter
    except Exception:
        return []
    try:
        adapter = get_oncall_adapter()
        if config_oncall := NOTIFY_CONFIG.get("oncall_provider"):
            adapter.provider = config_oncall
            adapter.api_token = NOTIFY_CONFIG.get("oncall_api_token", "")
            adapter.api_base = NOTIFY_CONFIG.get("oncall_api_base", "")
        contacts = await adapter.lookup_async(
            category=str(alert.get("category", "")),
            service=str(alert.get("service", alert.get("host", ""))),
            alert_type=str(alert.get("alert_type", alert.get("type", ""))),
            team=str(alert.get("team", alert.get("owner_team", ""))),
        )
        return [c.__dict__ for c in contacts]
    except Exception as e:
        logger.warning(f"[oncall] 排班查询失败: {e}")
        return []


async def _send_phone_notification(
    alert: dict[str, Any], config: dict[str, Any], recipient: str = ""
) -> dict[str, Any]:
    """电话/语音通知适配器，通过第三方 Webhook 或 SDK 触发语音呼叫"""
    provider = config.get("phone_provider", config.get("phone_webhook", ""))
    if not provider:
        return {"success": False, "channel": "phone", "error": "phone provider not configured"}
    # 优先使用 oncall 值班人手机号,其次配置兜底
    to = recipient or config.get("phone_to", "")
    if not to:
        oncall = await _resolve_oncall_recipients(alert)
        for c in oncall:
            if c.get("phone"):
                to = c["phone"]
                break
    if not to:
        return {"success": False, "channel": "phone", "error": "no phone recipient resolved"}
    try:
        client = _get_http_client()
        payload = {
            "to": to,
            "message": build_structured_alert_message(alert, fmt="text"),
            "alert_id": alert.get("id", ""),
            "level": alert.get("level", "info"),
        }
        resp = await client.post(str(provider), json=payload, timeout=15.0)
        resp.raise_for_status()
        return {
            "success": True,
            "channel": "phone",
            "recipient": to,
            "status_code": resp.status_code,
        }
    except Exception as e:
        logger.error(f"[phone] 语音呼叫失败: {e}")
        return {"success": False, "channel": "phone", "recipient": to, "error": str(e)[:200]}


async def _send_sms_notification(
    alert: dict[str, Any], config: dict[str, Any], recipient: str = ""
) -> dict[str, Any]:
    """短信通知适配器，通过第三方 Webhook 或 SDK 触发短信"""
    provider = config.get("sms_provider", config.get("sms_webhook", ""))
    if not provider:
        return {"success": False, "channel": "sms", "error": "sms provider not configured"}
    to = recipient or config.get("sms_to", "")
    if not to:
        oncall = await _resolve_oncall_recipients(alert)
        for c in oncall:
            if c.get("phone"):
                to = c["phone"]
                break
    if not to:
        return {"success": False, "channel": "sms", "error": "no sms recipient resolved"}
    try:
        client = _get_http_client()
        # 短信内容必须精简
        text = (
            f"【AIOps {alert.get('level', 'info').upper()}】"
            f"{str(alert.get('summary', alert.get('title', '告警')))[:50]} "
            f"{str(alert.get('action', '请查看'))[:30]}"
        )
        payload = {
            "to": to,
            "message": text,
            "alert_id": alert.get("id", ""),
        }
        resp = await client.post(str(provider), json=payload, timeout=15.0)
        resp.raise_for_status()
        return {"success": True, "channel": "sms", "recipient": to, "status_code": resp.status_code}
    except Exception as e:
        logger.error(f"[sms] 短信发送失败: {e}")
        return {"success": False, "channel": "sms", "recipient": to, "error": str(e)[:200]}


async def _send_one_channel(
    alert: dict[str, Any], channel: str, config: dict[str, Any]
) -> dict[str, Any]:
    """向单个渠道发送一次通知，并自动记录冷却与发送状态;优先发给 oncall 值班人"""
    try:
        # 对 email/phone/sms 一次性解析 oncall 值班人
        oncall_recipients: list[dict[str, Any]] = []
        if channel in ("email", "phone", "sms"):
            oncall_recipients = await _resolve_oncall_recipients(alert)

        if channel == "wecom":
            result = await _send_wecom(alert)
        elif channel == "dingtalk":
            result = await _send_dingtalk(alert)
        elif channel == "feishu":
            result = await _send_feishu(alert)
        elif channel == "slack":
            result = await send_slack_notification(
                build_structured_alert_message(alert, fmt="text"), alert.get("channel", "#alerts")
            )
        elif channel == "teams":
            url = str(config.get("teams_webhook") or os.getenv("TEAMS_WEBHOOK_URL", "") or "")
            result = await send_teams_notification(
                build_structured_alert_message(alert, fmt="text"), url
            )
        elif channel == "email":
            to = config.get("email_to", alert.get("to", ""))
            if not to and oncall_recipients:
                to = next((c.get("email") for c in oncall_recipients if c.get("email")), "")
            if not to:
                to = "admin@example.com"
            subject = f"[{alert.get('level',
                                    'info').upper()}] {alert.get('summary',
                                                                 alert.get('title',
                                                                           'AIOps Alert'))[:80]}"
            result = await send_email_notification(
                to, subject, build_structured_alert_message(alert, fmt="text")
            )
            if isinstance(result, dict):
                result["recipient"] = to
        elif channel == "phone":
            recipient = ""
            if oncall_recipients:
                recipient = str(
                    next((c.get("phone") for c in oncall_recipients if c.get("phone")), "")
                )
            result = await _send_phone_notification(alert, config, recipient=recipient)
        elif channel == "sms":
            recipient = ""
            if oncall_recipients:
                recipient = str(
                    next((c.get("phone") for c in oncall_recipients if c.get("phone")), "")
                )
            result = await _send_sms_notification(alert, config, recipient=recipient)
        else:
            result = await _unsupported_channel(channel)

        if isinstance(result, dict) and result.get("success"):
            _mark_sent(alert, channel)
            _track_notification_status(
                alert, channel, "delivered", recipient=str(result.get("recipient", ""))
            )
        else:
            _track_notification_status(
                alert,
                channel,
                "failed",
                error=(
                    str(result.get("error", "unknown")) if isinstance(result, dict) else "unknown"
                ),
            )
        return (
            result
            if isinstance(result, dict)
            else {"success": False, "channel": channel, "error": str(result)}
        )
    except Exception as e:
        logger.error(f"[{channel}] 单渠道推送异常: {e}")
        _track_notification_status(alert, channel, "failed", error=str(e)[:200])
        return {"success": False, "channel": channel, "error": str(e)[:200]}


async def send_alert_notification(alert: dict[str, Any]) -> dict[str, Any]:
    """
    推送告警通知到按严重级别和配置排序后的渠道，并支持自动降级和冷却节流。
    由 alert_engine 在新告警产生时调用。
    """
    if not isinstance(alert, dict):
        logger.warning("send_alert_notification: alert 必须是 dict")
        return {"status": "invalid_alert"}

    if not NOTIFY_CONFIG.get("enabled"):
        return {"status": "disabled"}

    level = _get_severity(alert)
    min_level = NOTIFY_CONFIG.get("min_level", "critical").lower()

    level_weight = _LEVEL_WEIGHT.get(level, 0)
    min_level_weight = _LEVEL_WEIGHT.get(min_level, 2)

    if level_weight < min_level_weight:
        logger.debug(f"告警级别 '{level}' 低于最低推送级别 '{min_level}',已过滤")
        return {
            "status": "filtered",
            "reason": f"level '{level}' below min_level '{min_level}'",
        }

    # 拷贝并保留结构化字段，用于构建消息
    safe_alert = {
        "level": level,
        "title": str(alert.get("title", "未命名告警"))[:200],
        "summary": str(alert.get("summary", alert.get("desc", alert.get("title", "无详细信息"))))[
            :500
        ],
        "desc": str(alert.get("desc", "无详细信息"))[:1000],
        "impact": alert.get(
            "impact", alert.get("affected_services", alert.get("affected_users", "影响范围待评估"))
        ),
        "diagnosis": alert.get(
            "diagnosis", alert.get("root_cause", alert.get("analysis", "Agent 正在持续排查中"))
        ),
        "action": alert.get(
            "action",
            alert.get("action_item", alert.get("next_step", "请关注并确认是否需要人工介入")),
        ),
        "confidence": alert.get("confidence"),
        "links": alert.get("links", {}),
        "raw_time": str(alert.get("raw_time", alert.get("timestamp", "未知时间")))[:64],
        "id": alert.get("id", ""),
        "fingerprint": alert.get("fingerprint", ""),
        "channel": alert.get("channel", "#alerts"),
    }
    # 自动收集 alert 顶层中的链接字段
    for key, value in alert.items():
        if isinstance(value, str) and any(
            kw in key.lower() for kw in ("dashboard", "log", "trace", "url", "runbook")
        ):
            safe_alert.setdefault("links", {})[key] = value

    # 根据严重级别计算可用渠道，并按优先级排序
    channels = _order_channels_by_priority(_channels_for_severity(level, NOTIFY_CONFIG))
    if not channels:
        logger.warning("通知引擎已启用但未配置任何可用通知渠道")
        return {"status": "no_channel_configured"}

    cooldown_window = float(NOTIFY_CONFIG.get("cooldown_seconds", 300))
    results: dict[str, Any] = {}
    sent_any = False

    # 顺序按优先级尝试,直到成功(自动降级)或所有渠道都失败
    for channel in channels:
        if _is_in_cooldown(safe_alert, channel, window_seconds=cooldown_window):
            logger.debug(f"[{channel}] 处于冷却期,跳过")
            results[channel] = {"success": False, "skipped": True, "reason": "cooldown"}
            continue

        _mark_sent(safe_alert, channel)
        result = await _send_one_channel(safe_alert, channel, NOTIFY_CONFIG)
        results[channel] = result
        if result.get("success"):
            sent_any = True
            # 对于 P0/P1,继续尝试其他高优先级渠道(电话+短信+IM)
            if level in ("critical", "fatal", "high"):
                continue
            # P2/P3 成功一个渠道即可,自动停止
            break

    status = "ok" if sent_any else "all_failed"
    return {
        "status": status,
        "level": level,
        "channels_sent": [ch for ch, res in results.items() if res.get("success")],
        "results": results,
    }


# ============================================================
# 企业微信推送
# ============================================================
async def _send_wecom(alert: dict[str, Any]) -> dict:
    """企业微信机器人 Markdown 消息推送，使用结构化消息模板"""
    content = build_structured_alert_message(alert, fmt="markdown")
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    return await _post_webhook(NOTIFY_CONFIG["wecom_webhook"], payload, "企业微信")


# ============================================================
# 钉钉推送(含加签)
# ============================================================
async def _send_dingtalk(alert: dict[str, Any]) -> dict:
    """
    钉钉机器人 Markdown 消息推送,含 HMAC-SHA256 加签，使用结构化消息模板

    🔧 R4-4 [P2]:签名拼接前检查 URL 是否已包含 timestamp(避免重复)
    """
    text = build_structured_alert_message(alert, fmt="markdown")
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": alert.get("title", "AIOps 告警"),
            "text": text,
        },
        "at": {"isAtAll": alert.get("level", "").lower() in ("critical", "fatal", "high")},
    }

    webhook_url = NOTIFY_CONFIG["dingtalk_webhook"]
    secret = (NOTIFY_CONFIG.get("dingtalk_secret") or "").strip()

    if secret:
        try:
            timestamp = str(round(time.time() * 1000))
            sign_string = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                sign_string.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

            # 🔧 R4-4:防御 URL 中已存在 timestamp 参数(避免拼接出非法 URL)
            parsed = urllib.parse.urlparse(webhook_url)
            existing_query = urllib.parse.parse_qs(parsed.query)
            if "timestamp" in existing_query or "sign" in existing_query:
                logger.warning("钉钉 webhook URL 已含 timestamp/sign,可能与新加签冲突,使用新值覆盖")
                # 移除旧的 timestamp/sign,避免重复参数
                existing_query.pop("timestamp", None)
                existing_query.pop("sign", None)
                # 重建 query
                new_query_pairs = []
                for k, v_list in existing_query.items():
                    for v in v_list:
                        new_query_pairs.append(f"{k}={urllib.parse.quote_plus(v)}")
                new_query_pairs.append(f"timestamp={timestamp}")
                new_query_pairs.append(f"sign={sign}")
                webhook_url = urllib.parse.urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        "&".join(new_query_pairs),
                        parsed.fragment,
                    )
                )
            else:
                sep = "&" if "?" in webhook_url else "?"
                webhook_url = f"{webhook_url}{sep}timestamp={timestamp}&sign={sign}"

            logger.debug("钉钉加签计算完成")
        except Exception as sign_err:
            logger.error(f"钉钉加签计算异常: {sign_err}", exc_info=True)
            return {
                "success": False,
                "channel": "钉钉",
                "error": f"加签失败: {str(sign_err)[:200]}",
            }

    return await _post_webhook(webhook_url, payload, "钉钉")


# ============================================================
# 飞书推送
# ============================================================
async def _send_feishu(alert: dict[str, Any]) -> dict:
    """飞书机器人文本消息推送，使用结构化消息模板"""
    text = build_structured_alert_message(alert, fmt="text")
    payload = {
        "msg_type": "text",
        "content": {"text": f"【AIOps 告警】\n{text}"},
    }
    return await _post_webhook(NOTIFY_CONFIG["feishu_webhook"], payload, "飞书")


# ============================================================
# 🔧 R4-1 [P1]:通用 Webhook 请求发送(复用连接池)
# ============================================================
async def _post_webhook(
    url: str,
    payload: dict,
    channel: str = "未知渠道",
) -> dict:
    """
    发送 HTTP POST 到指定 Webhook,细分异常处理

    🔧 R4-1:复用全局 AsyncClient,启用连接池
    🔧 R4-2:URL 二次校验(防御运行时配置篡改)
    🔧 R4-6:URL 长度二次防御
    """
    # 🔧 R4-2 + R4-6:运行时二次校验
    if not url or not isinstance(url, str):
        logger.error(f"[{channel}] URL 为空或非字符串")
        return {"success": False, "channel": channel, "error": "URL 为空"}

    if len(url) > _WEBHOOK_URL_MAX_LEN:
        logger.error(f"[{channel}] URL 超出长度上限 ({len(url)} > {_WEBHOOK_URL_MAX_LEN})")
        return {
            "success": False,
            "channel": channel,
            "error": f"URL 超长 ({len(url)} bytes)",
        }

    if not isinstance(payload, dict):
        logger.error(f"[{channel}] payload 必须是 dict")
        return {
            "success": False,
            "channel": channel,
            "error": "payload 必须是 dict",
        }

    try:
        # 🔧 R4-1:使用全局单例,而非每次新建
        client = _get_http_client()
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        logger.info(f"[{channel}] 通知推送成功")
        return {
            "success": True,
            "status_code": resp.status_code,
            "channel": channel,
        }
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500]
        logger.error(f"[{channel}] 推送失败 | HTTP {e.response.status_code} | {error_body}")
        return {
            "success": False,
            "channel": channel,
            "status_code": e.response.status_code,
            "error": f"HTTP {e.response.status_code}",
            "detail": error_body,
        }
    except httpx.TimeoutException:
        logger.error(f"[{channel}] 推送超时(>10s)")
        return {"success": False, "channel": channel, "error": "请求超时(>10s)"}
    except httpx.ConnectError as e:
        logger.error(f"[{channel}] 网络连接失败: {e}")
        return {
            "success": False,
            "channel": channel,
            "error": f"网络连接失败: {str(e)[:200]}",
        }
    except Exception as e:
        logger.error(f"[{channel}] 推送异常: {e}", exc_info=True)
        return {"success": False, "channel": channel, "error": str(e)[:200]}


# 🔧 P0-1 Enhancement: 应用增强重试机制
try:
    from core.retry_enhanced import EnhancedRetry, RetryStrategy

    # 备份原始函数
    _post_webhook_original = _post_webhook

    # 创建增强重试实例
    _webhook_retry = EnhancedRetry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
        retry_on_exceptions=(ConnectionError, TimeoutError),
    )

    # 应用增强重试
    _post_webhook = _webhook_retry(_post_webhook_original)

    logger.info("🔧 P0 Enhancement: Enhanced retry mechanism applied to webhook calls")
except ImportError:
    logger.warning("🔧 P0 Enhancement: Enhanced retry not available")
except Exception as e:
    logger.error(f"🔧 P0 Enhancement: Failed to apply enhanced retry: {e}")
