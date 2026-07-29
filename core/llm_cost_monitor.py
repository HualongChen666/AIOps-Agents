# -*- coding: utf-8 -*-
"""
LLM 成本监控器
----------------
集中管理 LLM 路由与成本相关配置、定价、预算控制。

将原本分散在 `config.py` 和 `core/ai/llm_router/cost_optimizer.py` 中的
成本配置与预算逻辑统一迁移到本模块，供 `ai_engine`、LLM router 和其他
组件共享。
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from core.ai.token_budget import estimate_tokens

# 默认 LLM 模型清单（从 config.py 迁移过来）
DEFAULT_LLM_ROUTER_MODELS: List[Dict[str, Any]] = [
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "max_tokens": 128000,
        "cost_per_1k": 0.015,
    },
    {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "max_tokens": 16384,
        "cost_per_1k": 0.005,
    },
    {
        "provider": "minimax",
        "model": "MiniMax-Text-01",
        "max_tokens": 12000,
        "cost_per_1k": 0.02,
    },
]

DEFAULT_LLM_ROUTER_TOKEN_COST_THRESHOLD = 20000

DEFAULT_LLM_BUDGET_PER_REQUEST = 0.5
DEFAULT_LLM_MAX_COST_PER_HOUR = 10.0
DEFAULT_LLM_MAX_COST_PER_DAY = 50.0


def _safe_float_env(
    name: str,
    default: float = 0.0,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> float:
    """安全地从环境变量读取浮点配置，并支持上下限。"""
    try:
        val = float(os.environ.get(name, str(default)).strip())
    except (TypeError, ValueError):
        logger.warning(f"[llm_cost_monitor] {name} invalid, using default {default}")
        return default

    if min_val is not None and val < min_val:
        logger.warning(f"[llm_cost_monitor] {name}={val} below min {min_val}, using {min_val}")
        return min_val
    if max_val is not None and val > max_val:
        logger.warning(f"[llm_cost_monitor] {name}={val} above max {max_val}, using {max_val}")
        return max_val
    return val


class LLMCostMonitor:
    """
    LLM 成本监控器。

     responsibilities:
    - 维护模型单价 (`cost_per_1k`)
    - 维护 token 成本阈值和单次/小时/天预算
    - 估算 token 数与费用
    - 检查并累计实际费用，实现预算控制
    """

    def __init__(
        self,
        model_configs: Optional[List[Dict[str, Any]]] = None,
        token_cost_threshold: Optional[int] = None,
        budget_per_request: Optional[float] = None,
        max_cost_per_hour: Optional[float] = None,
        max_cost_per_day: Optional[float] = None,
    ) -> None:
        self.model_configs: List[Dict[str, Any]] = (
            model_configs if model_configs is not None else list(DEFAULT_LLM_ROUTER_MODELS)
        )
        self.token_cost_threshold: int = (
            token_cost_threshold
            if token_cost_threshold is not None
            else DEFAULT_LLM_ROUTER_TOKEN_COST_THRESHOLD
        )

        self.budget_per_request: float = (
            budget_per_request
            if budget_per_request is not None
            else _safe_float_env(
                "LLM_BUDGET_PER_REQUEST",
                DEFAULT_LLM_BUDGET_PER_REQUEST,
                0.01,
                100.0,
            )
        )
        self.max_cost_per_hour: float = (
            max_cost_per_hour
            if max_cost_per_hour is not None
            else _safe_float_env(
                "LLM_MAX_COST_PER_HOUR",
                DEFAULT_LLM_MAX_COST_PER_HOUR,
                1.0,
                1000.0,
            )
        )
        self.max_cost_per_day: float = (
            max_cost_per_day
            if max_cost_per_day is not None
            else _safe_float_env(
                "LLM_MAX_COST_PER_DAY",
                DEFAULT_LLM_MAX_COST_PER_DAY,
                1.0,
                10000.0,
            )
        )

        self._hourly_cost: float = 0.0
        self._daily_cost: float = 0.0
        self._request_count: int = 0
        self._hour_start: Optional[float] = None
        self._day_start: Optional[float] = None

    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """根据模型名查找模型配置。"""
        for config in self.model_configs:
            if config.get("model") == model_name or config.get("name") == model_name:
                return config
        return None

    def get_cost_per_1k(self, model_name: str, default: float = 0.0) -> float:
        """获取模型每 1k token 的单价；找不到时返回 default。"""
        config = self.get_model_config(model_name)
        if config:
            return float(config.get("cost_per_1k", default))
        return default

    def estimate_tokens(self, text: str, model: Optional[str] = None) -> int:
        """估算文本 token 数。"""
        return estimate_tokens(text, model)

    def estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int = 0) -> float:
        """估算一次调用的费用（USD）。"""
        cost_per_1k = self.get_cost_per_1k(model_name, default=0.0)
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000.0) * cost_per_1k

    def check_budget(self, estimated_cost: float) -> bool:
        """检查当前费用是否在预算范围内。"""
        if self.budget_per_request and estimated_cost > self.budget_per_request:
            logger.warning(
                f"Cost {estimated_cost} exceeds per-request budget {self.budget_per_request}"
            )
            return False

        if self.max_cost_per_hour:
            self._update_hourly_tracking()
            if self._hourly_cost + estimated_cost > self.max_cost_per_hour:
                logger.warning(f"Hourly cost would exceed {self.max_cost_per_hour}")
                return False

        if self.max_cost_per_day:
            self._update_daily_tracking()
            if self._daily_cost + estimated_cost > self.max_cost_per_day:
                logger.warning(f"Daily cost would exceed {self.max_cost_per_day}")
                return False

        return True

    def record_cost(self, actual_cost: float) -> None:
        """记录一次实际费用。"""
        self._update_hourly_tracking()
        self._update_daily_tracking()
        self._hourly_cost += actual_cost
        self._daily_cost += actual_cost
        self._request_count += 1

    def get_hourly_stats(self) -> Dict[str, Any]:
        """返回当前小时/天的费用统计。"""
        self._update_hourly_tracking()
        self._update_daily_tracking()
        return {
            "hourly_cost": self._hourly_cost,
            "daily_cost": self._daily_cost,
            "request_count": self._request_count,
            "avg_cost_per_request": (
                self._hourly_cost / self._request_count if self._request_count else 0.0
            ),
        }

    def _update_hourly_tracking(self) -> None:
        """更新小时窗口；超过 1 小时则清零。"""
        now = time.time()
        if self._hour_start is None:
            self._hour_start = now
        elif now - self._hour_start > 3600:
            self._hourly_cost = 0.0
            self._request_count = 0
            self._hour_start = now

    def _update_daily_tracking(self) -> None:
        """更新天窗口；超过 1 天则清零。"""
        now = time.time()
        if self._day_start is None:
            self._day_start = now
        elif now - self._day_start > 86400:
            self._daily_cost = 0.0
            self._day_start = now


# 全局单例
_llm_cost_monitor_instance: Optional[LLMCostMonitor] = None


def get_llm_cost_monitor() -> LLMCostMonitor:
    """返回全局 LLM 成本监控器单例。"""
    global _llm_cost_monitor_instance
    if _llm_cost_monitor_instance is None:
        _llm_cost_monitor_instance = LLMCostMonitor()
    return _llm_cost_monitor_instance


def set_llm_cost_monitor(monitor: LLMCostMonitor) -> None:
    """设置全局 LLM 成本监控器单例（主要用于 router 初始化后共享实例）。"""
    global _llm_cost_monitor_instance
    _llm_cost_monitor_instance = monitor


def reset_llm_cost_monitor() -> None:
    """重置全局单例（测试用）。"""
    global _llm_cost_monitor_instance
    _llm_cost_monitor_instance = None


class SessionBudget:
    """Per-session token / cost budget tracker."""

    def __init__(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
        max_cost: Optional[float] = None,
    ) -> None:
        self.session_id = session_id
        self.max_tokens = max_tokens
        self.max_cost = max_cost
        self.tokens_used = 0
        self.cost_used = 0.0
        self._lock = threading.Lock()

    def check_and_record(self, tokens: int, cost: float = 0.0) -> bool:
        """Check request against session budget; record if it fits."""
        with self._lock:
            if self.max_tokens is not None and self.tokens_used + tokens > self.max_tokens:
                logger.warning(
                    f"Session {self.session_id} token budget exceeded "
                    f"({self.tokens_used + tokens} > {self.max_tokens})"
                )
                return False
            if self.max_cost is not None and self.cost_used + cost > self.max_cost:
                logger.warning(
                    f"Session {self.session_id} cost budget exceeded "
                    f"({self.cost_used + cost:.4f} > {self.max_cost})"
                )
                return False
            self.tokens_used += tokens
            self.cost_used += cost
            return True

    def record_cost(self, cost: float) -> None:
        """Record actual cost after the call completes."""
        with self._lock:
            self.cost_used += cost


# Defaults: 50k tokens / 10 USD per session, configurable via env vars.
try:
    _DEFAULT_SESSION_TOKEN_BUDGET = int(os.environ.get("AIOPS_SESSION_TOKEN_BUDGET", "50000"))
except ValueError:
    _DEFAULT_SESSION_TOKEN_BUDGET = 50000

_DEFAULT_SESSION_COST_BUDGET = _safe_float_env("AIOPS_SESSION_COST_BUDGET", 10.0, 0.0, 10000.0)

_SESSION_BUDGETS: Dict[str, SessionBudget] = {}
_SESSION_BUDGETS_LOCK = threading.Lock()


def get_session_budget(session_id: Optional[str]) -> Optional[SessionBudget]:
    """Return (or create) the budget tracker for a session."""
    if not session_id:
        return None
    with _SESSION_BUDGETS_LOCK:
        if session_id not in _SESSION_BUDGETS:
            _SESSION_BUDGETS[session_id] = SessionBudget(
                session_id,
                _DEFAULT_SESSION_TOKEN_BUDGET,
                _DEFAULT_SESSION_COST_BUDGET,
            )
        return _SESSION_BUDGETS[session_id]
