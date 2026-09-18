# -*- coding: utf-8 -*-
"""
进度跟踪器
Progress Tracker

跟踪子agent的执行进度，提供进度信息显示。
基于GitHub上Hermes Agent项目的经验，显示子agent进度对用户体验很重要。
"""

import time
import threading
from typing import Dict, Any, Optional


class ProgressTracker:
    """
    进度跟踪器
    
    跟踪子agent的执行进度，提供进度信息显示。
    """
    
    def __init__(self):
        """初始化进度跟踪器"""
        self.active_children: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def register_child(self, child_id: str, task: str):
        """
        注册子agent
        
        Args:
            child_id: 子agent ID
            task: 任务描述
        """
        with self._lock:
            self.active_children[child_id] = {
                "task": task,
                "status": "running",
                "start_time": time.time(),
                "end_time": None
            }
    
    def update_child_status(self, child_id: str, status: str):
        """
        更新子agent状态
        
        Args:
            child_id: 子agent ID
            status: 状态（running/completed/failed/timeout）
        """
        with self._lock:
            if child_id in self.active_children:
                self.active_children[child_id]["status"] = status
                if status in ["completed", "failed", "timeout"]:
                    self.active_children[child_id]["end_time"] = time.time()
    
    def unregister_child(self, child_id: str):
        """
        注销子agent
        
        Args:
            child_id: 子agent ID
        """
        with self._lock:
            self.active_children.pop(child_id, None)
    
    def get_progress(self) -> Dict[str, Any]:
        """
        获取进度信息
        
        Returns:
            进度信息字典
        """
        with self._lock:
            total = len(self.active_children)
            completed = sum(
                1 for c in self.active_children.values()
                if c["status"] == "completed"
            )
            failed = sum(
                1 for c in self.active_children.values()
                if c["status"] == "failed"
            )
            timeout = sum(
                1 for c in self.active_children.values()
                if c["status"] == "timeout"
            )
            running = total - completed - failed - timeout
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "timeout": timeout,
                "running": running,
                "children": self.active_children.copy()
            }
    
    def get_child_info(self, child_id: str) -> Optional[Dict[str, Any]]:
        """
        获取子agent信息
        
        Args:
            child_id: 子agent ID
        
        Returns:
            子agent信息或None
        """
        with self._lock:
            return self.active_children.get(child_id)
    
    def format_progress(self) -> str:
        """
        格式化进度信息
        
        Returns:
            格式化的进度字符串
        """
        progress = self.get_progress()
        return (
            f"[{progress['completed']}/{progress['total']} 子agent完成, "
            f"{progress['running']} 运行中, "
            f"{progress['failed']} 失败, "
            f"{progress['timeout']} 超时]"
        )