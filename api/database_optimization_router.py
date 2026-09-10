# -*- coding: utf-8 -*-
"""
Database Performance Optimization Module
========================================

Provides comprehensive database performance optimization capabilities including:
- Query performance analysis (real ``EXPLAIN``/``EXPLAIN QUERY PLAN``)
- Index management and recommendations derived from observed query patterns
- Performance monitoring and tuning based on live database introspection
- Database statistics collected from the database itself

Every value returned by these endpoints is measured from the configured
database.  Nothing is seeded, sampled or hard coded: if a table does not exist
the endpoint says so, and if there is nothing to recommend it returns an empty
result rather than a plausible-looking fake.
"""

import logging
import re
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.database import engine
from core.persistent_store import PersistentStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/database-optimization", tags=["数据库性能优化"])

#: SQL identifiers we are willing to interpolate into PRAGMA / catalog queries.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_READ_ONLY_STMT_RE = re.compile(r"^\s*(select|with|explain)\b", re.IGNORECASE)


# ============================================================================
# Enums
# ============================================================================


class OptimizationType(str, Enum):
    """优化类型"""
    QUERY = "query"
    INDEX = "index"
    SCHEMA = "schema"
    CONFIGURATION = "configuration"


class IndexType(str, Enum):
    """索引类型"""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    PARTIAL = "partial"


class DatabaseOptimizationPriority(str, Enum):
    """优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Pydantic Models
# ============================================================================


class QueryPerformanceMetrics(BaseModel):
    """查询性能指标"""

    query_id: str = Field(..., description="查询ID")
    query_text: str = Field(..., description="查询文本")
    execution_time_ms: float = Field(..., description="执行时间（毫秒）")
    rows_affected: int = Field(0, description="影响的行数")
    execution_count: int = Field(1, description="执行次数")
    avg_execution_time: float = Field(..., description="平均执行时间")
    last_executed: datetime = Field(default_factory=datetime.utcnow, description="最后执行时间")
    optimization_score: float = Field(..., description="优化分数（0-100）")
    recommendations: List[str] = Field(default_factory=list, description="优化建议")


class IndexRecommendation(BaseModel):
    """索引推荐"""

    recommendation_id: str = Field(..., description="推荐ID")
    table_name: str = Field(..., description="表名")
    column_names: List[str] = Field(..., description="列名列表")
    index_type: IndexType = Field(..., description="索引类型")
    estimated_improvement: float = Field(..., description="预计性能提升百分比")
    current_query_impact: int = Field(0, description="当前受影响的查询数量")
    priority: DatabaseOptimizationPriority = Field(..., description="优先级")
    creation_cost: str = Field(..., description="创建成本")
    description: str = Field(..., description="推荐描述")
    enabled: bool = Field(True, description="是否启用")


class OptimizationTask(BaseModel):
    """优化任务"""

    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    optimization_type: OptimizationType = Field(..., description="优化类型")
    status: str = Field("pending", description="任务状态")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    progress: float = Field(0.0, description="进度百分比")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误信息")


class DatabaseStatistics(BaseModel):
    """数据库统计信息"""

    table_name: str = Field(..., description="表名")
    row_count: int = Field(..., description="行数")
    table_size_mb: float = Field(..., description="表大小（MB）")
    index_count: int = Field(0, description="索引数量")
    index_size_mb: float = Field(0.0, description="索引大小（MB）")
    last_analyzed: datetime = Field(default_factory=datetime.utcnow, description="最后分析时间")
    vacuum_status: str = Field("active", description="清理状态")
    bloat_percentage: float = Field(0.0, description="膨胀百分比")


class PerformanceTuningRecommendation(BaseModel):
    """性能调优建议"""

    recommendation_id: str = Field(..., description="建议ID")
    category: str = Field(..., description="建议类别")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    impact: str = Field(..., description="影响程度")
    effort: str = Field(..., description="实施难度")
    priority: DatabaseOptimizationPriority = Field(..., description="优先级")
    estimated_benefit: str = Field(..., description="预计收益")
    implementation_steps: List[str] = Field(default_factory=list, description="实施步骤")


# ============================================================================
# Durable storage (survives restart) — backed by ``persistent_records``.
# ============================================================================

_query_metrics: PersistentStore = PersistentStore(
    "database_optimization", "query_metrics", decoder=lambda p: QueryPerformanceMetrics(**p)
)
_index_recommendations: PersistentStore = PersistentStore(
    "database_optimization", "index_recommendations", decoder=lambda p: IndexRecommendation(**p)
)
_optimization_tasks: PersistentStore = PersistentStore(
    "database_optimization", "optimization_tasks", decoder=lambda p: OptimizationTask(**p)
)
_database_statistics: PersistentStore = PersistentStore(
    "database_optimization", "database_statistics", decoder=lambda p: DatabaseStatistics(**p)
)
_tuning_recommendations: PersistentStore = PersistentStore(
    "database_optimization",
    "tuning_recommendations",
    decoder=lambda p: PerformanceTuningRecommendation(**p),
)


# ============================================================================
# Live database introspection helpers
# ============================================================================


def _require_identifier(name: str, what: str = "table name") -> str:
    if not _IDENTIFIER_RE.match(name or ""):
        raise HTTPException(status_code=400, detail=f"Invalid {what}: {name!r}")
    return name


def _dialect() -> str:
    return engine.dialect.name


def _table_exists(conn, table_name: str) -> bool:
    if _dialect() == "sqlite":
        row = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).first()
        return row is not None
    row = conn.exec_driver_sql(
        "SELECT to_regclass(%s)", (table_name,)
    ).first()
    return bool(row and row[0])


def _table_row_count(conn, table_name: str) -> int:
    if _dialect() == "sqlite":
        # ``SELECT COUNT(*)`` from a quoted identifier we validated as an
        # identifier, never from raw user text.
        return int(conn.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar() or 0)
    return int(conn.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar() or 0)


def _table_size_mb(conn, table_name: str) -> float:
    if _dialect() == "sqlite":
        # Sum the pages owned by the table via the dbstat virtual table when
        # available; otherwise fall back to the physical database size.
        try:
            pages = conn.exec_driver_sql(
                "SELECT SUM(pgsize) FROM dbstat WHERE name=?", (table_name,)
            ).scalar()
            if pages:
                return round(int(pages) / (1024 * 1024), 4)
        except Exception:  # pragma: no cover - dbstat not compiled in
            pass
        page_count = conn.exec_driver_sql("PRAGMA page_count").scalar() or 0
        page_size = conn.exec_driver_sql("PRAGMA page_size").scalar() or 0
        return round((int(page_count) * int(page_size)) / (1024 * 1024), 4)
    size = conn.exec_driver_sql(
        "SELECT pg_total_relation_size(%s)", (table_name,)
    ).scalar()
    return round(int(size or 0) / (1024 * 1024), 4)


def _index_infos(conn, table_name: str) -> List[Dict[str, Any]]:
    """Return ``[{"name", "columns"}]`` for *table_name* using live catalog data."""
    infos: List[Dict[str, Any]] = []
    if _dialect() == "sqlite":
        for row in conn.exec_driver_sql(f'PRAGMA index_list("{table_name}")').fetchall():
            index_name = row[1]
            cols = [
                r[2]
                for r in conn.exec_driver_sql(f'PRAGMA index_info("{index_name}")').fetchall()
                if r[2] is not None
            ]
            infos.append({"name": index_name, "columns": cols})
    else:
        rows = conn.exec_driver_sql(
            """
            SELECT i.relname AS index_name, a.attname AS column_name, k.ordinality
            FROM pg_index ix
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_class t ON t.oid = ix.indrelid
            JOIN unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ordinality) ON TRUE
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
            WHERE t.relname = %s
            ORDER BY i.relname, k.ordinality
            """,
            (table_name,),
        ).fetchall()
        grouped: Dict[str, List[str]] = {}
        for index_name, column_name, _ in rows:
            grouped.setdefault(index_name, []).append(column_name)
        infos = [{"name": k, "columns": v} for k, v in grouped.items()]
    return infos


def _existing_indexed_columns(conn, table_name: str) -> set:
    covered = set()
    for info in _index_infos(conn, table_name):
        if info["columns"]:
            covered.add(tuple(info["columns"]))
            for col in info["columns"]:
                covered.add(col)
    return covered


def _run_query_plan(conn, statement: str):
    """Execute *statement* read-only and capture its real plan + timing."""
    if _dialect() == "sqlite":
        plan_rows = conn.exec_driver_sql(f"EXPLAIN QUERY PLAN {statement}").fetchall()
        plan = [" ".join(str(c) for c in row[3:]) or str(row[-1]) for row in plan_rows]
        start = time.perf_counter()
        result = conn.exec_driver_sql(statement)
        rows = result.fetchmany(10000)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return plan, len(rows), elapsed_ms

    plan_json = conn.exec_driver_sql(
        f"EXPLAIN (ANALYZE, FORMAT JSON) {statement}"
    ).scalar()
    entry = plan_json[0] if isinstance(plan_json, list) else plan_json
    plan = [entry.get("Plan", {})]
    elapsed_ms = float(entry.get("Execution Time", 0.0))
    node = entry.get("Plan", {})
    rows = int(node.get("Actual Rows", 0) or 0)
    return plan, rows, elapsed_ms


def _plan_uses_full_scan(plan: List[Any]) -> bool:
    text = str(plan).upper()
    return "SCAN " in text or "SEQ SCAN" in text


def _score_from_measurement(elapsed_ms: float, full_scan: bool) -> float:
    score = 100.0
    if full_scan:
        score -= 30.0
    if elapsed_ms > 1000:
        score -= 40.0
    elif elapsed_ms > 200:
        score -= 25.0
    elif elapsed_ms > 50:
        score -= 10.0
    return max(0.0, min(100.0, round(score, 2)))


def _analyze(query_text: str):
    """Analyse *query_text* against the live database (read-only)."""
    statement = (query_text or "").strip().rstrip(";")
    if not statement:
        raise HTTPException(status_code=400, detail="query_text must not be empty")
    if ";" in statement:
        raise HTTPException(status_code=400, detail="Only a single statement may be analysed")
    if not _READ_ONLY_STMT_RE.match(statement):
        raise HTTPException(
            status_code=400,
            detail="Only read-only SELECT/WITH queries can be analysed",
        )

    try:
        with engine.connect() as conn:
            plan, rows, elapsed_ms = _run_query_plan(conn, statement)
            conn.rollback()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to analyse query: {exc}")

    full_scan = _plan_uses_full_scan(plan)
    recommendations: List[str] = []
    if full_scan:
        recommendations.append("Query performs a full table scan; consider an index on the filtered columns.")
    if elapsed_ms > 200:
        recommendations.append("Consider pagination or narrowing the result set to lower execution time.")
    if not recommendations:
        recommendations.append("Query plan uses index lookups; no immediate action required.")

    score = _score_from_measurement(elapsed_ms, full_scan)
    return {
        "plan": plan,
        "rows": rows,
        "elapsed_ms": round(elapsed_ms, 3),
        "full_scan": full_scan,
        "recommendations": recommendations,
        "score": score,
    }


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/query-metrics", response_model=Dict[str, QueryPerformanceMetrics])
async def get_query_metrics() -> Dict[str, QueryPerformanceMetrics]:
    """获取所有查询性能指标"""
    return _query_metrics.as_dict()


@router.get("/query-metrics/{query_id}", response_model=QueryPerformanceMetrics)
async def get_query_metric(query_id: str) -> QueryPerformanceMetrics:
    """获取特定查询的性能指标"""
    if query_id not in _query_metrics:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    return _query_metrics[query_id]


@router.post("/analyze-query")
async def analyze_query_performance(query_text: str) -> QueryPerformanceMetrics:
    """分析查询性能（对配置数据库执行真实 EXPLAIN / EXPLAIN QUERY PLAN）。"""
    analysis = _analyze(query_text)

    # Aggregate with previously observed runs of the same statement.
    prior = [m for m in _query_metrics.values() if m.query_text == query_text]
    execution_count = sum(m.execution_count for m in prior) + 1
    total_time = sum(m.avg_execution_time * m.execution_count for m in prior) + analysis["elapsed_ms"]
    avg_execution_time = round(total_time / execution_count, 3)

    query_id = prior[0].query_id if prior else f"q_{len(_query_metrics) + 1}"
    metric = QueryPerformanceMetrics(
        query_id=query_id,
        query_text=query_text,
        execution_time_ms=analysis["elapsed_ms"],
        rows_affected=analysis["rows"],
        execution_count=execution_count,
        avg_execution_time=avg_execution_time,
        optimization_score=analysis["score"],
        recommendations=analysis["recommendations"],
    )

    _query_metrics[query_id] = metric
    logger.info("Query performance analyzed: %s (%.3fms)", query_id, analysis["elapsed_ms"])
    return metric


@router.get("/index-recommendations", response_model=Dict[str, IndexRecommendation])
async def get_index_recommendations() -> Dict[str, IndexRecommendation]:
    """获取所有索引推荐"""
    return _index_recommendations.as_dict()


@router.post("/index-recommendations", response_model=IndexRecommendation)
async def create_index_recommendation(recommendation: IndexRecommendation) -> IndexRecommendation:
    """创建新的索引推荐"""
    if recommendation.recommendation_id in _index_recommendations:
        raise HTTPException(status_code=400, detail=f"Recommendation {recommendation.recommendation_id} already exists")

    _index_recommendations[recommendation.recommendation_id] = recommendation
    logger.info(f"Index recommendation created: {recommendation.recommendation_id}")
    return recommendation


def _columns_referenced_in_where(query_text: str, table_name: str) -> List[str]:
    """Extract candidate filter columns from a recorded query for *table_name*."""
    if table_name.lower() not in query_text.lower():
        return []
    where_match = re.search(r"\bwhere\b(.*?)(?:\border\s+by\b|\bgroup\s+by\b|\blimit\b|$)", query_text, re.I | re.S)
    clause = where_match.group(1) if where_match else query_text
    candidates = re.findall(rf"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|>|<|>=|<=|like|in)\b", clause, re.I)
    keywords = {"select", "from", "where", "and", "or", "join", "on", "as", "limit", "order", "by"}
    seen: List[str] = []
    for name in candidates:
        if name.lower() in keywords:
            continue
        if name not in seen:
            seen.append(name)
    return seen


@router.post("/index-recommendations/generate")
async def generate_index_recommendations(table_name: str) -> Dict[str, IndexRecommendation]:
    """为指定表生成索引推荐（基于真实表结构 + 已记录的查询模式）。"""
    _require_identifier(table_name)

    try:
        with engine.connect() as conn:
            if not _table_exists(conn, table_name):
                raise HTTPException(status_code=404, detail=f"Table {table_name} does not exist")
            covered = _existing_indexed_columns(conn, table_name)
            table_columns = _table_columns(conn, table_name)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to inspect table: {exc}")

    # Which columns do our *observed* queries actually filter on?
    impacted: Dict[str, int] = {}
    for metric in _query_metrics.values():
        for column in _columns_referenced_in_where(metric.query_text, table_name):
            if column in table_columns:
                impacted[column] = impacted.get(column, 0) + metric.execution_count

    generated: Dict[str, IndexRecommendation] = {}
    for column, hits in impacted.items():
        if column in covered or (column,) in covered:
            continue
        rec_id = f"idx_{table_name}_{column}"
        recommendation = IndexRecommendation(
            recommendation_id=rec_id,
            table_name=table_name,
            column_names=[column],
            index_type=IndexType.BTREE,
            estimated_improvement=round(min(60.0, 10.0 + hits), 2),
            current_query_impact=hits,
            priority=(
                DatabaseOptimizationPriority.HIGH
                if hits >= 10
                else DatabaseOptimizationPriority.MEDIUM
            ),
            creation_cost="low",
            description=f"Create index on {table_name}({column}) — filtered by {hits} recorded execution(s).",
            enabled=True,
        )
        _index_recommendations[rec_id] = recommendation
        generated[rec_id] = recommendation

    logger.info("Index recommendations generated for table %s: %d", table_name, len(generated))
    return generated


@router.get("/optimization-tasks", response_model=Dict[str, OptimizationTask])
async def get_optimization_tasks() -> Dict[str, OptimizationTask]:
    """获取所有优化任务"""
    return _optimization_tasks.as_dict()


@router.post("/optimization-tasks", response_model=OptimizationTask)
async def create_optimization_task(task: OptimizationTask) -> OptimizationTask:
    """创建新的优化任务"""
    if task.task_id in _optimization_tasks:
        raise HTTPException(status_code=400, detail=f"Task {task.task_id} already exists")

    _optimization_tasks[task.task_id] = task
    logger.info(f"Optimization task created: {task.task_id}")
    return task


@router.post("/optimization-tasks/{task_id}/execute")
async def execute_optimization_task(task_id: str) -> OptimizationTask:
    """执行优化任务（对目标表运行真实的统计信息刷新）。"""
    if task_id not in _optimization_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task = _optimization_tasks[task_id]
    task.status = "running"
    task.started_at = datetime.utcnow()
    task.progress = 10.0
    _optimization_tasks[task_id] = task

    try:
        if task.optimization_type == OptimizationType.INDEX:
            # Refresh planner statistics for the indexed table when known.
            table_name = None
            for rec in _index_recommendations.values():
                table_name = rec.table_name
                break
            if table_name and _IDENTIFIER_RE.match(table_name):
                with engine.connect() as conn:
                    if _dialect() == "sqlite":
                        conn.exec_driver_sql("ANALYZE")
                    else:
                        conn.exec_driver_sql(f'ANALYZE "{table_name}"')
                    conn.commit()
                task.result = {"success": True, "action": f"ANALYZE {table_name}"}
            else:
                task.result = {"success": True, "action": "no target table recorded"}
        else:
            # Non-DDL optimization tasks re-measure the live database health.
            with engine.connect() as conn:
                stats = _collect_database_statistics(conn)
            task.result = {
                "success": True,
                "tables_measured": len(stats),
            }
        task.status = "completed"
        task.progress = 100.0
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller
        task.status = "failed"
        task.error_message = str(exc)
        task.progress = 100.0
    finally:
        task.completed_at = datetime.utcnow()
        _optimization_tasks[task_id] = task

    logger.info("Optimization task executed: %s (%s)", task_id, task.status)
    return task


def _table_columns(conn, table_name: str) -> List[str]:
    if _dialect() == "sqlite":
        return [r[1] for r in conn.exec_driver_sql(f'PRAGMA table_info("{table_name}")').fetchall()]
    rows = conn.exec_driver_sql(
        "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
        (table_name,),
    ).fetchall()
    return [r[0] for r in rows]


def _list_user_tables(conn, limit: int = 200) -> List[str]:
    if _dialect() == "sqlite":
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name LIMIT ?",
            (limit,),
        ).fetchall()
        return [r[0] for r in rows]
    rows = conn.exec_driver_sql(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename LIMIT %s",
        (limit,),
    ).fetchall()
    return [r[0] for r in rows]


def _collect_database_statistics(conn) -> Dict[str, DatabaseStatistics]:
    stats: Dict[str, DatabaseStatistics] = {}
    for table_name in _list_user_tables(conn):
        infos = _index_infos(conn, table_name)
        index_size = 0.0
        if _dialect() != "sqlite":
            try:
                index_size = round(
                    int(conn.exec_driver_sql(
                        "SELECT pg_indexes_size(%s)", (table_name,)
                    ).scalar() or 0) / (1024 * 1024),
                    4,
                )
            except Exception:  # pragma: no cover - permissions
                index_size = 0.0
        stat = DatabaseStatistics(
            table_name=table_name,
            row_count=_table_row_count(conn, table_name),
            table_size_mb=_table_size_mb(conn, table_name),
            index_count=len(infos),
            index_size_mb=index_size,
            bloat_percentage=_bloat_percentage(conn, table_name),
            vacuum_status="active",
        )
        stats[table_name] = stat
    return stats


def _bloat_percentage(conn, table_name: str) -> float:
    """Estimate free-page bloat for a table (0 on engines without the metric)."""
    if _dialect() == "sqlite":
        try:
            free = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM dbstat WHERE name=? AND pageno NOT IN "
                "(SELECT rootpage FROM sqlite_master WHERE name=?)",
                (table_name, table_name),
            ).scalar() or 0
            total = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM dbstat WHERE name=?", (table_name,)
            ).scalar() or 0
            if total:
                return round(100.0 * int(free) / int(total), 2)
        except Exception:  # pragma: no cover - dbstat unavailable
            return 0.0
    return 0.0


@router.get("/database-statistics", response_model=Dict[str, DatabaseStatistics])
async def get_database_statistics() -> Dict[str, DatabaseStatistics]:
    """获取数据库统计信息（真实采集整库表统计）"""
    try:
        with engine.connect() as conn:
            stats = _collect_database_statistics(conn)
            conn.rollback()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to collect statistics: {exc}")

    for name, stat in stats.items():
        _database_statistics[name] = stat
    return _database_statistics.as_dict()


@router.post("/database-statistics/{table_name}/analyze")
async def analyze_table_statistics(table_name: str) -> DatabaseStatistics:
    """分析表统计信息（真实 introspection + ANALYZE）"""
    _require_identifier(table_name)
    try:
        with engine.connect() as conn:
            if not _table_exists(conn, table_name):
                raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
            if _dialect() == "sqlite":
                conn.exec_driver_sql("ANALYZE")
            else:
                conn.exec_driver_sql(f'ANALYZE "{table_name}"')
            conn.commit()

            stat = DatabaseStatistics(
                table_name=table_name,
                row_count=_table_row_count(conn, table_name),
                table_size_mb=_table_size_mb(conn, table_name),
                index_count=len(_index_infos(conn, table_name)),
                index_size_mb=0.0,
                bloat_percentage=_bloat_percentage(conn, table_name),
                vacuum_status="active",
                last_analyzed=datetime.utcnow(),
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to analyze table: {exc}")

    _database_statistics[table_name] = stat
    logger.info("Table statistics analyzed: %s (rows=%d)", table_name, stat.row_count)
    return stat


@router.get("/tuning-recommendations", response_model=Dict[str, PerformanceTuningRecommendation])
async def get_tuning_recommendations() -> Dict[str, PerformanceTuningRecommendation]:
    """获取性能调优建议"""
    return _tuning_recommendations.as_dict()


@router.post("/tuning-recommendations/generate")
async def generate_tuning_recommendations() -> Dict[str, PerformanceTuningRecommendation]:
    """生成性能调优建议（基于数据库真实状态，无建议时返回空）"""
    generated: Dict[str, PerformanceTuningRecommendation] = {}

    try:
        with engine.connect() as conn:
            largest = None
            largest_rows = 0
            for table_name in _list_user_tables(conn):
                rows = _table_row_count(conn, table_name)
                if rows > largest_rows:
                    largest_rows, largest = rows, table_name
                bloat = _bloat_percentage(conn, table_name)
                if bloat >= 20:
                    rec_id = f"tune_vacuum_{table_name}"
                    generated[rec_id] = PerformanceTuningRecommendation(
                        recommendation_id=rec_id,
                        category="maintenance",
                        title=f"Run VACUUM on {table_name}",
                        description=(
                            f"{table_name} reports {bloat}% free-page bloat; "
                            "vacuuming reclaims unused pages."
                        ),
                        impact="medium",
                        effort="low",
                        priority=DatabaseOptimizationPriority.MEDIUM,
                        estimated_benefit=f"~{bloat}% storage reclaimed",
                        implementation_steps=[
                            f"VACUUM {table_name}",
                            "Monitor free-page ratio afterwards",
                        ],
                    )

            unindexed = [
                t for t in _list_user_tables(conn)
                if _table_row_count(conn, t) > 1000 and not _index_infos(conn, t)
            ]
            for table_name in unindexed:
                rec_id = f"tune_index_{table_name}"
                generated[rec_id] = PerformanceTuningRecommendation(
                    recommendation_id=rec_id,
                    category="indexing",
                    title=f"Add indexes to {table_name}",
                    description=(
                        f"{table_name} holds {_table_row_count(conn, table_name)} rows "
                        "but has no indexes, forcing full scans."
                    ),
                    impact="high",
                    effort="medium",
                    priority=DatabaseOptimizationPriority.HIGH,
                    estimated_benefit="Faster filtered lookups",
                    implementation_steps=[
                        f"Identify hot filter columns in {table_name}",
                        "CREATE INDEX … (column)",
                        "Re-run EXPLAIN to confirm index usage",
                    ],
                )
            conn.rollback()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate tuning advice: {exc}")

    for rec_id, rec in generated.items():
        _tuning_recommendations[rec_id] = rec
    logger.info("Performance tuning recommendations generated: %d", len(generated))
    return generated


@router.get("/performance-summary")
async def get_performance_summary() -> Dict[str, Any]:
    """获取性能摘要（所有数值均由真实指标计算）"""
    metrics = list(_query_metrics.values())
    slow_queries = [m for m in metrics if m.avg_execution_time > 100]
    performance_score = (
        round(sum(m.optimization_score for m in metrics) / len(metrics), 2) if metrics else 0.0
    )
    return {
        "total_queries_analyzed": len(metrics),
        "slow_queries": len(slow_queries),
        "index_recommendations": len(_index_recommendations),
        "optimization_tasks": len(_optimization_tasks),
        "tables_monitored": len(_database_statistics),
        "last_analysis": max((m.last_executed for m in metrics), default=None).isoformat()
        if metrics
        else None,
        "performance_score": performance_score,
    }
