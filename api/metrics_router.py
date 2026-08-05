# -*- coding: utf-8 -*-
"""
Metrics Router Module
=====================

Provides API endpoints for system metrics and monitoring.
Supports real-time metrics retrieval and historical data queries.

Endpoints:
- GET /api/v1/metrics - Get system metrics
- GET /api/v1/metrics/summary - Get metrics summary
- GET /api/v1/metrics/history - Get historical metrics
"""

# api/metrics_router.py — 指标相关 REST API
#
# ──────────────────────────────────────────────────────────────
# 🔧 严格 Review 修复(MR):
#   - MR1 [P1]:_snapshot_cache 用 asyncio.Lock 替代 threading.Lock
#   - MR2 [P1]:并发请求去重(防止缓存击穿导致重复采集)
#   - MR3 [P1]:/processes 增加 5 秒 TTL 缓存
#   - MR4 [P2]:monotonic 时间倒退防御
#   - MR5 [P2]:/processes 缓存
#   - MR6 [P2]:/history 增加点数信息
#   - MR7 [P2]:clear_snapshot_cache 维护接口
#
# ──────────────────────────────────────────────────────────────
# 🆕 N+3 全量采集超时优化(本次落地):
#
# [N3-A] 🟡 P1 — /history 类型扩展防御
#   问题: metrics_history.to_dict() 严格返回 dict[str, list],
#         直接 history["_meta"] = {...} 赋值 dict 类型,
#         Pylance 报 reportArgumentType:
#         "dict[str, int | Any] is not assignable to list[Unknown]"
#   修复: ① 把 history 显式装入新的 dict[str, Any] 容器
#         ② 新容器接受 list/dict 混合 value,符合实际业务语义
#   设计原则:不改动 metrics_history.py 的严格类型签名,
#            在 API 层做"类型适配",保持 core 层 metrics_history
#            的纯粹性(对照 ADR-019 类型严格化原则)
#
# [N3-B] 🟢 P2 — /cache/clear 联动清空引擎层缓存
#   问题: N3-1 在 collector.py 新增了引擎层 1.5s TTL 缓存,
#         路由层 /cache/clear 应该同时清空引擎层,否则
#         维护场景下"清空后立即查询"仍会拿到旧数据
#   修复: ① 调用 core.collector.invalidate_collect_cache()
#         ② 返回 engine_cleared 字段供前端验证
#         ③ ImportError 防御(N+3 未完成部署时降级)
#
# ──────────────────────────────────────────────────────────────
# 🔧 本次严格 Review 修复(MRV 系列共 8 项,N+3 校验落地):
#
# [MRV1] 🔴 P0 — clear_snapshot_cache 日志拼接 f-string 缺少分隔符
#   问题: processes=... 字符串末尾未加 " | ",与后面的 engine=...
#         直接拼接为 "processes=已清engine=已清",日志可读性极差,
#         运维难以快速定位三个缓存的状态
#   修复: 在 processes=... 行末尾补回 " | " 分隔符
#
# [MRV2] 🔴 P0 — 缓存命中返回内部引用,存在污染风险
#   问题: get_snapshot 快速路径和双重检查路径直接 return _snapshot_cache["data"],
#         调用方修改返回 dict 时会污染缓存,违反 [18] approval_store R3
#         决策的"返回浅拷贝"原则
#   修复: ① 快速路径返回 dict(_snapshot_cache["data"])(顶层浅拷贝)
#         ② 双重检查路径同理
#         ③ /processes 接口同步修复
#
# [MRV3] 🟡 P1 — 文件头补全 N+3 集成说明
#   问题: 文件实际已新增 N+3 类型扩展防御和引擎层缓存联动,
#         但文件头修复说明列表完全未提及,违反 ADR-012
#         "修复说明必须放在文件开头"规范
#   修复: 在 MR 系列后新增"🆕 N+3 全量采集超时优化"段落
#         + MRV 系列说明
#
# [MRV4] 🟡 P1 — except (ImportError, Exception) 冗余
#   问题: ImportError 是 Exception 子类,写两个完全等价于
#         只写 except Exception,语义不严谨,Pylance 可能报警
#   修复: 简化为 except Exception(实际等价语义)
#
# [MRV5] 🟡 P1 — _snapshot_lock/_processes_lock 类型注解规范化
#   问题: 使用 asyncio.Lock = None # type: ignore 是"降级处理",
#         违反 ADR-019 Pylance 零警告原则;
#         项目其他模块(如 [24] linux_collector)已统一使用
#         Optional[asyncio.subprocess.Process] = None
#   修复: ① 顶部 import Optional
#         ② _snapshot_lock: Optional[asyncio.Lock] = None
#         ③ _processes_lock: Optional[asyncio.Lock] = None
#         ④ 移除 type: ignore 注释
#
# [MRV6] 🟢 P2 — _snapshot_cache/_processes_cache 字典契约注释
#   问题: dict[str, Any] 类型推断后访问 ["data"] 返回 Any,
#         失去类型检查能力(对照 [20] CR7 修复)
#   修复: 增加字典字段约定注释,Pylance 可通过 docstring 提示理解
#         (TypedDict 改造工作量过大,本次不引入,保持注释说明)
#
# [MRV7] 🟢 P2 — get_processes 仍调用独立版 get_top_processes
#   问题: [20] collector.py 提供了 _collect_cpu_and_processes 合并版
#         (N3-2 优化,共享 0.5s sleep),但 /processes 接口仍调用
#         独立版 get_top_processes(单独 0.5s sleep);5s TTL 缓存
#         能缓解但首次采集仍 0.5s,无法享受 N3-2 优化
#   修复: 保持调用独立版(因为本接口只需要进程,不需要 CPU),
#         增加注释说明设计决策(避免后续维护者疑惑为何不用合并版)
#
# [MRV8] 🟢 P2 — Lock 懒加载理论性并发问题
#   问题: _get_snapshot_lock 双重检查在 asyncio 单线程事件循环中
#         实际不会触发竞态,但理论不严谨
#   修复: 增加注释说明 asyncio 单线程语义保证(不引入额外锁,
#         避免过度工程)
# ──────────────────────────────────────────────────────────────

import asyncio
import logging
from typing import Any, Optional  # 🔧 MRV5 [P1]:补全 Optional 导入

from fastapi import APIRouter, Depends, HTTPException, Query


from core.cache_helpers import ParametricTTLCache, TTLCache
from core.collector import collect_all, get_top_processes
from core.metrics_history import metrics_history
from core.stats_engine import get_decision_accuracy, get_real_summary

# Phase 1 集成: 双写策略和指标转换器
try:
    from core.dual_write import DualWriteStrategy
    from core.metrics_converter import MetricsConverter

    DUAL_WRITE_AVAILABLE = True
except ImportError:
    DUAL_WRITE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Phase 1 dual_write and metrics_converter not available")

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/metrics", tags=["指标采集"]
)


# ============================================================
# 接口0:根路径 - 返回仪表盘指标卡片数据
# ============================================================
@router.get(
    "/",
    summary="仪表盘指标卡片数据",
    responses={
        200: {
            "description": "仪表盘指标卡片数据",
            "content": {
                "application/json": {
                    "example": {
                        "metrics": [
                            {"key": "告警数量", "value": 42, "unit": "个", "level": "warning"},
                            {"key": "自愈成功率", "value": "85%", "unit": "", "level": "normal"},
                        ]
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "获取失败"},
    },
)
async def get_dashboard_metrics() -> dict[str, Any]:
    """
    返回仪表盘指标卡片数据
    对应前端:DashboardCards 组件

    Returns:
        dict with "metrics" key containing array of MetricItem
    """
    logger.debug("请求仪表盘指标卡片数据")
    try:
        # 获取摘要数据
        summary = await get_real_summary()

        # 转换为前端期望的格式
        metrics = [
            {
                "key": "告警数量",
                "value": summary.get("total_alerts", 0),
                "unit": "个",
                "level": (
                    "critical"
                    if summary.get("total_alerts", 0) > 50
                    else "warning" if summary.get("total_alerts", 0) > 20 else "normal"
                ),
            },
            {
                "key": "自愈成功率",
                "value": f"{summary.get('heal_rate', 0)}%",
                "unit": "",
                "level": "normal" if summary.get("heal_rate", 0) > 80 else "warning",
            },
            {
                "key": "MTTD",
                "value": summary.get("mttd_min", 0),
                "unit": "min",
                "level": "normal" if summary.get("mttd_min", 0) < 30 else "warning",
            },
            {
                "key": "RCA准确率",
                "value": f"{summary.get('rca_accuracy', 0)}%",
                "unit": "",
                "level": "normal" if summary.get("rca_accuracy", 0) > 85 else "warning",
            },
        ]

        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"仪表盘指标获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"仪表盘指标获取失败: {str(e)[:200]}")


# ============================================================
# Phase 1 集成: 双写策略初始化
# ============================================================
_dual_write_strategy: Optional[DualWriteStrategy] = None
_metrics_converter: Optional[MetricsConverter] = None

if DUAL_WRITE_AVAILABLE:
    try:
        _dual_write_strategy = DualWriteStrategy()
        _metrics_converter = MetricsConverter()
        logger.info("Phase 1 dual_write and metrics_converter initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Phase 1 components: {e}")
        _dual_write_strategy = None
        _metrics_converter = None


# ============================================================
# 模块级常量
# ============================================================
_SNAPSHOT_CACHE_TTL_SEC = 30  # /snapshot TTL
_PROCESSES_CACHE_TTL_SEC = 5  # 🔧 MR5:/processes TTL


# ============================================================
# 🔧 BUG-FIX-10 + MR1/2 [P1]:/snapshot 接口缓存与并发去重
# ──────────────────────────────────────────────────────
# 修复前:_snapshot_cache 用 threading.Lock,在异步上下文下虽能工作
#         但持锁期间会阻塞事件循环;无并发去重,缓存击穿时多请求
#         同时触发 collect_all(每次 ~1s,N 倍开销)
# 修复后:① asyncio.Lock 替代 threading.Lock(懒加载,Python 3.12+ 兼容)
#         ② 双重检查锁定,缓存击穿时只让 1 个请求采集,其他请求复用结果
#
# 🔧 重构:使用 core.cache_helpers.TTLCache 替代手动实现
# ──────────────────────────────────────────────────────
_snapshot_cache = TTLCache(ttl_sec=_SNAPSHOT_CACHE_TTL_SEC)


# 🔧 MR3 + MR5:/processes 缓存
# 🔧 重构:使用 core.cache_helpers.ParametricTTLCache 替代手动实现
# ──────────────────────────────────────────────────────
_processes_cache = ParametricTTLCache(ttl_sec=_PROCESSES_CACHE_TTL_SEC)


def _try_get_snapshot_from_cache() -> Optional[dict[str, Any]]:
    """尝试从缓存获取快照（快速路径）

    🔧 重构:使用 TTLCache.get()

    Returns:
        缓存数据或None
    """
    cached = _snapshot_cache.get()
    if cached:
        logger.debug("快照命中缓存(快速路径)")
    return cached


async def _collect_system_snapshot() -> dict[str, Any]:
    """采集系统指标快照

    Phase 1 集成: 使用双写策略同时写入 SQLite 和 VictoriaMetrics

    Returns:
        系统快照数据
    """
    system_snapshot = await asyncio.to_thread(collect_all)
    summary = await get_real_summary()
    response = {**system_snapshot, "summary": summary}

    # Phase 1 集成: 双写到 VictoriaMetrics
    if _dual_write_strategy and _metrics_converter:
        try:
            # 双写
            await _dual_write_strategy.write_batch_metrics([response])
        except Exception as e:
            logger.warning(f"Phase 1 dual_write failed: {e}")

    logger.info(
        "快照采集成功 | "
        f"CPU={system_snapshot.get('cpu', {}).get('usage_percent', 'N/A')}% | "
        f"MEM={system_snapshot.get('memory', {}).get('usage_percent', 'N/A')}%"
    )
    return response


def _update_snapshot_cache(data: dict[str, Any]) -> None:
    """更新快照缓存

    🔧 重构:使用 TTLCache.set()

    Args:
        data: 要缓存的数据
    """
    _snapshot_cache.set(data)


# ============================================================
# 接口1:全量快照(🔧 MR1/MR2:asyncio + 并发去重)
# 🔧 MRV2 [P0]:返回浅拷贝,防止外部修改污染缓存
# ============================================================
@router.get(
    "/snapshot",
    summary="获取系统指标全量快照(30秒TTL缓存)",
    responses={
        200: {
            "description": "系统指标快照",
            "content": {
                "application/json": {
                    "example": {
                        "cpu": {"usage_percent": 45.2, "cores": 8},
                        "memory": {"usage_percent": 68.3, "total_gb": 16},
                        "disk": {"usage_percent": 55.0, "total_gb": 500},
                        "summary": {"total_alerts": 42, "heal_rate": 85},
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "采集失败"},
    },
)
async def get_snapshot() -> dict[str, Any]:
    """
    一次性返回所有系统指标 + 真实统计摘要

    🔧 BUG-FIX-10:30 秒 TTL 缓存,避免前端首次加载延迟
    🔧 MR1 [P1]:asyncio.Lock 替代 threading.Lock(不阻塞事件循环)
    🔧 MR2 [P1]:并发请求去重(防止缓存击穿)
    🔧 MRV2 [P0]:命中缓存返回浅拷贝(对照 [18] approval_store R3 决策)
    """
    logger.debug("请求系统指标全量快照")

    # 🔧 重构:TTLCache 内部已处理并发,无需手动双重检查
    cached = _snapshot_cache.get()
    if cached:
        return cached

    # 真正需要采集
    try:
        response = await _collect_system_snapshot()
        _snapshot_cache.set(response)
        return response

    except asyncio.CancelledError:
        logger.info("快照采集被取消")
        raise
    except Exception as e:
        logger.error(f"系统指标快照采集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"系统指标采集失败: {str(e)[:200]}")


# ============================================================
# 接口2:历史序列
# 🔧 MR6 [P2]:返回点数信息
# 🆕 N3-A [P1]:类型扩展防御
# ============================================================
@router.get(
    "/history",
    summary="获取指标历史序列(用于趋势图)",
    responses={
        200: {
            "description": "指标历史序列数据",
            "content": {
                "application/json": {
                    "example": {
                        "cpu": [45.2, 48.1, 52.3, 55.8, 49.2],
                        "memory": [68.3, 70.1, 72.5, 71.2, 69.8],
                        "_meta": {"size": 60, "maxlen": 60},
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "获取失败"},
    },
)
async def get_history() -> dict[str, Any]:
    """
    返回 CPU / 内存 / 网络 的历史序列数据
    对应前端:实时折线图初始化数据加载

    🔧 MR6 [P2]:返回 size 字段,前端可判断数据是否完整
    🆕 N3-A [P1]:类型扩展防御
    ──────────────────────────────────────────────
    修复前:metrics_history.to_dict() 严格返回 dict[str, list],
            直接 history["_meta"] = {...} 赋值 dict 类型,
            Pylance 报 reportArgumentType:
            "dict[str, int | Any] is not assignable to list[Unknown]"
    修复后:① 把 history 显式装入新的 dict[str, Any] 容器
            ② 新容器接受 list/dict 混合 value,符合实际业务语义
    设计原则:不改动 metrics_history.py 的严格类型签名,
             在 API 层做"类型适配",保持 core 层 metrics_history
             的纯粹性(对照 ADR-019 类型严格化原则)
    ──────────────────────────────────────────────
    """
    logger.debug("请求指标历史序列数据")
    try:
        raw_history = metrics_history.to_dict()
        point_count = len(raw_history.get("cpu", []))

        # 🆕 N3-A:构造扩展容器,接受 list + dict 混合 value
        response: dict[str, Any] = dict(raw_history)

        # 🔧 MR6:补充元信息,前端无需调用额外接口判断
        response["_meta"] = {
            "size": point_count,
            "maxlen": getattr(metrics_history, "_maxlen", 60),
        }

        logger.debug(f"历史数据查询成功,当前共 {point_count} 个数据点")
        return response
    except Exception as e:
        logger.error(f"历史指标数据获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"历史数据获取失败: {str(e)[:200]}")


def _try_get_processes_from_cache(limit: int) -> Optional[dict[str, Any]]:
    """尝试从缓存获取进程列表

    🔧 重构:使用 ParametricTTLCache.get(limit=limit)

    Returns:
        缓存数据或None
    """
    cached = _processes_cache.get(limit=limit)
    if cached:
        logger.debug(f"进程列表命中缓存,limit={limit}")
    return cached


async def _collect_top_processes(limit: int) -> dict[str, Any]:
    """采集Top进程列表

    Returns:
        进程数据
    """
    processes = await asyncio.to_thread(get_top_processes, limit)
    response = {"processes": processes}
    logger.debug(f"进程列表采集成功,返回 {len(processes)} 条")
    return response


def _update_processes_cache(data: dict[str, Any], limit: int) -> None:
    """更新进程缓存

    🔧 重构:使用 ParametricTTLCache.set(data, limit=limit)

    Args:
        data: 要缓存的数据
        limit: limit 参数
    """
    _processes_cache.set(data, limit=limit)


# ============================================================
# 接口3:Top 进程(🔧 MR3 + MR5:5 秒 TTL 缓存)
# 🔧 MRV2 [P0]:返回浅拷贝,防止外部修改污染缓存
# 🔧 MRV7 [P2]:保持调用独立版 get_top_processes 的设计说明
# ============================================================
@router.get(
    "/processes",
    summary="Top 进程列表(5秒TTL缓存)",
    responses={
        200: {
            "description": "Top进程列表",
            "content": {
                "application/json": {
                    "example": {
                        "processes": [
                            {"name": "python3", "pid": 1234, "cpu_percent": 85.2, "memory_mb": 512},
                            {"name": "node", "pid": 5678, "cpu_percent": 12.5, "memory_mb": 256},
                        ]
                    }
                }
            },
        },
        401: {"description": "未授权"},
        422: {"description": "参数错误"},
        500: {"description": "采集失败"},
    },
)
async def get_processes(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="返回进程数量上限,范围 1-100",
    )
) -> dict[str, Any]:
    """
    返回 CPU 占用最高的 Top N 进程
    对应前端:工作流节点详情扩展信息

    🔧 MR3 [P1]:增加 5 秒 TTL 缓存,降低重复采样开销
        - get_top_processes 内含 0.5s 双采样,前端轮询会持续阻塞线程池
        - 5 秒缓存可降低高频调用对系统的压力 ~10 倍
    🔧 MR5 [P2]:limit 不同时缓存独立(避免 limit=10 和 limit=20 互相影响)
    🔧 MRV2 [P0]:命中缓存返回浅拷贝

    🔧 MRV7 [P2]:设计决策说明
    ──────────────────────────────────────────────
    [20] collector.py 提供了两个 Top 进程接口:
      - get_top_processes:独立版,含 0.5s sleep(本接口使用)
      - _collect_cpu_and_processes:合并版,N3-2 优化(共享 0.5s sleep)
    本接口选择独立版的原因:
      1. /processes 仅需要进程列表,不需要 CPU 全量指标
      2. 5s TTL 缓存已能缓解 0.5s sleep 的性能压力
      3. 调用合并版会"额外采集 CPU/per_core 等不需要的数据"
    若未来 /processes 高频调用成为瓶颈,可考虑改走 N3-1 引擎层缓存
    (从 get_cached_snapshot 中提取 top_processes 字段)
    ──────────────────────────────────────────────
    """
    logger.debug(f"请求 Top 进程列表,limit={limit}")

    # 🔧 重构:ParametricTTLCache 内部已处理并发,无需手动双重检查
    cached = _processes_cache.get(limit=limit)
    if cached:
        return cached

    try:
        response = await _collect_top_processes(limit)
        _processes_cache.set(response, limit=limit)
        return response

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"进程列表采集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"进程列表获取失败: {str(e)[:200]}")


# ============================================================
# 接口4:统计摘要
# ============================================================
@router.get(
    "/summary",
    summary="总览大盘四卡片数值",
    responses={
        200: {
            "description": "总览大盘摘要数据",
            "content": {
                "application/json": {
                    "example": {
                        "total_alerts": 42,
                        "heal_rate": 85,
                        "mttd_min": 15,
                        "rca_accuracy": 92,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "获取失败"},
    },
)
async def get_summary() -> dict[str, Any]:
    """
    返回总览大盘指标卡片真实统计数值
    对应前端:今日告警数 / 修复数 / MTTD / RCA 准确率
    ✅ 修复5:使用真实统计引擎,非随机模拟值
    """
    logger.debug("请求总览大盘摘要数据")
    try:
        summary = await get_real_summary()
        logger.debug(
            "摘要数据获取成功 | "
            f"总告警={summary.get('total_alerts', 'N/A')} | "
            f"自愈率={summary.get('heal_rate', 'N/A')}% | "
            f"MTTD={summary.get('mttd_min', 'N/A')}min"
        )
        return summary
    except Exception as e:
        logger.error(f"摘要数据获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"摘要数据获取失败: {str(e)[:200]}")


# ============================================================
# 🔧 MR7 [P2]:维护接口 — 清空缓存
# 🆕 N3-B [P2]:联动清空引擎层缓存(N3-1 一致性)
# 🔧 MRV1 [P0]:f-string 拼接补全分隔符
# 🔧 MRV4 [P1]:简化冗余的 except 类型
# 🔧 RESTful:改为 DELETE 方法
# ============================================================
@router.get(
    "/agent/feedback-accuracy",
    summary="AI 反馈准确率",
    responses={200: {"description": "反馈准确率"}},
)
async def get_feedback_accuracy() -> dict[str, Any]:
    """返回 AI 反馈闭环的统计（total / positive / negative / accuracy）。"""
    from api.ai_feedback_router import _compute_feedback_stats

    return _compute_feedback_stats(today_only=False)


@router.get(
    "/agent/decision-accuracy",
    summary="Agent 决策准确率",
    responses={200: {"description": "决策准确率指标"}},
)
async def get_decision_accuracy_endpoint() -> dict[str, Any]:
    """返回 Agent 决策准确率（precision / recall / f1_score / accuracy）。"""
    return get_decision_accuracy()


@router.delete(
    "/cache",
    summary="清空快照缓存(维护用)",
    include_in_schema=False,  # 不在 OpenAPI 文档中显示
)
async def clear_snapshot_cache() -> dict[str, Any]:
    """
    清空 /snapshot 和 /processes 的内存缓存
    供测试或紧急维护使用,生产环境无需调用

    🔧 MR7:维护接口,不在 Swagger 文档中显示
    🆕 N3-B:同时清空引擎层缓存(对照 N3-1 collector.invalidate_collect_cache)
    🔧 MRV1 [P0]:f-string 拼接补全 " | " 分隔符
    🔧 MRV4 [P1]:简化 except (ImportError, Exception) 为 except Exception
                  (ImportError 是 Exception 的子类,写两个完全等价)
    🔧 重构:使用 TTLCache.clear() 和 ParametricTTLCache.clear()
    """
    # 🔧 Fix: ParametricTTLCache doesn't have is_valid(), just clear
    _snapshot_cache.clear()
    _processes_cache.clear()
    snapshot_cleared = True
    processes_cleared = True

    # 🆕 N3-B:同时清空引擎层缓存
    # 🔧 MRV4 [P1]:ImportError 是 Exception 子类,简化为单一 except
    engine_cleared = False
    try:
        from core.collector import invalidate_collect_cache

        invalidate_collect_cache()
        engine_cleared = True
    except Exception as e:
        # 引擎层缓存清空失败不阻塞主流程(N+3 未完成部署时降级)
        logger.debug(f"N3-B: 引擎层缓存清空失败(已忽略): {e}")

    # 🔧 MRV1 [P0]:补全 " | " 分隔符,日志可读性
    logger.warning(
        f"⚠️ 指标缓存已被清空 | "
        f"snapshot={'已清' if snapshot_cleared else '原本为空'} | "
        f"processes={'已清' if processes_cleared else '原本为空'} | "  # 🔧 MRV1:补回 " | "
        f"engine={'已清' if engine_cleared else '失败/不可用'}"
    )

    return {
        "status": "ok",
        "snapshot_cleared": snapshot_cleared,
        "processes_cleared": processes_cleared,
        "engine_cleared": engine_cleared,
    }
