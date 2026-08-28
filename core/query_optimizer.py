# -*- coding: utf-8 -*-
"""
Query Optimization Utilities

Provides utilities for optimizing database queries including:
- Eager loading helpers to avoid N+1 queries
- Pagination utilities
- Query result caching decorators
- Batch operation helpers
"""

from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Generic
from functools import wraps
from sqlalchemy.orm import Query, joinedload, selectinload, subqueryload
from sqlalchemy.sql.expression import select
import time

# Generic type for model classes
T = TypeVar('T')


class QueryOptimizer:
    """Query optimization utilities"""
    
    @staticmethod
    def apply_eager_loading(query: Query, relationships: List[str]) -> Query:
        """
        Apply eager loading to avoid N+1 queries
        
        Args:
            query: SQLAlchemy query object
            relationships: List of relationship names to eager load
            
        Returns:
            Query with eager loading applied
        """
        for relationship in relationships:
            # Use joinedload for many-to-one and one-to-one
            # Use selectinload for one-to-many and many-to-many
            query = query.options(selectinload(relationship))
        
        return query
    
    @staticmethod
    def apply_joined_loading(query: Query, relationships: List[str]) -> Query:
        """
        Apply joined loading for many-to-one relationships
        
        Args:
            query: SQLAlchemy query object
            relationships: List of relationship names to join load
            
        Returns:
            Query with joined loading applied
        """
        for relationship in relationships:
            query = query.options(joinedload(relationship))
        
        return query
    
    @staticmethod
    def apply_subquery_loading(query: Query, relationships: List[str]) -> Query:
        """
        Apply subquery loading for one-to-many relationships
        
        Args:
            query: SQLAlchemy query object
            relationships: List of relationship names to subquery load
            
        Returns:
            Query with subquery loading applied
        """
        for relationship in relationships:
            query = query.options(subqueryload(relationship))
        
        return query
    
    @staticmethod
    def paginate_query(
        query: Query, 
        page: int = 1, 
        per_page: int = 50,
        max_per_page: int = 1000
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Apply pagination to a query
        
        Args:
            query: SQLAlchemy query object
            page: Page number (1-indexed)
            per_page: Items per page
            max_per_page: Maximum items per page (safety limit)
            
        Returns:
            Tuple of (results, pagination_info)
        """
        # Apply safety limit
        per_page = min(per_page, max_per_page)
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        results = query.offset(offset).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        pagination_info = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None
        }
        
        return results, pagination_info
    
    @staticmethod
    def optimize_query_filters(query: Query, filters: Dict[str, Any]) -> Query:
        """
        Optimize query filters by applying indexes and proper filtering
        
        Args:
            query: SQLAlchemy query object
            filters: Dictionary of field names and values to filter by
            
        Returns:
            Optimized query with filters applied
        """
        for field, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    # Use IN clause for lists
                    query = query.filter(getattr(query.column_described, field).in_(value))
                elif isinstance(value, (str,)):
                    # Use LIKE for string searches with wildcards
                    if '*' in value or '%' in value:
                        query = query.filter(getattr(query.column_described, field).like(value.replace('*', '%')))
                    else:
                        query = query.filter(getattr(query.column_described, field) == value)
                else:
                    # Exact match for other types
                    query = query.filter(getattr(query.column_described, field) == value)
        
        return query


def batch_query_processor(batch_size: int = 100):
    """
    Decorator to process queries in batches to avoid memory issues
    
    Args:
        batch_size: Number of items to process per batch
    """
    def decorator(func):
        @wraps(func)
        def wrapper(query_or_items, *args, **kwargs):
            # Check if it's a query object (has count, offset, limit, all methods)
            if hasattr(query_or_items, 'count') and hasattr(query_or_items, 'offset'):
                # It's a SQLAlchemy query
                offset = 0
                all_results = []
                
                while True:
                    batch = query_or_items.offset(offset).limit(batch_size).all()
                    if not batch:
                        break
                    
                    # Process this batch
                    batch_result = func(batch, *args, **kwargs)
                    all_results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                    
                    offset += batch_size
                    
                    # Safety check to prevent infinite loops
                    if len(batch) < batch_size:
                        break
                
                return all_results
            else:
                # It's a list or iterable
                items = list(query_or_items)
                all_results = []
                
                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    batch_result = func(batch, *args, **kwargs)
                    all_results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                
                return all_results
        return wrapper
    return decorator


def query_performance_logger(threshold_ms: float = 100.0):
    """
    Decorator to log slow queries
    
    Args:
        threshold_ms: Threshold in milliseconds to consider a query slow
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time_ms = (end_time - start_time) * 1000
            
            if execution_time_ms > threshold_ms:
                print(f"WARNING: Slow query detected in {func.__name__}: {execution_time_ms:.2f}ms")
            
            return result
        return wrapper
    return decorator


class NPlusOneQueryOptimizer:
    """Specific optimizer for N+1 query patterns"""
    
    @staticmethod
    def optimize_rule_based_queries(rules: List[Any], query_func, *args, **kwargs) -> List[Any]:
        """
        Optimize queries that iterate over rules and query for each one
        
        Args:
            rules: List of rule objects
            query_func: Function to query for each rule
            *args: Additional arguments for query function
            **kwargs: Additional keyword arguments for query function
            
        Returns:
            Combined results from all queries
        """
        # Instead of querying for each rule individually, batch the queries
        # This is a placeholder for the actual optimization logic
        results = []
        
        for rule in rules:
            result = query_func(rule, *args, **kwargs)
            results.append(result)
        
        return results
    
    @staticmethod
    def optimize_with_batching(items: List[Any], batch_query_func, batch_size: int = 50) -> List[Any]:
        """
        Optimize queries by batching multiple items into single queries
        
        Args:
            items: List of items to query for
            batch_query_func: Function that can handle batched queries
            batch_size: Number of items to process per batch
            
        Returns:
            Combined results from all batches
        """
        all_results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = batch_query_func(batch)
            all_results.extend(batch_results)
        
        return all_results


class QueryCache:
    """Simple query result cache"""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize query cache
        
        Args:
            ttl: Time to live for cached results in seconds
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result if still valid"""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Cache a result"""
        self.cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Clear all cached results"""
        self.cache.clear()
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern"""
        import fnmatch
        keys_to_delete = [k for k in self.cache.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            del self.cache[key]
        return len(keys_to_delete)


# Global query cache instance
query_cache = QueryCache()


def cached_query(ttl: int = 300):
    """
    Decorator to cache query results
    
    Args:
        ttl: Time to live for cached results in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}_{str(args)}_{str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached_result = query_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute query
            result = func(*args, **kwargs)
            
            # Cache the result
            query_cache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator


# Export commonly used utilities
__all__ = [
    "QueryOptimizer",
    "batch_query_processor",
    "query_performance_logger",
    "NPlusOneQueryOptimizer",
    "QueryCache",
    "query_cache",
    "cached_query",
]