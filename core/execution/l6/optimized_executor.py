# -*- coding: utf-8 -*-
"""
L6 Execution Layer - Optimized Executor
Enhanced execution engine with performance optimizations and layer integration
"""

import asyncio
from datetime import datetime
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class ExecutionMetrics:
    """Execution metrics collection"""

    def __init__(self):
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_duration = 0.0
        self.avg_duration = 0.0
        self.cache_hits = 0
        self.cache_misses = 0

    def record_execution(self, success: bool, duration: float) -> None:
        """Record an execution"""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        self.total_duration += duration
        self.avg_duration = self.total_duration / self.total_executions

    def record_cache_hit(self) -> None:
        """Record a cache hit"""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss"""
        self.cache_misses += 1

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def get_success_rate(self) -> float:
        """Get success rate"""
        return (
            self.successful_executions / self.total_executions if self.total_executions > 0 else 0.0
        )


class OptimizedExecutor:
    """
    Optimized Executor for L6 Execution Layer

    This executor provides:
    - Caching for repeated operations
    - Async parallel execution
    - Integration with L2 Analysis Layer
    - Integration with L3 Processing Layer
    - Integration with L4 Storage Layer
    - Performance metrics
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config

        # Cache configuration
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_ttl = config.get("cache_ttl", 300)  # 5 minutes
        self.cache: Dict[str, tuple] = {}  # (value, timestamp)

        # Parallel execution configuration
        self.max_parallel_tasks = config.get("max_parallel_tasks", 5)

        # Layer integrations
        self.l2_enabled = config.get("l2_integration", True)
        self.l3_enabled = config.get("l3_integration", True)
        self.l4_enabled = config.get("l4_integration", True)

        # Metrics
        self.metrics = ExecutionMetrics()

        self._is_initialized = True
        logger.info("Optimized Executor initialized for L6 Layer")

    @lru_cache(maxsize=128)
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result with LRU cache"""
        if not self.cache_enabled:
            return None

        if cache_key in self.cache:
            value, timestamp = self.cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()

            if age < self.cache_ttl:
                self.metrics.record_cache_hit()
                return value
            else:
                # Cache expired
                del self.cache[cache_key]

        self.metrics.record_cache_miss()
        return None

    def _set_cached_result(self, cache_key: str, value: Any) -> None:
        """Set cached result"""
        if not self.cache_enabled:
            return

        self.cache[cache_key] = (value, datetime.now())

    async def execute_with_cache(
        self, operation: str, params: Dict[str, Any], handler: Callable[..., Any]
    ) -> Dict[str, Any]:
        """
        Execute operation with caching

        Args:
            operation: Operation name
            params: Operation parameters
            handler: Handler function

        Returns:
            Execution result
        """
        # Generate cache key
        cache_key = f"{operation}:{hash(str(params))}"

        # Check cache
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            logger.info(f"Cache hit for operation: {operation}")
            return cached_result  # type: ignore

        # Execute operation
        start_time = datetime.now()
        try:
            result = await handler(params)  # type: ignore
            duration = (datetime.now() - start_time).total_seconds()

            # Cache result
            self._set_cached_result(cache_key, result)

            # Record metrics
            self.metrics.record_execution(True, duration)

            return {"success": True, "result": result, "cached": False, "duration": duration}

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_execution(False, duration)
            logger.error(f"Execution failed: {e}")
            return {"success": False, "error": str(e), "duration": duration}

    async def execute_parallel(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute tasks in parallel

        Args:
            tasks: List of tasks with operation, params, handler

        Returns:
            List of execution results
        """
        # Create semaphore to limit parallelism
        semaphore = asyncio.Semaphore(self.max_parallel_tasks)

        async def execute_with_semaphore(task: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.execute_with_cache(
                    task["operation"], task["params"], task["handler"]
                )

        # Execute all tasks in parallel
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks], return_exceptions=True
        )

        # Handle exceptions
        processed_results: List[Dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({"success": False, "error": str(result)})
            else:
                processed_results.append(result)  # type: ignore

        return processed_results

    async def execute_with_l2_analysis(
        self, operation: str, params: Dict[str, Any], handler: Callable[..., Any]
    ) -> Dict[str, Any]:
        """
        Execute operation with L2 Analysis Layer integration

        Args:
            operation: Operation name
            params: Operation parameters
            handler: Handler function

        Returns:
            Execution result with analysis
        """
        if not self.l2_enabled:
            return await self.execute_with_cache(operation, params, handler)

        # Get L2 analysis components
        try:
            from core.analysis.l2.model_router import get_model_router
            from core.analysis.l2.rag_engine import get_rag_engine

            rag_engine = get_rag_engine()
            model_router = get_model_router()

            # Use RAG to enhance execution context
            if rag_engine:
                context_enhancement = await rag_engine.retrieve_knowledge(
                    query=operation, limit=3
                )  # type: ignore[attr-defined]
                params["context_enhancement"] = context_enhancement

            # Use model router to select optimal model
            if model_router:
                selected_model = model_router.select_model(operation, params)
                params["selected_model"] = selected_model

        except Exception as e:
            logger.warning(f"L2 integration failed: {e}")

        # Execute operation
        return await self.execute_with_cache(operation, params, handler)

    async def execute_with_l3_workflow(
        self, workflow_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute operation with L3 Processing Layer workflow integration

        Args:
            workflow_name: Workflow name
            context: Workflow context

        Returns:
            Workflow execution result
        """
        if not self.l3_enabled:
            return {"error": "L3 integration not enabled"}

        try:
            from core.processing.l3.workflow_engine import get_workflow_engine

            workflow_engine = get_workflow_engine()
            if not workflow_engine:
                return {"error": "Workflow engine not initialized"}

            result = await workflow_engine.execute_workflow(workflow_name, context)
            return result  # type: ignore

        except Exception as e:
            logger.error(f"L3 workflow execution failed: {e}")
            return {"error": str(e)}

    async def execute_with_l4_storage(
        self, operation: str, result: Any, metadata: Dict[str, Any]
    ) -> None:
        """
        Store execution result in L4 Storage Layer

        Args:
            operation: Operation name
            result: Execution result
            metadata: Additional metadata
        """
        if not self.l4_enabled:
            return

        try:
            from core.storage.l4.storage_manager import get_l4_storage_manager

            storage_manager = get_l4_storage_manager()
            if not storage_manager:
                logger.warning("L4 Storage Manager not initialized")
                return

            # Store metrics using VictoriaMetrics
            if "metrics" in metadata and storage_manager.victoriametrics:
                await storage_manager.victoriametrics.store(
                    operation, metadata["metrics"]
                )  # type: ignore[attr-defined]

            # Store logs using Loki
            if "logs" in metadata and storage_manager.loki:
                # type: ignore[attr-defined]
                await storage_manager.loki.store(operation, metadata["logs"])

            logger.info(f"Stored execution result in L4 Storage: {operation}")

        except Exception as e:
            logger.warning(f"L4 storage integration failed: {e}")

    def clear_cache(self) -> None:
        """Clear the execution cache"""
        self.cache.clear()
        logger.info("Execution cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        return {
            "total_executions": self.metrics.total_executions,
            "successful_executions": self.metrics.successful_executions,
            "failed_executions": self.metrics.failed_executions,
            "success_rate": self.metrics.get_success_rate(),
            "avg_duration": self.metrics.avg_duration,
            "cache_hit_rate": self.metrics.get_cache_hit_rate(),
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "cache_size": len(self.cache),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get executor status"""
        return {
            "initialized": self._is_initialized,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "max_parallel_tasks": self.max_parallel_tasks,
            "l2_integration": self.l2_enabled,
            "l3_integration": self.l3_enabled,
            "l4_integration": self.l4_enabled,
        }


# Global singleton instance
_optimized_executor: Optional[OptimizedExecutor] = None


def get_optimized_executor() -> Optional[OptimizedExecutor]:
    """Get global optimized executor instance"""
    return _optimized_executor


def init_optimized_executor(config: Dict[str, Any]) -> OptimizedExecutor:
    """Initialize global optimized executor"""
    global _optimized_executor
    _optimized_executor = OptimizedExecutor(config)
    return _optimized_executor
