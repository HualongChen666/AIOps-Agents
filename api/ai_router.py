# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from core.ai_engine import analyze
from core.collector import collect_all, get_cached_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI分析"])
_METRICS_CTX_MAX_LEN = 500
try:
    from config import AI_RICH_CONTEXT_TIMEOUT_SEC as _CFG_RC_TIMEOUT

    _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC: float = max(0.5, min(10.0, float(_CFG_RC_TIMEOUT)))
except (ImportError, AttributeError, ValueError, TypeError):
    _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC = 2.0


class AnalyzeRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="自然语言问题描述",
        examples=["CPU 使用率飙升,请分析根因"],
    )
    include_metrics: bool = Field(default=True, description="是否采集当前系统指标作为分析上下文")
    platform: str = Field(
        default="windows", description="目标平台: windows | linux", pattern="^(windows|linux)$"
    )
    include_rich_context: bool = Field(
        default=True, description="是否包含富上下文(进程/告警/修复历史),默认开启"
    )

    @field_validator("platform")
    @classmethod
    def _normalize_platform(cls, v: str) -> str:
        return (v or "windows").strip().lower()

    @field_validator("query")
    @classmethod
    def _strip_query(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("query 不能为纯空白字符串")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "query": "example",
                "include_metrics": True,
                "platform": "example",
                "include_rich_context": True,
            }
        },
    }


def _safe_alert_value(val: Any) -> Any:
    """
    🔧 AIRV5:统一处理 alert.value 字段
    - 数字 / bool / None:原样保留
    - 字符串:尝试转 float,失败保留原值
    - 其他类型:str() 转换后截断
    """
    if val is None or isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, str):
        try:
            return float(val)
        except (ValueError, TypeError):
            return val[:64]
    return str(val)[:64]


def _safe_get_metric(
    snapshot: dict[str, Any], section: str, field: str, default: Any = "N/A"
) -> Any:
    """
    🔧 AIRV7:从 snapshot 中安全提取嵌套字段
    - snapshot[section] 不存在或非 dict → 返回 default
    - snapshot[section][field] 不存在 → 返回 default
    """
    if not isinstance(snapshot, dict):
        return default
    section_data = snapshot.get(section)
    if not isinstance(section_data, dict):
        return default
    return section_data.get(field, default)


def _extract_gather_result(result: Any, name: str, expected_type: type) -> Any:
    """
    🔧 AIRV1 [P0]:统一处理 asyncio.gather(return_exceptions=True) 结果
    严格区分 Exception / None / 正常返回值,记录精细日志

    Args:
        result:        gather 单项结果(可能是 Exception/None/正常值)
        name:          数据源名称(用于日志)
        expected_type: 期望的返回类型(list/dict)

    Returns:
        正常值 / None(Exception 或类型不匹配)

    注意:CancelledError 由 AIRV2 修复路径单独处理,本函数不处理
    """
    if isinstance(result, asyncio.CancelledError):
        logger.error(f"N3 富上下文 [{name}] CancelledError 未被上游处理(异常)")
        return None
    if isinstance(result, Exception):
        logger.warning(f"N3 富上下文 [{name}] 任务异常: {type(result).__name__}: {result}")
        return None
    if result is None:
        return None
    if isinstance(result, expected_type):
        return result
    logger.warning(
        f"N3 富上下文 [{name}] 返回类型异常: {type(result).__name__},期望 {expected_type.__name__}"
    )
    return None


async def _collect_rich_context(snapshot: Optional[dict] = None) -> dict[str, Any]:
    """
    🆕 N3 优化版:4 个数据源并行采集

    改造要点:
      1. 4 个数据源 asyncio.gather 并行(原串行)
      2. 各数据源独立 2s 超时(原共享 8s)
      3. 优先复用 get_cached_snapshot()(N3-1 缓存)
      4. return_exceptions=True 确保单个失败不中断
      5. 🔧 AIRV1:gather 结果统一通过 _extract_gather_result 解析
      6. 🔧 AIRV2:手动检测 CancelledError 并 reraise

    总耗时:从 sum(各源) 降到 max(各源) ≈ 2s

    Args:
        snapshot: 调用方传入的快照(可选)
                  优先级:传入 snapshot > 引擎层缓存 > 空列表

    Returns:
        rich_context dict(失败的字段为默认空值)
    """
    rich_context: dict[str, Any] = {
        "top_processes": [],
        "recent_alerts": [],
        "recent_repairs": [],
        "stats": {},
    }

    async def _fetch_processes():
        try:
            src = snapshot
            if not src or not isinstance(src, dict):
                src = get_cached_snapshot()
            if src and isinstance(src, dict):
                top_procs = src.get("top_processes", [])
                return top_procs[:5] if isinstance(top_procs, list) else []
        except Exception as e:
            logger.warning(f"N3 富上下文:进程数据提取失败 {e}")
        return []

    async def _fetch_alerts():
        try:
            from core.alert_engine import alert_history

            recent_alerts = list(alert_history)[:10]
            cleaned = []
            for a in recent_alerts:
                if not isinstance(a, dict):
                    continue
                level = a.get("level", "info")
                if not isinstance(level, str):
                    level = str(level) if level is not None else "info"
                cleaned.append(
                    {
                        "level": level,
                        "title": str(a.get("title", ""))[:200],
                        "desc": str(a.get("desc", ""))[:500],
                        "raw_time": str(a.get("raw_time", ""))[:32],
                        "metric": str(a.get("metric", ""))[:64],
                        "value": _safe_alert_value(a.get("value", 0)),
                    }
                )
            return cleaned
        except Exception as e:
            logger.warning(f"N3 富上下文:告警历史读取失败 {e}")
        return []

    async def _fetch_repairs():
        try:
            return await asyncio.to_thread(_get_recent_repairs)
        except Exception as e:
            logger.warning(f"N3 富上下文:修复记录读取失败 {e}")
        return []

    async def _fetch_stats():
        try:
            from core.stats_engine import get_real_summary

            summary = await asyncio.to_thread(get_real_summary)
            return {
                "current_anomalies": summary.get("current_anomalies", 0),
                "heal_rate": summary.get("heal_rate", 0),
                "total_alerts": summary.get("total_alerts", 0),
                "mttr": summary.get("mttr", 0),
            }
        except Exception as e:
            logger.warning(f"N3 富上下文:统计摘要读取失败 {e}")
        return {}

    async def _with_timeout(coro, name: str):
        """为单个数据源添加独立超时"""
        try:
            return await asyncio.wait_for(coro, timeout=_RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            logger.warning(f"N3 富上下文:{name} 超时(>{_RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC}s)")
            return None
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"N3 富上下文:{name} 异常: {e}")
            return None

    try:
        results = await asyncio.gather(
            _with_timeout(_fetch_processes(), "进程"),
            _with_timeout(_fetch_alerts(), "告警"),
            _with_timeout(_fetch_repairs(), "修复"),
            _with_timeout(_fetch_stats(), "统计"),
            return_exceptions=True,
        )
        for idx, r in enumerate(results):
            if isinstance(r, asyncio.CancelledError):
                logger.info(f"N3 富上下文采集被取消(检测点 idx={idx})")
                raise r
        top_procs = _extract_gather_result(results[0], "进程", list)
        if top_procs is not None:
            rich_context["top_processes"] = top_procs
        recent_alerts = _extract_gather_result(results[1], "告警", list)
        if recent_alerts is not None:
            rich_context["recent_alerts"] = recent_alerts
        recent_repairs = _extract_gather_result(results[2], "修复", list)
        if recent_repairs is not None:
            rich_context["recent_repairs"] = recent_repairs
        stats = _extract_gather_result(results[3], "统计", dict)
        if stats is not None:
            rich_context["stats"] = stats
    except asyncio.CancelledError:
        logger.info("N3 富上下文采集被取消(外层 except 捕获)")
        raise
    except Exception as e:
        logger.warning(f"N3 富上下文 gather 异常,返回部分结果: {e}")
    return rich_context


def _get_recent_repairs() -> list[dict[str, Any]]:
    """
    获取最近 5 次修复记录

    🔧 AIR2 [P1]:增加 today_only=True 过滤
        - 修复前:可能返回 90 天前的旧记录,污染 AI 上下文质量
        - 修复后:仅看今日数据,贴合"最近"语义
    🔧 BUG-FIX-9(中危):简化死代码 — N-1 SQLite 持久化已完成
    """
    try:
        from core.db_engine import query_repairs

        repairs = query_repairs(today_only=True, limit=5)
        return [
            {
                "success": r.get("success", False),
                "script_name": r.get("rule_name") or r.get("script_key", ""),
                "script_key": r.get("script_key", ""),
                "repair_duration_sec": r.get("repair_duration_sec"),
                "platform": r.get("platform", "windows"),
            }
            for r in repairs
        ]
    except Exception as e:
        logger.warning(f"M-1 富上下文:SQLite 修复记录读取失败,返回空列表: {e}")
        return []


def _extract_disk_usage(snapshot: dict[str, Any]) -> str:
    """从快照中提取磁盘使用率"""
    disk_usage = "N/A"
    disk_data = snapshot.get("disk")
    if isinstance(disk_data, list) and len(disk_data) > 0:
        first = disk_data[0]
        if isinstance(first, dict):
            disk_usage = first.get("usage_percent", "N/A")
    elif isinstance(disk_data, dict):
        first_key = next(iter(disk_data), None)
        if first_key:
            first_val = disk_data[first_key]
            if isinstance(first_val, dict):
                disk_usage = first_val.get("usage_percent", "N/A")
    return disk_usage


def _build_metrics_context(snapshot: dict[str, Any]) -> str:
    """构造指标上下文字符串"""
    cpu_usage = _safe_get_metric(snapshot, "cpu", "usage_percent")
    mem_usage = _safe_get_metric(snapshot, "memory", "usage_percent")
    disk_usage = _extract_disk_usage(snapshot)
    metrics_ctx = f"CPU={cpu_usage}% | 内存={mem_usage}% | 磁盘={disk_usage}%"[
        :_METRICS_CTX_MAX_LEN
    ]
    return metrics_ctx


async def _collect_snapshot_with_cache() -> Optional[dict[str, Any]]:
    """采集快照（优先使用缓存）"""
    snapshot = get_cached_snapshot()
    if snapshot is None:
        snapshot = await asyncio.to_thread(collect_all) or {}
    else:
        logger.debug("N3-C: AI 分析复用引擎层采集缓存")
    return snapshot


def _build_context_summary(rich_context: Optional[dict[str, Any]]) -> dict[str, Any]:
    """构造上下文摘要"""
    return {
        "rich_enabled": rich_context is not None,
        "process_count": len(rich_context.get("top_processes", [])) if rich_context else 0,
        "alert_count": len(rich_context.get("recent_alerts", [])) if rich_context else 0,
        "repair_count": len(rich_context.get("recent_repairs", [])) if rich_context else 0,
    }


@router.post(
    "/analyze",
    summary="AI 根因分析(🔧 M-1 富上下文增强)",
    responses={
        (200): {
            "description": "AI分析结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "analysis": "High CPU usage detected in python3 process consuming 85% CPU",
                        "metrics_context": "CPU=85.2% | 内存=68.3% | 磁盘=45.0%",
                        "platform": "windows",
                        "context_summary": {
                            "rich_enabled": True,
                            "process_count": 5,
                            "alert_count": 10,
                            "repair_count": 3,
                        },
                    }
                }
            },
        },
        (400): {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Invalid request parameters",
                        "error_code": "VALIDATION_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (500): {
            "description": "AI分析服务不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "AI analysis service unavailable",
                        "error_code": "AI_ANALYSIS_FAILED",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        (503): {
            "description": "服务暂时不可用",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Service temporarily unavailable",
                        "error_code": "SERVICE_UNAVAILABLE",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def ai_analyze(req: AnalyzeRequest, request: Request) -> dict[str, Any]:
    """
    接收自然语言问题,结合当前系统快照 + 富上下文,返回 AI 根因分析结果
    支持 Windows 和 Linux 双平台

    🔧 AIR1 [P0]:include_metrics 与 include_rich_context 参数语义独立
        - include_metrics=True:采集简易指标(CPU/MEM/磁盘百分比)
        - include_rich_context=True:采集富上下文(进程/告警/修复)
        - 两者都可独立启用/禁用

    🆕 N3-C:优先复用 get_cached_snapshot()(引擎层 1.5s TTL 缓存)
        - 缓存命中时直接返回,避免重复触发 collect_all(~1.1s)
        - 缓存未命中才触发真实采集

    🔧 M-1:可传入 include_rich_context=true 启用富上下文增强(默认开启)
            富上下文包含:Top 5 进程、最近 10 条告警、最近 5 次修复记录、系统统计

    Returns:
        dict: AI analysis result
        - analysis: Natural language root cause analysis
        - confidence: Confidence score (0-1)
        - suggested_actions: List of recommended actions
        - context_used: Context data used for analysis
        - timestamp: ISO format timestamp

    Example response:
        {
            "analysis": "High CPU usage detected in python3 process consuming 85% CPU",
            "confidence": 0.92,
            "suggested_actions": [
                "Check process logs for unusual activity",
                "Consider scaling resources",
                "Monitor memory usage"
            ],
            "context_used": {
                "cpu_usage": 85.2,
                "memory_usage": 68.3,
                "top_processes": [
                    {"name": "python3", "cpu": 85.2, "memory": 12.5}
                ]
            },
            "timestamp": "2026-07-02T00:00:00Z"
        }

    Error responses:
        - 400: Invalid request parameters
        - 500: AI analysis service unavailable
        - 503: Service temporarily unavailable
    """
    operator_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"收到 AI 分析请求 | operator={operator_ip} | query='{req.query[:50]}' |"
        f" include_metrics={req.include_metrics} | platform={req.platform} |"
        f" rich_context={req.include_rich_context}"
    )
    metrics_ctx = ""
    rich_context: Optional[dict[str, Any]] = None
    snapshot: Optional[dict] = None
    need_collect = req.include_metrics or req.include_rich_context
    if need_collect:
        try:
            snapshot = await _collect_snapshot_with_cache()
            if req.include_metrics and isinstance(snapshot, dict):
                metrics_ctx = _build_metrics_context(snapshot)
                logger.debug(f"系统指标快照采集成功: {metrics_ctx}")
        except asyncio.CancelledError:
            logger.info("AI 分析的指标采集被取消")
            raise
        except Exception as e:
            logger.warning(f"系统指标采集失败,降级为无指标分析模式: {e}")
    if req.include_rich_context:
        try:
            rich_context = await _collect_rich_context(snapshot)
            logger.debug(
                f"N3 富上下文采集完成 | 进程={len(rich_context.get('top_processes', []))} |"
                f" 告警={len(rich_context.get('recent_alerts', []))} |"
                f" 修复={len(rich_context.get('recent_repairs', []))}"
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"N3 富上下文采集失败,降级到简易模式: {e}")
            rich_context = None
    try:
        result = await analyze(
            query=req.query,
            metrics_snapshot=metrics_ctx,
            platform=req.platform,
            rich_context=rich_context,
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"AI 引擎调用异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 引擎调用失败: {str(e)[:200]}")
    result_length = len(result) if isinstance(result, str) else 0
    logger.info(
        f"AI 分析完成 | operator={operator_ip} | platform={req.platform} |"
        f" 结果长度={result_length} 字符"
    )
    return {
        "status": "ok",
        "analysis": result,
        "metrics_context": metrics_ctx,
        "platform": req.platform,
        "context_summary": _build_context_summary(rich_context),
    }
