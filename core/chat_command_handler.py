# -*- coding: utf-8 -*-
"""
core/chat_command_handler.py
Inbound chat message / command handler for bidirectional human↔Agent interaction.

Responsibilities:
  - Parse natural language instructions from Slack/Teams/IM replies.
  - Map instructions to concrete agent actions (pause, investigate, approve, reject, etc.).
  - Validate user identity, role and permissions.
  - Guard against malicious instructions (e.g. "delete all pods" from chat).
  - Return structured action plan for downstream execution.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    PAUSE = "pause"  # 暂停自动操作
    INVESTIGATE = "investigate"  # 继续/重新排查
    APPROVE = "approve"  # 批准某个操作
    REJECT = "reject"  # 拒绝某个操作
    IGNORE = "ignore"  # 忽略此告警/静音
    ASSIGN = "assign"  # 转交给某人
    STATUS = "status"  # 查询进展
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class ParsedCommand:
    action: ActionType
    target: str = ""  # 被作用的目标,例如 pod 名称、service、incident_id
    params: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    user_id: str = ""
    user_name: str = ""
    channel: str = ""
    risk_level: RiskLevel = RiskLevel.SAFE
    reason: str = ""
    allowed: bool = True


# 恶意/危险关键词黑名单(用于聊天指令,不是 shell 命令)
_CHAT_BLOCKED_PATTERNS = [
    (r"删除\s*所有\s*(pod|容器|pod|服务|service|数据库|database|表|table)", "禁止删除所有资源"),
    (r"(删掉|干掉|杀掉)\s*所有", "禁止泛化删除/终止指令"),
    (r"rm\s+.*-rf", "禁止通过聊天发送 rm -rf"),
    (r"drop\s+(database|table|所有)", "禁止删除数据库/表"),
    (r"shutdown\s+所有|重启\s*所有", "禁止全局重启/关机"),
    (r"(?:kill|终止)\s*所有\s*(pod|进程|服务)", "禁止终止所有服务"),
    (r"删除.*生产.*数据", "禁止删除生产数据"),
]

# 允许执行指令的角色白名单;默认只允许 oncall/admin,只读指令允许 viewer
_ALLOWED_ROLES_FOR_ACTION: dict[ActionType, set[str]] = {
    ActionType.PAUSE: {"admin", "oncall", "sre"},
    ActionType.INVESTIGATE: {"admin", "oncall", "sre", "viewer"},
    ActionType.APPROVE: {"admin", "oncall", "sre"},
    ActionType.REJECT: {"admin", "oncall", "sre"},
    ActionType.IGNORE: {"admin", "oncall", "sre"},
    ActionType.ASSIGN: {"admin", "oncall"},
    ActionType.STATUS: {"admin", "oncall", "sre", "viewer"},
    ActionType.UNKNOWN: {"admin"},  # 未知/无法解析的指令仅管理员可放行
    ActionType.BLOCKED: set(),
}


def _normalize_text(text: str) -> str:
    """Normalize Chinese punctuation and whitespace for matching."""
    text = text.strip()
    text = text.replace("，", ",").replace("。", ".").replace("！", "!").replace("？", "?")
    return text


def _check_malicious(text: str) -> Optional[tuple[RiskLevel, str]]:
    """Check whether a chat message contains malicious intent."""
    lowered = text.lower()
    for pattern, reason in _CHAT_BLOCKED_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            return RiskLevel.BLOCKED, reason
    # High-risk if it asks to delete/restart without qualifier
    if re.search(r"\b(删除|删掉|drop|shutdown|reboot|restart|kill)\b", lowered, re.IGNORECASE):
        if not re.search(r"\b(这个|该|指定|名为|name[d]?=?)\b", lowered, re.IGNORECASE):
            return RiskLevel.HIGH, "删除/重启/终止指令必须指定明确目标,不允许泛化操作"
    return None


def _extract_target(text: str) -> str:
    """Try to extract a target name from the instruction."""
    # Match "名为 xxx", "name=xxx", 引号内, 或者 'pod xxx'
    patterns = [
        r"(?:名为|name=|name:\s*|名字叫)\s*['\"]?([^'\"，。,\.\s]{1,64})['\"]?",
        r"\b(pod|service|deployment|deploy|container|job|db|table)\s+['\"]?([^'\"，。,\.\s]{1,64})['\"]?",  # noqa: E501
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(m.lastindex or 1)
    return ""


def _contains_any(text: str, *keywords: str) -> bool:
    """Check if any of the Chinese/English keywords appears in text (case-insensitive)."""
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False


def _classify_action(text: str) -> tuple[ActionType, dict[str, Any]]:
    """Classify the user intent into a structured action."""
    lowered = text.lower()

    # 暂停 / 不要自动执行
    if _contains_any(
        lowered, "不要重启", "不要启动", "不要执行", "不要恢复", "先别", "暂停", "stop", "halt"
    ):
        return ActionType.PAUSE, {"note": "user requested to pause automatic remediation"}

    # 先查日志/指标
    if _contains_any(lowered, "查日志", "看日志", "查log", "看log", "logs", "查下日志"):
        return ActionType.INVESTIGATE, {"focus": "logs"}

    if _contains_any(lowered, "查监控", "看监控", "dashboard", "metrics", "指标"):
        return ActionType.INVESTIGATE, {"focus": "metrics"}

    if _contains_any(lowered, "继续", "继续排查", "继续调查", "go ahead"):
        return ActionType.INVESTIGATE, {"note": "user asked to continue investigation"}

    # 批准 / 同意
    if _contains_any(lowered, "同意", "批准", "允许", "approve", "yes", "ok"):
        return ActionType.APPROVE, {"target": _extract_target(text)}

    # 拒绝 / 驳回
    if _contains_any(lowered, "拒绝", "不允许", "驳回", "reject", "no"):
        return ActionType.REJECT, {"target": _extract_target(text)}

    # 忽略 / 静音
    if _contains_any(lowered, "忽略", "静音", "silence", "mute", "ack", "acknowledge"):
        return ActionType.IGNORE, {"target": _extract_target(text)}

    # 转交
    m = re.search(r"(?:转给|assign|交给|@)\s*@?([^\s,，]+)", lowered)
    if m:
        return ActionType.ASSIGN, {"assignee": m.group(1)}

    # 查询状态
    if _contains_any(lowered, "进展", "状态", "status", "怎么样", "如何了", "现在怎样"):
        return ActionType.STATUS, {}

    return ActionType.UNKNOWN, {}


def _get_user_roles(user_id: str, user_name: str = "") -> set[str]:
    """Resolve user roles from environment or a simple static mapping."""
    raw = os.getenv("CHAT_COMMAND_ROLES", "")
    roles: set[str] = {"viewer"}
    if raw:
        # Format: user1:admin,oncall;user2:viewer
        for entry in raw.split(";"):
            if ":" not in entry:
                continue
            uid, rlist = entry.split(":", 1)
            if uid.strip().lower() in (user_id.lower(), user_name.lower()):
                roles = {r.strip().lower() for r in rlist.split(",")}
                break
    # Default: any user id starting with 'oncall' or 'admin' gets those roles
    lowered = (user_id + user_name).lower()
    if "admin" in lowered:
        roles.add("admin")
    if "oncall" in lowered:
        roles.add("oncall")
    if "sre" in lowered:
        roles.add("sre")
    return roles


def parse_chat_command(
    text: str,
    user_id: str = "",
    user_name: str = "",
    channel: str = "",
    verified: bool = False,
) -> ParsedCommand:
    """
    Parse a chat message from an engineer and decide whether it is allowed.

    Args:
        text: raw chat message.
        user_id: platform user id.
        user_name: display name.
        channel: source channel (slack/teams/wecom/...).
        verified: whether the inbound request has been signature-verified.

    Returns:
        ParsedCommand with action, params, risk level and allowed flag.
    """
    text = _normalize_text(text)
    action, params = _classify_action(text)
    target = _extract_target(text) or params.get("target", "")

    # Malicious instruction guard
    malicious = _check_malicious(text)
    if malicious:
        risk, reason = malicious
        return ParsedCommand(
            action=ActionType.BLOCKED,
            target=target,
            params={"blocked_text": text},
            raw_text=text,
            user_id=user_id,
            user_name=user_name,
            channel=channel,
            risk_level=risk,
            reason=reason,
            allowed=False,
        )

    # Identity / permission check
    if not verified:
        return ParsedCommand(
            action=action,
            target=target,
            params=params,
            raw_text=text,
            user_id=user_id,
            user_name=user_name,
            channel=channel,
            risk_level=RiskLevel.HIGH,
            reason="unverified sender; chat command rejected",
            allowed=False,
        )

    roles = _get_user_roles(user_id, user_name)
    required = _ALLOWED_ROLES_FOR_ACTION.get(action, set())
    if required and not (roles & required):
        return ParsedCommand(
            action=action,
            target=target,
            params=params,
            raw_text=text,
            user_id=user_id,
            user_name=user_name,
            channel=channel,
            risk_level=RiskLevel.HIGH,
            reason=f"用户角色 {roles} 无权执行 {action.value},需要 {required}",
            allowed=False,
        )

    return ParsedCommand(
        action=action,
        target=target,
        params=params,
        raw_text=text,
        user_id=user_id,
        user_name=user_name,
        channel=channel,
        risk_level=(
            RiskLevel.SAFE if action not in (ActionType.PAUSE, ActionType.IGNORE) else RiskLevel.LOW
        ),
        reason="allowed",
        allowed=True,
    )


def handle_instruction(text: str, **kwargs: Any) -> dict[str, Any]:
    """Convenience wrapper returning a plain dict."""
    cmd = parse_chat_command(text, **kwargs)
    return {
        "action": cmd.action.value,
        "target": cmd.target,
        "params": cmd.params,
        "allowed": cmd.allowed,
        "risk_level": cmd.risk_level.value,
        "reason": cmd.reason,
        "user_id": cmd.user_id,
        "channel": cmd.channel,
    }
