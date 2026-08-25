# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/ai_enhancement.py
Target: 90%+ statement and branch coverage
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.ai_enhancement import (
    AIAnalysisEnhancer,
    MultiTurnConversationManager,
    get_ai_enhancer,
    get_conversation_manager,
)


class TestAIAnalysisEnhancer:
    """Test suite for AIAnalysisEnhancer class"""

    @pytest.fixture
    def enhancer(self):
        """Create a fresh enhancer instance for each test"""
        return AIAnalysisEnhancer()

    def test_init(self, enhancer):
        """Test initialization"""
        assert enhancer._context_cache == {}
        assert enhancer._analysis_history == []
        assert enhancer._performance_metrics["total_analyses"] == 0
        assert enhancer._performance_metrics["successful_analyses"] == 0
        assert enhancer._performance_metrics["failed_analyses"] == 0
        assert enhancer._performance_metrics["average_response_time"] == 0.0
        assert enhancer._performance_metrics["model_usage"] == {}
        assert enhancer._cache_ttl == 3600

    def test_generate_context_key_basic(self, enhancer):
        """Test context key generation with basic alert data"""
        alert_data = {
            "host": "server1",
            "platform": "linux",
            "level": "warning",
            "message": "High CPU usage detected",
        }
        key = enhancer.generate_context_key(alert_data)

        # Verify it's a valid SHA256 hash (64 hex characters)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

        # Verify same data produces same key
        key2 = enhancer.generate_context_key(alert_data)
        assert key == key2

    def test_generate_context_key_missing_fields(self, enhancer):
        """Test context key generation with missing fields"""
        alert_data = {}
        key = enhancer.generate_context_key(alert_data)
        assert len(key) == 64

        # Verify different data produces different key
        alert_data2 = {"host": "server2"}
        key2 = enhancer.generate_context_key(alert_data2)
        assert key != key2

    def test_generate_context_key_long_message(self, enhancer):
        """Test context key generation truncates long messages"""
        alert_data = {
            "host": "server1",
            "platform": "linux",
            "level": "warning",
            "message": "x" * 300,  # Longer than 200 char limit
        }
        key = enhancer.generate_context_key(alert_data)
        assert len(key) == 64

    def test_get_cached_analysis_no_cache(self, enhancer):
        """Test getting cached analysis when cache is empty"""
        result = enhancer.get_cached_analysis("nonexistent_key")
        assert result is None

    def test_get_cached_analysis_hit(self, enhancer):
        """Test getting cached analysis when cache hit"""
        context_key = "test_key"
        analysis = {"result": "test_analysis"}
        enhancer._context_cache[context_key] = {
            "analysis": analysis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = enhancer.get_cached_analysis(context_key)
        assert result == analysis

    def test_get_cached_analysis_expired(self, enhancer):
        """Test getting cached analysis when entry is expired"""
        context_key = "test_key"
        old_time = datetime.now(timezone.utc) - timedelta(seconds=4000)
        enhancer._context_cache[context_key] = {
            "analysis": {"result": "old"},
            "timestamp": old_time.isoformat(),
        }

        result = enhancer.get_cached_analysis(context_key)
        assert result is None
        assert context_key not in enhancer._context_cache

    def test_cache_analysis(self, enhancer):
        """Test caching analysis result"""
        context_key = "test_key"
        analysis = {"result": "test_analysis"}

        enhancer.cache_analysis(context_key, analysis)

        assert context_key in enhancer._context_cache
        assert enhancer._context_cache[context_key]["analysis"] == analysis
        assert "timestamp" in enhancer._context_cache[context_key]

    def test_invalidate_cache_specific_key(self, enhancer):
        """Test invalidating specific cache entry"""
        context_key = "test_key"
        enhancer._context_cache[context_key] = {
            "analysis": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        enhancer.invalidate_cache(context_key)
        assert context_key not in enhancer._context_cache

    def test_invalidate_cache_all(self, enhancer):
        """Test invalidating all cache entries"""
        enhancer._context_cache = {
            "key1": {"analysis": {}, "timestamp": datetime.now(timezone.utc).isoformat()},
            "key2": {"analysis": {}, "timestamp": datetime.now(timezone.utc).isoformat()},
        }

        enhancer.invalidate_cache()
        assert enhancer._context_cache == {}

    def test_invalidate_cache_nonexistent_key(self, enhancer):
        """Test invalidating nonexistent cache entry (should not raise)"""
        enhancer.invalidate_cache("nonexistent_key")
        # Should not raise any exception

    def test_record_analysis(self, enhancer):
        """Test recording analysis to history"""
        analysis_data = {"result": "test", "confidence": 0.9}

        enhancer.record_analysis(analysis_data)

        assert len(enhancer._analysis_history) == 1
        assert enhancer._analysis_history[0]["result"] == "test"
        assert "timestamp" in enhancer._analysis_history[0]

    def test_record_analysis_history_limit(self, enhancer):
        """Test that analysis history is limited to 1000 entries"""
        # Add 1001 analyses
        for i in range(1001):
            enhancer.record_analysis({"id": i})

        assert len(enhancer._analysis_history) == 1000
        # Should keep the most recent 1000
        assert enhancer._analysis_history[0]["id"] == 1  # First kept
        assert enhancer._analysis_history[-1]["id"] == 1000  # Last added

    def test_update_performance_metrics_success(self, enhancer):
        """Test updating performance metrics with successful analysis"""
        metrics = {"success": True, "response_time": 1.5, "model": "gpt-4"}

        enhancer.update_performance_metrics(metrics)

        assert enhancer._performance_metrics["total_analyses"] == 1
        assert enhancer._performance_metrics["successful_analyses"] == 1
        assert enhancer._performance_metrics["failed_analyses"] == 0
        assert enhancer._performance_metrics["average_response_time"] == 1.5
        assert enhancer._performance_metrics["model_usage"]["gpt-4"] == 1

    def test_update_performance_metrics_failure(self, enhancer):
        """Test updating performance metrics with failed analysis"""
        metrics = {"success": False, "response_time": 2.0, "model": "gpt-3.5"}

        enhancer.update_performance_metrics(metrics)

        assert enhancer._performance_metrics["total_analyses"] == 1
        assert enhancer._performance_metrics["successful_analyses"] == 0
        assert enhancer._performance_metrics["failed_analyses"] == 1
        assert enhancer._performance_metrics["model_usage"]["gpt-3.5"] == 1

    def test_update_performance_metrics_average_calculation(self, enhancer):
        """Test average response time calculation"""
        # First analysis
        enhancer.update_performance_metrics(
            {"success": True, "response_time": 1.0, "model": "gpt-4"}
        )
        assert enhancer._performance_metrics["average_response_time"] == 1.0

        # Second analysis
        enhancer.update_performance_metrics(
            {"success": True, "response_time": 2.0, "model": "gpt-4"}
        )
        assert enhancer._performance_metrics["average_response_time"] == 1.5

        # Third analysis
        enhancer.update_performance_metrics(
            {"success": True, "response_time": 3.0, "model": "gpt-4"}
        )
        assert enhancer._performance_metrics["average_response_time"] == 2.0

    def test_update_performance_metrics_no_response_time(self, enhancer):
        """Test updating metrics without response time"""
        metrics = {"success": True, "model": "gpt-4"}

        enhancer.update_performance_metrics(metrics)

        assert enhancer._performance_metrics["total_analyses"] == 1
        assert enhancer._performance_metrics["average_response_time"] == 0.0

    def test_update_performance_metrics_unknown_model(self, enhancer):
        """Test updating metrics with unknown model (missing key)"""
        metrics = {"success": True}  # No model key provided

        enhancer.update_performance_metrics(metrics)

        # When model key is missing, it defaults to "unknown"
        assert "unknown" in enhancer._performance_metrics["model_usage"]
        assert enhancer._performance_metrics["model_usage"]["unknown"] == 1

    def test_update_performance_metrics_none_model(self, enhancer):
        """Test updating metrics when model is explicitly None"""
        metrics = {"success": True, "model": None}

        enhancer.update_performance_metrics(metrics)

        # When model is None, it uses None as the key
        assert None in enhancer._performance_metrics["model_usage"]
        assert enhancer._performance_metrics["model_usage"][None] == 1

    def test_get_performance_metrics_empty(self, enhancer):
        """Test getting performance metrics when no analyses recorded"""
        metrics = enhancer.get_performance_metrics()

        assert metrics["total_analyses"] == 0
        assert metrics["successful_analyses"] == 0
        assert metrics["failed_analyses"] == 0
        assert metrics["success_rate"] == "0.00%"
        assert metrics["cache_hit_rate"] == 0.0
        assert "timestamp" in metrics

    def test_get_performance_metrics_with_data(self, enhancer):
        """Test getting performance metrics with recorded data"""
        enhancer.update_performance_metrics(
            {"success": True, "response_time": 1.0, "model": "gpt-4"}
        )
        enhancer.update_performance_metrics(
            {"success": False, "response_time": 2.0, "model": "gpt-3.5"}
        )

        metrics = enhancer.get_performance_metrics()

        assert metrics["total_analyses"] == 2
        assert metrics["successful_analyses"] == 1
        assert metrics["failed_analyses"] == 1
        assert metrics["success_rate"] == "50.00%"
        assert "timestamp" in metrics

    def test_calculate_cache_hit_rate(self, enhancer):
        """Test cache hit rate calculation"""
        # No analyses, no cache
        assert enhancer._calculate_cache_hit_rate() == 0.0

        # Add analyses but no cache
        enhancer.update_performance_metrics({"success": True, "model": "gpt-4"})
        enhancer.update_performance_metrics({"success": True, "model": "gpt-4"})
        assert enhancer._calculate_cache_hit_rate() == 0.0

        # Add cache entries
        enhancer._context_cache = {"key1": {}, "key2": {}}
        hit_rate = enhancer._calculate_cache_hit_rate()
        assert hit_rate == 100.0  # 2 cache entries / 2 analyses = 100%

    def test_get_analysis_history_default_limit(self, enhancer):
        """Test getting analysis history with default limit"""
        for i in range(150):
            enhancer.record_analysis({"id": i})

        history = enhancer.get_analysis_history()
        assert len(history) == 100
        assert history[0]["id"] == 50  # Should get last 100
        assert history[-1]["id"] == 149

    def test_get_analysis_history_custom_limit(self, enhancer):
        """Test getting analysis history with custom limit"""
        for i in range(50):
            enhancer.record_analysis({"id": i})

        history = enhancer.get_analysis_history(limit=10)
        assert len(history) == 10
        assert history[0]["id"] == 40
        assert history[-1]["id"] == 49

    def test_get_analysis_history_empty(self, enhancer):
        """Test getting analysis history when empty"""
        history = enhancer.get_analysis_history()
        assert history == []

    def test_get_context_suggestions_with_similar_analyses(self, enhancer):
        """Test getting context suggestions with similar historical analyses"""
        alert_data = {"host": "server1", "platform": "linux", "level": "warning"}
        context_key = enhancer.generate_context_key(alert_data)

        # Add similar analysis
        enhancer.record_analysis({"context_key": context_key, "result": "similar"})

        suggestions = enhancer.get_context_suggestions(alert_data)

        assert len(suggestions) >= 2
        assert any("similar historical analyses" in s for s in suggestions)
        assert any("cached results" in s for s in suggestions)

    def test_get_context_suggestions_platform_specific(self, enhancer):
        """Test getting context suggestions with platform-specific patterns"""
        alert_data = {"host": "server1", "platform": "windows", "level": "info"}

        suggestions = enhancer.get_context_suggestions(alert_data)

        assert any("windows" in s.lower() for s in suggestions)

    def test_get_context_suggestions_high_severity(self, enhancer):
        """Test getting context suggestions for high severity alerts"""
        alert_data = {"host": "server1", "platform": "linux", "level": "critical"}

        suggestions = enhancer.get_context_suggestions(alert_data)

        assert any("priority analysis" in s for s in suggestions)

    def test_get_context_suggestions_fatal_severity(self, enhancer):
        """Test getting context suggestions for fatal severity alerts"""
        alert_data = {"host": "server1", "platform": "linux", "level": "fatal"}

        suggestions = enhancer.get_context_suggestions(alert_data)

        assert any("priority analysis" in s for s in suggestions)

    def test_get_context_suggestions_no_suggestions(self, enhancer):
        """Test getting context suggestions when no patterns match"""
        alert_data = {"host": "server1", "platform": "", "level": "info"}

        suggestions = enhancer.get_context_suggestions(alert_data)

        # Should return empty list when no patterns match
        assert suggestions == []


class TestMultiTurnConversationManager:
    """Test suite for MultiTurnConversationManager class"""

    @pytest.fixture
    def manager(self):
        """Create a fresh conversation manager for each test"""
        return MultiTurnConversationManager()

    def test_init(self, manager):
        """Test initialization"""
        assert manager._conversations == {}
        assert manager._conversation_ttl == 86400

    def test_create_conversation(self, manager):
        """Test creating a new conversation"""
        conv_id = "conv_1"
        result = manager.create_conversation(conv_id)

        assert result == conv_id
        assert conv_id in manager._conversations
        assert manager._conversations[conv_id] == []

    def test_add_message_new_conversation(self, manager):
        """Test adding message to a new conversation"""
        conv_id = "conv_1"

        manager.add_message(conv_id, "user", "Hello")

        assert conv_id in manager._conversations
        assert len(manager._conversations[conv_id]) == 1
        assert manager._conversations[conv_id][0]["role"] == "user"
        assert manager._conversations[conv_id][0]["content"] == "Hello"

    def test_add_message_existing_conversation(self, manager):
        """Test adding message to an existing conversation"""
        conv_id = "conv_1"
        manager.create_conversation(conv_id)

        manager.add_message(conv_id, "user", "Hello")
        manager.add_message(conv_id, "assistant", "Hi there")

        assert len(manager._conversations[conv_id]) == 2
        assert manager._conversations[conv_id][1]["role"] == "assistant"

    def test_add_message_with_metadata(self, manager):
        """Test adding message with metadata"""
        conv_id = "conv_1"

        manager.add_message(conv_id, "user", "Hello", metadata={"source": "web"})

        assert manager._conversations[conv_id][0]["metadata"] == {"source": "web"}

    def test_add_message_without_metadata(self, manager):
        """Test adding message without metadata"""
        conv_id = "conv_1"

        manager.add_message(conv_id, "user", "Hello")

        assert manager._conversations[conv_id][0]["metadata"] == {}

    def test_get_conversation_history_nonexistent(self, manager):
        """Test getting history for nonexistent conversation"""
        history = manager.get_conversation_history("nonexistent")
        assert history == []

    def test_get_conversation_history_default_limit(self, manager):
        """Test getting conversation history with default limit"""
        conv_id = "conv_1"
        for i in range(15):
            manager.add_message(conv_id, "user", f"Message {i}")

        history = manager.get_conversation_history(conv_id)
        assert len(history) == 10  # Default limit
        assert history[0]["content"] == "Message 5"
        assert history[-1]["content"] == "Message 14"

    def test_get_conversation_history_custom_limit(self, manager):
        """Test getting conversation history with custom limit"""
        conv_id = "conv_1"
        for i in range(10):
            manager.add_message(conv_id, "user", f"Message {i}")

        history = manager.get_conversation_history(conv_id, limit=5)
        assert len(history) == 5
        assert history[0]["content"] == "Message 5"
        assert history[-1]["content"] == "Message 9"

    def test_get_conversation_context_empty(self, manager):
        """Test getting context for empty conversation"""
        context = manager.get_conversation_context("conv_1")
        assert context == ""

    def test_get_conversation_context_with_messages(self, manager):
        """Test getting context for conversation with messages"""
        conv_id = "conv_1"
        manager.add_message(conv_id, "user", "Hello")
        manager.add_message(conv_id, "assistant", "Hi there")

        context = manager.get_conversation_context(conv_id)

        assert "user: Hello" in context
        assert "assistant: Hi there" in context

    def test_cleanup_expired_conversations_empty_messages(self, manager):
        """Test cleanup of conversations with empty messages"""
        conv_id = "conv_1"
        manager.create_conversation(conv_id)

        # Set old timestamp by manipulating directly
        old_time = datetime.now(timezone.utc) - timedelta(seconds=90000)
        manager._conversations[conv_id] = []

        manager.cleanup_expired_conversations()

        assert conv_id not in manager._conversations

    def test_cleanup_expired_conversations_old_messages(self, manager):
        """Test cleanup of conversations with old messages"""
        conv_id = "conv_1"
        manager.create_conversation(conv_id)

        # Manually set old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(seconds=90000)
        manager._conversations[conv_id] = [
            {"role": "user", "content": "test", "metadata": {}, "timestamp": old_time.isoformat()}
        ]

        manager.cleanup_expired_conversations()

        assert conv_id not in manager._conversations

    def test_cleanup_expired_conversations_recent_messages(self, manager):
        """Test that recent conversations are not cleaned up"""
        conv_id = "conv_1"
        manager.add_message(conv_id, "user", "Hello")

        manager.cleanup_expired_conversations()

        assert conv_id in manager._conversations

    def test_cleanup_expired_conversations_mixed(self, manager):
        """Test cleanup with mix of expired and active conversations"""
        # Old conversation
        old_conv = "old_conv"
        old_time = datetime.now(timezone.utc) - timedelta(seconds=90000)
        manager._conversations[old_conv] = [
            {"role": "user", "content": "test", "metadata": {}, "timestamp": old_time.isoformat()}
        ]

        # Recent conversation
        recent_conv = "recent_conv"
        manager.add_message(recent_conv, "user", "Hello")

        manager.cleanup_expired_conversations()

        assert old_conv not in manager._conversations
        assert recent_conv in manager._conversations


class TestGlobalInstances:
    """Test suite for global instance functions"""

    def test_get_ai_enhancer_singleton(self):
        """Test that get_ai_enhancer returns singleton instance"""
        enhancer1 = get_ai_enhancer()
        enhancer2 = get_ai_enhancer()

        assert enhancer1 is enhancer2
        assert isinstance(enhancer1, AIAnalysisEnhancer)

    def test_get_conversation_manager_singleton(self):
        """Test that get_conversation_manager returns singleton instance"""
        manager1 = get_conversation_manager()
        manager2 = get_conversation_manager()

        assert manager1 is manager2
        assert isinstance(manager1, MultiTurnConversationManager)

    def test_global_instances_persistence(self):
        """Test that global instances persist state across calls"""
        enhancer = get_ai_enhancer()
        enhancer.record_analysis({"test": "data"})

        enhancer2 = get_ai_enhancer()
        history = enhancer2.get_analysis_history()

        assert len(history) == 1
        assert history[0]["test"] == "data"
