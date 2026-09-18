# -*- coding: utf-8 -*-
"""
增强优化测试
Enhanced Optimization Tests

测试功能开关、降级策略、性能监控、安全加固等增强优化功能。
"""

import pytest
import time
from core.agent.feature_flags import FeatureFlags
from core.agent.degradation_strategy import DegradationStrategy, HealthChecker
from core.agent.performance_monitor import PerformanceMonitor
from core.agent.security_auditor import SecurityAuditor, SecurityScanner


class TestFeatureFlags:
    """功能开关测试"""
    
    def test_timeout_enabled(self):
        """测试超时功能开关"""
        flags = FeatureFlags()
        result = flags.is_timeout_enabled()
        assert isinstance(result, bool)
    
    def test_validation_enabled(self):
        """测试参数验证功能开关"""
        flags = FeatureFlags()
        result = flags.is_validation_enabled()
        assert isinstance(result, bool)
    
    def test_whitelist_enabled(self):
        """测试白名单功能开关"""
        flags = FeatureFlags()
        result = flags.is_whitelist_enabled()
        assert isinstance(result, bool)
    
    def test_get_enabled_features(self):
        """测试获取启用的功能"""
        flags = FeatureFlags()
        enabled = flags.get_enabled_features()
        assert isinstance(enabled, list)
        assert all(isinstance(f, str) for f in enabled)
    
    def test_get_disabled_features(self):
        """测试获取禁用的功能"""
        flags = FeatureFlags()
        disabled = flags.get_disabled_features()
        assert isinstance(disabled, list)
        assert all(isinstance(f, str) for f in disabled)


class TestDegradationStrategy:
    """降级策略测试"""
    
    def test_initial_level(self):
        """测试初始级别"""
        strategy = DegradationStrategy(initial_level="full")
        assert strategy.get_current_level() == "full"
    
    def test_manual_degrade(self):
        """测试手动降级"""
        strategy = DegradationStrategy()
        success = strategy.manual_degrade("minimal")
        assert success is True
        assert strategy.get_current_level() == "minimal"
    
    def test_invalid_level(self):
        """测试无效级别"""
        strategy = DegradationStrategy()
        success = strategy.manual_degrade("invalid")
        assert success is False
    
    def test_get_level_config(self):
        """测试获取级别配置"""
        strategy = DegradationStrategy()
        config = strategy.get_level_config()
        assert isinstance(config, dict)
        assert "timeout" in config
        assert "validation" in config
    
    def test_health_check(self):
        """测试健康检查"""
        checker = HealthChecker()
        health = checker.check()
        assert "status" in health
        assert health["status"] in ["healthy", "warning", "critical"]


class TestPerformanceMonitor:
    """性能监控测试"""
    
    def test_record_execution(self):
        """测试记录执行"""
        monitor = PerformanceMonitor()
        monitor.record_execution(0.1, True)
        
        summary = monitor.get_summary()
        assert summary["total_requests"] == 1
        assert summary["avg_time"] == 0.1
    
    def test_record_error(self):
        """测试记录错误"""
        monitor = PerformanceMonitor()
        monitor.record_execution(0.1, False)
        
        summary = monitor.get_summary()
        assert summary["error_rate"] == 1.0
    
    def test_record_timeout(self):
        """测试记录超时"""
        monitor = PerformanceMonitor()
        monitor.record_execution(0.1, False, timeout=True)
        
        summary = monitor.get_summary()
        assert summary["timeout_rate"] == 1.0
    
    def test_percentile_calculation(self):
        """测试百分位数计算"""
        monitor = PerformanceMonitor()
        
        # 记录多个执行时间
        for i in range(100):
            monitor.record_execution(i * 0.01, True)
        
        summary = monitor.get_summary()
        assert summary["p95_time"] > 0
        assert summary["p99_time"] > summary["p95_time"]
    
    def test_reset(self):
        """测试重置"""
        monitor = PerformanceMonitor()
        monitor.record_execution(0.1, True)
        
        monitor.reset()
        summary = monitor.get_summary()
        assert summary["total_requests"] == 0


class TestSecurityAuditor:
    """安全审计器测试"""
    
    def test_log_execution(self):
        """测试记录执行"""
        auditor = SecurityAuditor()
        auditor.log_execution("agent_1", "bash", {"command": "ls"}, True)
        
        report = auditor.get_audit_report()
        assert report["total_executions"] == 1
        assert report["success_rate"] == 1.0
    
    def test_sanitize_params(self):
        """测试参数清理"""
        auditor = SecurityAuditor()
        auditor.log_execution("agent_1", "bash", {"password": "secret"}, True)
        
        report = auditor.get_audit_report()
        # 密码应该被清理
        assert "secret" not in str(report)
    
    def test_suspicious_activity_detection(self):
        """测试可疑活动检测"""
        auditor = SecurityAuditor()
        
        # 记录多次失败
        for i in range(10):
            auditor.log_execution("agent_1", "bash", {"command": "ls"}, False)
        
        report = auditor.get_audit_report()
        # 应该检测到高失败率
        assert len(report["suspicious_activities"]) > 0


class TestSecurityScanner:
    """安全扫描器测试"""
    
    def test_command_injection_detection(self):
        """测试命令注入检测"""
        scanner = SecurityScanner()
        issues = scanner.scan_params("bash", {"command": "ls; rm -rf /"})
        
        assert len(issues) > 0
        assert "command injection" in issues[0].lower()
    
    def test_path_traversal_detection(self):
        """测试路径穿越检测"""
        scanner = SecurityScanner()
        issues = scanner.scan_params("read_file", {"file_path": "../../../etc/passwd"})
        
        assert len(issues) > 0
        assert "path traversal" in issues[0].lower()
    
    def test_safe_params(self):
        """测试安全参数"""
        scanner = SecurityScanner()
        issues = scanner.scan_params("bash", {"command": "ls"})
        
        # 安全参数应该没有问题
        assert len(issues) == 0
    
    def test_pipe_injection(self):
        """测试管道注入检测"""
        scanner = SecurityScanner()
        issues = scanner.scan_params("bash", {"command": "cat file | grep test"})
        
        assert len(issues) > 0
    
    def test_ampersand_injection(self):
        """测试&注入检测"""
        scanner = SecurityScanner()
        issues = scanner.scan_params("bash", {"command": "ls && rm file"})
        
        assert len(issues) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])