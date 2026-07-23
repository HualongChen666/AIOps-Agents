# -*- coding: utf-8 -*-
"""
L6 Execution Layer - Optimized Execution
Enhanced execution engine with performance optimizations
"""

from .optimized_executor import (
    ExecutionMetrics,
    OptimizedExecutor,
    get_optimized_executor,
    init_optimized_executor,
)

__all__ = [
    "OptimizedExecutor",
    "ExecutionMetrics",
    "get_optimized_executor",
    "init_optimized_executor",
]
