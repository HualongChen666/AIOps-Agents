# -*- coding: utf-8 -*-
"""Priority engine – 计算业务影响优先级 (SLA Score)

本实现提供一个极简的 `compute_sla_score(alert: dict) -> int` 函数，
根据 alert 中的业务字段返回 0~3 四级优先级（P0‑P3）。

- `alert.get("business_name")` 与配置中的 `BUSINESS_SLA` 映射匹配。
- 若未匹配或缺失字段，返回默认的 `DEFAULT_SLA`（在 config 中配置）。

该模块在二期任务 **任务二之三** 中被 `heal_graph` 与其他业务逻辑调用。
"""

from __future__ import annotations

import logging
from typing import Dict

from config import BUSINESS_SLA, DEFAULT_SLA

logger = logging.getLogger(__name__)


def compute_sla_score(alert: Dict) -> int:
    """根据 alert 内容返回业务 SLA 优先级。

    参数
    ------
    alert: Dict
        从监控平台/日志系统收到的告警结构体，必须包含 `business_name`
        字段（若不存在则使用默认 SLA）。

    返回
    ------
    int
        0（P0）最高优先级，1‑3 递减。
    """
    business = alert.get("business_name")
    if not business:
        logger.warning("Alert missing 'business_name', using DEFAULT_SLA")
        return DEFAULT_SLA
    # BUSINESS_SLA 期望是 {"业务A": 0, "业务B": 1, ...}
    score = BUSINESS_SLA.get(business, DEFAULT_SLA)
    if not isinstance(score, int) or score not in (0, 1, 2, 3):
        logger.warning(
            "Invalid SLA score %s for business %s, fallback to DEFAULT_SLA", score, business
        )
        return DEFAULT_SLA
    return score
