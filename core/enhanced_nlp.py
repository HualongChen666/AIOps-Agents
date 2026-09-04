# -*- coding: utf-8 -*-
"""
Enhanced NLP Module with Deep Semantic Understanding
================================================

Based on existing sentence-transformers infrastructure for deep semantic analysis.
Extends basic keyword matching in chat_command_handler.py with embedding-based understanding.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

# Try to import sentence-transformers for deep semantic understanding
SENTENCE_TRANSFORMERS_AVAILABLE = False
ENHANCED_NLP_AVAILABLE = False
_model = None
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    ENHANCED_NLP_AVAILABLE = True
    logger.info("sentence-transformers available for deep semantic understanding")
except ImportError:
    logger.warning("sentence-transformers not available, using fallback semantic matching")


@dataclass
class SemanticMatch:
    """Semantic match result with confidence score"""
    text: str
    confidence: float
    category: str
    metadata: Dict[str, Any]


class EnhancedNLPProcessor:
    """
    Enhanced NLP processor with deep semantic understanding capabilities.

    Uses sentence-transformers for embedding-based semantic analysis
    when available, falls back to keyword matching otherwise.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize enhanced NLP processor.

        Args:
            model_name: Pre-trained sentence-transformers model name
        """
        self.model_name = model_name
        self._model = None
        self._action_embeddings: Optional[Dict[str, Any]] = None

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._model = SentenceTransformer(model_name)
                self._precompute_action_embeddings()
                logger.info(f"Enhanced NLP processor initialized with {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load sentence-transformers model: {e}")
                self._model = None

    def _precompute_action_embeddings(self) -> None:
        """Precompute embeddings for common action patterns"""
        if self._model is None:
            return

        action_patterns = {
            "pause": ["暂停", "停止", "不要执行", "stop", "pause", "halt"],
            "investigate": ["排查", "调查", "查看", "investigate", "check", "analyze"],
            "approve": ["批准", "同意", "允许", "approve", "allow", "yes"],
            "reject": ["拒绝", "不允许", "驳回", "reject", "deny", "no"],
            "ignore": ["忽略", "静音", "ignore", "silence", "mute"],
            "assign": ["转交", "分配", "assign", "delegate", "transfer"],
            "status": ["状态", "进展", "status", "progress", "how"],
        }

        self._action_embeddings = {}
        for action, patterns in action_patterns.items():
            embeddings = self._model.encode(patterns, convert_to_tensor=True)
            self._action_embeddings[action] = {
                "patterns": patterns,
                "embeddings": embeddings
            }

    def semantic_match_action(self, text: str, threshold: float = 0.7) -> SemanticMatch:
        """
        Match user input to action using semantic similarity.

        Args:
            text: User input text
            threshold: Confidence threshold for matching

        Returns:
            SemanticMatch with confidence score
        """
        # Apply input length limit
        from core.model_inference_config import get_inference_config
        config = get_inference_config()
        if len(text) > config.max_input_length:
            logger.warning(f"Input length {len(text)} exceeds limit {config.max_input_length}")
            text = text[:config.max_input_length]

        if self._model is None or self._action_embeddings is None:
            # Fallback to keyword matching
            return self._keyword_match_action(text)

        try:
            text_embedding = self._model.encode([text], convert_to_tensor=True)

            best_match = None
            best_confidence = 0.0

            for action, data in self._action_embeddings.items():
                # Compute cosine similarity
                from torch.nn.functional import cosine_similarity
                similarities = cosine_similarity(text_embedding, data["embeddings"])
                max_similarity = similarities.max().item()

                if max_similarity > best_confidence:
                    best_confidence = max_similarity
                    best_match = action

            if best_confidence >= threshold and best_match:
                return SemanticMatch(
                    text=text,
                    confidence=best_confidence,
                    category=best_match,
                    metadata={"method": "semantic_embedding"}
                )
            else:
                return SemanticMatch(
                    text=text,
                    confidence=best_confidence,
                    category="unknown",
                    metadata={"method": "semantic_embedding"}
                )

        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}, falling back to keyword matching")
            return self._keyword_match_action(text)

    def _keyword_match_action(self, text: str) -> SemanticMatch:
        """Fallback keyword-based action matching"""
        text_lower = text.lower()

        action_keywords = {
            "pause": ["暂停", "停止", "不要执行", "stop", "pause", "halt"],
            "investigate": ["排查", "调查", "查看", "investigate", "check", "analyze"],
            "approve": ["批准", "同意", "允许", "approve", "allow", "yes"],
            "reject": ["拒绝", "不允许", "驳回", "reject", "deny", "no"],
            "ignore": ["忽略", "静音", "ignore", "silence", "mute"],
            "assign": ["转交", "分配", "assign", "delegate", "transfer"],
            "status": ["状态", "进展", "status", "progress", "how"],
        }

        for action, keywords in action_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return SemanticMatch(
                    text=text,
                    confidence=0.8,  # Default confidence for keyword match
                    category=action,
                    metadata={"method": "keyword_matching"}
                )

        return SemanticMatch(
            text=text,
            confidence=0.0,
            category="unknown",
            metadata={"method": "keyword_matching"}
        )

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using pattern matching.

        Args:
            text: Input text

        Returns:
            List of extracted entities with types
        """
        import re

        entities = []

        # Extract service names
        service_pattern = r'(?:service|服务)[:\s]+([a-zA-Z0-9_\-\.]+)'
        for match in re.finditer(service_pattern, text, re.IGNORECASE):
            entities.append({
                "type": "service",
                "value": match.group(1),
                "start": match.start(),
                "end": match.end()
            })

        # Extract pod names
        pod_pattern = r'(?:pod|容器)[:\s]+([a-zA-Z0-9_\-\.]+)'
        for match in re.finditer(pod_pattern, text, re.IGNORECASE):
            entities.append({
                "type": "pod",
                "value": match.group(1),
                "start": match.start(),
                "end": match.end()
            })

        # Extract incident IDs
        incident_pattern = r'(?:incident|告警|工单)[:\s]+([a-zA-Z0-9_\-]+)'
        for match in re.finditer(incident_pattern, text, re.IGNORECASE):
            entities.append({
                "type": "incident",
                "value": match.group(1),
                "start": match.start(),
                "end": match.end()
            })

        return entities

    def analyze_intent(self, text: str) -> Dict[str, Any]:
        """
        Comprehensive intent analysis combining semantic matching and entity extraction.

        Args:
            text: User input text

        Returns:
            Dictionary with action, confidence, entities, and metadata
        """
        semantic_match = self.semantic_match_action(text)
        entities = self.extract_entities(text)

        return {
            "action": semantic_match.category,
            "confidence": semantic_match.confidence,
            "entities": entities,
            "metadata": semantic_match.metadata,
            "original_text": text
        }


# Global instance for reuse
_enhanced_nlp_processor: Optional[EnhancedNLPProcessor] = None


def get_enhanced_nlp_processor() -> EnhancedNLPProcessor:
    """Get or create global enhanced NLP processor instance"""
    global _enhanced_nlp_processor
    if _enhanced_nlp_processor is None:
        _enhanced_nlp_processor = EnhancedNLPProcessor()
    return _enhanced_nlp_processor


# Rate Limiter for NLP operations
class NLPRateLimiter:
    """Rate limiter for NLP operations to prevent API abuse"""

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_timestamps = deque()
        self._lock = None

    async def acquire(self) -> bool:
        """
        Acquire permission to make a request.

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        # Remove timestamps older than 1 minute
        minute_ago = now - 60
        while self.request_timestamps and self.request_timestamps[0] < minute_ago:
            self.request_timestamps.popleft()

        # Check if under limit
        if len(self.request_timestamps) < self.requests_per_minute:
            self.request_timestamps.append(now)
            return True

        return False

    def get_wait_time(self) -> float:
        """
        Get time to wait before next request can be made.

        Returns:
            Seconds to wait
        """
        if len(self.request_timestamps) < self.requests_per_minute:
            return 0.0

        # Calculate when oldest request will be 1 minute old
        oldest_timestamp = self.request_timestamps[0]
        wait_time = 60 - (time.time() - oldest_timestamp)
        return max(0.0, wait_time)


# Global rate limiter instance
_nlp_rate_limiter: Optional[NLPRateLimiter] = None


def get_nlp_rate_limiter() -> NLPRateLimiter:
    """Get or create global NLP rate limiter instance"""
    global _nlp_rate_limiter
    if _nlp_rate_limiter is None:
        from core.model_inference_config import get_inference_config
        config = get_inference_config()
        _nlp_rate_limiter = NLPRateLimiter(config.requests_per_minute)
    return _nlp_rate_limiter
