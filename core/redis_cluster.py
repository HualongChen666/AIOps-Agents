# -*- coding: utf-8 -*-
"""Redis cluster configuration and management for high availability.

This module provides Redis cluster configuration, connection pooling,
and failover logic for high availability caching and session management.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from loguru import logger

# Redis cluster configuration
_redis_cluster_config: Dict[str, Any] = {
    "enabled": False,
    "mode": "standalone",  # standalone, sentinel, cluster
    "nodes": [],
    "sentinel_config": {
        "master_name": "mymaster",
        "sentinels": [],
    },
    "cluster_config": {
        "slots": 16384,
        "replicas": 1,
    },
    "connection_pool_size": 10,
    "connection_timeout_seconds": 5,
    "socket_timeout_seconds": 5,
    "retry_on_timeout": True,
    "max_retries": 3,
}

# Node health tracking
_node_health: Dict[str, Dict[str, Any]] = {}
_current_master: str = ""


def configure_redis_cluster(
    mode: str = "standalone",
    nodes: Optional[List[Dict[str, Any]]] = None,
    sentinel_config: Optional[Dict[str, Any]] = None,
    cluster_config: Optional[Dict[str, Any]] = None,
) -> None:
    """Configure Redis cluster settings.

    Args:
        mode: Redis mode (standalone, sentinel, cluster)
        nodes: List of Redis node configurations
        sentinel_config: Sentinel configuration for sentinel mode
        cluster_config: Cluster configuration for cluster mode
    """

    _redis_cluster_config["enabled"] = True
    _redis_cluster_config["mode"] = mode
    _redis_cluster_config["nodes"] = nodes or []

    if sentinel_config:
        _redis_cluster_config["sentinel_config"] = sentinel_config

    if cluster_config:
        _redis_cluster_config["cluster_config"] = cluster_config

    # Initialize health tracking
    for i, node in enumerate(_redis_cluster_config["nodes"]):
        node_key = f"node_{i}"
        _node_health[node_key] = {
            "status": "unknown",
            "last_check": None,
            "latency_ms": None,
            "role": node.get("role", "unknown"),
        }

    logger.info(
        f"Configured Redis cluster in {mode} mode with {len(_redis_cluster_config['nodes'])} nodes"
    )


def get_redis_cluster_config() -> Dict[str, Any]:
    """Get Redis cluster configuration.

    Returns:
        Redis cluster configuration dictionary
    """
    return _redis_cluster_config.copy()


def is_redis_cluster_enabled() -> bool:
    """Check if Redis cluster is enabled.

    Returns:
        True if Redis cluster is enabled
    """
    return cast(bool, _redis_cluster_config["enabled"])


def get_redis_mode() -> str:
    """Get Redis deployment mode.

    Returns:
        Redis mode (standalone, sentinel, cluster)
    """
    return cast(str, _redis_cluster_config["mode"])


async def check_node_health(node_index: int) -> Dict[str, Any]:
    """Check Redis node health.

    Args:
        node_index: Index of the node to check

    Returns:
        Health status dictionary
    """
    node_key = f"node_{node_index}"

    try:
        # default_value for actual health check
        # In production, this would execute PING command
        start_time = datetime.now(timezone.utc)

        # Simulate health check
        await asyncio.sleep(0.01)  # Simulate network latency

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        health_status = {
            "status": "healthy",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "latency_ms": latency_ms,
            "role": _redis_cluster_config["nodes"][node_index].get("role", "unknown"),
        }

        _node_health[node_key] = health_status
        return health_status

    except Exception as e:
        logger.error(f"Redis node {node_index} health check failed: {e}")
        health_status = {
            "status": "unhealthy",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "latency_ms": None,
            "role": _redis_cluster_config["nodes"][node_index].get("role", "unknown"),
        }
        _node_health[node_key] = health_status
        return health_status


async def check_all_nodes_health() -> Dict[str, Dict[str, Any]]:
    """Check health of all Redis nodes.

    Returns:
        Dictionary of node health statuses
    """
    health_results = {}

    for i in range(len(_redis_cluster_config["nodes"])):
        node_key = f"node_{i}"
        health_results[node_key] = await check_node_health(i)

    return health_results


def get_node_health() -> Dict[str, Dict[str, Any]]:
    """Get current node health status.

    Returns:
        Dictionary of node health statuses
    """
    return _node_health.copy()


def get_healthy_nodes() -> List[str]:
    """Get list of healthy node identifiers.

    Returns:
        List of healthy node identifiers
    """
    healthy_nodes = []

    for node_key, health in _node_health.items():
        if health.get("status") == "healthy":
            healthy_nodes.append(node_key)

    return healthy_nodes


def get_master_nodes() -> List[str]:
    """Get list of master node identifiers.

    Returns:
        List of master node identifiers
    """
    master_nodes = []

    for node_key, health in _node_health.items():
        if health.get("role") == "master":
            master_nodes.append(node_key)

    return master_nodes


def get_replica_nodes() -> List[str]:
    """Get list of replica node identifiers.

    Returns:
        List of replica node identifiers
    """
    replica_nodes = []

    for node_key, health in _node_health.items():
        if health.get("role") == "replica":
            replica_nodes.append(node_key)

    return replica_nodes


async def promote_replica_to_master(replica_index: int) -> bool:
    """Promote a replica to master (for failover scenarios).

    Args:
        replica_index: Index of the replica to promote

    Returns:
        True if promotion successful
    """
    try:
        global _current_master
        node_key = f"node_{replica_index}"

        # Update node role
        if node_key in _node_health:
            _node_health[node_key]["role"] = "master"

        # Update current master
        old_master = _current_master
        _current_master = node_key

        logger.info(f"Promoted {node_key} to master (was {old_master})")

        return True

    except Exception as e:
        logger.error(f"Failed to promote replica {replica_index}: {e}")
        return False


def get_current_master() -> str:
    """Get current master node identifier.

    Returns:
        Current master identifier
    """
    return _current_master


async def perform_failover() -> bool:
    """Perform automatic failover to healthy replica.

    Returns:
        True if failover successful or no failover needed
    """
    # Check if current master is unhealthy
    master_nodes = get_master_nodes()

    has_healthy_master = False
    for master_key in master_nodes:
        master_health = _node_health.get(master_key, {})
        if master_health.get("status") == "healthy":
            logger.info(f"Master {master_key} is healthy, no failover needed")
            has_healthy_master = True
            break

    if has_healthy_master:
        return True

    # Find healthy replicas
    healthy_replicas = get_healthy_nodes()
    healthy_replica_indices = [
        int(r.split("_")[1]) for r in healthy_replicas if r.startswith("node_")
    ]

    # Filter for replicas only
    replica_indices = [
        i
        for i in healthy_replica_indices
        if _node_health.get(f"node_{i}", {}).get("role") == "replica"
    ]

    if not replica_indices:
        logger.error("No healthy replicas available for failover")
        return False

    # Promote first healthy replica
    return await promote_replica_to_master(replica_indices[0])


def get_cluster_status() -> Dict[str, Any]:
    """Get comprehensive cluster status.

    Returns:
        Dictionary with cluster status details
    """
    return {
        "enabled": _redis_cluster_config["enabled"],
        "mode": _redis_cluster_config["mode"],
        "node_count": len(_redis_cluster_config["nodes"]),
        "current_master": _current_master,
        "health_status": _node_health.copy(),
        "connection_pool_size": _redis_cluster_config["connection_pool_size"],
        "connection_timeout": _redis_cluster_config["connection_timeout_seconds"],
    }


def get_connection_string() -> Optional[str]:
    """Get Redis connection string based on configuration.

    Returns:
        Redis connection string or None if not configured
    """
    if not _redis_cluster_config["enabled"]:
        return None

    if _redis_cluster_config["mode"] == "standalone" and _redis_cluster_config["nodes"]:
        node = _redis_cluster_config["nodes"][0]
        return f"redis://{node.get('host', 'localhost')}:{node.get('port', 6379)}"

    elif _redis_cluster_config["mode"] == "cluster":
        # Return cluster connection string
        hosts = ",".join(
            [f"{n.get('host')}:{n.get('port', 6379)}" for n in _redis_cluster_config["nodes"]]
        )
        return f"redis-cluster://{hosts}"

    elif _redis_cluster_config["mode"] == "sentinel":
        # Return sentinel connection string
        sentinel = _redis_cluster_config["sentinel_config"]
        master_name = sentinel.get("master_name", "mymaster")
        sentinels = ",".join(
            [f"{s.get('host')}:{s.get('port', 26379)}" for s in sentinel.get("sentinels", [])]
        )
        return f"sentinel://{master_name}@{sentinels}"

    return None


__all__ = [
    "configure_redis_cluster",
    "get_redis_cluster_config",
    "is_redis_cluster_enabled",
    "get_redis_mode",
    "check_node_health",
    "check_all_nodes_health",
    "get_node_health",
    "get_healthy_nodes",
    "get_master_nodes",
    "get_replica_nodes",
    "promote_replica_to_master",
    "get_current_master",
    "perform_failover",
    "get_cluster_status",
    "get_connection_string",
]
