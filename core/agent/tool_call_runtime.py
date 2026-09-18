# -*- coding: utf-8 -*-
"""
工具调用运行时
Tool Call Runtime

提供基于Semaphore的并发控制，避免RwLock死锁问题。
"""

import threading
from contextlib import contextmanager
from typing import Dict


class ToolCallRuntime:
    """
    工具调用运行时
    
    使用Semaphore代替RwLock，避免重入工具调用在同一个锁上死锁。
    基于GitHub上CodeWhale项目的经验，Semaphore(1)比RwLock更安全。
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        初始化工具调用运行时
        
        Args:
            max_concurrent: 最大并发数，默认10
        """
        self.semaphore = threading.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.active_executions: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def acquire_execution_slot(self, tool_name: str):
        """
        获取执行槽位
        
        Args:
            tool_name: 工具名称
        """
        self.semaphore.acquire()
        
        with self._lock:
            self.active_executions[tool_name] = self.active_executions.get(tool_name, 0) + 1
        
        try:
            yield
        finally:
            with self._lock:
                self.active_executions[tool_name] = self.active_executions.get(tool_name, 0) - 1
                if self.active_executions[tool_name] == 0:
                    del self.active_executions[tool_name]
            
            self.semaphore.release()
    
    def get_active_count(self, tool_name: str) -> int:
        """
        获取工具的活跃执行数
        
        Args:
            tool_name: 工具名称
        
        Returns:
            活跃执行数
        """
        with self._lock:
            return self.active_executions.get(tool_name, 0)
    
    def get_all_active_counts(self) -> Dict[str, int]:
        """
        获取所有工具的活跃执行数
        
        Returns:
            工具名称到活跃执行数的映射
        """
        with self._lock:
            return self.active_executions.copy()
    
    def get_concurrency_stats(self) -> Dict[str, any]:
        """
        获取并发统计信息
        
        Returns:
            并发统计信息字典
        """
        with self._lock:
            total_active = sum(self.active_executions.values())
            return {
                "max_concurrent": self.max_concurrent,
                "total_active": total_active,
                "available_slots": self.max_concurrent - total_active,
                "active_by_tool": self.active_executions.copy()
            }