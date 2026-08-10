# -*- coding: utf-8 -*-
import logging
import os
import sqlite3
import time
from threading import Lock
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from core.authentication import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/feedback", tags=["AI反馈闭环"])
_STATS_CACHE_TTL_SEC = 5
_stats_cache: dict = {"all": {"data": None, "ts": 0.0}, "today": {"data": None, "ts": 0.0}}
_stats_cache_lock = Lock()


# Persistent feedback store via SQLite
# Use in-memory DB when running under pytest to keep tests deterministic.
_FEEDBACK_DB_PATH = os.environ.get(
    "AI_FEEDBACK_DB_PATH",
    ":memory:" if os.environ.get("PYTEST_CURRENT_TEST") else "data/ai_feedback.db",
)
_feedback_lock = Lock()


def _init_feedback_db() -> None:
    """初始化 SQLite 反馈表（幂等）。"""
    if _FEEDBACK_DB_PATH != ":memory:":
        try:
            os.makedirs(os.path.dirname(os.path.abspath(_FEEDBACK_DB_PATH)), exist_ok=True)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            logging.warning("Suppressed exception", exc_info=True)
    conn = sqlite3.connect(_FEEDBACK_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_feedback (
            feedback_id TEXT PRIMARY KEY,
            feedback_type TEXT NOT NULL,
            analysis_text TEXT,
            query_text TEXT,
            platform TEXT,
            stage_name TEXT,
            comment TEXT,
            rich_context INTEGER,
            operator_ip TEXT,
            created_at TEXT NOT NULL
        )
        """)
    conn.commit()
    conn.close()


def _insert_feedback(record: dict[str, Any]) -> None:
    with _feedback_lock:
        conn = sqlite3.connect(_FEEDBACK_DB_PATH, check_same_thread=False)
        try:
            conn.execute(
                """
                INSERT INTO ai_feedback (
                    feedback_id, feedback_type, analysis_text, query_text, platform,
                    stage_name, comment, rich_context, operator_ip, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["feedback_id"],
                    record["feedback_type"],
                    record["analysis_text"],
                    record["query_text"],
                    record["platform"],
                    record["stage_name"],
                    record["comment"],
                    1 if record.get("rich_context") else 0,
                    record["operator_ip"],
                    record["created_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _fetch_feedback(
    today_only: bool = False, feedback_type: Optional[str] = None
) -> list[dict[str, Any]]:
    import datetime

    today_str = datetime.date.today().isoformat()
    sql = "SELECT * FROM ai_feedback WHERE 1=1"
    params: list[Any] = []
    if today_only:
        sql += " AND created_at LIKE ?"
        params.append(f"{today_str}%")
    if feedback_type:
        sql += " AND feedback_type = ?"
        params.append(feedback_type)
    sql += " ORDER BY created_at DESC"
    conn = sqlite3.connect(_FEEDBACK_DB_PATH, check_same_thread=False)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        records = [dict(row) for row in rows]
        for r in records:
            r["rich_context"] = bool(r.get("rich_context"))
        return records
    finally:
        conn.close()


_init_feedback_db()


def _get_cached_stats(today_only: bool) -> Optional[dict]:
    """🔧 FB4:从缓存读取统计(命中返回数据,未命中返回 None)"""
    cache_key = "today" if today_only else "all"
    now = time.monotonic()
    with _stats_cache_lock:
        cached = _stats_cache[cache_key]
        if cached["data"] is not None and now - cached["ts"] < _STATS_CACHE_TTL_SEC:
            return dict(cached["data"])
    return None


def _set_cached_stats(today_only: bool, data: dict) -> None:
    """🔧 FB4:写入缓存"""
    cache_key = "today" if today_only else "all"
    with _stats_cache_lock:
        _stats_cache[cache_key]["data"] = dict(data)
        _stats_cache[cache_key]["ts"] = time.monotonic()


def _compute_feedback_stats(today_only: bool = False) -> dict[str, Any]:
    """统计反馈总数、正负样本数及准确率。"""
    records = _fetch_feedback(today_only=today_only)
    total = len(records)
    positive = sum(1 for r in records if r.get("feedback_type") == "positive")
    negative = sum(1 for r in records if r.get("feedback_type") == "negative")
    accuracy = round((positive / total) * 100, 2) if total else 0.0
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "accuracy": accuracy,
    }


def _invalidate_stats_cache() -> None:
    """🔧 FB4:写入新反馈后失效缓存"""
    with _stats_cache_lock:
        for key in _stats_cache:
            _stats_cache[key]["data"] = None
            _stats_cache[key]["ts"] = 0.0


class FeedbackRequest(BaseModel):
    feedback_type: Literal["positive", "negative"] = Field(
        ..., description="反馈类型:positive=👍 准确,negative=👎 不准确"
    )
    analysis_text: str = Field(
        default="", max_length=5000, description="AI 分析结果原文(用于审计回溯)"
    )
    query_text: str = Field(
        default="", max_length=2000, description="用户原始 query(对齐 ai_engine 上限 2000)"
    )
    platform: str = Field(default="windows", pattern="^(windows|linux)$", description="目标平台")
    stage_name: str = Field(default="", max_length=128, description="流水线阶段名称")
    comment: str = Field(default="", max_length=500, description="用户附加评论(可选)")
    rich_context: bool = Field(default=False, description="AI 分析时是否启用了富上下文(M-1)")

    @field_validator("comment")
    @classmethod
    def _strip_comment(cls, v: str) -> str:
        return (v or "").strip()[:500]

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "feedback_type": None,
                "analysis_text": "example",
                "query_text": "example",
                "platform": "example",
                "stage_name": "example",
                "comment": "example",
                "rich_context": True,
            }
        },
    }


@router.post(
    "/submit",
    summary="提交 AI 分析反馈(👍/👎)",
    responses={
        (200): {
            "description": "反馈提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "feedback_id": "fb-550e8400-e29b-41d4-a716-446655440000",
                        "message": "反馈已记录,感谢您的评价!",
                        "stats": {"total": 1, "positive": 1, "negative": 0},
                    }
                }
            },
        },
        (400): {"description": "反馈参数错误"},
        (500): {"description": "反馈记录失败"},
    },
)
async def submit_feedback(
    req: FeedbackRequest,
    request: Request,
    _: Any = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    用户对 AI 分析结果点击👍或👎后调用此接口
    反馈数据写入 SQLite,供 stats_engine 计算真实 RCA 准确率

    🔧 FB3 [P2]:记录操作 IP
    🔧 FB4 [P2]:写入后失效缓存
    """
    operator_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"收到 AI 反馈 | operator={operator_ip} | type={req.feedback_type} |"
        f" platform={req.platform} | stage={req.stage_name} | rich_context={req.rich_context} |"
        f" comment_len={len(req.comment)}"
    )
    try:
        import datetime
        import uuid

        feedback_id = str(uuid.uuid4())
        record: dict[str, Any] = {
            "feedback_id": feedback_id,
            "feedback_type": req.feedback_type,
            "analysis_text": req.analysis_text,
            "query_text": req.query_text,
            "platform": req.platform,
            "stage_name": req.stage_name,
            "comment": req.comment,
            "rich_context": req.rich_context,
            "operator_ip": operator_ip,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        _insert_feedback(record)

        _invalidate_stats_cache()
        stats = _compute_feedback_stats(today_only=False)
        logger.info(f"反馈已记录 | feedback_id={feedback_id} | operator={operator_ip}")
        return {
            "status": "ok",
            "feedback_id": feedback_id,
            "message": "反馈已记录,感谢您的评价!",
            "stats": stats,
        }
    except ValueError as ve:
        logger.warning(f"反馈参数错误 | operator={operator_ip} | error={ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"反馈写入失败 | operator={operator_ip} | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="反馈记录失败,请稍后重试")


@router.get(
    "/stats",
    summary="获取 AI 反馈统计数据",
    responses={
        (200): {
            "description": "反馈统计数据",
            "content": {
                "application/json": {
                    "example": {"total": 100, "positive": 80, "negative": 20, "accuracy": 80.0}
                }
            },
        },
        (500): {"description": "反馈统计查询失败"},
    },
)
async def feedback_stats(
    today_only: bool = Query(default=False, description="是否仅统计今日数据(true/false)")
) -> dict[str, Any]:
    """
    返回 AI 分析的真实准确率统计
    供流水线 RCA 卡片实时显示

    🔧 FB4 [P2]:5 秒 TTL 缓存,降低高频轮询时的 SQLite 压力
    """
    cached = _get_cached_stats(today_only)
    if cached is not None:
        logger.debug(f"反馈统计命中缓存 | today_only={today_only}")
        return cached
    try:
        stats = _compute_feedback_stats(today_only=today_only)
        _set_cached_stats(today_only, stats)
        logger.debug(
            f"反馈统计查询 | today_only={today_only} | total={stats['total']} |"
            f" accuracy={stats['accuracy']}%"
        )
        return stats
    except Exception as e:
        logger.error(f"反馈统计查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="反馈统计查询失败")


@router.get(
    "/recent",
    summary="查询最近的反馈记录",
    responses={
        (200): {
            "description": "反馈记录列表",
            "content": {
                "application/json": {
                    "example": {
                        "total": 10,
                        "filter": {"today_only": False, "feedback_type": None},
                        "records": [],
                    }
                }
            },
        },
        (500): {"description": "反馈记录查询失败"},
    },
)
async def recent_feedback(
    limit: int = Query(default=20, ge=1, le=200, description="返回的反馈记录数量上限"),
    today_only: bool = Query(default=False, description="是否仅返回今日反馈记录(true/false)"),
    feedback_type: Optional[Literal["positive", "negative"]] = Query(
        default=None, description="按反馈类型过滤(positive/negative,留空返回全部)"
    ),
) -> dict[str, Any]:
    """
    返回最近 N 条反馈记录,用于审计 AI 分析质量
    包含 analysis_preview 用于回溯当时的 AI 输出

    🔧 FB2 [P1]:增加 today_only 参数(运维只想看今天的反馈)
    🔧 FB5 [P2]:增加 feedback_type 参数(只看 👎 便于排查 AI 问题)
    """
    try:
        filtered = _fetch_feedback(today_only=today_only, feedback_type=feedback_type)
        filtered = filtered[:limit]
        logger.debug(
            f"最近反馈查询 | limit={limit} | today_only={today_only} | type={feedback_type} |"
            f" 返回={len(filtered)}"
        )
        return {
            "total": len(filtered),
            "filter": {"today_only": today_only, "feedback_type": feedback_type},
            "records": filtered,
        }
    except Exception as e:
        logger.error(f"反馈记录查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="反馈记录查询失败")
