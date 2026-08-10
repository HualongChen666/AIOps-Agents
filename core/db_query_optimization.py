# -*- coding: utf-8 -*-
"""
Database Query Optimization Enhancements
数据库查询优化增强

Additional query optimization utilities for the AIOps Agent system.
Includes query caching, batch operations, and connection monitoring.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal


class QueryCache:
    """Simple in-memory query cache for frequently accessed data"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize query cache

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if exists and not expired

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/not found
        """
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now(timezone.utc) < entry["expires"]:
                logger.debug(f"Cache hit for key: {key}")
                return entry["value"]
            else:
                # Expired, remove it
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")
        return None

    def set(self, key: str, value: Any):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = {
            "value": value,
            "expires": datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
            "created": datetime.now(timezone.utc),
        }
        logger.debug(f"Cache set for key: {key}")

    def invalidate(self, key: str = None):
        """
        Invalidate cache entry

        Args:
            key: Specific key to invalidate, or None to clear all
        """
        if key:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache invalidated for key: {key}")
        else:
            self.cache.clear()
            logger.debug("All cache invalidated")

    def cleanup_expired(self):
        """Clean up expired cache entries"""
        now = datetime.now(timezone.utc)
        expired_keys = [key for key, entry in self.cache.items() if now >= entry["expires"]]
        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global query cache instance
query_cache = QueryCache(ttl_seconds=300)


def cache_query_result(ttl_seconds: int = 300):
    """
    Decorator to cache query results

    Args:
        ttl_seconds: Time-to-live for cache in seconds
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"

            # Try to get from cache
            cached = query_cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            query_cache.ttl_seconds = ttl_seconds
            query_cache.set(cache_key, result)

            return result

        return wrapper

    return decorator


class BatchQueryOptimizer:
    """Optimizer for batch database operations"""

    @staticmethod
    async def batch_insert(
        session: AsyncSession, model_class: Any, items: List[Dict[str, Any]], batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Perform batch insert operation

        Args:
            session: Database session
            model_class: SQLAlchemy model class
            items: List of dictionaries with data to insert
            batch_size: Number of items per batch

        Returns:
            Dictionary with insert results
        """
        results = {"total": len(items), "inserted": 0, "failed": 0, "batches": 0}

        try:
            for i in range(0, len(items), batch_size):
                batch = items[i: i + batch_size]
                results["batches"] += 1

                try:
                    # Create model instances
                    instances = [model_class(**item) for item in batch]

                    # Add to session
                    session.add_all(instances)
                    await session.commit()

                    results["inserted"] += len(batch)
                    logger.info(f"Batch insert completed: {len(batch)} items")

                except Exception as e:
                    await session.rollback()
                    results["failed"] += len(batch)
                    logger.error(f"Batch insert failed: {e}")

            return results

        except Exception as e:
            logger.error(f"Batch insert operation failed: {e}")
            return {"error": str(e), **results}

    @staticmethod
    async def batch_update(
        session: AsyncSession,
        model_class: Any,
        updates: List[Dict[str, Any]],
        id_field: str = "id",
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Perform batch update operation

        Args:
            session: Database session
            model_class: SQLAlchemy model class
            updates: List of dictionaries with update data
            id_field: Field name to use as identifier
            batch_size: Number of items per batch

        Returns:
            Dictionary with update results
        """
        results = {"total": len(updates), "updated": 0, "failed": 0, "batches": 0}

        try:
            for i in range(0, len(updates), batch_size):
                batch = updates[i: i + batch_size]
                results["batches"] += 1

                try:
                    for update_data in batch:
                        item_id = update_data.pop(id_field)

                        # Build update statement
                        stmt = select(model_class).where(getattr(model_class, id_field) == item_id)
                        result = await session.execute(stmt)
                        instance = result.scalar_one_or_none()

                        if instance:
                            for field, value in update_data.items():
                                setattr(instance, field, value)

                    await session.commit()
                    results["updated"] += len(batch)
                    logger.info(f"Batch update completed: {len(batch)} items")

                except Exception as e:
                    await session.rollback()
                    results["failed"] += len(batch)
                    logger.error(f"Batch update failed: {e}")

            return results

        except Exception as e:
            logger.error(f"Batch update operation failed: {e}")
            return {"error": str(e), **results}


class ConnectionPoolMonitor:
    """Monitor database connection pool health"""

    @staticmethod
    async def get_pool_stats() -> Dict[str, Any]:
        """
        Get connection pool statistics

        Returns:
            Dictionary with pool statistics
        """
        try:
            async with AsyncSessionLocal() as session:
                # Get PostgreSQL connection statistics
                stats_query = text("""
                    SELECT
                        count(*) as total_connections,
                        count(*) filter (where state = 'active') as active_connections,
                        count(*) filter (where state = 'idle') as idle_connections
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)

                result = await session.execute(stats_query)
                stats = result.fetchone()

                return {
                    "total_connections": stats[0] if stats else 0,
                    "active_connections": stats[1] if stats else 0,
                    "idle_connections": stats[2] if stats else 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    async def check_pool_health() -> Dict[str, Any]:
        """
        Check connection pool health

        Returns:
            Dictionary with health status
        """
        try:
            stats = await ConnectionPoolMonitor.get_pool_stats()

            if "error" in stats:
                return {"healthy": False, "error": stats["error"]}

            # Simple health check
            total = stats["total_connections"]
            active = stats["active_connections"]

            # Consider unhealthy if too many connections
            healthy = total < 100 and active < 50

            return {
                "healthy": healthy,
                "stats": stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Pool health check failed: {e}")
            return {"healthy": False, "error": str(e)}


async def optimize_database_queries():
    """
    Run database query optimization routines

    Returns:
        Dictionary with optimization results
    """
    results = {
        "cache_cleanup": None,
        "pool_health": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Clean up expired cache entries
        query_cache.cleanup_expired()
        results["cache_cleanup"] = "completed"

        # Check pool health
        pool_health = await ConnectionPoolMonitor.check_pool_health()
        results["pool_health"] = str(pool_health)

        logger.info("Database query optimization completed")
        return results

    except Exception as e:
        logger.error(f"Database query optimization failed: {e}")
        return {"error": str(e), **results}
