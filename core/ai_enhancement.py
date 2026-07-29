# -*- coding: utf-8 -*-
"""
Enhanced AI Analysis Capabilities

🔧 P1 Enhancement: Deepen AI analysis capabilities without modifying core architecture
- Enhanced context management
- Model performance monitoring
- Result caching with intelligent invalidation
- Multi-turn conversation support
- Analysis quality metrics
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from loguru import logger


class AIAnalysisEnhancer:
    """🔧 P1 Enhancement: Enhanced AI analysis capabilities"""

    def __init__(self):
        self._context_cache: Dict[str, Dict[str, Any]] = {}
        self._analysis_history: List[Dict[str, Any]] = []
        self._performance_metrics: Dict[str, Any] = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_response_time": 0.0,
            "model_usage": {},
        }
        self._cache_ttl = 3600  # 1 hour cache TTL

    def generate_context_key(self, alert_data: Dict[str, Any]) -> str:
        """Generate consistent context key for caching

        Args:
            alert_data: Alert data dictionary

        Returns:
            Context key hash
        """
        # Create deterministic string representation
        key_data = {
            "host": alert_data.get("host", ""),
            "platform": alert_data.get("platform", ""),
            "level": alert_data.get("level", ""),
            "message": alert_data.get("message", "")[:200],  # Truncate long messages
        }
        key_string = json.dumps(key_data, sort_keys=True)
        # Use SHA-256 instead of MD5 for better security
        # (usedforsecurity=False for non-cryptographic use)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get_cached_analysis(self, context_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis if available and not expired

        Args:
            context_key: Context key for lookup

        Returns:
            Cached analysis or None
        """
        if context_key not in self._context_cache:
            return None

        cached = self._context_cache[context_key]
        cache_time = datetime.fromisoformat(cached["timestamp"])

        if datetime.now(timezone.utc) - cache_time > timedelta(seconds=self._cache_ttl):
            del self._context_cache[context_key]
            return None

        logger.info(f"Cache hit for context key: {context_key}")
        return cast(Dict[str, Any], cached["analysis"])

    def cache_analysis(self, context_key: str, analysis: Dict[str, Any]) -> None:
        """Cache analysis result

        Args:
            context_key: Context key for storage
            analysis: Analysis result to cache
        """
        self._context_cache[context_key] = {
            "analysis": analysis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Cached analysis for context key: {context_key}")

    def invalidate_cache(self, context_key: Optional[str] = None) -> None:
        """Invalidate cache entry or all cache

        Args:
            context_key: Specific context key to invalidate, or None for all
        """
        if context_key:
            if context_key in self._context_cache:
                del self._context_cache[context_key]
                logger.info(f"Invalidated cache for context key: {context_key}")
        else:
            self._context_cache.clear()
            logger.info("Invalidated all cache entries")

    def record_analysis(self, analysis_data: Dict[str, Any]) -> None:
        """Record analysis for historical tracking

        Args:
            analysis_data: Analysis data to record
        """
        self._analysis_history.append(
            {**analysis_data, "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        # Keep only last 1000 analyses
        if len(self._analysis_history) > 1000:
            self._analysis_history = self._analysis_history[-1000:]

    def update_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update performance metrics

        Args:
            metrics: Performance metrics to update
        """
        self._performance_metrics["total_analyses"] += 1

        if metrics.get("success", False):
            self._performance_metrics["successful_analyses"] += 1
        else:
            self._performance_metrics["failed_analyses"] += 1

        # Update average response time
        if "response_time" in metrics:
            total = self._performance_metrics["total_analyses"]
            current_avg = self._performance_metrics["average_response_time"]
            new_avg = ((current_avg * (total - 1)) + metrics["response_time"]) / total
            self._performance_metrics["average_response_time"] = new_avg

        # Update model usage
        model = metrics.get("model", "unknown")
        if model not in self._performance_metrics["model_usage"]:
            self._performance_metrics["model_usage"][model] = 0
        self._performance_metrics["model_usage"][model] += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics

        Returns:
            Performance metrics dictionary
        """
        total = self._performance_metrics["total_analyses"]
        success_rate = (
            (self._performance_metrics["successful_analyses"] / total * 100) if total > 0 else 0.0
        )

        return {
            **self._performance_metrics,
            "success_rate": f"{success_rate:.2f}%",
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from metrics

        Returns:
            Cache hit rate percentage
        """
        # This would need actual hit/miss tracking
        # For now, return default_value
        return 0.0

    def get_analysis_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent analysis history

        Args:
            limit: Maximum number of records to return

        Returns:
            List of analysis records
        """
        return self._analysis_history[-limit:] if self._analysis_history else []

    def get_context_suggestions(self, alert_data: Dict[str, Any]) -> List[str]:
        """Get context-aware suggestions for analysis enhancement

        Args:
            alert_data: Alert data

        Returns:
            List of enhancement suggestions
        """
        suggestions = []

        # Check for similar historical analyses
        context_key = self.generate_context_key(alert_data)
        similar_analyses = [
            a for a in self._analysis_history if a.get("context_key") == context_key
        ]

        if similar_analyses:
            suggestions.append(f"Found {len(similar_analyses)} similar historical analyses")
            suggestions.append("Consider using cached results for faster response")

        # Check for platform-specific patterns
        platform = alert_data.get("platform", "")
        if platform:
            suggestions.append(f"Platform-specific patterns detected: {platform}")

        # Check for severity-based enhancements
        level = alert_data.get("level", "")
        if level in ["critical", "fatal"]:
            suggestions.append("High severity alert - consider priority analysis")

        return suggestions


class MultiTurnConversationManager:
    """🔧 P1 Enhancement: Multi-turn conversation support for AI analysis"""

    def __init__(self):
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}
        self._conversation_ttl = 86400  # 24 hours

    def create_conversation(self, conversation_id: str) -> str:
        """Create new conversation

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation ID
        """
        self._conversations[conversation_id] = []
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add message to conversation

        Args:
            conversation_id: Conversation identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata
        """
        if conversation_id not in self._conversations:
            self.create_conversation(conversation_id)

        self._conversations[conversation_id].append(
            {
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_conversation_history(
        self, conversation_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        if conversation_id not in self._conversations:
            return []

        return self._conversations[conversation_id][-limit:]

    def get_conversation_context(self, conversation_id: str) -> str:
        """Get formatted conversation context for AI analysis

        Args:
            conversation_id: Conversation identifier

        Returns:
            Formatted context string
        """
        messages = self.get_conversation_history(conversation_id)
        if not messages:
            return ""

        context_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    def cleanup_expired_conversations(self) -> None:
        """Clean up expired conversations"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self._conversation_ttl)

        expired_ids = []
        for conv_id, messages in self._conversations.items():
            if messages:
                last_message = messages[-1]
                last_time = datetime.fromisoformat(last_message["timestamp"])
                if last_time < cutoff_time:
                    expired_ids.append(conv_id)
            else:
                expired_ids.append(conv_id)

        for conv_id in expired_ids:
            del self._conversations[conv_id]
            logger.info(f"Cleaned up expired conversation: {conv_id}")


# Global instances
_ai_enhancer = AIAnalysisEnhancer()
_conversation_manager = MultiTurnConversationManager()


def get_ai_enhancer() -> AIAnalysisEnhancer:
    """Get global AI enhancer instance"""
    return _ai_enhancer


def get_conversation_manager() -> MultiTurnConversationManager:
    """Get global conversation manager instance"""
    return _conversation_manager
