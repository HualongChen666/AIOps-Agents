# -*- coding: utf-8 -*-
"""
Database Connection Optimization
Enterprise-grade database connection pool optimization and monitoring
P2 Enhancement: Added read-write separation and transaction optimization
"""

import statistics
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

__all__ = [
    "ConnectionStatus",
    "PoolStrategy",
    "ReadWriteStrategy",
    "TransactionIsolationLevel",
    "ConnectionMetrics",
    "PoolMetrics",
    "ReplicaConfig",
    "TransactionMetrics",
    "DatabaseConnectionOptimizer",
    "get_database_connection_optimizer",
]


class ConnectionStatus(Enum):
    """Connection status"""

    IDLE = "idle"
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    CLOSED = "closed"
    ERROR = "error"


class PoolStrategy(Enum):
    """Pool strategy"""

    FIXED = "fixed"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"
    # Test compatibility aliases
    SIMPLE = "simple"
    PRE_PING = "pre_ping"
    RECYCLE = "recycle"


# P2 Enhancement: Read-Write Separation Strategy
class ReadWriteStrategy(Enum):
    """Read-write separation strategy"""

    NONE = "none"  # No separation
    PRIMARY_REPLICA = "primary_replica"  # Primary for writes, replicas for reads
    PRIMARY_ONLY = "primary_only"  # Primary only (test compatibility)
    ROUND_ROBIN = "round_robin"  # Round-robin among replicas
    WEIGHTED = "weighted"  # Weighted selection based on load
    GEOGRAPHICAL = "geographical"  # Geographical proximity based


# P2 Enhancement: Transaction Isolation Level
class TransactionIsolationLevel(Enum):
    """Transaction isolation levels"""

    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@dataclass
class ConnectionMetrics:
    """Connection metrics"""

    connection_id: str
    created_at: datetime
    last_used: datetime
    total_queries: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    status: ConnectionStatus = ConnectionStatus.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoolMetrics:
    """Pool metrics"""

    pool_name: str
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    waiting_requests: int = 0
    total_queries: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    errors: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# P2 Enhancement: Read-Write Separation Manager
@dataclass
class ReplicaConfig:
    """Replica database configuration"""

    replica_id: str
    host: str
    port: int
    database: str
    weight: int = 1
    is_primary: bool = False
    lag_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionMetrics:
    """Transaction metrics"""

    transaction_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: float = 0.0
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED
    status: str = "active"  # active, committed, rolled_back
    queries_executed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatabaseConnectionOptimizer:
    """Enterprise-grade database connection optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize database connection optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Connection pools
        self.pools: Dict[str, Dict[str, Any]] = {}

        # Connection metrics
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}

        # Pool metrics history
        self.pool_metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Configuration
        self.default_pool_size = self.config.get(
            "default_pool_size", 20
        )  # P2: Increased from 10 to 20
        self.max_overflow = self.config.get("max_overflow", 10)
        self.pool_recycle_seconds = self.config.get("pool_recycle_seconds", 3600)
        self.pool_timeout_seconds = self.config.get("pool_timeout_seconds", 30)
        self.pool_pre_ping = self.config.get("pool_pre_ping", True)

        # P2 Enhancement: Read-Write Separation Configuration
        self.read_write_strategy = ReadWriteStrategy(
            self.config.get("read_write_strategy", "primary_replica")
        )
        self.replicas: Dict[str, ReplicaConfig] = {}
        self.replica_pools: Dict[str, str] = {}  # replica_id -> pool_name mapping
        self.primary_pool_name = self.config.get("primary_pool_name", "primary")

        # P2 Enhancement: Transaction Management
        self.active_transactions: Dict[str, TransactionMetrics] = {}
        self.transaction_history: List[TransactionMetrics] = []
        self.default_isolation_level = TransactionIsolationLevel(
            self.config.get("default_isolation_level", "read_committed")
        )
        self.transaction_timeout_seconds = self.config.get("transaction_timeout_seconds", 30)
        self.transaction_lock = threading.Lock()

        # Statistics
        self.total_connections_created = 0
        self.total_connections_closed = 0
        self.total_queries_executed = 0

        logger.info("Database connection optimizer initialized with P2 enhancements")

    def create_pool(
        self,
        pool_name: str,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
        strategy: PoolStrategy = PoolStrategy.FIXED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create connection pool

        Args:
            pool_name: Pool name
            pool_size: Pool size
            max_overflow: Max overflow connections
            strategy: Pool strategy
            metadata: Additional metadata
        """
        if pool_name in self.pools:
            logger.warning(f"Pool {pool_name} already exists")
            return

        pool_size = pool_size or self.default_pool_size
        max_overflow = max_overflow or self.max_overflow

        self.pools[pool_name] = {
            "name": pool_name,
            "size": pool_size,
            "max_overflow": max_overflow,
            "strategy": strategy,
            "connections": [],
            "waiting_queue": deque(),
            "created_at": datetime.now(timezone.utc),
            "metadata": metadata or {},
        }

        # Pre-create connections for fixed pool
        if strategy == PoolStrategy.FIXED:
            for i in range(pool_size):
                self._create_connection(pool_name)

        logger.info(
            f"Created connection pool: {pool_name} (size: {pool_size}, strategy: {strategy})"
        )

    def _create_connection(self, pool_name: str) -> str:
        """
        Create a new connection

        Args:
            pool_name: Pool name

        Returns:
            Connection ID
        """
        pool = self.pools[pool_name]
        connection_id = (
            f"{pool_name}_conn_{len(pool['connections'])}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        )

        # Create connection metrics
        metrics = ConnectionMetrics(
            connection_id=connection_id,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            status=ConnectionStatus.IDLE,
        )

        self.connection_metrics[connection_id] = metrics
        pool["connections"].append(connection_id)
        self.total_connections_created += 1

        return connection_id

    def get_connection(self, pool_name: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Get connection from pool

        Args:
            pool_name: Pool name
            timeout: Timeout in seconds

        Returns:
            Connection ID or None
        """
        if pool_name not in self.pools:
            logger.error(f"Pool {pool_name} not found")
            return None

        pool = self.pools[pool_name]
        timeout = timeout or self.pool_timeout_seconds

        # Find idle connection
        for conn_id in pool["connections"]:
            conn_id_str: str = conn_id  # Type annotation for mypy
            metrics = self.connection_metrics[conn_id_str]
            if metrics.status == ConnectionStatus.IDLE:
                metrics.status = ConnectionStatus.CHECKED_OUT
                metrics.last_used = datetime.now(timezone.utc)
                return conn_id_str

        # Check if we can create overflow connection
        active_count = sum(
            1
            for conn_id in pool["connections"]
            if self.connection_metrics[conn_id].status
            in [ConnectionStatus.ACTIVE, ConnectionStatus.CHECKED_OUT]
        )

        if active_count < pool["size"] + pool["max_overflow"]:
            new_conn_id = self._create_connection(pool_name)
            self.connection_metrics[new_conn_id].status = ConnectionStatus.CHECKED_OUT
            return new_conn_id

        # Add to waiting queue
        pool["waiting_queue"].append(datetime.now(timezone.utc))

        logger.warning(f"No available connections in pool {pool_name}, added to waiting queue")

        return None

    def release_connection(
        self, pool_name: str, connection_id: str, query_duration_ms: Optional[float] = None
    ) -> None:
        """
        Release connection back to pool

        Args:
            pool_name: Pool name
            connection_id: Connection ID
            query_duration_ms: Query duration in milliseconds
        """
        if pool_name not in self.pools:
            logger.error(f"Pool {pool_name} not found")
            return

        if connection_id not in self.connection_metrics:
            logger.error(f"Connection {connection_id} not found")
            return

        metrics = self.connection_metrics[connection_id]
        metrics.status = ConnectionStatus.IDLE
        metrics.last_used = datetime.now(timezone.utc)

        if query_duration_ms:
            metrics.total_queries += 1
            metrics.total_duration_ms += query_duration_ms
            metrics.avg_duration_ms = metrics.total_duration_ms / metrics.total_queries
            self.total_queries_executed += 1

        # Process waiting queue
        if pool_name in self.pools:
            pool = self.pools[pool_name]
            if pool["waiting_queue"]:
                pool["waiting_queue"].popleft()

    def close_connection(self, pool_name: str, connection_id: str) -> None:
        """
        Close connection

        Args:
            pool_name: Pool name
            connection_id: Connection ID
        """
        if pool_name not in self.pools:
            logger.error(f"Pool {pool_name} not found")
            return

        if connection_id not in self.connection_metrics:
            logger.error(f"Connection {connection_id} not found")
            return

        pool = self.pools[pool_name]

        if connection_id in pool["connections"]:
            pool["connections"].remove(connection_id)

        del self.connection_metrics[connection_id]
        self.total_connections_closed += 1

        logger.debug(f"Closed connection: {connection_id}")

    def recycle_old_connections(self, pool_name: str) -> int:
        """
        Recycle old connections

        Args:
            pool_name: Pool name

        Returns:
            Number of connections recycled
        """
        if pool_name not in self.pools:
            return 0

        pool = self.pools[pool_name]
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.pool_recycle_seconds)

        recycled = 0
        for conn_id in list(pool["connections"]):
            metrics = self.connection_metrics[conn_id]
            if metrics.status == ConnectionStatus.IDLE and metrics.created_at < cutoff_time:
                self.close_connection(pool_name, conn_id)
                recycled += 1

        logger.info(f"Recycled {recycled} old connections in pool {pool_name}")

        return recycled

    def get_pool_metrics(self, pool_name: str) -> Optional[PoolMetrics]:
        """
        Get pool metrics

        Args:
            pool_name: Pool name

        Returns:
            Pool metrics or None
        """
        if pool_name not in self.pools:
            return None

        pool = self.pools[pool_name]

        # Calculate metrics
        active_count = 0
        idle_count = 0
        total_queries = 0
        total_duration = 0.0
        durations = []

        for conn_id in pool["connections"]:
            metrics = self.connection_metrics[conn_id]
            if metrics.status in [ConnectionStatus.ACTIVE, ConnectionStatus.CHECKED_OUT]:
                active_count += 1
            else:
                idle_count += 1

            total_queries += metrics.total_queries
            total_duration += metrics.total_duration_ms
            durations.append(metrics.avg_duration_ms)

        pool_metrics = PoolMetrics(
            pool_name=pool_name,
            total_connections=len(pool["connections"]),
            active_connections=active_count,
            idle_connections=idle_count,
            waiting_requests=len(pool["waiting_queue"]),
            total_queries=total_queries,
            total_duration_ms=total_duration,
            avg_duration_ms=statistics.mean(durations) if durations else 0.0,
            max_duration_ms=max(durations) if durations else 0.0,
            min_duration_ms=min(durations) if durations else 0.0,
        )

        # Add to history
        self.pool_metrics_history[pool_name].append(pool_metrics)

        return pool_metrics

    def optimize_pool_size(self, pool_name: str, analysis_window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze pool usage and recommend optimal size

        Args:
            pool_name: Pool name
            analysis_window_hours: Analysis window in hours

        Returns:
            Optimization recommendations
        """
        if pool_name not in self.pools:
            return {"error": "Pool not found"}

        # Get historical metrics
        history = list(self.pool_metrics_history[pool_name])

        if not history:
            return {"error": "No historical data available"}

        # Calculate statistics
        active_connections = [m.active_connections for m in history]
        max_active = max(active_connections)
        avg_active = statistics.mean(active_connections)
        p95_active = (
            statistics.quantiles(active_connections, n=20)[18]
            if len(active_connections) >= 20
            else max(active_connections)
        )

        waiting_requests = [m.waiting_requests for m in history]
        max_waiting = max(waiting_requests)
        avg_waiting = statistics.mean(waiting_requests)

        current_size = self.pools[pool_name]["size"]

        # Generate recommendations
        recommendations = []

        if max_waiting > 0:
            recommendations.append(
                {
                    "type": "increase_pool_size",
                    "reason": "High waiting queue detected",
                    "current_size": current_size,
                    "recommended_size": current_size + 5,
                    "impact": "Reduce waiting time",
                }
            )

        if p95_active < current_size * 0.5:
            recommendations.append(
                {
                    "type": "decrease_pool_size",
                    "reason": "Pool underutilized",
                    "current_size": current_size,
                    "recommended_size": int(p95_active * 1.2),
                    "impact": "Reduce resource usage",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "type": "no_change",
                    "reason": "Pool size is optimal",
                    "current_size": current_size,
                    "recommended_size": current_size,
                    "impact": "No change needed",
                }
            )

        return {
            "pool_name": pool_name,
            "current_size": current_size,
            "analysis": {
                "max_active_connections": max_active,
                "avg_active_connections": avg_active,
                "p95_active_connections": p95_active,
                "max_waiting_requests": max_waiting,
                "avg_waiting_requests": avg_waiting,
            },
            "recommendations": recommendations,
        }

    def monitor_connection_health(self, pool_name: str) -> Dict[str, Any]:
        """
        Monitor connection health

        Args:
            pool_name: Pool name

        Returns:
            Health status
        """
        if pool_name not in self.pools:
            return {"error": "Pool not found"}

        pool = self.pools[pool_name]

        # Check for stale connections
        stale_connections = []
        error_connections = []

        for conn_id in pool["connections"]:
            metrics = self.connection_metrics[conn_id]
            age = (datetime.now(timezone.utc) - metrics.created_at).total_seconds()

            if age > self.pool_recycle_seconds * 2:
                stale_connections.append(conn_id)

            if metrics.status == ConnectionStatus.ERROR:
                error_connections.append(conn_id)

        health_status: Dict[str, Any] = {
            "pool_name": pool_name,
            "status": "healthy",
            "stale_connections": len(stale_connections),
            "error_connections": len(error_connections),
            "recommendations": [],
        }

        if stale_connections:
            health_status["status"] = "warning"
            health_status["recommendations"].append("Recycle stale connections")

        if error_connections:
            health_status["status"] = "critical"
            health_status["recommendations"].append("Investigate and fix error connections")

        return health_status

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "total_pools": len(self.pools),
            "total_connections": len(self.connection_metrics),
            "total_connections_created": self.total_connections_created,
            "total_connections_closed": self.total_connections_closed,
            "total_queries_executed": self.total_queries_executed,
        }


def get_database_connection_optimizer(
    config: Optional[Dict[str, Any]] = None,
) -> DatabaseConnectionOptimizer:
    """
    Factory function to get database connection optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        DatabaseConnectionOptimizer: Optimizer instance
    """
    return DatabaseConnectionOptimizer(config)


# P2 Enhancement: Read-Write Separation Methods (added to DatabaseConnectionOptimizer)
def add_replica_config(
    self: "DatabaseConnectionOptimizer",
    replica_id: str,
    host: str,
    port: int,
    database: str,
    weight: int = 1,
    is_primary: bool = False,
    lag_ms: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add replica database configuration

    Args:
        replica_id: Replica ID
        host: Database host
        port: Database port
        database: Database name
        weight: Weight for weighted selection
        is_primary: Whether this is the primary database
        lag_ms: Replication lag in milliseconds
        metadata: Additional metadata
    """
    replica = ReplicaConfig(
        replica_id=replica_id,
        host=host,
        port=port,
        database=database,
        weight=weight,
        is_primary=is_primary,
        lag_ms=lag_ms,
        metadata=metadata or {},
    )

    self.replicas[replica_id] = replica

    # Create connection pool for this replica
    pool_name = f"replica_{replica_id}"
    self.create_pool(
        pool_name=pool_name,
        pool_size=self.default_pool_size // 2,  # Smaller pool for replicas
        metadata={"replica_id": replica_id, "is_primary": is_primary},
    )
    self.replica_pools[replica_id] = pool_name

    if is_primary:
        self.primary_pool_name = pool_name

    logger.info(f"Added replica config: {replica_id} (primary: {is_primary})")


def get_read_connection(  # noqa: E501
    self: "DatabaseConnectionOptimizer", query_type: str = "select"
) -> Optional[str]:
    """
    Get connection for read operations based on read-write strategy

    Args:
        query_type: Type of query (select, insert, update, delete)

    Returns:
        Connection ID or None
    """
    # Write operations always go to primary
    if query_type.lower() in ["insert", "update", "delete", "create", "alter", "drop"]:
        return self.get_connection(self.primary_pool_name)

    # Read operations use replica based on strategy
    if self.read_write_strategy == ReadWriteStrategy.NONE:
        return self.get_connection(self.primary_pool_name)

    if self.read_write_strategy == ReadWriteStrategy.PRIMARY_REPLICA:
        # Use primary if no replicas available
        if not self.replicas:
            return self.get_connection(self.primary_pool_name)

        # Select replica with lowest lag
        available_replicas = [
            r for r in self.replicas.values() if not r.is_primary and r.lag_ms < 1000
        ]
        if not available_replicas:
            return self.get_connection(self.primary_pool_name)

        best_replica = min(available_replicas, key=lambda r: r.lag_ms)
        pool_name = self.replica_pools[best_replica.replica_id]
        return self.get_connection(pool_name)

    if self.read_write_strategy == ReadWriteStrategy.ROUND_ROBIN:
        # Round-robin among replicas
        available_replicas = [r for r in self.replicas.values() if not r.is_primary]
        if not available_replicas:
            return self.get_connection(self.primary_pool_name)

        # Simple round-robin (in production, use proper counter)
        import time

        index = int(time.time()) % len(available_replicas)
        selected_replica = available_replicas[index]
        pool_name = self.replica_pools[selected_replica.replica_id]
        return self.get_connection(pool_name)

    if self.read_write_strategy == ReadWriteStrategy.WEIGHTED:
        # Weighted selection based on load
        available_replicas = [r for r in self.replicas.values() if not r.is_primary]
        if not available_replicas:
            return self.get_connection(self.primary_pool_name)

        # Select replica based on weight (simplified)
        total_weight = sum(r.weight for r in available_replicas)
        import secrets

        _random = secrets.SystemRandom()
        rand = _random.uniform(0, total_weight)
        cumulative = 0
        for replica in available_replicas:
            cumulative += replica.weight
            if rand <= cumulative:
                pool_name = self.replica_pools[replica.replica_id]
                return self.get_connection(pool_name)

        return self.get_connection(self.primary_pool_name)

    # Default to primary
    return self.get_connection(self.primary_pool_name)


def _begin_transaction(
    self: "DatabaseConnectionOptimizer",
    isolation_level: Optional[TransactionIsolationLevel] = None,
) -> Optional[str]:
    """
    Begin a new transaction

    Args:
        isolation_level: Transaction isolation level

    Returns:
        Transaction ID or None
    """
    transaction_id = f"txn_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

    with self.transaction_lock:
        transaction = TransactionMetrics(
            transaction_id=transaction_id,
            started_at=datetime.now(timezone.utc),
            isolation_level=isolation_level or self.default_isolation_level,
            status="active",
        )
        self.active_transactions[transaction_id] = transaction

    logger.info(f"Started transaction: {transaction_id} (isolation: {transaction.isolation_level})")
    return transaction_id


def _commit_transaction(self: "DatabaseConnectionOptimizer", transaction_id: str) -> bool:
    """
    Commit a transaction

    Args:
        transaction_id: Transaction ID

    Returns:
        Success status
    """
    with self.transaction_lock:
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction not found: {transaction_id}")
            return False

        transaction = self.active_transactions[transaction_id]
        transaction.ended_at = datetime.now(timezone.utc)
        transaction.duration_ms = (
            transaction.ended_at - transaction.started_at
        ).total_seconds() * 1000
        transaction.status = "committed"

        # Move to history
        self.transaction_history.append(transaction)
        del self.active_transactions[transaction_id]

        # Keep only last 1000 transactions in history
        if len(self.transaction_history) > 1000:
            self.transaction_history = self.transaction_history[-1000:]

    logger.info(
        f"Committed transaction: {transaction_id} (duration: {transaction.duration_ms:.2f}ms)"
    )
    return True


def _rollback_transaction(self: "DatabaseConnectionOptimizer", transaction_id: str) -> bool:
    """
    Rollback a transaction

    Args:
        transaction_id: Transaction ID

    Returns:
        Success status
    """
    with self.transaction_lock:
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction not found: {transaction_id}")
            return False

        transaction = self.active_transactions[transaction_id]
        transaction.ended_at = datetime.now(timezone.utc)
        transaction.duration_ms = (
            transaction.ended_at - transaction.started_at
        ).total_seconds() * 1000
        transaction.status = "rolled_back"

        # Move to history
        self.transaction_history.append(transaction)
        del self.active_transactions[transaction_id]

        # Keep only last 1000 transactions in history
        if len(self.transaction_history) > 1000:
            self.transaction_history = self.transaction_history[-1000:]

    logger.warning(
        f"Rolled back transaction: {transaction_id} (duration: {transaction.duration_ms:.2f}ms)"
    )
    return True


def _get_transaction_stats(self: "DatabaseConnectionOptimizer") -> Dict[str, Any]:
    """
    Get transaction statistics

    Returns:
        Transaction statistics
    """
    with self.transaction_lock:
        total_transactions = len(self.transaction_history)
        committed = sum(1 for t in self.transaction_history if t.status == "committed")
        rolled_back = sum(1 for t in self.transaction_history if t.status == "rolled_back")

        avg_duration = 0.0
        if self.transaction_history:
            durations = [t.duration_ms for t in self.transaction_history if t.duration_ms > 0]
            if durations:
                avg_duration = statistics.mean(durations)

        return {
            "active_transactions": len(self.active_transactions),
            "total_transactions": total_transactions,
            "committed": committed,
            "rolled_back": rolled_back,
            "success_rate": (committed / total_transactions * 100) if total_transactions > 0 else 0,
            "avg_duration_ms": avg_duration,
            "default_isolation_level": self.default_isolation_level.value,
        }


def monitor_replication_lag(self: "DatabaseConnectionOptimizer") -> Dict[str, Any]:
    """
    Monitor replication lag across all replicas

    Returns:
        Replication lag status
    """
    lag_status: Dict[str, Any] = {
        "replicas": [],
        "healthy": True,
        "max_lag_ms": 0,
    }

    for replica_id, replica in self.replicas.items():
        replica_status = {
            "replica_id": replica_id,
            "lag_ms": replica.lag_ms,
            "is_primary": replica.is_primary,
            "status": (
                "healthy"
                if replica.lag_ms < 1000
                else "warning" if replica.lag_ms < 5000 else "critical"
            ),
        }
        lag_status["replicas"].append(replica_status)
        lag_status["max_lag_ms"] = max(lag_status["max_lag_ms"], replica.lag_ms)

    if lag_status["max_lag_ms"] > 5000:
        lag_status["healthy"] = False

    return lag_status


def create_connection_pool(
    self: "DatabaseConnectionOptimizer",
    pool_name: str,
    url: Optional[str] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    strategy: PoolStrategy = PoolStrategy.FIXED,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a connection pool (test-compatible alias of create_pool)."""
    self.create_pool(
        pool_name=pool_name,
        pool_size=pool_size,
        max_overflow=max_overflow,
        strategy=strategy,
        metadata=metadata or {"url": url},
    )
    return self.pools[pool_name]


def get_pool_stats(self: "DatabaseConnectionOptimizer", pool_name: str) -> Dict[str, Any]:
    """Get pool statistics as a dict."""
    metrics = self.get_pool_metrics(pool_name)
    if metrics is None:
        return {"pool_name": pool_name, "total_connections": 0}
    return {
        "pool_name": metrics.pool_name,
        "total_connections": metrics.total_connections,
        "active_connections": metrics.active_connections,
        "idle_connections": metrics.idle_connections,
        "waiting_requests": metrics.waiting_requests,
        "total_queries": metrics.total_queries,
    }


def check_pool_health(self: "DatabaseConnectionOptimizer", pool_name: str) -> Dict[str, Any]:
    """Check pool health and return a dict."""
    return self.monitor_connection_health(pool_name)


def configure_read_write_splitting(
    self: "DatabaseConnectionOptimizer",
    primary: str,
    replicas: Optional[List[str]] = None,
    strategy: Optional[str] = None,
) -> None:
    """Configure read-write splitting (test-compatible)."""
    self.primary_pool_name = primary
    self.replicas.clear()
    self.replica_pools.clear()

    # Ensure primary pool exists
    if primary not in self.pools:
        self.create_pool(pool_name=primary, pool_size=self.default_pool_size)

    for idx, replica in enumerate(replicas or []):
        self.add_replica_config(  # type: ignore[attr-defined]
            replica_id=str(replica),
            host=replica,
            port=5432,
            database="replica",
            weight=1,
            is_primary=False,
        )

    if strategy:
        try:
            self.read_write_strategy = ReadWriteStrategy(strategy)
        except ValueError:
            pass


def get_write_connection(
    self: "DatabaseConnectionOptimizer", query_type: str = "write"
) -> Optional[str]:
    """Get a connection for write operations."""
    return self.get_connection(self.primary_pool_name)


def begin_transaction(
    self: "DatabaseConnectionOptimizer",
    pool_name: Optional[str] = None,
    isolation_level: Optional[TransactionIsolationLevel] = None,
) -> Optional[str]:
    """Begin a transaction (pool_name argument accepted for test compatibility)."""
    transaction_id = f"txn_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
    with self.transaction_lock:
        transaction = TransactionMetrics(
            transaction_id=transaction_id,
            started_at=datetime.now(timezone.utc),
            isolation_level=isolation_level or self.default_isolation_level,
            status="active",
        )
        self.active_transactions[transaction_id] = transaction
    logger.info(f"Started transaction: {transaction_id}")
    return transaction_id


def commit_transaction(
    self: "DatabaseConnectionOptimizer", pool_name: Optional[str] = None
) -> bool:
    """Commit a transaction (pool_name argument accepted for test compatibility)."""
    # Find the most recent active transaction if pool_name is not an id
    cls = self.__class__
    if pool_name in self.active_transactions:
        return cls._commit_transaction(self, pool_name)  # type: ignore[attr-defined, no-any-return]
    for txn_id in list(self.active_transactions.keys()):
        return cls._commit_transaction(self, txn_id)  # type: ignore[attr-defined, no-any-return]
    return False


def rollback_transaction(
    self: "DatabaseConnectionOptimizer", pool_name: Optional[str] = None
) -> bool:
    """Rollback a transaction (pool_name argument accepted for test compatibility)."""
    cls = self.__class__
    if pool_name in self.active_transactions:
        return cls._rollback_transaction(self, pool_name)  # type: ignore
    for txn_id in list(self.active_transactions.keys()):
        return cls._rollback_transaction(self, txn_id)  # type: ignore
    return False


def get_transaction_stats(
    self: "DatabaseConnectionOptimizer", pool_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get transaction statistics (pool_name argument accepted for test compatibility)."""
    with self.transaction_lock:
        total_transactions = len(self.transaction_history)
        committed = sum(1 for t in self.transaction_history if t.status == "committed")
        rolled_back = sum(1 for t in self.transaction_history if t.status == "rolled_back")
        avg_duration = 0.0
        if self.transaction_history:
            durations = [t.duration_ms for t in self.transaction_history if t.duration_ms > 0]
            if durations:
                avg_duration = statistics.mean(durations)
        return {
            "active_transactions": len(self.active_transactions),
            "total_transactions": total_transactions,
            "committed": committed,
            "rolled_back": rolled_back,
            "success_rate": (committed / total_transactions * 100) if total_transactions > 0 else 0,
            "avg_duration_ms": avg_duration,
            "default_isolation_level": self.default_isolation_level.value,
        }


# Add methods to DatabaseConnectionOptimizer class
DatabaseConnectionOptimizer.add_replica_config = add_replica_config  # type: ignore
DatabaseConnectionOptimizer.create_connection_pool = create_connection_pool  # type: ignore
DatabaseConnectionOptimizer.get_pool_stats = get_pool_stats  # type: ignore
DatabaseConnectionOptimizer.check_pool_health = check_pool_health  # type: ignore
attr_name = "configure_read_write_splitting"
setattr(DatabaseConnectionOptimizer, attr_name, configure_read_write_splitting)  # type: ignore
DatabaseConnectionOptimizer.get_read_connection = get_read_connection  # type: ignore
DatabaseConnectionOptimizer.get_write_connection = get_write_connection  # type: ignore
DatabaseConnectionOptimizer.begin_transaction = begin_transaction  # type: ignore
DatabaseConnectionOptimizer._commit_transaction = _commit_transaction  # type: ignore
DatabaseConnectionOptimizer._rollback_transaction = _rollback_transaction  # type: ignore
DatabaseConnectionOptimizer.commit_transaction = commit_transaction  # type: ignore
DatabaseConnectionOptimizer.rollback_transaction = rollback_transaction  # type: ignore
DatabaseConnectionOptimizer.get_transaction_stats = get_transaction_stats  # type: ignore
DatabaseConnectionOptimizer.monitor_replication_lag = monitor_replication_lag  # type: ignore
