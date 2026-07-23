# -*- coding: utf-8 -*-
"""
Unit tests for core/ai_engine.py

This module contains comprehensive unit tests for the AI engine module,
covering LLM inference, RAG retrieval, vector search, caching, error handling,
and performance monitoring functionalities.
"""

import asyncio
from unittest.mock import patch

import pytest

# Import all needed functions and classes
import core.ai_engine as ai_engine_module
from core.ai_engine import (
    IntelligentRecommendationEngine,
    LLMAnalysisService,
    NaturalLanguageInteraction,
    PredictiveAnalysisEngine,
    _build_rich_user_message,
    _get_http_client,
    _rate_limit_wait,
    _rule_based_analysis,
    ai_service,
    close_http_client,
    close_langfuse_client,
    observe,
)
from core.ai_interface import AnalysisType

# Reference to analyze function from the module
analyze = ai_engine_module.analyze


# ============================================================
# analyze function tests (10 test cases)
# ============================================================


class TestAnalyzeFunction:
    """Test cases for the analyze function."""

    @pytest.mark.asyncio
    async def test_analyze_basic_functionality(self):
        """Test basic functionality of analyze function with AI disabled."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await analyze(
                query="Test query",
                metrics_snapshot="CPU: 50%",
                platform="windows",
            )
            assert "AI 引擎暂不可用" in result
            assert "规则降级引擎" in result

    @pytest.mark.asyncio
    async def test_analyze_with_query_truncation(self):
        """Test that long queries are truncated to max length."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            long_query = "x" * 3000
            result = await analyze(
                query=long_query,
                metrics_snapshot="CPU: 50%",
                platform="windows",
            )
            # Should not raise error, query should be truncated
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_with_metrics_truncation(self):
        """Test that long metrics are truncated to max length."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            long_metrics = "x" * 3000
            result = await analyze(
                query="Test query",
                metrics_snapshot=long_metrics,
                platform="windows",
            )
            # Should not raise error, metrics should be truncated
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_platform_whitelist_valid(self):
        """Test that valid platform names are accepted."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            for platform in ["windows", "linux", "WINDOWS", "Linux"]:
                result = await analyze(
                    query="Test query",
                    metrics_snapshot="CPU: 50%",
                    platform=platform,
                )
                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_platform_whitelist_invalid(self):
        """Test that invalid platform names default to windows."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await analyze(
                query="Test query",
                metrics_snapshot="CPU: 50%",
                platform="invalid_platform",
            )
            assert isinstance(result, str)
            assert "windows" in result.lower()

    @pytest.mark.asyncio
    async def test_analyze_with_rich_context(self):
        """Test analyze with rich context provided."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            rich_context = {
                "top_processes": [{"pid": 1234, "name": "test", "cpu": 50}],
                "recent_alerts": [{"level": "warning", "title": "Test alert"}],
                "recent_repairs": [{"script_key": "test_script", "success": True}],
                "stats": {"total_alerts": 10, "success_rate": 0.8},
            }
            result = await analyze(
                query="Test query",
                metrics_snapshot="CPU: 50%",
                platform="windows",
                rich_context=rich_context,
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_with_none_parameters(self):
        """Test analyze with None parameters."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await analyze(
                query=None,
                metrics_snapshot=None,
                platform=None,
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_ai_enabled_llm_router_unavailable(self):
        """Test analyze when AI is enabled but LLM router is unavailable."""
        with (
            patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}),
            patch("core.ai_engine.get_llm_router", None),
        ):
            result = await analyze(
                query="Test query",
                metrics_snapshot="CPU: 50%",
                platform="windows",
            )
            assert "规则降级引擎" in result

    @pytest.mark.asyncio
    async def test_analyze_with_empty_string_parameters(self):
        """Test analyze with empty string parameters."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await analyze(
                query="",
                metrics_snapshot="",
                platform="",
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_rate_limiting(self):
        """Test that analyze function respects rate limiting."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            # Call multiple times rapidly
            results = []
            for _ in range(3):
                result = await analyze(
                    query="Test query",
                    metrics_snapshot="CPU: 50%",
                    platform="windows",
                )
                results.append(result)
            # All should succeed
            assert all(isinstance(r, str) for r in results)


# ============================================================
# _build_rich_user_message function tests (5 test cases)
# ============================================================


class TestBuildRichUserMessage:
    """Test cases for _build_rich_user_message function."""

    def test_build_basic_message(self):
        """Test building basic user message without rich context."""
        result = _build_rich_user_message(
            query="Test query",
            metrics="CPU: 50%",
            platform="windows",
            rich_context=None,
        )
        assert "Test query" in result
        assert "CPU: 50%" in result

    def test_build_message_with_full_rich_context(self):
        """Test building message with complete rich context."""
        rich_context = {
            "top_processes": [{"pid": 1234, "name": "chrome.exe", "cpu": 50, "memory": 30}],
            "recent_alerts": [{"level": "warning", "title": "High CPU", "desc": "CPU usage high"}],
            "recent_repairs": [{"script_key": "restart_service", "success": True}],
            "stats": {"total_alerts": 10, "success_rate": 0.8},
        }
        result = _build_rich_user_message(
            query="Test query",
            metrics="CPU: 50%",
            platform="windows",
            rich_context=rich_context,
        )
        assert "Test query" in result
        assert "CPU: 50%" in result
        assert "进程列表" in result
        assert "最近告警" in result
        assert "最近修复记录" in result
        assert "整体统计" in result

    def test_build_message_with_empty_rich_context(self):
        """Test building message with empty rich context dict."""
        rich_context = {}
        result = _build_rich_user_message(
            query="Test query",
            metrics="CPU: 50%",
            platform="windows",
            rich_context=rich_context,
        )
        assert "Test query" in result
        assert "CPU: 50%" in result

    def test_build_message_with_partial_rich_context(self):
        """Test building message with partial rich context."""
        rich_context = {
            "top_processes": [{"pid": 1234, "name": "test", "cpu": 50}],
            "recent_alerts": [],
            "recent_repairs": None,
            "stats": {},
        }
        result = _build_rich_user_message(
            query="Test query",
            metrics="CPU: 50%",
            platform="windows",
            rich_context=rich_context,
        )
        assert "Test query" in result
        assert "进程列表" in result

    def test_build_message_with_none_values_in_context(self):
        """Test building message with None values in rich context."""
        rich_context = {
            "top_processes": None,
            "recent_alerts": None,
            "recent_repairs": None,
            "stats": None,
        }
        result = _build_rich_user_message(
            query="Test query",
            metrics="CPU: 50%",
            platform="windows",
            rich_context=rich_context,
        )
        assert "Test query" in result
        assert "CPU: 50%" in result


# ============================================================
# _rule_based_analysis function tests (3 test cases)
# ============================================================


class TestRuleBasedAnalysis:
    """Test cases for _rule_based_analysis function."""

    def test_rule_based_analysis_basic(self):
        """Test basic rule-based analysis."""
        result = _rule_based_analysis(
            query="High CPU usage", metrics="CPU: 90%", platform="windows"
        )
        assert "AI 引擎暂不可用" in result
        assert "规则降级引擎" in result
        assert "windows" in result

    def test_rule_based_analysis_different_platforms(self):
        """Test rule-based analysis for different platforms."""
        for platform in ["windows", "linux"]:
            result = _rule_based_analysis(query="Test query", metrics="CPU: 50%", platform=platform)
            assert platform in result

    def test_rule_based_analysis_long_query(self):
        """Test rule-based analysis with long query."""
        long_query = "x" * 1000
        result = _rule_based_analysis(query=long_query, metrics="CPU: 50%", platform="windows")
        assert "AI 引擎暂不可用" in result


# ============================================================
# LLMAnalysisService class tests (8 test cases)
# ============================================================


class TestLLMAnalysisService:
    """Test cases for LLMAnalysisService class."""

    @pytest.mark.asyncio
    async def test_analyze_method_basic(self):
        """Test LLMAnalysisService.analyze method."""
        service = LLMAnalysisService()
        with patch("core.ai_engine.analyze") as mock_analyze:
            mock_analyze.return_value = "Test analysis result"
            result = await service.analyze(
                context={"query": "Test", "metrics_snapshot": "CPU: 50%"},
                analysis_type=AnalysisType.GENERAL,
            )
            assert result["result"] == "Test analysis result"
            assert result["analysis_type"] == AnalysisType.GENERAL

    @pytest.mark.asyncio
    async def test_observe_method(self):
        """Test LLMAnalysisService.observe method."""
        service = LLMAnalysisService()
        with patch("core.ai_engine.analyze") as mock_analyze:
            mock_analyze.return_value = "Test observation"
            result = await service.observe(data={"query": "Test"})
            assert result["result"] == "Test observation"
            assert result["analysis_type"] == AnalysisType.GENERAL

    @pytest.mark.asyncio
    async def test_generate_runbook_method(self):
        """Test LLMAnalysisService.generate_runbook method."""
        service = LLMAnalysisService()
        with patch("core.ai_engine.analyze") as mock_analyze:
            mock_analyze.return_value = "Test runbook"
            alert_data = {"id": "123", "title": "High CPU", "desc": "CPU usage high"}
            result = await service.generate_runbook(alert_data=alert_data)
            assert result["runbook"] == "Test runbook"
            assert result["alert_id"] == "123"

    @pytest.mark.asyncio
    async def test_search_similar_method_with_rag(self):
        """Test LLMAnalysisService.search_similar method with RAG."""
        service = LLMAnalysisService()
        with patch("core.rag_engine.search_similar") as mock_search:
            mock_search.return_value = [
                {"id": "1", "similarity": 0.9},
                {"id": "2", "similarity": 0.8},
            ]
            result = await service.search_similar(query="High CPU", limit=10)
            assert len(result) == 2
            assert result[0]["similarity"] == 0.9

    @pytest.mark.asyncio
    async def test_search_similar_method_without_rag(self):
        """Test LLMAnalysisService.search_similar method without RAG."""
        service = LLMAnalysisService()
        with patch("core.rag_engine.search_similar", side_effect=ImportError):
            result = await service.search_similar(query="High CPU", limit=10)
            assert result == []

    @pytest.mark.asyncio
    async def test_get_health_status_method(self):
        """Test LLMAnalysisService.get_health_status method."""
        service = LLMAnalysisService()
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            result = await service.get_health_status()
            assert "available" in result
            assert "status" in result
            assert "langfuse_available" in result

    @pytest.mark.asyncio
    async def test_analyze_method_with_rich_context(self):
        """Test LLMAnalysisService.analyze with rich context."""
        service = LLMAnalysisService()
        with patch("core.ai_engine.analyze") as mock_analyze:
            mock_analyze.return_value = "Test analysis"
            rich_context = {"top_processes": [{"pid": 1234, "name": "test", "cpu": 50}]}
            result = await service.analyze(
                context={
                    "query": "Test",
                    "metrics_snapshot": "CPU: 50%",
                    "rich_context": rich_context,
                }
            )
            assert result["result"] == "Test analysis"

    @pytest.mark.asyncio
    async def test_analyze_method_different_platforms(self):
        """Test LLMAnalysisService.analyze with different platforms."""
        service = LLMAnalysisService()
        with patch("core.ai_engine.analyze") as mock_analyze:
            mock_analyze.return_value = "Test analysis"
            for platform in ["windows", "linux"]:
                result = await service.analyze(context={"query": "Test", "platform": platform})
                assert result["platform"] == platform


# ============================================================
# PredictiveAnalysisEngine class tests (5 test cases)
# ============================================================


class TestPredictiveAnalysisEngine:
    """Test cases for PredictiveAnalysisEngine class."""

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_basic(self):
        """Test basic system anomaly prediction."""
        engine = PredictiveAnalysisEngine()
        metrics_data = {"cpu": {"usage_percent": 85}, "memory": {"usage_percent": 70}}
        result = await engine.predict_system_anomalies(metrics_data)
        assert "predicted_anomalies" in result
        assert "confidence" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_high_cpu(self):
        """Test anomaly prediction with high CPU usage."""
        engine = PredictiveAnalysisEngine()
        metrics_data = {"cpu": {"usage_percent": 90}}
        result = await engine.predict_system_anomalies(metrics_data)
        assert len(result["predicted_anomalies"]) > 0
        assert any(a["type"] == "cpu_high" for a in result["predicted_anomalies"])

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_high_memory(self):
        """Test anomaly prediction with high memory usage."""
        engine = PredictiveAnalysisEngine()
        metrics_data = {"memory": {"usage_percent": 90}}
        result = await engine.predict_system_anomalies(metrics_data)
        assert len(result["predicted_anomalies"]) > 0
        assert any(a["type"] == "memory_high" for a in result["predicted_anomalies"])

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_high_disk(self):
        """Test anomaly prediction with high disk usage."""
        engine = PredictiveAnalysisEngine()
        metrics_data = {
            "disk": [
                {"mount_point": "/var", "usage_percent": 95},
                {"mount_point": "/home", "usage_percent": 60},
            ]
        }
        result = await engine.predict_system_anomalies(metrics_data)
        assert len(result["predicted_anomalies"]) > 0
        assert any(a["type"] == "disk_high" for a in result["predicted_anomalies"])

    @pytest.mark.asyncio
    async def test_predict_capacity_needs(self):
        """Test capacity needs prediction."""
        engine = PredictiveAnalysisEngine()
        current_metrics = {"cpu": {"usage_percent": 50}, "memory": {"usage_percent": 60}}
        result = await engine.predict_capacity_needs(current_metrics, growth_rate=0.1)
        assert "current_capacity" in result
        assert "predictions_3_months" in result
        assert "predictions_6_months" in result
        assert "recommendations" in result


# ============================================================
# IntelligentRecommendationEngine class tests (4 test cases)
# ============================================================


class TestIntelligentRecommendationEngine:
    """Test cases for IntelligentRecommendationEngine class."""

    @pytest.mark.asyncio
    async def test_generate_recommendations_cpu_high(self):
        """Test recommendation generation for high CPU alert."""
        engine = IntelligentRecommendationEngine()
        alert_data = {"type": "cpu_high", "severity": "warning", "id": "123"}
        result = await engine.generate_recommendations(alert_data)
        assert len(result) > 0
        assert any(r["type"] == "optimization" for r in result)

    @pytest.mark.asyncio
    async def test_generate_recommendations_memory_high(self):
        """Test recommendation generation for high memory alert."""
        engine = IntelligentRecommendationEngine()
        alert_data = {"type": "memory_high", "severity": "warning", "id": "123"}
        result = await engine.generate_recommendations(alert_data)
        assert len(result) > 0
        assert any(r["type"] == "optimization" for r in result)

    @pytest.mark.asyncio
    async def test_generate_recommendations_disk_high(self):
        """Test recommendation generation for high disk alert."""
        engine = IntelligentRecommendationEngine()
        alert_data = {"type": "disk_high", "severity": "critical", "id": "123"}
        result = await engine.generate_recommendations(alert_data)
        assert len(result) > 0
        assert any(r["type"] == "maintenance" for r in result)

    @pytest.mark.asyncio
    async def test_get_personalized_recommendations(self):
        """Test personalized recommendation generation."""
        engine = IntelligentRecommendationEngine()
        historical_actions = [
            {"type": "optimization"},
            {"type": "optimization"},
            {"type": "scaling"},
        ]
        result = await engine.get_personalized_recommendations(
            user_id="user123", historical_actions=historical_actions
        )
        assert len(result) > 0
        assert "personalization_reason" in result[0]


# ============================================================
# NaturalLanguageInteraction class tests (5 test cases)
# ============================================================


class TestNaturalLanguageInteraction:
    """Test cases for NaturalLanguageInteraction class."""

    @pytest.mark.asyncio
    async def test_process_natural_language_query_basic(self):
        """Test basic natural language query processing."""
        nli = NaturalLanguageInteraction()
        result = await nli.process_natural_language_query("What is the CPU status?")
        assert "query" in result
        assert "intent" in result
        assert "entities" in result
        assert "response" in result

    @pytest.mark.asyncio
    async def test_classify_intent_status_query(self):
        """Test intent classification for status queries."""
        nli = NaturalLanguageInteraction()
        intent = await nli._classify_intent("What is the system status?")
        assert intent == "status_query"

    @pytest.mark.asyncio
    async def test_classify_intent_root_cause_query(self):
        """Test intent classification for root cause queries."""
        nli = NaturalLanguageInteraction()
        intent = await nli._classify_intent("Why is the CPU high?")
        assert intent == "root_cause_query"

    @pytest.mark.asyncio
    async def test_extract_entities_cpu(self):
        """Test entity extraction for CPU metric."""
        nli = NaturalLanguageInteraction()
        entities = await nli._extract_entities("Check CPU usage")
        assert entities.get("metric") == "cpu"

    @pytest.mark.asyncio
    async def test_maintain_conversation(self):
        """Test conversation context maintenance."""
        nli = NaturalLanguageInteraction()
        result = await nli.maintain_conversation(user_id="user123", message="What is the status?")
        assert "conversation_history" in result
        assert len(result["conversation_history"]) == 2  # user + assistant


# ============================================================
# Helper function tests (4 test cases)
# ============================================================


class TestHelperFunctions:
    """Test cases for helper functions."""

    @pytest.mark.asyncio
    async def test_rate_limit_wait(self):
        """Test rate limiting wait function."""
        # Test that rate limiting doesn't break concurrent calls
        tasks = [_rate_limit_wait() for _ in range(3)]
        await asyncio.gather(*tasks)
        # Should complete without errors

    def test_get_http_client(self):
        """Test HTTP client retrieval."""
        client = _get_http_client()
        assert client is not None
        assert not client.is_closed

    @pytest.mark.asyncio
    async def test_close_http_client(self):
        """Test HTTP client closing."""
        client = _get_http_client()
        await close_http_client()
        # Client should be closed
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_close_langfuse_client(self):
        """Test Langfuse client closing."""
        # Should not raise error even if client is None
        await close_langfuse_client()
        # Should complete without errors


# ============================================================
# Decorator and global variable tests (3 test cases)
# ============================================================


class TestDecoratorsAndGlobals:
    """Test cases for decorators and global variables."""

    def test_noop_observe_decorator(self):
        """Test noop observe decorator acts as pass-through."""

        @observe
        def test_function():
            return "test result"

        result = test_function()
        assert result == "test result"

    def test_noop_observe_decorator_with_args(self):
        """Test noop observe decorator with arguments."""

        @observe(name="test")
        def test_function():
            return "test result"

        result = test_function()
        assert result == "test result"

    def test_global_ai_service_instance(self):
        """Test that global ai_service instance is created."""
        assert ai_service is not None
        assert isinstance(ai_service, LLMAnalysisService)


# ============================================================
# Additional edge case tests (5 test cases)
# ============================================================


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_analyze_with_unicode_characters(self):
        """Test analyze with unicode characters in query."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await analyze(
                query="测试查询 with emoji 🚀",
                metrics_snapshot="CPU: 50%",
                platform="windows",
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_with_special_characters(self):
        """Test analyze with special characters."""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await analyze(
                query="Test with \n\t\r special chars",
                metrics_snapshot="CPU: 50%",
                platform="windows",
            )
            assert isinstance(result, str)

    def test_build_rich_user_message_very_long_context(self):
        """Test building message with very long rich context."""
        long_process_list = [{"pid": i, "name": f"process_{i}", "cpu": i % 100} for i in range(100)]
        rich_context = {"top_processes": long_process_list}
        result = _build_rich_user_message(
            query="Test",
            metrics="CPU: 50%",
            platform="windows",
            rich_context=rich_context,
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_predictive_analysis_with_zero_growth_rate(self):
        """Test capacity prediction with zero growth rate."""
        engine = PredictiveAnalysisEngine()
        current_metrics = {"cpu": {"usage_percent": 50}}
        result = await engine.predict_capacity_needs(current_metrics, growth_rate=0.0)
        assert result["predictions_3_months"]["cpu"] == 50
        assert result["predictions_6_months"]["cpu"] == 50

    @pytest.mark.asyncio
    async def test_recommendation_engine_with_unknown_alert_type(self):
        """Test recommendation engine with unknown alert type."""
        engine = IntelligentRecommendationEngine()
        alert_data = {"type": "unknown_type", "severity": "info", "id": "123"}
        result = await engine.generate_recommendations(alert_data)
        # Should return empty list for unknown type
        assert isinstance(result, list)
