# -*- coding: utf-8 -*-
"""
性能监控器
Performance Monitor

提供核心性能监控，记录执行时间、错误率等指标。
"""

import time
import threading
from typing import Dict, Any, List


class PerformanceMonitor:
    """
    性能监控器
    
    记录执行时间、错误率等核心性能指标。
    """
    
    def __init__(self, max_samples: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_samples: 最大样本数
        """
        self.max_samples = max_samples
        self.metrics = {
            "execution_times": [],
            "error_count": 0,
            "timeout_count": 0,
            "total_requests": 0
        }
        self._lock = threading.Lock()
    
    def record_execution(self, duration: float, success: bool, timeout: bool = False):
        """
        记录执行
        
        Args:
            duration: 执行时间（秒）
            success: 是否成功
            timeout: 是否超时
        """
        with self._lock:
            self.metrics["execution_times"].append(duration)
            self.metrics["total_requests"] += 1
            
            if not success:
                self.metrics["error_count"] += 1
            
            if timeout:
                self.metrics["timeout_count"] += 1
            
            # 保持样本数量在限制内
            if len(self.metrics["execution_times"]) > self.max_samples:
                self.metrics["execution_times"].pop(0)
    
    def get_summary(self) -> Dict[str, float]:
        """
        获取性能摘要
        
        Returns:
            性能摘要字典
        """
        with self._lock:
            if not self.metrics["execution_times"]:
                return {
                    "avg_time": 0.0,
                    "p95_time": 0.0,
                    "p99_time": 0.0,
                    "error_rate": 0.0,
                    "timeout_rate": 0.0,
                    "total_requests": 0
                }
            
            execution_times = self.metrics["execution_times"]
            total_requests = self.metrics["total_requests"]
            
            return {
                "avg_time": sum(execution_times) / len(execution_times),
                "p95_time": self._percentile(execution_times, 95),
                "p99_time": self._percentile(execution_times, 99),
                "error_rate": self.metrics["error_count"] / max(total_requests, 1),
                "timeout_rate": self.metrics["timeout_count"] / max(total_requests, 1),
                "total_requests": total_requests
            }
    
    def _percentile(self, data: List[float], p: int) -> float:
        """
        计算百分位数
        
        Args:
            data: 数据列表
            p: 百分位数
        
        Returns:
            百分位数值
        """
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def reset(self):
        """重置监控数据"""
        with self._lock:
            self.metrics = {
                "execution_times": [],
                "error_count": 0,
                "timeout_count": 0,
                "total_requests": 0
            }