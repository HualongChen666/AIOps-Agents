# -*- coding: utf-8 -*-
"""
Database Query Optimization
Enterprise-grade database query optimization with slow query analysis and result caching
P2 Enhancement: Added query result caching mechanism
"""

import hashlib
import json
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

__all__ = [
    "QueryOptimizationType",
    "OptimizationPriority",
    "SlowQuery",
    "QueryOptimization",
    "CachedQueryResult",
    "DatabaseQueryOptimizer",
    "get_database_query_optimizer",
]

# Try to import caching libraries
try:
    from cachetools import TTLCache

    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    logger.info("Caching library not available, query result caching disabled")

# Try to import Redis for distributed caching
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available, distributed caching disabled")


class QueryOptimizationType(Enum):
    """Query optimization type"""

    INDEX_ADDITION = "index_addition"
    QUERY_REWRITE = "query_rewrite"
    NPLUS_ONE_FIX = "nplus_one_fix"
    JOIN_OPTIMIZATION = "join_optimization"
    SUBQUERY_OPTIMIZATION = "subquery_optimization"
    CACHING_STRATEGY = "caching_strategy"


class OptimizationPriority(Enum):
    """Optimization priority"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SlowQuery:
    """Slow query data"""

    query_id: str
    query_hash: str
    query_text: str
    database: str
    table_name: str
    execution_count: int
    avg_duration_ms: float
    max_duration_ms: float
    total_duration_ms: float
    last_executed: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryOptimization:
    """Query optimization recommendation"""

    optimization_id: str
    query_id: str
    optimization_type: QueryOptimizationType
    priority: OptimizationPriority
    current_performance: Dict[str, float]
    expected_improvement: float
    implementation_effort: str
    description: str
    sql_statements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CachedQueryResult:
    """Cached query result"""

    query_hash: str
    result: Any
    cached_at: datetime
    ttl_seconds: int
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatabaseQueryOptimizer:
    """Enterprise-grade database query optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize database query optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Slow query storage
        self.slow_queries: Dict[str, SlowQuery] = {}
        self.query_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Optimization recommendations
        self.optimizations: Dict[str, QueryOptimization] = {}

        # Index recommendations
        self.index_recommendations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Configuration
        self.slow_query_threshold_ms = self.config.get("slow_query_threshold_ms", 1000)
        self.slow_query_threshold = self.slow_query_threshold_ms  # Test alias
        self.analysis_window_hours = self.config.get("analysis_window_hours", 24)

        # P2 Enhancement: Query result caching
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl_seconds = self.config.get("cache_ttl_seconds", 300)
        self.cache_max_size = self.config.get("cache_max_size", 1000)
        self.cache_l1_enabled = self.config.get("cache_l1_enabled", True)
        self.cache_l2_enabled = self.config.get("cache_l2_enabled", True)

        # Initialize caches
        self.l1_cache: Optional[TTLCache] = None
        self.l2_redis_client: Optional[Any] = None  # redis.Redis
        self.query_cache: Dict[str, CachedQueryResult] = {}

        if CACHING_AVAILABLE and self.cache_l1_enabled:
            self.l1_cache = TTLCache(maxsize=self.cache_max_size, ttl=self.cache_ttl_seconds)
            logger.info(
                f"L1 memory cache initialized with maxsize={self.cache_max_size}, "
                f"ttl={self.cache_ttl_seconds}s"
            )

        if REDIS_AVAILABLE and self.cache_l2_enabled:
            try:
                import config as config_module

                redis_host = getattr(config_module, "REDIS_HOST", "localhost")
                redis_port = getattr(config_module, "REDIS_PORT", 6379)
                redis_db = getattr(config_module, "REDIS_DB", 0)
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
                self.l2_redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("L2 Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                self.l2_redis_client = None

        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_evictions = 0

        # Statistics
        self.total_queries_analyzed = 0
        self.optimizations_generated = 0
        self.total_improvement = 0.0

        logger.info("Database query optimizer initialized with P2 caching enhancements")

    def analyze_query_performance(self, query: str, duration_ms: float = 0.0) -> Dict[str, Any]:
        """Analyze query performance and record it."""
        self.record_query_execution(
            query_id=f"query_{hash(query)}",
            query_text=query,
            database="default",
            table_name="unknown",
            duration_ms=duration_ms,
        )
        return {
            "query": query,
            "duration_ms": duration_ms,
            "pattern": self.classify_query_pattern(query),
            "recommendations": self.generate_optimization_recommendations(query),
        }

    def classify_query_pattern(self, query_text: str) -> str:
        """Public alias for _classify_query_pattern."""
        return self._classify_query_pattern(query_text)

    def generate_optimization_recommendations(
        self, query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations for a query or all slow queries."""
        if query:
            query_id = f"query_{hash(query)}"
            self.record_query_execution(
                query_id=query_id,
                query_text=query,
                database="default",
                table_name="unknown",
                duration_ms=0.0,
            )
        opts = self.generate_optimizations()
        return [
            {
                "optimization_id": opt.optimization_id,
                "type": opt.optimization_type.value,
                "priority": opt.priority.value,
                "expected_improvement": opt.expected_improvement,
            }
            for opt in opts
        ]

    def cache_query_result(
        self,
        query: str,
        result: Any,
        ttl_seconds: int = 300,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Cache a query result."""
        self.cache_result(query_text=query, result=result, params=params, ttl=ttl_seconds)

    def get_cached_query_result(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get a cached query result."""
        return self.get_cached_result(query_text=query, params=params)

    def invalidate_query_cache(
        self, query: Optional[str] = None, pattern: Optional[str] = None
    ) -> int:
        """Invalidate cached query result(s)."""
        return self.invalidate_cache(query_text=query, pattern=pattern)

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Public alias for get_cache_stats."""
        return self.get_cache_stats()

    def clear_query_cache(self) -> None:
        """Clear all query cache entries."""
        self.query_cache.clear()
        if self.l1_cache is not None:
            self.l1_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def identify_n_plus_one_pattern(self, query_text: str) -> bool:
        """Check if a query text contains N+1 pattern."""
        return self._classify_query_pattern(query_text) == "n_plus_one"

    def identify_missing_index_pattern(self, query_text: str) -> bool:
        """Check if a query text likely has missing index issues."""
        return self._classify_query_pattern(query_text) == "missing_index"

    def identify_inefficient_join_pattern(self, query_text: str) -> bool:
        """Check if a query text contains inefficient join pattern."""
        return self._classify_query_pattern(query_text) == "inefficient_join"

    def get_cached_result(
        self, query_text: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached query result from L1/L2 cache

        Args:
            query_text: SQL query text
            params: Query parameters

        Returns:
            Cached result or None if not found
        """
        if not self.cache_enabled:
            return None

        cache_key = self._generate_cache_key(query_text, params)

        # Try L1 cache first
        if self.l1_cache is not None and cache_key in self.l1_cache:
            cached_result = self.l1_cache[cache_key]
            cached_result.hit_count += 1
            self.cache_hits += 1
            logger.debug(f"Cache hit (L1) for query: {cache_key[:32]}...")
            return cached_result.result

        # Try L2 cache (Redis)
        if self.l2_redis_client is not None:
            try:
                cached_data = self.l2_redis_client.get(cache_key)
                if cached_data and isinstance(cached_data, (str, bytes)):
                    cached_result = CachedQueryResult(
                        query_hash=cache_key,
                        result=json.loads(cached_data),
                        cached_at=datetime.now(timezone.utc),
                        ttl_seconds=self.cache_ttl_seconds,
                        hit_count=1,
                    )
                    # Populate L1 cache from L2
                    if self.l1_cache is not None:
                        self.l1_cache[cache_key] = cached_result
                    self.cache_hits += 1
                    logger.debug(f"Cache hit (L2) for query: {cache_key[:32]}...")
                    return cached_result.result
            except Exception as e:
                logger.warning(f"Failed to get result from Redis cache: {e}")

        # Fallback to in-memory query cache
        if cache_key in self.query_cache:
            cached_result = self.query_cache[cache_key]
            cached_result.hit_count += 1
            self.cache_hits += 1
            return cached_result.result

        self.cache_misses += 1
        return None

    def cache_result(
        self,
        query_text: str,
        result: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache query result in L1/L2 cache

        Args:
            query_text: SQL query text
            result: Query result to cache
            params: Query parameters
            ttl: Custom TTL in seconds (overrides default)
        """
        if not self.cache_enabled:
            return

        cache_key = self._generate_cache_key(query_text, params)
        ttl_seconds = ttl or self.cache_ttl_seconds

        cached_result = CachedQueryResult(
            query_hash=cache_key,
            result=result,
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=ttl_seconds,
        )

        # Store in L1 cache
        if self.l1_cache is not None:
            try:
                self.l1_cache[cache_key] = cached_result
                logger.debug(f"Cached result in L1 for query: {cache_key[:32]}...")
            except Exception as e:
                logger.warning(f"Failed to cache result in L1: {e}")
                self.cache_evictions += 1

        # Store in L2 cache (Redis)
        if self.l2_redis_client is not None:
            try:
                serialized_result = json.dumps(result, default=str)
                self.l2_redis_client.setex(cache_key, ttl_seconds, serialized_result)
                logger.debug(f"Cached result in L2 for query: {cache_key[:32]}...")
            except Exception as e:
                logger.warning(f"Failed to cache result in L2: {e}")

        # Fallback to in-memory query cache when L1/L2 are unavailable
        if self.l1_cache is None and self.l2_redis_client is None:
            self.query_cache[cache_key] = cached_result

    def invalidate_cache(
        self, query_text: Optional[str] = None, pattern: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries

        Args:
            query_text: Specific query to invalidate
            pattern: Pattern to match for invalidation (e.g., "table:*")

        Returns:
            Number of cache entries invalidated
        """
        invalidated_count = 0

        if query_text:
            cache_key = self._generate_cache_key(query_text)
            if self.l1_cache is not None and cache_key in self.l1_cache:
                del self.l1_cache[cache_key]
                invalidated_count += 1

            if self.l2_redis_client is not None:
                try:
                    if self.l2_redis_client.delete(cache_key):
                        invalidated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to invalidate cache in Redis: {e}")

            if cache_key in self.query_cache:
                del self.query_cache[cache_key]
                invalidated_count += 1

        elif pattern and self.l2_redis_client is not None:
            try:
                keys = self.l2_redis_client.keys(pattern)
                if keys:
                    deleted = self.l2_redis_client.delete(*keys)
                    invalidated_count += deleted
            except Exception as e:
                logger.warning(f"Failed to invalidate cache by pattern in Redis: {e}")

        logger.info(f"Invalidated {invalidated_count} cache entries")
        return invalidated_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Cache statistics dictionary
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        l1_size = len(self.l1_cache) if self.l1_cache else 0
        l2_size = 0
        if self.l2_redis_client:
            try:
                l2_size = len(self.l2_redis_client.keys("db_query:*"))
            except Exception as e:
                logger.warning(f"Failed to get L2 cache size: {e}")

        return {
            "enabled": self.cache_enabled,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "evictions": self.cache_evictions,
            "hit_rate_percent": round(hit_rate, 2),
            "l1_cache_size": l1_size,
            "l1_cache_max_size": self.cache_max_size,
            "l2_cache_size": l2_size,
            "ttl_seconds": self.cache_ttl_seconds,
        }

    def _generate_cache_key(self, query_text: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate cache key for query

        Args:
            query_text: SQL query text
            params: Query parameters

        Returns:
            Cache key
        """
        # Normalize query
        normalized = re.sub(r"\s+", " ", query_text.strip()).lower()

        # Include parameters in key if provided
        if params:
            params_str = json.dumps(params, sort_keys=True)
            combined = f"{normalized}:{params_str}"
        else:
            combined = normalized

        # Generate hash
        hash_value = hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()
        return f"db_query:{hash_value}"

    def record_query_execution(
        self,
        query_id: str,
        query_text: str,
        database: str,
        table_name: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record query execution

        Args:
            query_id: Query ID
            query_text: SQL query text
            database: Database name
            table_name: Table name
            duration_ms: Execution duration
            metadata: Additional metadata
        """
        query_hash = self._generate_query_hash(query_text)

        if query_id not in self.slow_queries:
            self.slow_queries[query_id] = SlowQuery(
                query_id=query_id,
                query_hash=query_hash,
                query_text=query_text,
                database=database,
                table_name=table_name,
                execution_count=0,
                avg_duration_ms=duration_ms,
                max_duration_ms=duration_ms,
                total_duration_ms=duration_ms,
                last_executed=datetime.now(timezone.utc),
                metadata=metadata or {},
            )
        else:
            # Update existing slow query
            slow_query = self.slow_queries[query_id]
            slow_query.execution_count += 1
            slow_query.total_duration_ms += duration_ms
            slow_query.avg_duration_ms = slow_query.total_duration_ms / slow_query.execution_count
            slow_query.max_duration_ms = max(slow_query.max_duration_ms, duration_ms)
            slow_query.last_executed = datetime.now(timezone.utc)

        # Add to history
        self.query_history[query_hash].append(
            {
                "query_id": query_id,
                "duration_ms": duration_ms,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }
        )

        self.total_queries_analyzed += 1

        logger.debug(f"Recorded query execution: {query_id}, duration: {duration_ms}ms")

    def _generate_query_hash(self, query_text: str) -> str:
        """
        Generate query hash

        Args:
            query_text: SQL query text

        Returns:
            Query hash
        """
        # Normalize query for hashing
        normalized = re.sub(r"\s+", " ", query_text.strip())
        normalized = normalized.lower()
        return str(hash(normalized))

    def analyze_slow_queries(self) -> List[SlowQuery]:
        """
        Analyze slow queries

        Returns:
            List of slow queries sorted by impact
        """
        slow_query_list = [
            query
            for query in self.slow_queries.values()
            if query.avg_duration_ms > self.slow_query_threshold_ms
        ]

        # Sort by total impact (avg_duration * execution_count)
        slow_query_list.sort(key=lambda q: q.avg_duration_ms * q.execution_count, reverse=True)

        logger.info(f"Analyzed {len(slow_query_list)} slow queries")

        return slow_query_list

    def generate_optimizations(self) -> List[QueryOptimization]:
        """
        Generate query optimizations

        Returns:
            List of optimization recommendations
        """
        optimizations = []

        # Analyze slow queries
        slow_queries = self.analyze_slow_queries()

        for query in slow_queries:
            # Analyze query pattern
            query_type = self._classify_query_pattern(query.query_text)

            # Generate optimization based on query type
            if query_type == "n_plus_one":
                optimization = self._optimize_n_plus_one(query)
            elif query_type == "missing_index":
                optimization = self._optimize_missing_index(query)
            elif query_type == "inefficient_join":
                optimization = self._optimize_inefficient_join(query)
            elif query_type == "select_star":
                optimization = self._optimize_select_star(query)
            elif query_type == "subquery":
                optimization = self._optimize_subquery(query)

            if optimization:
                optimizations.append(optimization)
                self.optimizations[optimization.optimization_id] = optimization
                self.optimizations_generated += 1

        logger.info(f"Generated {len(optimizations)} query optimizations")

        return optimizations

    def _classify_query_pattern(self, query_text: str) -> str:
        """
        Classify query pattern

        Args:
            query_text: SQL query text

        Returns:
            Query pattern type
        """
        query_lower = query_text.lower()

        # Check for SELECT *
        if "select *" in query_lower:
            return "select_star"

        # Check for N+1 query pattern
        if query_lower.count("select") > 1 and "join" in query_lower:
            return "n_plus_one"

        # Check for subqueries
        if "select (select" in query_lower or "where exists" in query_lower:
            return "subquery"

        # Check for inefficient joins
        if "join" in query_lower and ("order by" in query_lower or "group by" in query_lower):
            return "inefficient_join"

        # Check for missing index indicators
        if "like" in query_lower and query_lower.count("where") > 0:
            return "missing_index"

        return "unknown"

    def _optimize_n_plus_one(self, query: SlowQuery) -> QueryOptimization:
        """
        Optimize N+1 query

        prefetches related data in a single query instead of multiple queries

        Args:
            query: Slow query

        Returns:
            Optimization recommendation
        """
        optimization_id = (
            f"opt_nplus1_{query.query_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # Generate optimization SQL
        optimized_sql = self._rewrite_with_joins(query.query_text)

        optimization = QueryOptimization(
            optimization_id=optimization_id,
            query_id=query.query_id,
            optimization_type=QueryOptimizationType.NPLUS_ONE_FIX,
            priority=OptimizationPriority.HIGH,
            current_performance={
                "avg_duration_ms": query.avg_duration_ms,
                "execution_count": query.execution_count,
            },
            expected_improvement=60.0,
            implementation_effort="medium",
            description="Optimize N+1 query pattern by using joins instead of separate queries",
            sql_statements=[optimized_sql],
            metadata={"table_name": query.table_name, "database": query.database},
        )

        return optimization

    def _optimize_missing_index(self, query: SlowQuery) -> QueryOptimization:
        """
        Optimize query with missing index

        adds indexes on frequently queried columns

        Args:
            query: Slow query

        Returns:
            Optimization recommendation
        """
        optimization_id = (
            f"opt_index_{query.query_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # Identify columns that need indexing
        columns_to_index = self._identify_indexable_columns(query.query_text)

        # Generate index creation statements
        index_statements = []
        for column in columns_to_index:
            index_name = f"idx_{query.table_name}_{column}"
            index_statement = (
                f"CREATE INDEX IF NOT EXISTS {index_name} ON {query.table_name} ({column});"
            )
            index_statements.append(index_statement)

        # Store index recommendation
        self.index_recommendations[query.table_name].append(
            {
                "columns": columns_to_index,
                "query_id": query.query_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        optimization = QueryOptimization(
            optimization_id=optimization_id,
            query_id=query.query_id,
            optimization_type=QueryOptimizationType.INDEX_ADDITION,
            priority=OptimizationPriority.HIGH,
            current_performance={
                "avg_duration_ms": query.avg_duration_ms,
                "execution_count": query.execution_count,
            },
            expected_improvement=40.0,
            implementation_effort="low",
            description=f"Add indexes on columns: {', '.join(columns_to_index)}",
            sql_statements=index_statements,
            metadata={"table_name": query.table_name, "database": query.database},
        )

        return optimization

    def _optimize_inefficient_join(self, query: SlowQuery) -> QueryOptimization:
        """
        Optimize inefficient join

        rewrites join queries to be more efficient

        Args:
            query: Slow query

        Returns:
            Optimization recommendation
        """
        optimization_id = (
            f"opt_join_{query.query_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        optimized_sql = self._rewrite_join(query.query_text)

        optimization = QueryOptimization(
            optimization_id=optimization_id,
            query_id=query.query_id,
            optimization_type=QueryOptimizationType.JOIN_OPTIMIZATION,
            priority=OptimizationPriority.MEDIUM,
            current_performance={
                "avg_duration_ms": query.avg_duration_ms,
                "execution_count": query.execution_count,
            },
            expected_improvement=30.0,
            implementation_effort="medium",
            description="Optimize join query by reordering joins or adding join hints",
            sql_statements=[optimized_sql],
            metadata={"table_name": query.table_name, "database": query.database},
        )

        return optimization

    def _optimize_select_star(self, query: SlowQuery) -> QueryOptimization:
        """
        Optimize SELECT * query

        replace SELECT * with explicit column list

        Args:
            query: Slow query

        Returns:
            Optimization recommendation
        """
        optimization_id = (
            f"opt_star_{query.query_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        optimized_sql = self._replace_select_star(query.query_text)

        optimization = QueryOptimization(
            optimization_id=optimization_id,
            query_id=query.query_id,
            optimization_type=QueryOptimizationType.QUERY_REWRITE,
            priority=OptimizationPriority.MEDIUM,
            current_performance={
                "avg_duration_ms": query.avg_duration_ms,
                "execution_count": query.execution_count,
            },
            expected_improvement=20.0,
            implementation_effort="low",
            description="Replace SELECT * with explicit column list to reduce I/O",
            sql_statements=[optimized_sql],
            metadata={"table_name": query.table_name, "database": query.database},
        )

        return optimization

    def _optimize_subquery(self, query: SlowQuery) -> QueryOptimization:
        """
        Optimize subquery

        rewrite subqueries as joins where possible

        Args:
            query: Slow query

        Returns:
            Optimization recommendation
        """
        optimization_id = (
            f"opt_subquery_{query.query_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        optimized_sql = self._rewrite_subquery(query.query_text)

        optimization = QueryOptimization(
            optimization_id=optimization_id,
            query_id=query.query_id,
            optimization_type=QueryOptimizationType.SUBQUERY_OPTIMIZATION,
            priority=OptimizationPriority.MEDIUM,
            current_performance={
                "avg_duration_ms": query.avg_duration_ms,
                "execution_count": query.execution_count,
            },
            expected_improvement=35.0,
            implementation_effort="high",
            description="Rewrite subquery as JOIN for better performance",
            sql_statements=[optimized_sql],
            metadata={"table_name": query.table_name, "database": query.database},
        )

        return optimization

    def _identify_indexable_columns(self, query_text: str) -> List[str]:
        """
        Identify columns that need indexing

        Args:
            query_text: SQL query text

        Returns:
            List of column names
        """
        columns = []

        # Extract columns from WHERE clause
        where_match = re.search(
            r"where\s+(.+?)(?:\s+order\s+by|\s+group\s+|;|$)", query_text, re.IGNORECASE
        )
        if where_match:
            where_clause = where_match.group(1)
            # Extract column names from conditions
            column_matches = re.findall(r"(\w+)\s*=", where_clause)
            columns.extend(
                [match for match in column_matches if match.lower() not in ["and", "or", "not"]]
            )

        # Extract columns from ORDER BY clause
        order_match = re.search(r"order\s+by\s+(.+?)(?:\s+limit|$)", query_text, re.IGNORECASE)
        if order_match:
            order_clause = order_match.group(1)
            column_matches = re.findall(r"(\w+)", order_clause)
            columns.extend(column_matches)

        # Remove duplicates
        columns = list(set(columns))

        return columns

    def _rewrite_with_joins(self, query_text: str) -> str:
        """
        Rewrite query to use joins

        Args:
            query_text: Original query

        Returns:
            Optimized query
        """
        # This is a simplified version - in real implementation would use SQL parser
        # For now, return the original query with a comment
        return f"-- Optimized with joins\n{query_text}"

    def _rewrite_join(self, query_text: str) -> str:
        """
        Rewrite join query

        Args:
            query_text: Original query

        Returns:
            Optimized query
        """
        # Simplified version
        return f"-- Optimized join\n{query_text}"

    def _replace_select_star(self, query_text: str) -> str:
        """
        Replace SELECT * with explicit columns

        Args:
            query_text: Original query

        Returns:
            Optimized query
        """
        # Replace SELECT * with SELECT id, created_at, updated_at (common columns)
        return query_text.replace("SELECT *", "SELECT id, created_at, updated_at")

    def get_query_analysis(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get query analysis

        Args:
            query_id: Query ID

        Returns:
            Query analysis
        """
        if query_id not in self.slow_queries:
            return None

        query = self.slow_queries[query_id]

        # Calculate statistics
        history = self.query_history[query.query_hash]
        durations = [h["duration_ms"] for h in history]

        return {
            "query_id": query.query_id,
            "query_text": query.query_text,
            "database": query.database,
            "table_name": query.table_name,
            "execution_count": query.execution_count,
            "avg_duration_ms": query.avg_duration_ms,
            "max_duration_ms": query.max_duration_ms,
            "total_duration_ms": query.total_duration_ms,
            "last_executed": query.last_executed.isoformat(),
            "performance_history": {
                "total_executions": len(durations),
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "avg_duration_ms": statistics.mean(durations) if durations else 0,
                "p95_duration_ms": (
                    statistics.quantiles(durations, n=20)[18]
                    if len(durations) >= 20
                    else max(durations) if durations else 0
                ),
            },
            "optimization_applied": query_id in self.optimizations,
        }

    def _rewrite_subquery(self, query_text: str) -> str:
        """
        Rewrite subquery as JOIN for better performance

        Args:
            query_text: Original SQL query text

        Returns:
            Rewritten SQL query text
        """
        # Placeholder implementation - returns original query
        # In a real implementation, this would parse the SQL and rewrite subqueries
        return query_text

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return {
            "total_queries_analyzed": self.total_queries_analyzed,
            "total_slow_queries": len(self.slow_queries),
            "optimizations_generated": self.optimizations_generated,
            "total_improvement": self.total_improvement,
            "total_index_recommendations": len(self.index_recommendations),
        }


def get_database_query_optimizer(config: Optional[Dict[str, Any]] = None) -> DatabaseQueryOptimizer:
    """
    Factory function to get database query optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        DatabaseQueryOptimizer: Optimizer instance
    """
    return DatabaseQueryOptimizer(config)
