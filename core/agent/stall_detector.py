# -*- coding: utf-8 -*-
"""
停滞检测器
Stall Detector

检测工具执行是否停滞，用于超时监控。
"""

import time
import threading
from typing import Optional


class StallDetector:
    """
    停滞检测器
    
    检测工具执行是否在指定时间内没有任何活动。
    用于检测工具执行停滞，避免无限等待。
    """
    
    def __init__(self, stall_timeout: int = 120):
        """
        初始化停滞检测器
        
        Args:
            stall_timeout: 停滞超时时间（秒），默认120秒
        """
        self.stall_timeout = stall_timeout
        self.last_activity = time.time()
        self._lock = threading.Lock()
    
    def update_activity(self):
        """更新活动时间"""
        with self._lock:
            self.last_activity = time.time()
    
    def check_stall(self) -> bool:
        """
        检查是否停滞
        
        Returns:
            是否停滞（超过超时时间无活动）
        """
        with self._lock:
            elapsed = time.time() - self.last_activity
            return elapsed > self.stall_timeout
    
    def get_idle_time(self) -> float:
        """
        获取空闲时间
        
        Returns:
            空闲时间（秒）
        """
        with self._lock:
            return time.time() - self.last_activity
    
    def reset(self):
        """重置检测器"""
        with self._lock:
            self.last_activity = time.time()


class TimeoutError(Exception):
    """超时异常"""
    pass


class TimeoutContext:
    """
    超时上下文管理器
    
    管理超时的设置、触发和清理。
    """
    
    def __init__(self, timeout: int, task_id: str):
        """
        初始化超时上下文
        
        Args:
            timeout: 超时时间（秒）
            task_id: 任务ID
        """
        self.timeout = timeout
        self.task_id = task_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.timeout_triggered = False
        self.timeout_reason: Optional[str] = None
        self.thread_id = threading.get_ident()
    
    def check_timeout(self) -> bool:
        """
        检查是否超时
        
        Returns:
            是否超时
        """
        if self.timeout_triggered:
            return True
        
        elapsed = time.time() - self.start_time
        if elapsed > self.timeout:
            self.timeout_triggered = True
            self.end_time = time.time()
            self.timeout_reason = f"执行超时 ({elapsed:.1f}s > {self.timeout}s)"
            return True
        
        return False
    
    def get_timeout_info(self) -> dict:
        """
        获取超时信息
        
        Returns:
            超时信息字典
        """
        return {
            "task_id": self.task_id,
            "timeout": self.timeout,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed": (self.end_time or time.time()) - self.start_time,
            "timeout_triggered": self.timeout_triggered,
            "timeout_reason": self.timeout_reason,
            "thread_id": self.thread_id
        }