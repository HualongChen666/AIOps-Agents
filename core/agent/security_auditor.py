# -*- coding: utf-8 -*-
"""
安全审计器
Security Auditor

提供安全审计日志和参数安全扫描功能。
"""

import time
import threading
from typing import Dict, Any, List


class SecurityAuditor:
    """
    安全审计器
    
    记录工具执行审计日志，用于安全审计和问题排查。
    """
    
    def __init__(self, max_logs: int = 1000):
        """
        初始化安全审计器
        
        Args:
            max_logs: 最大日志数量
        """
        self.max_logs = max_logs
        self.audit_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def log_execution(self, agent_id: str, tool_name: str, params: Dict[str, Any], success: bool):
        """
        记录工具执行
        
        Args:
            agent_id: agent ID
            tool_name: 工具名称
            params: 参数字典
            success: 是否成功
        """
        with self._lock:
            self.audit_log.append({
                "timestamp": time.time(),
                "agent_id": agent_id,
                "tool_name": tool_name,
                "params": self._sanitize_params(params),
                "success": success
            })
            
            # 保持日志数量在限制内
            if len(self.audit_log) > self.max_logs:
                self.audit_log.pop(0)
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理敏感参数
        
        Args:
            params: 参数字典
        
        Returns:
            清理后的参数字典
        """
        sensitive_keys = ["password", "token", "api_key", "secret", "key"]
        sanitized = params.copy()
        for key in sensitive_keys:
            if key in sanitized:
                sanitized[key] = "***REDACTED***"
        return sanitized
    
    def get_audit_report(self) -> Dict[str, Any]:
        """
        获取审计报告
        
        Returns:
            审计报告字典
        """
        with self._lock:
            if not self.audit_log:
                return {
                    "total_executions": 0,
                    "success_rate": 0.0,
                    "suspicious_activities": []
                }
            
            total = len(self.audit_log)
            success_count = sum(1 for log in self.audit_log if log["success"])
            
            return {
                "total_executions": total,
                "success_rate": success_count / total,
                "suspicious_activities": self._detect_suspicious_activities()
            }
    
    def _detect_suspicious_activities(self) -> List[Dict[str, Any]]:
        """
        检测可疑活动
        
        Returns:
            可疑活动列表
        """
        suspicious = []
        
        # 检测失败率过高的工具
        tool_stats = {}
        for log in self.audit_log:
            tool_name = log["tool_name"]
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {"total": 0, "failed": 0}
            tool_stats[tool_name]["total"] += 1
            if not log["success"]:
                tool_stats[tool_name]["failed"] += 1
        
        for tool_name, stats in tool_stats.items():
            if stats["total"] >= 10 and stats["failed"] / stats["total"] > 0.5:
                suspicious.append({
                    "type": "high_failure_rate",
                    "tool": tool_name,
                    "failure_rate": stats["failed"] / stats["total"]
                })
        
        return suspicious


class SecurityScanner:
    """
    安全扫描器
    
    扫描参数安全性，检测命令注入、路径穿越等安全问题。
    """
    
    def scan_params(self, tool_name: str, params: Dict[str, Any]) -> List[str]:
        """
        扫描参数安全性
        
        Args:
            tool_name: 工具名称
            params: 参数字典
        
        Returns:
            安全问题列表
        """
        issues = []
        
        # 命令注入检查
        if tool_name == "bash":
            command = params.get("command", "")
            if self._detect_command_injection(command):
                issues.append("Potential command injection detected")
        
        # 路径穿越检查
        if "file_path" in params:
            file_path = params["file_path"]
            if self._detect_path_traversal(file_path):
                issues.append("Potential path traversal detected")
        
        return issues
    
    def _detect_command_injection(self, command: str) -> bool:
        """
        检测命令注入
        
        Args:
            command: 命令字符串
        
        Returns:
            是否检测到命令注入
        """
        dangerous_chars = [";", "|", "&", "$", "`", "$(", "&&", "||", "\n", "\r"]
        return any(char in str(command) for char in dangerous_chars)
    
    def _detect_path_traversal(self, path: str) -> bool:
        """
        检测路径穿越
        
        Args:
            path: 路径字符串
        
        Returns:
            是否检测到路径穿越
        """
        return "../" in str(path) or "..\\" in str(path)