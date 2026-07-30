# -*- coding: utf-8 -*-
"""Context compression that preserves key diagnostic findings.

Compresses a prompt/context to fit a token budget while keeping protected
sections (system prompt, confirmed findings, current hypothesis, goal, etc.)
intact. Older execution history / auxiliary context is summarized first, then
non-critical sections are truncated.
"""

from __future__ import annotations

import logging
import copy
import json
from typing import Any, Dict, List, Optional, Set, cast

from core.ai.token_budget import estimate_tokens

# Sections that should survive compression if present.
_PROTECTED_KEYS: Set[str] = {
    "goal",
    "query",
    "system_prompt",
    "diagnostic_state",
    "confirmed_findings",
    "current_hypothesis",
    "pending_verification",
    "ruled_out",
    "recommended_action",
    "user_query",
}

# Keys whose values are likely long historical lists that can be summarized.
_SUMMARIZABLE_KEYS: Set[str] = {
    "history",
    "execution_log",
    "steps",
    "reasoning_steps",
    "messages",
    "chat_history",
    "recent_alerts",
    "recent_repairs",
    "correlated_alerts",
    "change_events",
    "top_processes",
    "results",
}


def _json_summary(value: Any, max_items: int = 3, max_chars: int = 80) -> str:
    """Create a tiny one-line summary of a list/dict."""
    if isinstance(value, list):
        total = len(value)
        if total == 0:
            return "[]"
        samples = []
        for item in value[:max_items]:
            s = json.dumps(item, ensure_ascii=False)
            samples.append(s[:max_chars])
        tail = f" (+{total - max_items} more)" if total > max_items else ""
        return "[" + ", ".join(samples) + tail + "]"
    if isinstance(value, dict):
        keys = list(value.keys())[:max_items]
        parts = [f"{k}={json.dumps(value[k], ensure_ascii=False)[:max_chars]}" for k in keys]
        return "{" + ", ".join(parts) + "}"
    return str(value)[:max_chars]


def compress_context(
    context: Dict[str, Any],
    max_tokens: int,
    protected_keys: Optional[Set[str]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Compress ``context`` to fit ``max_tokens``.

    Always preserves ``protected_keys``. Summarizes long historical lists and,
    as a last resort, removes the lowest-priority auxiliary keys.
    """
    if not context:
        return {}

    protected = protected_keys or _PROTECTED_KEYS
    compressed = copy.deepcopy(context)

    def _current_tokens() -> int:
        return estimate_tokens(_serialize(compressed), model)

    # 1. If already under budget, return as-is.
    if _current_tokens() <= max_tokens:
        return compressed

    # 2. Summarize long lists/histories.
    for key in list(compressed.keys()):
        if key in protected:
            continue
        value = compressed[key]
        if isinstance(value, list) and key in _SUMMARIZABLE_KEYS and len(value) > 3:
            compressed[key] = _summarize_list(value)
            if _current_tokens() <= max_tokens:
                return compressed

    # 3. Truncate long strings under non-protected keys.
    for key in list(compressed.keys()):
        if key in protected:
            continue
        value = compressed[key]
        if isinstance(value, str) and len(value) > 200:
            compressed[key] = _truncate_text(value, 200)
            if _current_tokens() <= max_tokens:
                return compressed

    # 4. Drop lower-priority auxiliary keys entirely (except protected).
    priority = list(compressed.keys())
    for key in priority:
        if key in protected:
            continue
        if key in compressed:
            del compressed[key]
            if _current_tokens() <= max_tokens:
                return compressed

    return compressed


def _summarize_list(items: List[Any], keep_last: int = 3) -> List[Any]:
    """Keep the most recent ``keep_last`` items and summarize the rest."""
    if len(items) <= keep_last:
        return items
    earlier = items[:-keep_last]
    summary = f"[... {len(earlier)} earlier items: {_json_summary(earlier)} ...]"
    return [summary] + items[-keep_last:]


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate a string while keeping the beginning and end."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2 - 10
    return text[:half] + f"\n... [{len(text) - max_chars} chars omitted] ...\n" + text[-half:]


def _serialize(value: Any) -> str:
    """Serialize a value to a string for token counting."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        return str(value)


def compress_prompt_text(
    text: str,
    max_tokens: int,
    protected_prefixes: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> str:
    """Compress a plain-text prompt while protecting important sections.

    Splits the prompt by double newlines, protects sections whose first line
    matches one of ``protected_prefixes``, and summarizes/truncates the rest.
    """
    if not text:
        return text

    if estimate_tokens(text, model) <= max_tokens:
        return text

    prefixes = protected_prefixes or [
        "用户问题",
        "系统指标快照",
        "告警",
        "修复",
        "服务依赖",
        "服务拓扑",
        "同时段",
        "最近变更",
        "--- BEGIN",
        "--- END",
        "系统提示",
        "[诊断状态]",
        "当前假设",
        "已确认",
        "已排除",
        "建议操作",
    ]

    # Split into sections; keep a small buffer for join overhead.
    sections: List[Optional[str]] = cast(List[Optional[str]], text.split("\n\n"))
    protected_idx: Set[int] = set()
    for i, sec in enumerate(sections):
        if sec is None:
            continue
        first_line = sec.split("\n", 1)[0].strip().lower()
        for p in prefixes:
            if first_line.startswith(p.lower()):
                protected_idx.add(i)
                break

    # First pass: summarize non-protected long sections.
    for i, sec in enumerate(sections):
        if sec is None or i in protected_idx:
            continue
        if estimate_tokens(sec, model) <= 80:
            continue
        lines = sec.split("\n")
        if len(lines) > 4:
            sections[i] = lines[0] + f"\n... ({len(lines) - 2} lines summarized) ...\n" + lines[-1]
        current = "\n\n".join([s for s in sections if s is not None])
        if estimate_tokens(current, model) <= max_tokens:
            return current

    # Second pass: drop non-protected sections starting from the middle.
    order = list(range(len(sections)))
    # Remove from middle outward to preserve beginning (instructions) and end (latest data).
    middle = len(order) // 2
    removal_order = []
    left, right = middle - 1, middle
    while left >= 0 or right < len(order):
        if right < len(order):
            removal_order.append(right)
            right += 1
        if left >= 0:
            removal_order.append(left)
            left -= 1

    for idx in removal_order:
        if idx in protected_idx:
            continue
        if sections[idx] is None:
            continue
        sections[idx] = None
        current = "\n\n".join([s for s in sections if s is not None])
        if estimate_tokens(current, model) <= max_tokens:
            return current

    return "\n\n".join([s for s in sections if s is not None])
