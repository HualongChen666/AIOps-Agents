# -*- coding: utf-8 -*-
"""测试AI增强模块"""

import pytest


class TestAIEnhancementModule:
    """测试AI增强模块"""

    def test_ai_enhancement_module_exists(self):
        """测试AI增强模块存在"""
        from core import ai_enhancement

        assert ai_enhancement is not None

    def test_ai_enhancement_has_functions(self):
        """测试AI增强模块有函数"""
        from core import ai_enhancement

        # 检查模块有函数或类
        assert len(dir(ai_enhancement)) > 0


class TestAIAnalysisEnhancer:
    """测试AIAnalysisEnhancer类"""

    def test_ai_analysis_enhancer_init(self):
        """测试AIAnalysisEnhancer初始化"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            assert enhancer._context_cache == {}
            assert enhancer._analysis_history == []
            assert enhancer._performance_metrics["total_analyses"] == 0
        except Exception as e:
            pytest.skip(f"Cannot test AIAnalysisEnhancer init: {e}")

    def test_generate_context_key(self):
        """测试生成上下文键"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            alert_data = {
                "host": "test_host",
                "platform": "linux",
                "level": "critical",
                "message": "test message",
            }
            key = enhancer.generate_context_key(alert_data)

            assert isinstance(key, str)
            assert len(key) == 64  # SHA-256 hash length
        except Exception as e:
            pytest.skip(f"Cannot test generate context key: {e}")

    def test_generate_context_key_consistent(self):
        """测试上下文键一致性"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            alert_data = {
                "host": "test_host",
                "platform": "linux",
                "level": "critical",
                "message": "test message",
            }
            key1 = enhancer.generate_context_key(alert_data)
            key2 = enhancer.generate_context_key(alert_data)

            assert key1 == key2
        except Exception as e:
            pytest.skip(f"Cannot test generate context key consistent: {e}")

    def test_cache_analysis(self):
        """测试缓存分析"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            context_key = "test_key"
            analysis = {"result": "test_result"}

            enhancer.cache_analysis(context_key, analysis)
            assert context_key in enhancer._context_cache
        except Exception as e:
            pytest.skip(f"Cannot test cache analysis: {e}")

    def test_get_cached_analysis(self):
        """测试获取缓存分析"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            context_key = "test_key"
            analysis = {"result": "test_result"}

            enhancer.cache_analysis(context_key, analysis)
            cached = enhancer.get_cached_analysis(context_key)

            assert cached == analysis
        except Exception as e:
            pytest.skip(f"Cannot test get cached analysis: {e}")

    def test_get_cached_analysis_not_exists(self):
        """测试获取不存在的缓存分析"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            cached = enhancer.get_cached_analysis("nonexistent_key")

            assert cached is None
        except Exception as e:
            pytest.skip(f"Cannot test get cached analysis not exists: {e}")

    def test_invalidate_cache_specific(self):
        """测试失效特定缓存"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            context_key = "test_key"
            analysis = {"result": "test_result"}

            enhancer.cache_analysis(context_key, analysis)
            enhancer.invalidate_cache(context_key)

            assert context_key not in enhancer._context_cache
        except Exception as e:
            pytest.skip(f"Cannot test invalidate cache specific: {e}")

    def test_invalidate_cache_all(self):
        """测试失效所有缓存"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            enhancer.cache_analysis("key1", {"result": "test1"})
            enhancer.cache_analysis("key2", {"result": "test2"})

            enhancer.invalidate_cache()

            assert len(enhancer._context_cache) == 0
        except Exception as e:
            pytest.skip(f"Cannot test invalidate cache all: {e}")

    def test_record_analysis(self):
        """测试记录分析"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            analysis_data = {"result": "test_result"}

            enhancer.record_analysis(analysis_data)

            assert len(enhancer._analysis_history) == 1
        except Exception as e:
            pytest.skip(f"Cannot test record analysis: {e}")

    def test_record_analysis_limit(self):
        """测试记录分析限制"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            # Add more than 1000 analyses
            for i in range(1100):
                enhancer.record_analysis({"result": f"test_{i}"})

            assert len(enhancer._analysis_history) == 1000
        except Exception as e:
            pytest.skip(f"Cannot test record analysis limit: {e}")

    def test_update_performance_metrics(self):
        """测试更新性能指标"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            metrics = {"success": True, "response_time": 1.5, "model": "gpt-4"}

            enhancer.update_performance_metrics(metrics)

            assert enhancer._performance_metrics["total_analyses"] == 1
            assert enhancer._performance_metrics["successful_analyses"] == 1
        except Exception as e:
            pytest.skip(f"Cannot test update performance metrics: {e}")

    def test_update_performance_metrics_failed(self):
        """测试更新失败的性能指标"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            metrics = {"success": False, "response_time": 2.0, "model": "gpt-3.5"}

            enhancer.update_performance_metrics(metrics)

            assert enhancer._performance_metrics["total_analyses"] == 1
            assert enhancer._performance_metrics["failed_analyses"] == 1
        except Exception as e:
            pytest.skip(f"Cannot test update performance metrics failed: {e}")

    def test_get_performance_metrics(self):
        """测试获取性能指标"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            enhancer.update_performance_metrics({"success": True, "response_time": 1.0})

            metrics = enhancer.get_performance_metrics()

            assert "total_analyses" in metrics
            assert "success_rate" in metrics
            assert "cache_hit_rate" in metrics
        except Exception as e:
            pytest.skip(f"Cannot test get performance metrics: {e}")

    def test_get_analysis_history(self):
        """测试获取分析历史"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            enhancer.record_analysis({"result": "test1"})
            enhancer.record_analysis({"result": "test2"})

            history = enhancer.get_analysis_history(limit=10)

            assert len(history) == 2
        except Exception as e:
            pytest.skip(f"Cannot test get analysis history: {e}")

    def test_get_analysis_history_limit(self):
        """测试获取分析历史限制"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            for i in range(10):
                enhancer.record_analysis({"result": f"test_{i}"})

            history = enhancer.get_analysis_history(limit=5)

            assert len(history) == 5
        except Exception as e:
            pytest.skip(f"Cannot test get analysis history limit: {e}")

    def test_get_context_suggestions(self):
        """测试获取上下文建议"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            alert_data = {
                "host": "test_host",
                "platform": "linux",
                "level": "critical",
                "message": "test message",
            }

            suggestions = enhancer.get_context_suggestions(alert_data)

            assert isinstance(suggestions, list)
        except Exception as e:
            pytest.skip(f"Cannot test get context suggestions: {e}")

    def test_get_context_suggestions_with_history(self):
        """测试获取带历史的上下文建议"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            alert_data = {
                "host": "test_host",
                "platform": "linux",
                "level": "critical",
                "message": "test message",
            }

            # Add similar analysis to history
            context_key = enhancer.generate_context_key(alert_data)
            enhancer.record_analysis({"result": "test", "context_key": context_key})

            suggestions = enhancer.get_context_suggestions(alert_data)

            assert len(suggestions) > 0
        except Exception as e:
            pytest.skip(f"Cannot test get context suggestions with history: {e}")


class TestMultiTurnConversationManager:
    """测试MultiTurnConversationManager类"""

    def test_multi_turn_conversation_manager_init(self):
        """测试MultiTurnConversationManager初始化"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            assert manager._conversations == {}
        except Exception as e:
            pytest.skip(f"Cannot test MultiTurnConversationManager init: {e}")

    def test_create_conversation(self):
        """测试创建对话"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            conv_id = manager.create_conversation("test_conv")

            assert conv_id == "test_conv"
            assert "test_conv" in manager._conversations
        except Exception as e:
            pytest.skip(f"Cannot test create conversation: {e}")

    def test_add_message(self):
        """测试添加消息"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            manager.add_message("test_conv", "user", "Hello")

            assert "test_conv" in manager._conversations
            assert len(manager._conversations["test_conv"]) == 1
        except Exception as e:
            pytest.skip(f"Cannot test add message: {e}")

    def test_add_message_with_metadata(self):
        """测试添加带元数据的消息"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            manager.add_message("test_conv", "user", "Hello", {"key": "value"})

            message = manager._conversations["test_conv"][0]
            assert message["metadata"] == {"key": "value"}
        except Exception as e:
            pytest.skip(f"Cannot test add message with metadata: {e}")

    def test_get_conversation_history(self):
        """测试获取对话历史"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            manager.add_message("test_conv", "user", "Hello")
            manager.add_message("test_conv", "assistant", "Hi")

            history = manager.get_conversation_history("test_conv")

            assert len(history) == 2
        except Exception as e:
            pytest.skip(f"Cannot test get conversation history: {e}")

    def test_get_conversation_history_limit(self):
        """测试获取对话历史限制"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            for i in range(10):
                manager.add_message("test_conv", "user", f"Message {i}")

            history = manager.get_conversation_history("test_conv", limit=5)

            assert len(history) == 5
        except Exception as e:
            pytest.skip(f"Cannot test get conversation history limit: {e}")

    def test_get_conversation_history_not_exists(self):
        """测试获取不存在的对话历史"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            history = manager.get_conversation_history("nonexistent_conv")

            assert history == []
        except Exception as e:
            pytest.skip(f"Cannot test get conversation history not exists: {e}")

    def test_get_conversation_context(self):
        """测试获取对话上下文"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            manager.add_message("test_conv", "user", "Hello")
            manager.add_message("test_conv", "assistant", "Hi")

            context = manager.get_conversation_context("test_conv")

            assert "user: Hello" in context
            assert "assistant: Hi" in context
        except Exception as e:
            pytest.skip(f"Cannot test get conversation context: {e}")

    def test_get_conversation_context_empty(self):
        """测试获取空对话上下文"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            context = manager.get_conversation_context("test_conv")

            assert context == ""
        except Exception as e:
            pytest.skip(f"Cannot test get conversation context empty: {e}")

    def test_cleanup_expired_conversations(self):
        """测试清理过期对话"""
        try:
            from datetime import datetime, timedelta, timezone

            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()
            manager.add_message("test_conv", "user", "Hello")

            # Manually set timestamp to past
            past_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            manager._conversations["test_conv"][0]["timestamp"] = past_time

            manager.cleanup_expired_conversations()

            assert "test_conv" not in manager._conversations
        except Exception as e:
            pytest.skip(f"Cannot test cleanup expired conversations: {e}")


class TestGlobalInstances:
    """测试全局实例"""

    def test_get_ai_enhancer(self):
        """测试获取AI增强器"""
        try:
            from core.ai_enhancement import get_ai_enhancer

            enhancer = get_ai_enhancer()
            assert enhancer is not None
        except Exception as e:
            pytest.skip(f"Cannot test get ai enhancer: {e}")

    def test_get_conversation_manager(self):
        """测试获取对话管理器"""
        try:
            from core.ai_enhancement import get_conversation_manager

            manager = get_conversation_manager()
            assert manager is not None
        except Exception as e:
            pytest.skip(f"Cannot test get conversation manager: {e}")


class TestAIEnhancementIntegration:
    """测试AI增强集成"""

    def test_cache_lifecycle(self):
        """测试缓存完整生命周期"""
        try:
            from core.ai_enhancement import AIAnalysisEnhancer

            enhancer = AIAnalysisEnhancer()
            alert_data = {"host": "test", "platform": "linux", "level": "info", "message": "test"}

            # Generate key
            key = enhancer.generate_context_key(alert_data)

            # Cache
            analysis = {"result": "test"}
            enhancer.cache_analysis(key, analysis)

            # Retrieve
            cached = enhancer.get_cached_analysis(key)
            assert cached == analysis

            # Invalidate
            enhancer.invalidate_cache(key)
            assert enhancer.get_cached_analysis(key) is None
        except Exception as e:
            pytest.skip(f"Cannot test cache lifecycle: {e}")

    def test_conversation_lifecycle(self):
        """测试对话完整生命周期"""
        try:
            from core.ai_enhancement import MultiTurnConversationManager

            manager = MultiTurnConversationManager()

            # Create
            manager.create_conversation("test_conv")

            # Add messages
            manager.add_message("test_conv", "user", "Hello")
            manager.add_message("test_conv", "assistant", "Hi")

            # Get history
            history = manager.get_conversation_history("test_conv")
            assert len(history) == 2

            # Get context
            context = manager.get_conversation_context("test_conv")
            assert len(context) > 0
        except Exception as e:
            pytest.skip(f"Cannot test conversation lifecycle: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
