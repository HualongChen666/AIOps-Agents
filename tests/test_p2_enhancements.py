# -*- coding: utf-8 -*-
"""
P2 Enhancement: Enhanced Integration Tests
提高集成测试覆盖率，覆盖P0和P1增强功能
"""

import asyncio  # noqa: F401
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ========================================
# P0 Enhancement Tests
# ========================================


class TestAuthenticationEnhancements:
    """测试认证增强功能"""

    @pytest.mark.asyncio
    async def test_jwt_with_jti_claim(self):
        """测试JWT包含jti声明"""
        from core.authentication import create_access_token

        token_data = {"sub": "test_user", "jti": "unique_token_id"}
        token = create_access_token(token_data)

        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_ip_whitelist_validation(self):
        """测试IP白名单验证"""
        from core.authentication import is_ip_allowed

        # 测试允许的IP（通过环境变量明确指定）
        with patch.dict(os.environ, {"IP_WHITELIST": "127.0.0.1,192.168.1.100"}):
            assert is_ip_allowed("192.168.1.100")
            assert is_ip_allowed("127.0.0.1")

        # 测试不允许的IP
        with patch.dict(os.environ, {"IP_WHITELIST": "192.168.1.0/24"}):
            assert is_ip_allowed("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_token_revocation_with_jti(self):
        """测试基于jti的令牌撤销"""
        from core.authentication import is_token_revoked, revoke_token

        jti = "test_token_id_123"
        revoke_token(jti)
        assert is_token_revoked(jti)


class TestInputValidation:
    """测试输入验证功能"""

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        from core.input_validator import validate_and_clean_input

        malicious_input = "'; DROP TABLE users; --"
        cleaned = validate_and_clean_input(malicious_input)

        assert "DROP TABLE" not in cleaned
        assert cleaned != malicious_input

    @pytest.mark.asyncio
    async def test_xss_prevention(self):
        """测试XSS防护"""
        from core.input_validator import validate_and_clean_input

        xss_input = "<script>alert('xss')</script>"
        cleaned = validate_and_clean_input(xss_input)

        assert "<script>" not in cleaned
        assert "alert" not in cleaned

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """测试路径遍历防护"""
        from core.input_validator import validate_and_clean_input

        malicious_path = "../../../etc/passwd"
        cleaned = validate_and_clean_input(malicious_path)

        assert ".." not in cleaned


class TestAuditLogging:
    """测试审计日志增强功能"""

    @pytest.mark.asyncio
    async def test_security_event_detection(self):
        """测试安全事件检测"""
        from core.audit_service import detect_security_event

        # 测试检测到的安全事件
        event = detect_security_event("login_failure", {"ip": "192.168.1.100"})
        assert event is not None
        assert event["severity"] in ["warning", "critical"]

    @pytest.mark.asyncio
    async def test_log_integrity_verification(self):
        """测试日志完整性验证"""
        from core.audit_service import verify_log_integrity

        log_entry = {"message": "test", "hash": "test_hash"}
        is_valid = verify_log_integrity(log_entry)

        assert isinstance(is_valid, bool)


class TestRetryMechanism:
    """测试增强的重试机制"""

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """测试指数退避"""
        from core.retry_enhanced import EnhancedRetry

        retry = EnhancedRetry(max_attempts=3, base_delay=0.1, strategy="exponential_backoff")

        delays = [retry.calculate_delay(i) for i in range(1, 4)]
        assert delays[1] > delays[0]  # 指数增长
        assert delays[2] > delays[1]

    @pytest.mark.asyncio
    async def test_jitter_addition(self):
        """测试抖动添加"""
        from core.retry_enhanced import EnhancedRetry

        retry = EnhancedRetry(max_attempts=3, base_delay=1.0, jitter=True)

        delay1 = retry.calculate_delay(1)
        delay2 = retry.calculate_delay(1)

        # 由于抖动，两次计算的延迟应该不同
        assert delay1 != delay2


class TestRateLimiting:
    """测试增强的限流功能"""

    @pytest.mark.asyncio
    async def test_sliding_window_rate_limit(self):
        """测试滑动窗口限流"""
        from core.rate_limiter import AdvancedRateLimiter

        limiter = AdvancedRateLimiter()

        # 测试限流
        for i in range(5):
            allowed, _ = await limiter.check_rate_limit_advanced("test_key", 3, 60)
            if i < 3:
                assert allowed
            else:
                assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_stats(self):
        """测试限流统计"""
        from core.rate_limiter import AdvancedRateLimiter

        limiter = AdvancedRateLimiter()
        stats = limiter.get_stats("test_key")

        assert "request_count" in stats
        assert "is_blocked" in stats


class TestBackupStrategy:
    """测试备份策略功能"""

    @pytest.mark.asyncio
    async def test_backup_integrity_check(self):
        """测试备份完整性检查"""
        # 创建临时文件用于测试
        import tempfile

        from core.backup_strategy import calculate_file_hash, verify_backup_integrity

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            hash_value = calculate_file_hash(temp_file)
            is_valid = verify_backup_integrity(temp_file, hash_value)
            assert is_valid
        finally:
            os.unlink(temp_file)


class TestHealthCheck:
    """测试健康检查增强功能"""

    @pytest.mark.asyncio
    async def test_system_resources_check(self):
        """测试系统资源检查"""
        from core.health_check import check_system_resources

        result = await check_system_resources()

        assert "status" in result
        assert "metrics" in result
        assert "cpu_percent" in result["metrics"]
        assert "memory_percent" in result["metrics"]

    @pytest.mark.asyncio
    async def test_health_trend_analysis(self):
        """测试健康趋势分析"""
        # 添加一些历史数据
        from core.health_check import _analyze_health_trend, _health_history

        _health_history.extend(
            [
                {"overall_status": "healthy", "timestamp": datetime.utcnow().isoformat()}
                for _ in range(10)
            ]
        )

        trend = _analyze_health_trend()
        assert "trend" in trend
        assert trend["trend"] in ["improving", "stable", "deteriorating"]


# ========================================
# P1 Enhancement Tests
# ========================================


class TestAPMMetrics:
    """测试APM指标功能"""

    @pytest.mark.asyncio
    async def test_apm_metric_recording(self):
        """测试APM指标记录"""
        from core.telemetry import get_apm_metrics, record_apm_metric

        record_apm_metric("request_count", 1.0)
        record_apm_metric("error_count", 0.0)

        metrics = get_apm_metrics()
        assert metrics["request_count"] >= 1

    @pytest.mark.asyncio
    async def test_apm_metric_reset(self):
        """测试APM指标重置"""
        from core.telemetry import get_apm_metrics, reset_apm_metrics

        reset_apm_metrics()
        metrics = get_apm_metrics()

        assert metrics["request_count"] == 0
        assert metrics["error_count"] == 0


class TestAIEnhancement:
    """测试AI分析增强功能"""

    @pytest.mark.asyncio
    async def test_context_key_generation(self):
        """测试上下文键生成"""
        from core.ai_enhancement import AIAnalysisEnhancer

        enhancer = AIAnalysisEnhancer()
        alert_data = {
            "host": "server-01",
            "platform": "linux",
            "level": "warning",
            "message": "CPU high",
        }

        key1 = enhancer.generate_context_key(alert_data)
        key2 = enhancer.generate_context_key(alert_data)

        # 相同输入应该生成相同的键
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_analysis_caching(self):
        """测试分析缓存"""
        from core.ai_enhancement import AIAnalysisEnhancer

        enhancer = AIAnalysisEnhancer()
        alert_data = {"host": "server-01", "platform": "linux"}
        key = enhancer.generate_context_key(alert_data)

        analysis = {"result": "test_analysis"}
        enhancer.cache_analysis(key, analysis)

        cached = enhancer.get_cached_analysis(key)
        assert cached == analysis

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self):
        """测试性能指标跟踪"""
        from core.ai_enhancement import AIAnalysisEnhancer

        enhancer = AIAnalysisEnhancer()
        enhancer.update_performance_metrics(
            {"success": True, "response_time": 1.5, "model": "gpt-4"}
        )

        metrics = enhancer.get_performance_metrics()
        assert metrics["total_analyses"] >= 1
        assert "gpt-4" in metrics["model_usage"]


class TestConversationManager:
    """测试多轮对话管理"""

    @pytest.mark.asyncio
    async def test_conversation_creation(self):
        """测试对话创建"""
        from core.ai_enhancement import MultiTurnConversationManager

        manager = MultiTurnConversationManager()
        conv_id = manager.create_conversation("conv-001")

        assert conv_id == "conv-001"

    @pytest.mark.asyncio
    async def test_message_adding(self):
        """测试消息添加"""
        from core.ai_enhancement import MultiTurnConversationManager

        manager = MultiTurnConversationManager()
        manager.create_conversation("conv-001")

        manager.add_message("conv-001", "user", "Hello")
        history = manager.get_conversation_history("conv-001")

        assert len(history) == 1
        assert history[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_conversation_context(self):
        """测试对话上下文获取"""
        from core.ai_enhancement import MultiTurnConversationManager

        manager = MultiTurnConversationManager()
        manager.create_conversation("conv-001")

        manager.add_message("conv-001", "user", "Hello")
        manager.add_message("conv-001", "assistant", "Hi there")

        context = manager.get_conversation_context("conv-001")
        assert "user: Hello" in context
        assert "assistant: Hi there" in context


# ========================================
# Database Optimization Tests
# ========================================


class TestDatabaseOptimization:
    """测试数据库优化功能"""

    @pytest.mark.asyncio
    async def test_index_creation_simulation(self):
        """测试索引创建（模拟）"""
        from core.db_optimization import PERFORMANCE_INDEXES  # noqa: F401

        # 验证索引定义存在
        assert len(PERFORMANCE_INDEXES) > 0

        # 验证索引包含必要的字段
        for index in PERFORMANCE_INDEXES:
            assert hasattr(index, "name")
            assert hasattr(index, "table")

    @pytest.mark.asyncio
    async def test_query_performance_analysis_structure(self):
        """测试查询性能分析结构"""
        # 这个测试验证分析函数的结构，不需要实际数据库
        from core.db_optimization import QUERY_PERFORMANCE_THRESHOLDS

        assert "slow_query_ms" in QUERY_PERFORMANCE_THRESHOLDS
        assert "very_slow_query_ms" in QUERY_PERFORMANCE_THRESHOLDS


# ========================================
# Cache Enhancement Tests
# ========================================


class TestCacheEnhancements:
    """测试缓存增强功能"""

    @pytest.mark.asyncio
    async def test_lru_cache_eviction(self):
        """测试LRU缓存逐出"""
        from core.cache_helpers import LRUCache

        cache = LRUCache(max_size=3, ttl_sec=60)

        # 添加超过容量的项目
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")

        # 最旧的项目应该被逐出
        assert cache.get("key1") is None
        assert cache.get("key4") is not None

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """测试缓存统计"""
        from core.cache_helpers import LRUCache

        cache = LRUCache(max_size=10, ttl_sec=60)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert stats["hits"] >= 1


# ========================================
# Connection Pool Tests
# ========================================


class TestConnectionPoolOptimization:
    """测试连接池优化功能"""

    @pytest.mark.asyncio
    async def test_pool_recommendations(self):
        """测试连接池配置建议"""
        from core.connection_pool_optimization import get_connection_pool_recommendations

        # 测试不同工作负载的建议
        rec_read = get_connection_pool_recommendations("read_heavy")
        rec_write = get_connection_pool_recommendations("write_heavy")

        assert "pool_size" in rec_read
        assert "pool_size" in rec_write
        assert rec_read["pool_size"] >= rec_write["pool_size"]


# ========================================
# Performance Tuning Tests
# ========================================


class TestPerformanceTuning:
    """测试性能调优功能"""

    @pytest.mark.asyncio
    async def test_performance_recommendations(self):
        """测试性能建议"""
        from core.performance_tuning import get_performance_recommendations

        recs = get_performance_recommendations()

        assert "system_info" in recs
        assert "recommendations" in recs
        assert isinstance(recs["recommendations"], list)

    @pytest.mark.asyncio
    async def test_metrics_monitoring(self):
        """测试性能指标监控"""
        from core.performance_tuning import monitor_performance_metrics

        metrics = monitor_performance_metrics()

        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
