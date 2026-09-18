# -*- coding: utf-8 -*-
"""
降级策略
Degradation Strategy

提供二级降级策略，当系统健康状态不佳时自动降级。
"""

import time
import threading
from typing import Dict, Any


class DegradationStrategy:
    """
    降级策略
    
    提供二级降级策略（full/minimal），当系统健康状态不佳时自动降级。
    """
    
    LEVELS = {
        "full": {
            "timeout": True,
            "validation": True,
            "whitelist": True,
            "progress": False,
            "stall_detection": False
        },
        "minimal": {
            "timeout": True,
            "validation": False,
            "whitelist": False,
            "progress": False,
            "stall_detection": False
        }
    }
    
    def __init__(self, initial_level: str = "full"):
        """
        初始化降级策略
        
        Args:
            initial_level: 初始级别
        """
        self.current_level = initial_level
        self.health_checker = HealthChecker()
        self._lock = threading.Lock()
    
    def check_and_degrade(self) -> str:
        """
        检查健康状态并降级
        
        Returns:
            当前级别
        """
        with self._lock:
            health = self.health_checker.check()
            
            if health["status"] == "critical" and self.current_level != "minimal":
                self.current_level = "minimal"
                print(f"降级到minimal级别: {health['reason']}")
            elif health["status"] == "warning" and self.current_level == "full":
                self.current_level = "minimal"
                print(f"降级到minimal级别: {health['reason']}")
            
            return self.current_level
    
    def get_current_level(self) -> str:
        """
        获取当前级别
        
        Returns:
            当前级别
        """
        with self._lock:
            return self.current_level
    
    def get_level_config(self) -> Dict[str, bool]:
        """
        获取当前级别的配置
        
        Returns:
            当前级别的功能配置
        """
        with self._lock:
            return self.LEVELS.get(self.current_level, self.LEVELS["minimal"])
    
    def manual_degrade(self, level: str) -> bool:
        """
        手动降级
        
        Args:
            level: 目标级别
        
        Returns:
            是否成功
        """
        with self._lock:
            if level in self.LEVELS:
                self.current_level = level
                return True
            return False


class HealthChecker:
    """
    健康检查器
    
    检查系统健康状态，为降级策略提供依据。
    """
    
    def __init__(self):
        """初始化健康检查器"""
        self.error_count = 0
        self.total_requests = 0
        self.last_check_time = time.time()
        self._lock = threading.Lock()
    
    def check(self) -> Dict[str, Any]:
        """
        检查健康状态
        
        Returns:
            健康状态字典
        """
        with self._lock:
            self.total_requests += 1
            error_rate = self.error_count / max(self.total_requests, 1)
            
            # 综合评估
            if error_rate > 0.5:
                return {
                    "status": "critical",
                    "reason": f"错误率过高: {error_rate:.2%}",
                    "error_rate": error_rate
                }
            elif error_rate > 0.2:
                return {
                    "status": "warning",
                    "reason": f"错误率偏高: {error_rate:.2%}",
                    "error_rate": error_rate
                }
            else:
                return {
                    "status": "healthy",
                    "reason": "系统健康",
                    "error_rate": error_rate
                }
    
    def record_error(self):
        """记录错误"""
        with self._lock:
            self.error_count += 1
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self.total_requests += 1
    
    def reset(self):
        """重置统计"""
        with self._lock:
            self.error_count = 0
            self.total_requests = 0