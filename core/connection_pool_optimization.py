# -*- coding: utf-8 -*-
"""
Database Connection Pool Optimization

🔧 P0 Performance Enhancement:
This module provides enhanced connection pool configuration and monitoring:
- Optimized pool size configuration
- Connection health monitoring
- Pool statistics and metrics
- Automatic pool tuning recommendations
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# 🔧 P0 Enhancement: Optimized connection pool configuration
CONNECTION_POOL_CONFIG = {
    "pool_size": 20,  # Base pool size
    "max_overflow": 40,  # Maximum overflow connections
    "pool_timeout": 30,  # Timeout for getting connection from pool
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Verify connections before using
    "echo": False,  # Disable SQL echo for production
    "future": True,  # Use SQLAlchemy 2.0 style
}


class ConnectionPoolMonitor:
    """Monitor and analyze connection pool performance"""

    def __init__(self, engine: AsyncEngine):
        """
        Args:
            engine: SQLAlchemy async engine
        """
        self._engine = engine
        self._metrics_history: List[Dict[str, Any]] = []

    async def get_pool_status(self) -> Dict[str, Any]:
        """Get current connection pool status"""
        try:
            pool = self._engine.pool

            return {
                "size": pool.size(),  # type: ignore
                "checked_in": pool.checkedin(),  # type: ignore
                "checked_out": pool.checkedout(),  # type: ignore
                "overflow": pool.overflow(),  # type: ignore
                "max_overflow": pool._max_overflow,  # type: ignore
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    async def analyze_pool_performance(self) -> Dict[str, Any]:
        """Analyze connection pool performance and provide recommendations"""
        try:
            status = await self.get_pool_status()

            if "error" in status:
                return status

            recommendations = []

            # Analyze pool utilization
            pool_size = status["size"]
            checked_out = status["checked_out"]
            utilization = (checked_out / pool_size * 100) if pool_size > 0 else 0

            if utilization > 80:
                recommendations.append(
                    "High pool utilization detected. Consider increasing pool_size"
                )
            elif utilization < 20:
                recommendations.append(
                    "Low pool utilization. Consider reducing pool_size to save resources"
                )

            # Check overflow usage
            overflow = status["overflow"]
            max_overflow = status["max_overflow"]
            if overflow > max_overflow * 0.8:
                recommendations.append("High overflow usage. Consider increasing max_overflow")

            # Store metrics for trend analysis
            self._metrics_history.append(
                {
                    "timestamp": status["timestamp"],
                    "utilization_percent": utilization,
                    "overflow": overflow,
                    "checked_out": checked_out,
                }
            )

            # Keep only last 100 metrics
            if len(self._metrics_history) > 100:
                self._metrics_history = self._metrics_history[-100:]

            return {
                "current_status": status,
                "utilization_percent": f"{utilization:.2f}",
                "recommendations": recommendations,
                "metrics_count": len(self._metrics_history),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Pool performance analysis failed: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    async def test_connection_health(self) -> Dict[str, Any]:
        """Test database connection health"""
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()

            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Connection health test failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Connection test failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


async def create_optimized_engine(database_url: str) -> AsyncEngine:
    """🔧 P0 Enhancement: Create database engine with optimized connection pool.

    Args:
        database_url: Database connection URL

    Returns:
        Optimized async engine
    """
    try:
        engine = create_async_engine(database_url, **CONNECTION_POOL_CONFIG)

        logger.info(
            f"Created optimized connection pool: size={CONNECTION_POOL_CONFIG['pool_size']}, "
            f"max_overflow={CONNECTION_POOL_CONFIG['max_overflow']}"
        )

        return engine

    except Exception as e:
        logger.error(f"Failed to create optimized engine: {e}")
        raise


async def optimize_existing_engine(engine: AsyncEngine) -> Dict[str, Any]:
    """🔧 P0 Enhancement: Optimize existing engine configuration.

    Args:
        engine: Existing database engine

    Returns:
        Optimization results
    """
    try:
        # Note: SQLAlchemy doesn't allow changing pool configuration after creation
        # This function provides recommendations for restarting with optimal config

        monitor = ConnectionPoolMonitor(engine)
        analysis = await monitor.analyze_pool_performance()

        return {
            "status": "analysis_completed",
            "current_config": {
                "pool_size": engine.pool.size() if hasattr(engine.pool, "size") else "unknown",
                "max_overflow": getattr(engine.pool, "_max_overflow", "unknown"),
            },
            "recommended_config": CONNECTION_POOL_CONFIG,
            "analysis": analysis,
            "recommendation": (
                "Restart application with recommended configuration for optimal performance"
            ),
        }

    except Exception as e:
        logger.error(f"Engine optimization analysis failed: {e}")
        return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}


def get_connection_pool_recommendations(workload_type: str = "mixed") -> Dict[str, Any]:
    """🔧 P0 Enhancement: Get connection pool recommendations based on workload.

    Args:
        workload_type: Type of workload (read_heavy, write_heavy, mixed, analytics)

    Returns:
        Recommended pool configuration
    """
    recommendations = {
        "read_heavy": {
            "pool_size": 30,
            "max_overflow": 50,
            "pool_timeout": 30,
            "pool_recycle": 1800,  # More frequent recycling for read-heavy workloads
            "reasoning": (  # noqa: E501
                "Read-heavy workloads benefit from larger pools to handle concurrent queries"
            ),
        },
        "write_heavy": {
            "pool_size": 15,
            "max_overflow": 20,
            "pool_timeout": 60,  # Longer timeout for write operations
            "pool_recycle": 3600,
            "reasoning": (  # noqa: E501
                "Write-heavy workloads need smaller pools to avoid overwhelming the database"
            ),
        },
        "mixed": {
            "pool_size": 20,
            "max_overflow": 40,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "reasoning": "Mixed workloads need balanced pool configuration",
        },
        "analytics": {
            "pool_size": 10,
            "max_overflow": 15,
            "pool_timeout": 120,  # Long timeout for complex analytics queries
            "pool_recycle": 7200,  # Less frequent recycling for long-running queries
            "reasoning": "Analytics workloads need fewer connections but longer timeouts",
        },
    }

    return recommendations.get(workload_type, recommendations["mixed"])
