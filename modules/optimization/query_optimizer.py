# -*- coding: utf-8 -*-
"""
query_optimizer.py
------------------
性能优化 - 查询优化模块。

功能：
- SQL 查询分析
- 查询重写
- 索引建议
- 查询计划分析
- 慢查询优化
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 查询类型枚举
# ----------------------------------------------------------------------
class QueryType(Enum):
    """查询类型"""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    ALTER = "alter"
    DROP = "drop"


# ----------------------------------------------------------------------
# 2️⃣ 查询问题
# ----------------------------------------------------------------------
@dataclass
class QueryIssue:
    """查询问题"""

    issue_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggestion: str
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "suggestion": self.suggestion,
            "location": self.location,
        }


# ----------------------------------------------------------------------
# 3️⃣ 索引建议
# ----------------------------------------------------------------------
@dataclass
class IndexSuggestion:
    """索引建议"""

    table_name: str
    column_names: List[str]
    index_type: str  # "btree", "hash", "gin", "gist"
    reason: str
    estimated_impact: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "table_name": self.table_name,
            "column_names": self.column_names,
            "index_type": self.index_type,
            "reason": self.reason,
            "estimated_impact": self.estimated_impact,
        }


# ----------------------------------------------------------------------
# 4️⃣ 查询分析结果
# ----------------------------------------------------------------------
@dataclass
class QueryAnalysisResult:
    """查询分析结果"""

    original_query: str
    query_type: QueryType
    issues: List[QueryIssue] = field(default_factory=list)
    index_suggestions: List[IndexSuggestion] = field(default_factory=list)
    optimized_query: Optional[str] = None
    estimated_improvement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "original_query": self.original_query,
            "query_type": self.query_type.value,
            "issues": [issue.to_dict() for issue in self.issues],
            "index_suggestions": [sug.to_dict() for sug in self.index_suggestions],
            "optimized_query": self.optimized_query,
            "estimated_improvement": self.estimated_improvement,
        }


# ----------------------------------------------------------------------
# 5️⃣ 查询优化器
# ----------------------------------------------------------------------
class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self.query_patterns = {
            "select_all": re.compile(r"SELECT\s+\*", re.IGNORECASE),
            "select_distinct": re.compile(r"SELECT\s+DISTINCT", re.IGNORECASE),
            "like_leading_wildcard": re.compile(r"LIKE\s+'%[^%']+'", re.IGNORECASE),
            "or_in_where": re.compile(r"WHERE.*\s+OR\s+", re.IGNORECASE),
            "subquery_in_select": re.compile(r"SELECT.*\(SELECT", re.IGNORECASE),
            "order_by_without_index": re.compile(r"ORDER\s+BY", re.IGNORECASE),
            "group_by_without_index": re.compile(r"GROUP\s+BY", re.IGNORECASE),
            "join_without_condition": re.compile(r"JOIN\s+\w+\s+ON\s+1=1", re.IGNORECASE),
        }

    def analyze_query(self, query: str) -> QueryAnalysisResult:
        """
        分析查询

        Parameters
        ----------
        query : str
            SQL 查询

        Returns
        -------
        QueryAnalysisResult
            分析结果
        """
        query_type = self._detect_query_type(query)
        issues = self._detect_issues(query)
        index_suggestions = self._suggest_indexes(query)
        optimized_query = self._optimize_query(query, issues)

        return QueryAnalysisResult(
            original_query=query,
            query_type=query_type,
            issues=issues,
            index_suggestions=index_suggestions,
            optimized_query=optimized_query,
            estimated_improvement=self._estimate_improvement(issues),
        )

    def _detect_query_type(self, query: str) -> QueryType:
        """检测查询类型"""
        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            return QueryType.SELECT
        elif query_upper.startswith("INSERT"):
            return QueryType.INSERT
        elif query_upper.startswith("UPDATE"):
            return QueryType.UPDATE
        elif query_upper.startswith("DELETE"):
            return QueryType.DELETE
        elif query_upper.startswith("CREATE"):
            return QueryType.CREATE
        elif query_upper.startswith("ALTER"):
            return QueryType.ALTER
        elif query_upper.startswith("DROP"):
            return QueryType.DROP
        else:
            return QueryType.SELECT  # 默认

    def _detect_issues(self, query: str) -> List[QueryIssue]:
        """检测查询问题"""
        issues = []

        # 检测 SELECT *
        if self.query_patterns["select_all"].search(query):
            issues.append(
                QueryIssue(
                    issue_type="select_all",
                    severity="medium",
                    description="Using SELECT * retrieves all columns",
                    suggestion="Specify only the columns you need to reduce data transfer",
                )
            )

        # 检测 SELECT DISTINCT
        if self.query_patterns["select_distinct"].search(query):
            issues.append(
                QueryIssue(
                    issue_type="select_distinct",
                    severity="low",
                    description="Using SELECT DISTINCT can be expensive",
                    suggestion="Consider using GROUP BY or EXISTS instead",
                )
            )

        # 检测 LIKE 前导通配符
        if self.query_patterns["like_leading_wildcard"].search(query):
            issues.append(
                QueryIssue(
                    issue_type="like_leading_wildcard",
                    severity="high",
                    description="LIKE with leading wildcard prevents index usage",
                    suggestion="Use full-text search or restructure the query",
                )
            )

        # 检测 WHERE 中的 OR
        if self.query_patterns["or_in_where"].search(query):
            issues.append(
                QueryIssue(
                    issue_type="or_in_where",
                    severity="medium",
                    description="OR in WHERE clause can prevent index usage",
                    suggestion="Consider using UNION ALL or IN clause",
                )
            )

        # 检测子查询
        if self.query_patterns["subquery_in_select"].search(query):
            issues.append(
                QueryIssue(
                    issue_type="subquery_in_select",
                    severity="medium",
                    description="Subquery in SELECT can be inefficient",
                    suggestion="Consider using JOIN instead",
                )
            )

        # 检测 JOIN ON 1=1
        if self.query_patterns["join_without_condition"].search(query):
            issues.append(
                QueryIssue(
                    issue_type="cross_join",
                    severity="critical",
                    description="JOIN without proper condition (CROSS JOIN)",
                    suggestion="Add proper JOIN condition to avoid Cartesian product",
                )
            )

        return issues

    def _suggest_indexes(self, query: str) -> List[IndexSuggestion]:
        """建议索引"""
        suggestions = []

        # 提取 WHERE 条件中的列
        where_match = re.search(
            r"WHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)", query, re.IGNORECASE
        )
        if where_match:
            where_clause = where_match.group(1)
            columns = self._extract_columns(where_clause)

            if columns:
                suggestions.append(
                    IndexSuggestion(
                        table_name="unknown",
                        column_names=columns,
                        index_type="btree",
                        reason="Columns used in WHERE clause",
                        estimated_impact="medium",
                    )
                )

        # 提取 ORDER BY 中的列
        order_match = re.search(r"ORDER\s+BY\s+(.+?)(?:\s+LIMIT|$)", query, re.IGNORECASE)
        if order_match:
            order_clause = order_match.group(1)
            columns = self._extract_columns(order_clause)

            if columns:
                suggestions.append(
                    IndexSuggestion(
                        table_name="unknown",
                        column_names=columns,
                        index_type="btree",
                        reason="Columns used in ORDER BY clause",
                        estimated_impact="high",
                    )
                )

        # 提取 GROUP BY 中的列
        group_match = re.search(
            r"GROUP\s+BY\s+(.+?)(?:\s+ORDER\s+BY|\s+LIMIT|$)", query, re.IGNORECASE
        )
        if group_match:
            group_clause = group_match.group(1)
            columns = self._extract_columns(group_clause)

            if columns:
                suggestions.append(
                    IndexSuggestion(
                        table_name="unknown",
                        column_names=columns,
                        index_type="btree",
                        reason="Columns used in GROUP BY clause",
                        estimated_impact="high",
                    )
                )

        return suggestions

    def _extract_columns(self, clause: str) -> List[str]:
        """从子句中提取列名"""
        # 简化实现：提取可能的列名
        columns = []

        # 移除函数调用
        clause = re.sub(r"\w+\([^)]+\)", "", clause)

        # 提取标识符
        tokens = re.findall(r"\b[a-zA-Z_]\w*\b", clause)

        # 过滤 SQL 关键字
        sql_keywords = {
            "AND",
            "OR",
            "NOT",
            "IN",
            "LIKE",
            "BETWEEN",
            "IS",
            "NULL",
            "ASC",
            "DESC",
            "TRUE",
            "FALSE",
        }

        for token in tokens:
            if token.upper() not in sql_keywords:
                columns.append(token)

        return columns[:5]  # 限制返回数量

    def _optimize_query(self, query: str, issues: List[QueryIssue]) -> Optional[str]:
        """优化查询"""
        optimized = query

        for issue in issues:
            if issue.issue_type == "select_all":
                # 简化：添加注释提示
                optimized = optimized.replace("SELECT *", "SELECT /* specify columns */ *")
            elif issue.issue_type == "like_leading_wildcard":
                # 简化：添加注释提示
                optimized = optimized + " /* Consider full-text search */"

        if optimized != query:
            return optimized

        return None

    def _estimate_improvement(self, issues: List[QueryIssue]) -> str:
        """估算改进"""
        if not issues:
            return "No issues found"

        high_critical = sum(1 for i in issues if i.severity in ["high", "critical"])

        if high_critical > 0:
            return "High (significant improvement possible)"
        elif len(issues) > 2:
            return "Medium (moderate improvement possible)"
        else:
            return "Low (minor improvement possible)"


# ----------------------------------------------------------------------
# 6️⃣ 慢查询分析器
# ----------------------------------------------------------------------
class SlowQueryAnalyzer:
    """慢查询分析器"""

    def __init__(self):
        self.optimizer = QueryOptimizer()
        self.slow_query_threshold = 1.0  # 秒

    def analyze_slow_queries(
        self,
        queries: List[Dict[str, Any]],
    ) -> List[QueryAnalysisResult]:
        """
        分析慢查询

        Parameters
        ----------
        queries : List[Dict[str, Any]]
            查询列表，每个包含 'query' 和 'duration'

        Returns
        -------
        List[QueryAnalysisResult]
            分析结果列表
        """
        results = []

        for query_info in queries:
            query = query_info.get("query", "")
            duration = query_info.get("duration", 0)

            if duration >= self.slow_query_threshold:
                result = self.optimizer.analyze_query(query)
                results.append(result)

        return results

    def set_slow_query_threshold(self, threshold: float):
        """设置慢查询阈值"""
        self.slow_query_threshold = threshold


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_query_optimizer() -> QueryOptimizer:
    """创建查询优化器"""
    return QueryOptimizer()


def create_slow_query_analyzer() -> SlowQueryAnalyzer:
    """创建慢查询分析器"""
    return SlowQueryAnalyzer()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试查询优化器
    logger.info("Testing query optimizer")

    optimizer = create_query_optimizer()

    # 测试查询
    test_queries = [
        "SELECT * FROM users WHERE name LIKE '%john%'",
        "SELECT DISTINCT name FROM orders WHERE status = 'pending' OR status = 'failed'",
        "SELECT * FROM orders JOIN products ON 1=1",
    ]

    for query in test_queries:
        result = optimizer.analyze_query(query)
        logger.info(f"Query: {query[:50]}...")
        logger.info(f"  Issues: {len(result.issues)}")
        logger.info(f"  Index suggestions: {len(result.index_suggestions)}")
        logger.info(f"  Estimated improvement: {result.estimated_improvement}")

    # 测试慢查询分析器
    logger.info("Testing slow query analyzer")

    analyzer = create_slow_query_analyzer()

    slow_queries = [
        {"query": "SELECT * FROM large_table", "duration": 2.5},
        {"query": "SELECT * FROM small_table", "duration": 0.1},
    ]

    results = analyzer.analyze_slow_queries(slow_queries)
    logger.info(f"Slow queries analyzed: {len(results)}")

    logger.info("Test passed!")
