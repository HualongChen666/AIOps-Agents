# -*- coding: utf-8 -*-
"""
行为监控配置系统测试
Behavior Monitor Configuration System Tests

测试配置加载、验证、分析功能。
"""

import pytest
from behavior_monitor_config import BehaviorMonitorConfig, load_config, Environment, get_current_environment


class TestConfigLoading:
    """配置加载测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = BehaviorMonitorConfig()
        assert config.max_agents == 50
        assert config.ttl_days == 7
        assert config.min_samples_for_z_score == 30
        assert config.z_score_warning_threshold == 2.5

    def test_development_config(self):
        """测试开发环境配置"""
        config = load_config(Environment.DEVELOPMENT)
        assert config.max_agents == 20
        assert config.ttl_days == 1
        assert config.min_samples_for_z_score == 5
        assert config.min_days_for_time_window == 0

    def test_production_config(self):
        """测试生产环境配置"""
        config = load_config(Environment.PRODUCTION)
        assert config.max_agents == 100
        assert config.ttl_days == 7
        assert config.min_samples_for_z_score == 30
        assert config.min_days_for_time_window == 7

    def test_staging_config(self):
        """测试预发布环境配置"""
        config = load_config(Environment.STAGING)
        assert config.max_agents == 50
        assert config.ttl_days == 3
        assert config.min_samples_for_z_score == 20
        assert config.min_days_for_time_window == 3


class TestMonitoredMetrics:
    """监控指标配置测试"""

    def test_default_monitored_metrics(self):
        """测试默认监控指标配置"""
        config = BehaviorMonitorConfig()
        assert "iterations" in config.monitored_metrics
        assert "tool_calls" in config.monitored_metrics
        assert "errors" in config.monitored_metrics
        assert "execution_time" in config.monitored_metrics

    def test_iterations_metric_enabled(self):
        """测试iterations指标启用"""
        config = BehaviorMonitorConfig()
        assert config.monitored_metrics["iterations"]["enabled"] is True
        assert config.monitored_metrics["iterations"]["priority"] == "high"

    def test_execution_time_metric_disabled(self):
        """测试execution_time指标默认禁用"""
        config = BehaviorMonitorConfig()
        assert config.monitored_metrics["execution_time"]["enabled"] is False

    def test_z_score_thresholds_structure(self):
        """测试z-score阈值结构"""
        config = BehaviorMonitorConfig()
        thresholds = config.monitored_metrics["iterations"]["z_score_thresholds"]
        assert "warning" in thresholds
        assert "critical" in thresholds
        assert "fatal" in thresholds
        assert thresholds["warning"] < thresholds["critical"] < thresholds["fatal"]


class TestConfigValidator:
    """配置验证器测试"""

    def test_valid_config(self):
        """测试有效配置"""
        from core.agent.monitoring_config_validator import ConfigValidator

        config = BehaviorMonitorConfig()
        is_valid, errors = ConfigValidator.validate_config(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_max_agents(self):
        """测试无效的max_agents配置"""
        from core.agent.monitoring_config_validator import ConfigValidator

        config = BehaviorMonitorConfig()
        config.max_agents = -1
        is_valid, errors = ConfigValidator.validate_config(config)
        assert is_valid is False
        assert "max_agents必须大于0" in errors

    def test_invalid_z_score_thresholds(self):
        """测试无效的z-score阈值配置"""
        from core.agent.monitoring_config_validator import ConfigValidator

        config = BehaviorMonitorConfig()
        config.z_score_warning_threshold = 5.0
        config.z_score_critical_threshold = 3.0  # 不递增
        is_valid, errors = ConfigValidator.validate_config(config)
        assert is_valid is False
        # 修复：检查错误信息是否包含"递增"关键词
        assert any("递增" in error for error in errors)

    def test_invalid_confidence_threshold(self):
        """测试无效的置信度阈值配置"""
        from core.agent.monitoring_config_validator import ConfigValidator

        config = BehaviorMonitorConfig()
        config.confidence_threshold = 1.5  # 超过1
        is_valid, errors = ConfigValidator.validate_config(config)
        assert is_valid is False
        assert "confidence_threshold必须在0-1之间" in errors


class TestConfigAnalyzer:
    """配置分析器测试"""

    def test_memory_analysis(self):
        """测试内存需求分析"""
        from core.agent.monitoring_config_analyzer import ConfigAnalyzer

        config = BehaviorMonitorConfig()
        analysis = ConfigAnalyzer.analyze_memory_requirements(config)
        assert "estimated_per_agent_kb" in analysis
        assert "total_memory_mb" in analysis
        assert "recommendation" in analysis

    def test_time_window_analysis(self):
        """测试时间窗口合理性分析"""
        from core.agent.monitoring_config_analyzer import ConfigAnalyzer

        config = BehaviorMonitorConfig()
        analysis = ConfigAnalyzer.analyze_time_window_reasonableness(config)
        assert "configured_days" in analysis
        assert "closest_business_cycle" in analysis
        assert "is_aligned" in analysis

    def test_z_score_thresholds_analysis(self):
        """测试z-score阈值合理性分析"""
        from core.agent.monitoring_config_analyzer import ConfigAnalyzer

        config = BehaviorMonitorConfig()
        analysis = ConfigAnalyzer.analyze_z_score_thresholds(config)
        assert "warning_threshold" in analysis
        assert "warning_confidence" in analysis
        assert "critical_threshold" in analysis
        assert "fatal_threshold" in analysis


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
