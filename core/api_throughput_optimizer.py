# -*- coding: utf-8 -*-
"""
API Throughput Optimization
Enterprise-grade API throughput optimization with rate limiting and load balancing
"""

import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class RateLimitStrategy(Enum):
    """Rate limit strategy"""

    TOKEN_BUCKET = "token_bucket"  # nosec B105
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class LoadBalancingStrategy(Enum):
    """Load balancing strategy"""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    CONSISTENT_HASH = "consistent_hash"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""

    requests_per_second: float = 100.0
    burst_size: int = 200
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendServer:
    """Backend server"""

    server_id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    current_connections: int = 0
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThroughputMetrics:
    """Throughput metrics"""

    endpoint: str
    method: str
    total_requests: int = 0
    requests_per_second: float = 0.0
    successful_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    concurrent_connections: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class APIThroughputOptimizer:
    """Enterprise-grade API throughput optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize API throughput optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Rate limit configurations
        self.rate_limits: Dict[str, RateLimitConfig] = {}

        # Rate limit state
        self.rate_limit_state: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "tokens": 0,
                "last_update": datetime.now(timezone.utc),
                "request_history": deque(maxlen=1000),
            }
        )

        # Backend servers
        self.backend_servers: List[BackendServer] = []

        # Load balancing state
        self.lb_state: Dict[str, Any] = {"current_index": 0, "connection_counts": defaultdict(int)}

        # Concurrent connection limits
        self.concurrent_limits: Dict[str, int] = {}
        self.current_connections: Dict[str, int] = defaultdict(int)

        # Throughput metrics
        self.throughput_metrics: Dict[str, ThroughputMetrics] = {}

        # Request history for performance monitoring
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        # Configuration
        self.default_rate_limit = RateLimitConfig()
        self.default_concurrent_limit = self.config.get("default_concurrent_limit", 100)
        self.load_balancing_strategy = LoadBalancingStrategy.ROUND_ROBIN

        # Statistics
        self.total_requests_processed = 0
        self.total_requests_rate_limited = 0
        self.total_requests_rejected = 0

        logger.info("API throughput optimizer initialized")

    def set_rate_limit(
        self,
        key: str,
        requests_per_second: float,
        burst_size: int = 200,
        strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET,
    ) -> None:
        """
        Set rate limit for key

        Args:
            key: Rate limit key (e.g., endpoint or user ID)
            requests_per_second: Requests per second limit
            burst_size: Burst size
            strategy: Rate limit strategy
        """
        self.rate_limits[key] = RateLimitConfig(
            requests_per_second=requests_per_second, burst_size=burst_size, strategy=strategy
        )

        logger.info(f"Set rate limit for {key}: {requests_per_second} req/s, burst: {burst_size}")

    def check_rate_limit(self, key: str, tokens: int = 1) -> bool:
        """
        Check if request is allowed based on rate limit

        Args:
            key: Rate limit key
            tokens: Number of tokens to consume

        Returns:
            True if request is allowed, False otherwise
        """
        if key not in self.rate_limits:
            return True  # No rate limit configured

        config = self.rate_limits[key]
        state = self.rate_limit_state[key]

        now = datetime.now(timezone.utc)
        time_delta = (now - state["last_update"]).total_seconds()

        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            # Token bucket algorithm
            state["tokens"] = min(
                config.burst_size, state["tokens"] + time_delta * config.requests_per_second
            )

            if state["tokens"] >= tokens:
                state["tokens"] -= tokens
                state["last_update"] = now
                return True
            else:
                self.total_requests_rate_limited += 1
                return False

        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            # Sliding window algorithm
            state["request_history"].append(now)

            # Remove requests outside the window
            cutoff = now - timedelta(seconds=1)
            state["request_history"] = deque(
                [req_time for req_time in state["request_history"] if req_time > cutoff],
                maxlen=1000,
            )

            if len(state["request_history"]) <= config.requests_per_second:
                return True
            else:
                self.total_requests_rate_limited += 1
                return False

        else:
            # Fixed window algorithm
            window_start = now.replace(microsecond=0, second=0)
            if state["last_update"] < window_start:
                state["tokens"] = 0
                state["last_update"] = window_start

            if state["tokens"] + tokens <= config.requests_per_second:
                state["tokens"] += tokens
                return True
            else:
                self.total_requests_rate_limited += 1
                return False

    def add_backend_server(
        self, server_id: str, host: str, port: int, weight: int = 1, max_connections: int = 100
    ) -> None:
        """
        Add backend server

        Args:
            server_id: Server ID
            host: Server host
            port: Server port
            weight: Server weight
            max_connections: Max connections
        """
        server = BackendServer(
            server_id=server_id,
            host=host,
            port=port,
            weight=weight,
            max_connections=max_connections,
        )

        self.backend_servers.append(server)
        logger.info(f"Added backend server: {server_id} ({host}:{port})")

    def get_backend_server(self, client_ip: Optional[str] = None) -> Optional[BackendServer]:
        """
        Get backend server using load balancing

        Args:
            client_ip: Client IP address for hash-based balancing

        Returns:
            Backend server or None
        """
        if not self.backend_servers:
            return None

        # Filter healthy servers
        healthy_servers: List[BackendServer] = [s for s in self.backend_servers if s.is_healthy]

        if not healthy_servers:
            return None

        strategy = self.load_balancing_strategy

        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            # Round robin
            current_index = int(self.lb_state["current_index"])
            server = healthy_servers[current_index % len(healthy_servers)]
            self.lb_state["current_index"] = current_index + 1
            return server

        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            # Least connections
            return min(healthy_servers, key=lambda s: s.current_connections)

        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            # Weighted round robin
            total_weight = sum(s.weight for s in healthy_servers)
            if total_weight == 0:
                return healthy_servers[0]

            import random

            rand = random.uniform(0, total_weight)  # nosec B311
            cumulative = 0

            for server in healthy_servers:
                cumulative += server.weight
                if rand <= cumulative:
                    return server

            return healthy_servers[-1]

        elif strategy == LoadBalancingStrategy.IP_HASH and client_ip:
            # IP hash
            import hashlib

            hash_value = int(hashlib.md5(client_ip.encode(), usedforsecurity=False).hexdigest(), 16)
            index = hash_value % len(healthy_servers)
            return healthy_servers[index]

        else:
            # Default to round robin
            current_index = int(self.lb_state["current_index"])
            server = healthy_servers[current_index % len(healthy_servers)]
            self.lb_state["current_index"] = current_index + 1
            return server

    def set_concurrent_limit(self, endpoint: str, limit: int) -> None:
        """
        Set concurrent connection limit for endpoint

        Args:
            endpoint: API endpoint
            limit: Concurrent connection limit
        """
        self.concurrent_limits[endpoint] = limit
        logger.info(f"Set concurrent limit for {endpoint}: {limit}")

    def check_concurrent_limit(self, endpoint: str) -> bool:
        """
        Check if concurrent connection limit is reached

        Args:
            endpoint: API endpoint

        Returns:
            True if connection is allowed, False otherwise
        """
        limit = self.concurrent_limits.get(endpoint, self.default_concurrent_limit)
        current = self.current_connections[endpoint]

        if current >= limit:
            self.total_requests_rejected += 1
            return False

        self.current_connections[endpoint] += 1
        return True

    def release_connection(self, endpoint: str) -> None:
        """
        Release concurrent connection

        Args:
            endpoint: API endpoint
        """
        if self.current_connections[endpoint] > 0:
            self.current_connections[endpoint] -= 1

    def track_request(
        self, endpoint: str, method: str, success: bool, response_time_ms: float
    ) -> None:
        """
        Track request for performance monitoring

        Args:
            endpoint: API endpoint
            method: HTTP method
            success: Request success
            response_time_ms: Response time
        """
        key = f"{method}:{endpoint}"

        self.request_history[key].append(
            {
                "timestamp": datetime.now(timezone.utc),
                "success": success,
                "response_time_ms": response_time_ms,
            }
        )

        self.total_requests_processed += 1

        # Update metrics
        self._update_throughput_metrics(key)

    def _update_throughput_metrics(self, key: str) -> None:
        """
        Update throughput metrics

        Args:
            key: Endpoint key
        """
        history = self.request_history[key]

        if key not in self.throughput_metrics:
            method, endpoint = key.split(":", 1)
            self.throughput_metrics[key] = ThroughputMetrics(endpoint=endpoint, method=method)

        metrics = self.throughput_metrics[key]
        metrics.total_requests = len(history)

        # Calculate requests per second (last 60 seconds)
        now = datetime.now(timezone.utc)
        recent_requests = [r for r in history if (now - r["timestamp"]).total_seconds() <= 60]
        metrics.requests_per_second = len(recent_requests) / 60.0 if recent_requests else 0

        # Calculate success rate
        successful = sum(1 for r in history if r["success"])
        metrics.successful_requests = successful
        metrics.failed_requests = len(history) - successful
        metrics.success_rate = successful / len(history) if history else 0

        # Calculate average response time
        response_times = [r["response_time_ms"] for r in history]
        metrics.avg_response_time_ms = statistics.mean(response_times) if response_times else 0

        # Update concurrent connections
        metrics.concurrent_connections = self.current_connections.get(metrics.endpoint, 0)

        metrics.last_updated = now

    def get_throughput_metrics(self, endpoint: str, method: str) -> Optional[ThroughputMetrics]:
        """
        Get throughput metrics for endpoint

        Args:
            endpoint: API endpoint
            method: HTTP method

        Returns:
            Throughput metrics or None
        """
        key = f"{method}:{endpoint}"
        return self.throughput_metrics.get(key)

    def get_all_throughput_metrics(self) -> Dict[str, ThroughputMetrics]:
        """Get all throughput metrics"""
        for key in self.request_history:
            self._update_throughput_metrics(key)
        return self.throughput_metrics.copy()

    def health_check_backend(self, server_id: str) -> bool:
        """
        Perform health check on backend server

        Args:
            server_id: Server ID

        Returns:
            True if healthy, False otherwise
        """
        for server in self.backend_servers:
            if server.server_id == server_id:
                # In real implementation, this would make actual health check request
                server.is_healthy = True
                server.last_health_check = datetime.now(timezone.utc)
                return True

        return False

    def optimize_throughput(self, endpoint: str, method: str) -> Dict[str, Any]:
        """
        Analyze throughput and provide optimization recommendations

        Args:
            endpoint: API endpoint
            method: HTTP method

        Returns:
            Optimization recommendations
        """
        metrics = self.get_throughput_metrics(endpoint, method)

        if not metrics:
            return {"error": "No metrics available"}

        recommendations = []

        # Check success rate
        if metrics.success_rate < 0.95:
            recommendations.append(
                {
                    "type": "improve_error_handling",
                    "reason": f"Low success rate ({metrics.success_rate:.2%})",
                    "action": "Investigate and fix error causes",
                }
            )

        # Check response time
        if metrics.avg_response_time_ms > 500:
            recommendations.append(
                {
                    "type": "optimize_response_time",
                    "reason": f"High response time ({metrics.avg_response_time_ms:.2f}ms)",
                    "action": "Optimize endpoint performance or implement caching",
                }
            )

        # Check concurrent connections
        if (
            metrics.concurrent_connections
            > self.concurrent_limits.get(endpoint, self.default_concurrent_limit) * 0.8
        ):
            recommendations.append(
                {
                    "type": "increase_concurrent_limit",
                    "reason": "High concurrent connection usage",
                    "action": "Consider increasing concurrent connection limit",
                }
            )

        # Check requests per second
        if metrics.requests_per_second > 100:
            recommendations.append(
                {
                    "type": "scale_infrastructure",
                    "reason": f"High request rate ({metrics.requests_per_second:.2f} req/s)",
                    "action": "Consider horizontal scaling",
                }
            )

        return {
            "endpoint": endpoint,
            "method": method,
            "current_metrics": {
                "requests_per_second": metrics.requests_per_second,
                "success_rate": metrics.success_rate,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "concurrent_connections": metrics.concurrent_connections,
            },
            "recommendations": recommendations,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "total_requests_processed": self.total_requests_processed,
            "total_requests_rate_limited": self.total_requests_rate_limited,
            "total_requests_rejected": self.total_requests_rejected,
            "total_rate_limits": len(self.rate_limits),
            "total_backend_servers": len(self.backend_servers),
            "healthy_backend_servers": sum(1 for s in self.backend_servers if s.is_healthy),
            "total_concurrent_limits": len(self.concurrent_limits),
        }


def get_api_throughput_optimizer(config: Optional[Dict[str, Any]] = None) -> APIThroughputOptimizer:
    """
    Factory function to get API throughput optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        APIThroughputOptimizer: Optimizer instance
    """
    return APIThroughputOptimizer(config)
