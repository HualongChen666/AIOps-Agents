# -*- coding: utf-8 -*-
"""
Slow Query Analyzer
慢查询分析工具
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import text

from core.db_engine import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class SlowQuery:
    """慢查询数据类"""

    query_id: str
    query_text: str
    execution_time: float
    calls: int
    total_time: float
    mean_time: float
    max_time: float
    rows: int
    database: str
    timestamp: datetime


@dataclass
class QueryOptimization:
    """查询优化建议"""

    query_id: str
    query_text: str
    suggestions: List[str]
    priority: str
    estimated_improvement: float


class SlowQueryAnalyzer:
    """慢查询分析器"""

    def __init__(self, threshold_ms: float = 100.0):
        """
        初始化慢查询分析器

        Args:
            threshold_ms: 慢查询阈值（毫秒）
        """
        self.threshold_ms = threshold_ms
        self.slow_queries: List[SlowQuery] = []

    async def analyze_pg_stat_statements(self) -> List[SlowQuery]:
        """
        分析pg_stat_statements视图

        Returns:
            慢查询列表
        """
        try:
            async with AsyncSessionLocal() as session:
                # 查询pg_stat_statements
                query = text("""
                    SELECT
                        queryid,
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        rows,
                        datname
                    FROM pg_stat_statements
                    WHERE mean_exec_time > :threshold
                    ORDER BY mean_exec_time DESC
                    LIMIT 100
                """)

                result = await session.execute(query, {"threshold": self.threshold_ms / 1000})
                rows = result.fetchall()

                slow_queries = []
                for row in rows:
                    slow_query = SlowQuery(
                        query_id=str(row[0]),
                        query_text=row[1][:500],  # 限制长度
                        execution_time=row[4] * 1000,  # 转换为毫秒
                        calls=row[2],
                        total_time=row[3] * 1000,
                        mean_time=row[4] * 1000,
                        max_time=row[5] * 1000,
                        rows=row[6],
                        database=row[7],
                        timestamp=datetime.now(),
                    )
                    slow_queries.append(slow_query)

                self.slow_queries = slow_queries
                return slow_queries

        except Exception as e:
            logger.error(f"分析pg_stat_statements失败: {e}")
            return []

    async def analyze_pg_stat_activity(self) -> List[Dict[str, Any]]:
        """
        分析当前活动查询

        Returns:
            活动查询列表
        """
        try:
            async with AsyncSessionLocal() as session:
                query = text("""
                    SELECT
                        pid,
                        usename,
                        application_name,
                        client_addr,
                        state,
                        query_start,
                        state_change,
                        query,
                        wait_event_type,
                        wait_event
                    FROM pg_stat_activity
                    WHERE state != 'idle'
                    AND query_start < NOW() - INTERVAL '5 seconds'
                    ORDER BY query_start
                """)

                result = await session.execute(query)
                rows = result.fetchall()

                active_queries = []
                for row in rows:
                    active_queries.append(
                        {
                            "pid": row[0],
                            "usename": row[1],
                            "application_name": row[2],
                            "client_addr": row[3],
                            "state": row[4],
                            "query_start": row[5],
                            "state_change": row[6],
                            "query": row[7][:500] if row[7] else "",
                            "wait_event_type": row[8],
                            "wait_event": row[9],
                        }
                    )

                return active_queries

        except Exception as e:
            logger.error(f"分析pg_stat_activity失败: {e}")
            return []

    async def analyze_pg_stat_user_tables(self) -> List[Dict[str, Any]]:
        """
        分析表统计信息

        Returns:
            表统计信息列表
        """
        try:
            async with AsyncSessionLocal() as session:
                query = text("""
                    SELECT
                        schemaname,
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del,
                        n_tup_hot_upd,
                        n_live_tup,
                        n_dead_tup,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze,
                        vacuum_count,
                        autovacuum_count,
                        analyze_count,
                        autoanalyze_count
                    FROM pg_stat_user_tables
                    ORDER BY seq_tup_read DESC
                """)

                result = await session.execute(query)
                rows = result.fetchall()

                table_stats = []
                for row in rows:
                    table_stats.append(
                        {
                            "schemaname": row[0],
                            "tablename": row[1],
                            "seq_scan": row[2],
                            "seq_tup_read": row[3],
                            "idx_scan": row[4],
                            "idx_tup_fetch": row[5],
                            "n_tup_ins": row[6],
                            "n_tup_upd": row[7],
                            "n_tup_del": row[8],
                            "n_tup_hot_upd": row[9],
                            "n_live_tup": row[10],
                            "n_dead_tup": row[11],
                            "last_vacuum": row[12],
                            "last_autovacuum": row[13],
                            "last_analyze": row[14],
                            "last_autoanalyze": row[15],
                            "vacuum_count": row[16],
                            "autovacuum_count": row[17],
                            "analyze_count": row[18],
                            "autoanalyze_count": row[19],
                        }
                    )

                return table_stats

        except Exception as e:
            logger.error(f"分析pg_stat_user_tables失败: {e}")
            return []

    def generate_optimization_suggestions(
        self, slow_queries: List[SlowQuery]
    ) -> List[QueryOptimization]:
        """
        生成查询优化建议

        Args:
            slow_queries: 慢查询列表

        Returns:
            优化建议列表
        """
        optimizations = []

        for query in slow_queries:
            suggestions = []
            priority = "medium"
            estimated_improvement = 0.0

            query_text = query.query_text.lower()

            # 检查全表扫描
            if "seq scan" in query_text or query.rows > 10000:
                suggestions.append("考虑添加索引以避免全表扫描")
                priority = "high"
                estimated_improvement += 30.0

            # 检查SELECT *
            if "select *" in query_text:
                suggestions.append("避免使用SELECT *，只查询需要的字段")
                priority = "medium"
                estimated_improvement += 15.0

            # 检查LIKE查询
            if "like" in query_text and query_text.startswith("%"):
                suggestions.append("避免LIKE '%pattern'，考虑使用全文索引")
                priority = "high"
                estimated_improvement += 40.0

            # 检查ORDER BY
            if "order by" in query_text and "limit" not in query_text:
                suggestions.append("ORDER BY without LIMIT可能导致大量数据排序")
                priority = "medium"
                estimated_improvement += 20.0

            # 检查JOIN
            if "join" in query_text:
                suggestions.append("确保JOIN字段有索引")
                priority = "medium"
                estimated_improvement += 25.0

            # 检查子查询
            if "select" in query_text and query_text.count("select") > 1:
                suggestions.append("考虑将子查询重写为JOIN")
                priority = "medium"
                estimated_improvement += 20.0

            # 检查聚合函数
            if any(func in query_text for func in ["count(", "sum(", "avg(", "max(", "min("]):
                suggestions.append("考虑对聚合字段添加索引")
                priority = "low"
                estimated_improvement += 15.0

            # 检查频繁调用
            if query.calls > 1000:
                suggestions.append(f"查询被调用{query.calls}次，考虑缓存结果")
                priority = "high"
                estimated_improvement += 50.0

            if suggestions:
                optimization = QueryOptimization(
                    query_id=query.query_id,
                    query_text=query.query_text,
                    suggestions=suggestions,
                    priority=priority,
                    estimated_improvement=min(estimated_improvement, 80.0),
                )
                optimizations.append(optimization)

        return optimizations

    def generate_report(self) -> Dict[str, Any]:
        """
        生成慢查询分析报告

        Returns:
            分析报告
        """
        return {
            "threshold_ms": self.threshold_ms,
            "slow_query_count": len(self.slow_queries),
            "slow_queries": [asdict(q) for q in self.slow_queries],
            "summary": {
                "total_calls": sum(q.calls for q in self.slow_queries),
                "total_time_ms": sum(q.total_time for q in self.slow_queries),
                "avg_time_ms": (
                    sum(q.mean_time for q in self.slow_queries) / len(self.slow_queries)
                    if self.slow_queries
                    else 0
                ),
                "max_time_ms": (
                    max(q.max_time for q in self.slow_queries) if self.slow_queries else 0
                ),
            },
        }

    async def enable_query_logging(self):
        """启用查询日志"""
        try:
            async with AsyncSessionLocal() as session:
                # 设置log_min_duration_statement
                await session.execute(text("ALTER SYSTEM SET log_min_duration_statement = 100"))
                await session.execute(text("ALTER SYSTEM SET log_statement = 'all'"))
                await session.commit()

                logger.info("查询日志已启用")

        except Exception as e:
            logger.error(f"启用查询日志失败: {e}")

    async def disable_query_logging(self):
        """禁用查询日志"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("ALTER SYSTEM SET log_min_duration_statement = -1"))
                await session.execute(text("ALTER SYSTEM SET log_statement = 'none'"))
                await session.commit()

                logger.info("查询日志已禁用")

        except Exception as e:
            logger.error(f"禁用查询日志失败: {e}")


async def analyze_slow_queries(threshold_ms: float = 100.0) -> Dict[str, Any]:
    """
    分析慢查询的便捷函数

    Args:
        threshold_ms: 慢查询阈值（毫秒）

    Returns:
        分析报告
    """
    analyzer = SlowQueryAnalyzer(threshold_ms=threshold_ms)

    # 分析慢查询
    slow_queries = await analyzer.analyze_pg_stat_statements()

    # 生成优化建议
    optimizations = analyzer.generate_optimization_suggestions(slow_queries)

    # 生成报告
    report = analyzer.generate_report()
    report["optimizations"] = [asdict(opt) for opt in optimizations]

    return report


async def check_table_health() -> Dict[str, Any]:
    """
    检查表健康状态

    Returns:
        表健康报告
    """
    analyzer = SlowQueryAnalyzer()

    # 获取表统计信息
    table_stats = await analyzer.analyze_pg_stat_user_tables()

    # 分析表健康
    health_report = {"tables": [], "issues": []}

    for stat in table_stats:
        table_name = stat["tablename"]
        issues = []

        # 检查全表扫描比例
        if stat["seq_scan"] > 100 and stat["idx_scan"] < stat["seq_scan"]:
            issues.append(f"表{table_name}全表扫描过多，建议添加索引")

        # 检查死元组比例
        if stat["n_live_tup"] > 0:
            dead_ratio = stat["n_dead_tup"] / stat["n_live_tup"]
            if dead_ratio > 0.2:
                issues.append(f"表{table_name}死元组比例过高({dead_ratio:.2%})，建议执行VACUUM")

        # 检查最后清理时间
        if stat["last_vacuum"]:
            days_since_vacuum = (datetime.now() - stat["last_vacuum"]).days
            if days_since_vacuum > 7:
                issues.append(f"表{table_name}超过{days_since_vacuum}天未执行VACUUM")

        # 检查最后分析时间
        if stat["last_analyze"]:
            days_since_analyze = (datetime.now() - stat["last_analyze"]).days
            if days_since_analyze > 7:
                issues.append(f"表{table_name}超过{days_since_analyze}天未执行ANALYZE")

        health_report["tables"].append(
            {
                "table_name": table_name,
                "health": "healthy" if not issues else "unhealthy",
                "issues": issues,
                "stats": stat,
            }
        )

        if issues:
            health_report["issues"].extend(issues)

    return health_report
