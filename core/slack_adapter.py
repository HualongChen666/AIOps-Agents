# -*- coding: utf-8 -*-
# core/slack_adapter.py
# Slack Block‑Kit 交互适配器
# 负责构造 Block‑Kit 消息、发送到 Slack 并处理交互（按钮点击）
# 采用 Slack Web API (chat.postMessage) 与交互端点 (Events API) 的最简实现
# - `post_message` : 发送普通/Block‑Kit 消息
# - `post_interactive_message` : 包含按钮/下拉列表的交互式消息
# - `verify_slack_signature` : 用于在 Slack Events 端点校验请求
#   （在实际部署时应在对应的 FastAPI 路由中调用）
# 依赖: httpx (已在项目中), loguru

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from config import SLACK_BOT_TOKEN, SLACK_DEFAULT_CHANNEL, SLACK_SIGNING_SECRET

_logger = logging.getLogger(__name__)

# 若未配置 token, 直接在调用时抛出明确错误
if not SLACK_BOT_TOKEN:
    _logger.info("Slack Bot Token 未配置, Slack 相关功能将不可用")

# ---------------------------------------------------------------------------
# 基础 HTTP 客户端（复用全局的 notify_engine http client）
# ---------------------------------------------------------------------------
# 这里直接使用 httpx.AsyncClient, 与项目中 notify_engine 的全局 client 类似。
# 为避免循环依赖, 不直接 import notify_engine, 而是自行创建轻量版单例。
_HTTP_CLIENT: Optional[httpx.AsyncClient] = None
_HTTP_CLIENT_LOCK = asyncio.Lock()


async def _get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=15.0)
    return _HTTP_CLIENT


# ---------------------------------------------------------------------------
# Slack API Helper
# ---------------------------------------------------------------------------
SLACK_API_BASE = "https://slack.com/api"


async def _post_json(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON 到 Slack API, 自动注入 Authorization 头.
    返回解析后的 JSON, 若 `ok` 为 False 抛出异常.
    """
    client = await _get_http_client()
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    url = f"{SLACK_API_BASE}/{endpoint}"
    resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        err = data.get("error", "unknown_error")
        _logger.error("Slack API %s 返回错误: %s", endpoint, err)
        raise RuntimeError(f"Slack API {endpoint} error: {err}")
    return data  # type: ignore


# ---------------------------------------------------------------------------
# 公共接口
# ---------------------------------------------------------------------------
async def post_message(
    text: str,
    channel: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """发送普通文本或 Block‑Kit 消息到 Slack.
    参数:
        text: 消息纯文本（即使有 blocks, 仍需要提供 fallback 文本）
        channel: 目标频道 ID 或名称, 默认为 `SLACK_DEFAULT_CHANNEL`。
        blocks: Block‑Kit 结构体列表, 若为 None 则仅发送文本。
        thread_ts: 若提供, 消息将作为线程回复.
    返回:
        Slack API 响应的完整 JSON（包含 `ts`, `channel` 等字段）。
    """
    if not SLACK_BOT_TOKEN:
        raise RuntimeError("Slack Bot Token 未配置，无法发送消息")

    payload: Dict[str, Any] = {
        "channel": channel or SLACK_DEFAULT_CHANNEL,
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks
    if thread_ts:
        payload["thread_ts"] = thread_ts

    _logger.debug("向 Slack 发送消息: %s", json.dumps(payload, ensure_ascii=False))
    return await _post_json("chat.postMessage", payload)


# ---------------------------------------------------------------------------
# 交互式消息（按钮/下拉）帮助函数
# ---------------------------------------------------------------------------
def _action_id(prefix: str, identifier: str) -> str:
    """生成唯一的 action_id, 使用前缀防止冲突。"""
    return f"{prefix}_{identifier}"  # 简单拼接, 实际可加入 UUID 防冲突


async def post_interactive_message(
    title: str,
    description: str,
    actions: List[Dict[str, Any]],
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """发送包含交互按钮/下拉的 Block‑Kit 消息.
    `actions` 参数是一个列表, 每项符合 Slack Block‑Kit `element` 规范, 如:
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "批准"},
            "action_id": "approve_btn",
            "style": "primary"
        }
    返回 Slack API 响应 JSON。
    """
    blocks: List[Dict[str, Any]] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": description}},
        {
            "type": "actions",
            "elements": actions,
        },
    ]
    return await post_message(text=title, channel=channel, blocks=blocks)


# ---------------------------------------------------------------------------
# 请求签名校验（用于 Slack Events / Interactivity 端点）
# ---------------------------------------------------------------------------
def verify_slack_signature(timestamp: str, signature: str, body: bytes) -> bool:
    """验证 Slack 请求签名 (Slack Signing Secret).
    Slack 发送的请求头中会有 `X-Slack-Request-Timestamp` 与 `X-Slack-Signature`。
    校验步骤:
        1. 防止重放攻击: 时间戳和当前时间差不能超过 5 分钟。
        2. 计算 HMAC SHA256(`v0:{timestamp}:{body}`) 并与 `signature` 对比。
    返回 True 表示合法, False 表示非法。
    """
    if not SLACK_SIGNING_SECRET:
        _logger.warning("Slack Signing Secret 未配置, 无法校验签名")
        return False
    try:
        req_ts = int(timestamp)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        _logger.warning("Slack 请求时间戳无效: %s", timestamp)
        return False
    # 防止旧请求 (5 分钟窗口)
    now = int(time.time())
    if abs(now - req_ts) > 60 * 5:
        _logger.warning("Slack 请求时间戳超时: %s (now=%s)", req_ts, now)
        return False
    sig_basestring = f"v0:{timestamp}:".encode() + body
    my_sig = (
        "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode(), sig_basestring, hashlib.sha256).hexdigest()
    )
    # 使用 hmac.compare_digest 防止时序攻击
    return hmac.compare_digest(my_sig, signature)


# ---------------------------------------------------------------------------
# 示例：构建常用的审批按钮消息
# ---------------------------------------------------------------------------
def build_approval_buttons(incident_id: str) -> List[Dict[str, Any]]:
    """返回 approve / reject 按钮的 Block‑Kit 元素列表.
    `incident_id` 将被拼入 `action_id`，后端在处理交互时可据此定位事件。
    """
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "批准"},
            "style": "primary",
            "action_id": _action_id("approve", incident_id),
            "value": incident_id,
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "驳回"},
            "style": "danger",
            "action_id": _action_id("reject", incident_id),
            "value": incident_id,
        },
    ]


# ---------------------------------------------------------------------------
# 清理资源（在 FastAPI lifespan 退出时调用）
# ---------------------------------------------------------------------------
async def close_slack_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
        _HTTP_CLIENT = None
        _logger.info("✅ Slack HTTP 客户端已关闭")


# End of core/slack_adapter.py