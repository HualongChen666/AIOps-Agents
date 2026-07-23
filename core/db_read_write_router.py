# -*- coding: utf-8 -*-
"""
Database Read-Write Router (Phase 2)
Enhanced database read-write splitting with intelligent routing and load balancing
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class QueryType(Enum):
    """Query type classification"""

    READ = "read"
    WRITE = "write"
    TRANSACTION = "transaction"
    SCHEMA = "schema"


class ReplicaState(Enum):
    """Replica state"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"


@dataclass
class ReplicaInfo:
    """Replica information"""

    host: str
    port: int
    state: ReplicaState = ReplicaState.HEALTHY
    lag: float = 0.0  # Replication lag in seconds
    connections: int = 0
    load_score: float = 0.0
    last_check: Optional[datetime] = None

    def is_available(self) -> bool:
        """Check if replica is available for routing"""
        return self.state == ReplicaState.HEALTHY and self.lag < 5.0


@dataclass
class RoutingDecision:
    """Routing decision"""

    target_host: str
    target_port: int
    query_type: QueryType
    replica_used: bool = False
    routing_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReadWriteRouter:
    """Intelligent read-write router for database queries"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize read-write router

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Database configuration
        self.primary_host = self.config.get("primary_host", "localhost")
        self.primary_port = self.config.get("primary_port", 5432)

        # Replica configuration
        self.replicas: Dict[str, ReplicaInfo] = {}
        self._initialize_replicas()

        # Routing configuration
        self.read_write_splitting_enabled = self.config.get("read_write_splitting_enabled", True)
        self.lag_threshold = self.config.get("lag_threshold", 5.0)
        self.load_balancing_method = self.config.get("load_balancing_method", "round_robin")

        # Load balancing state
        self.round_robin_index = 0
        self.query_count = 0

        # Health check configuration
        self.health_check_interval = self.config.get("health_check_interval", 10)
        self.health_check_enabled = self.config.get("health_check_enabled", True)

        logger.info("Read-write router initialized with read-write splitting enabled")

    def _initialize_replicas(self):
        """Initialize replica information from configuration"""
        replicas_config = self.config.get("replicas", [])

        for i, replica_config in enumerate(replicas_config):
            replica_id = f"replica_{i}"
            self.replicas[replica_id] = ReplicaInfo(
                host=replica_config.get("host", "localhost"),
                port=replica_config.get("port", 5432),
                state=ReplicaState.HEALTHY,
                lag=0.0,
                connections=0,
                load_score=0.0,
                last_check=datetime.now(timezone.utc),
            )

    def classify_query(self, query: str) -> QueryType:
        """
        Classify SQL query type

        Args:
            query: SQL query string

        Returns:
            QueryType: Query classification
        """
        query_upper = query.upper().strip()

        # Transaction commands
        if query_upper.startswith(("BEGIN", "START TRANSACTION", "COMMIT", "ROLLBACK")):
            return QueryType.TRANSACTION

        # Schema modification commands
        if query_upper.startswith(("CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME")):
            return QueryType.SCHEMA

        # Write operations
        if query_upper.startswith(("INSERT", "UPDATE", "DELETE", "MERGE", "REPLACE")):
            return QueryType.WRITE

        # Read operations
        if query_upper.startswith(("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")):
            return QueryType.READ

        # Default to read for unknown queries
        return QueryType.READ

    def route_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Route database query to appropriate database instance

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            RoutingDecision: Routing decision
        """
        self.query_count += 1
        query_type = self.classify_query(query)

        # Always route writes and transactions to primary
        if query_type in (QueryType.WRITE, QueryType.TRANSACTION, QueryType.SCHEMA):
            return RoutingDecision(
                target_host=self.primary_host,
                target_port=self.primary_port,
                query_type=query_type,
                replica_used=False,
                routing_reason="Write/Transaction/Schema query routed to primary",
            )

        # Route reads according to configuration
        if not self.read_write_splitting_enabled:
            return RoutingDecision(
                target_host=self.primary_host,
                target_port=self.primary_port,
                query_type=query_type,
                replica_used=False,
                routing_reason="Read-write splitting disabled",
            )

        # Route to replica if available
        if self.replicas:
            replica = self._select_replica()
            if replica and replica.is_available():
                return RoutingDecision(
                    target_host=replica.host,
                    target_port=replica.port,
                    query_type=query_type,
                    replica_used=True,
                    routing_reason=f"Read query routed to replica (lag: {replica.lag:.2f}s)",
                    metadata={"replica_id": self._get_replica_id(replica), "lag": replica.lag},
                )

        # Fallback to primary if no suitable replica
        return RoutingDecision(
            target_host=self.primary_host,
            target_port=self.primary_port,
            query_type=query_type,
            replica_used=False,
            routing_reason="No suitable replica available, routing to primary",
        )

    def _select_replica(self) -> Optional[ReplicaInfo]:
        """Select replica based on load balancing method"""
        available_replicas = [r for r in self.replicas.values() if r.is_available()]

        if not available_replicas:
            return None

        if self.load_balancing_method == "round_robin":
            return self._round_robin_select(available_replicas)
        elif self.load_balancing_method == "least_lag":
            return self._least_lag_select(available_replicas)
        elif self.load_balancing_method == "least_connections":
            return self._least_connections_select(available_replicas)
        else:
            return random.choice(available_replicas)  # nosec B311

    def _round_robin_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Select replica using round-robin"""
        replica = replicas[self.round_robin_index % len(replicas)]
        self.round_robin_index += 1
        return replica

    def _least_lag_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Select replica with lowest replication lag"""
        return min(replicas, key=lambda r: r.lag)

    def _least_connections_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Select replica with lowest connection count"""
        return min(replicas, key=lambda r: r.connections)

    def _get_replica_id(self, replica: ReplicaInfo) -> str:
        """Get replica ID from replica info"""
        for replica_id, replica_info in self.replicas.items():
            if replica_info == replica:
                return replica_id
        return "unknown"

    def update_replica_state(
        self,
        replica_id: str,
        state: ReplicaState,
        lag: Optional[float] = None,
        connections: Optional[int] = None,
    ):
        """
        Update replica state

        Args:
            replica_id: Replica identifier
            state: New replica state
            lag: Optional replication lag
            connections: Optional connection count
        """
        if replica_id in self.replicas:
            replica = self.replicas[replica_id]
            replica.state = state
            replica.last_check = datetime.now(timezone.utc)

            if lag is not None:
                replica.lag = lag

            if connections is not None:
                replica.connections = connections

            # Update load score
            replica.load_score = self._calculate_load_score(replica)

            logger.info(f"Replica {replica_id} state updated: {state.value}, lag: {lag}")

    def _calculate_load_score(self, replica: ReplicaInfo) -> float:
        """Calculate load score for replica"""
        # Lower score is better
        lag_score = replica.lag / self.lag_threshold if self.lag_threshold > 0 else replica.lag
        connection_score = replica.connections / 100.0  # Normalize to 0-1 range

        return (lag_score * 0.7) + (connection_score * 0.3)

    async def health_check_loop(self):
        """Background health check loop for replicas"""
        if not self.health_check_enabled:
            return

        while True:
            try:
                await self._check_all_replicas_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _check_all_replicas_health(self):
        """Check health of all replicas"""
        for replica_id, replica in self.replicas.items():
            try:
                # Simulate health check (in real implementation, would check actual DB connectivity)
                is_healthy = await self._check_replica_health(replica)

                if is_healthy:
                    if replica.state != ReplicaState.HEALTHY:
                        self.update_replica_state(replica_id, ReplicaState.HEALTHY)
                else:
                    if replica.state == ReplicaState.HEALTHY:
                        self.update_replica_state(replica_id, ReplicaState.UNHEALTHY)

            except Exception as e:
                logger.error(f"Health check failed for replica {replica_id}: {e}")
                self.update_replica_state(replica_id, ReplicaState.UNHEALTHY)

    async def _check_replica_health(self, replica: ReplicaInfo) -> bool:
        """Check health of individual replica"""
        # In real implementation, would check actual database connectivity
        # For now, simulate health check
        return True

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "total_queries": self.query_count,
            "read_write_splitting_enabled": self.read_write_splitting_enabled,
            "replicas_count": len(self.replicas),
            "healthy_replicas": sum(1 for r in self.replicas.values() if r.is_available()),
            "load_balancing_method": self.load_balancing_method,
            "replicas": {
                replica_id: {
                    "host": replica.host,
                    "port": replica.port,
                    "state": replica.state.value,
                    "lag": replica.lag,
                    "connections": replica.connections,
                    "load_score": replica.load_score,
                }
                for replica_id, replica in self.replicas.items()
            },
        }

    def enable_read_write_splitting(self, enabled: bool = True):
        """Enable or disable read-write splitting"""
        self.read_write_splitting_enabled = enabled
        logger.info(f"Read-write splitting {'enabled' if enabled else 'disabled'}")


def get_read_write_router(config: Optional[Dict[str, Any]] = None) -> ReadWriteRouter:
    """
    Factory function to get read-write router instance

    Args:
        config: Optional configuration dictionary

    Returns:
        ReadWriteRouter: Router instance
    """
    return ReadWriteRouter(config)
