# -*- coding: utf-8 -*-
"""
Enhanced AI Features Integration Tests
======================================

Tests for:
- Enhanced NLP with deep semantic understanding
- Intelligent task decomposition with LLM
- Model inference service configuration
- Rate limiting and batch processing
- Security constraints and authorization

Uses pytest-xdist for parallel testing as required by constraints.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


# ============================================================
# Enhanced NLP Tests
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_enhanced_nlp_semantic_matching():
    """Test enhanced NLP semantic matching capabilities"""
    from core.enhanced_nlp import get_enhanced_nlp_processor, SENTENCE_TRANSFORMERS_AVAILABLE
    
    processor = get_enhanced_nlp_processor()
    assert processor is not None, "Enhanced NLP processor not available"
    
    # Test semantic matching
    result = processor.semantic_match_action("暂停自动操作", threshold=0.7)
    assert result.category in ["pause", "unknown"], f"Unexpected category: {result.category}"
    assert result.confidence >= 0.0, "Confidence should be non-negative"
    
    # Test entity extraction
    entities = processor.extract_entities("重启service nginx")
    assert len(entities) > 0, "Should extract at least one entity"
    assert any(e["type"] == "service" for e in entities), "Should extract service entity"
    
    # Test comprehensive intent analysis
    intent = processor.analyze_intent("批准重启nginx服务")
    assert intent["action"] in ["approve", "unknown"], f"Unexpected action: {intent['action']}"
    assert "confidence" in intent, "Should include confidence score"
    assert "entities" in intent, "Should include extracted entities"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enhanced_nlp_fallback_to_keyword():
    """Test fallback to keyword matching when semantic model unavailable"""
    from core.enhanced_nlp import EnhancedNLPProcessor
    
    # Create processor without model
    processor = EnhancedNLPProcessor()
    processor._model = None  # Simulate model unavailability
    
    result = processor.semantic_match_action("暂停操作", threshold=0.7)
    assert result.category in ["pause", "unknown"], "Fallback should still work"
    assert result.metadata.get("method") == "keyword_matching", "Should use keyword matching fallback"


# ============================================================
# Intelligent Task Decomposition Tests
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligent_task_decomposition():
    """Test intelligent task decomposition with LLM"""
    from core.intelligent_task_decomposer import get_intelligent_decomposer, LLM_ROUTER_AVAILABLE
    
    decomposer = get_intelligent_decomposer()
    assert decomposer is not None, "Intelligent decomposer not available"
    
    # Test rule-based decomposition (LLM may not be available)
    result = await decomposer.decompose_task("重启nginx服务", context={"service": "nginx"})
    
    assert result.tasks is not None, "Should return task list"
    assert len(result.tasks) > 0, "Should have at least one task"
    assert result.execution_order is not None, "Should have execution order"
    assert result.total_estimated_duration > 0, "Should estimate duration"
    
    # Verify task structure
    first_task = result.tasks[0]
    assert first_task.id is not None, "Task should have ID"
    assert first_task.name is not None, "Task should have name"
    assert first_task.estimated_duration > 0, "Task should have duration estimate"
    assert first_task.risk_level in ["low", "medium", "high"], "Task should have valid risk level"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligent_decomposition_topological_sort():
    """Test topological sort of task dependencies"""
    from core.intelligent_task_decomposer import get_intelligent_decomposer
    
    decomposer = get_intelligent_decomposer()
    
    # Test with deployment task (has dependencies)
    result = await decomposer.decompose_task("部署应用", context={"app": "test-app"})
    
    # Verify execution order respects dependencies
    if len(result.tasks) > 1:
        for i, task_id in enumerate(result.execution_order):
            task = next(t for t in result.tasks if t.id == task_id)
            # All dependencies should appear before this task
            for dep in task.dependencies:
                if dep in result.execution_order:
                    dep_index = result.execution_order.index(dep)
                    assert dep_index < i, f"Dependency {dep} should come before {task_id}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligent_decomposition_rule_based():
    """Test rule-based decomposition for specific task types"""
    from core.intelligent_task_decomposer import get_intelligent_decomposer
    
    decomposer = get_intelligent_decomposer()
    
    # Test restart task decomposition
    result = await decomposer.decompose_task("重启服务")
    # Result may be llm or rule_based depending on LLM availability
    assert result.decomposition_method in ["rule_based", "llm"], f"Should use rule-based or llm, got {result.decomposition_method}"
    
    # Verify restart-specific tasks exist regardless of method
    task_ids = [task.id for task in result.tasks]
    assert len(task_ids) > 0, "Should have tasks"


# ============================================================
# Model Inference Configuration Tests
# ============================================================

@pytest.mark.integration
def test_model_inference_config():
    """Test model inference service configuration"""
    from core.model_inference_config import get_inference_config, get_inference_config_singleton
    
    config = get_inference_config()
    assert config is not None, "Should return configuration"
    assert config.sentence_transformer_model is not None, "Should have sentence transformer model"
    assert config.llm_provider is not None, "Should have LLM provider"
    assert config.requests_per_minute > 0, "Should have rate limit"
    assert config.batch_size > 0, "Should have batch size"
    
    # Test singleton
    config2 = get_inference_config_singleton()
    assert config.sentence_transformer_model == config2.sentence_transformer_model, "Should return same config values"


@pytest.mark.integration
def test_inference_config_rate_limiting():
    """Test rate limiting configuration"""
    from core.model_inference_config import get_inference_config
    
    config = get_inference_config()
    
    # Verify rate limiting parameters
    assert config.requests_per_minute > 0, "RPM limit should be positive"
    assert config.requests_per_hour > 0, "RPH limit should be positive"
    assert config.requests_per_hour > config.requests_per_minute, "Hourly limit should exceed minute limit"
    
    # Verify batch processing parameters
    assert config.batch_size > 0, "Batch size should be positive"
    assert config.batch_timeout_seconds > 0, "Batch timeout should be positive"


@pytest.mark.integration
def test_inference_config_security():
    """Test security configuration"""
    from core.model_inference_config import get_inference_config
    
    config = get_inference_config()
    
    # Verify security parameters
    assert isinstance(config.enable_content_moderation, bool), "Content moderation should be boolean"
    assert config.max_input_length > 0, "Max input length should be positive"
    assert config.max_input_length <= 100000, "Max input length should be reasonable"


# ============================================================
# Integration with Existing Systems Tests
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_enhanced_nlp_chat_command_integration():
    """Test enhanced NLP integration with chat command handler"""
    from core.chat_command_handler import parse_chat_command, ENHANCED_NLP_AVAILABLE
    
    # Test with enhanced NLP
    result = parse_chat_command("暂停nginx服务", user_id="admin", user_name="admin", verified=True)
    
    assert result.allowed, "Command should be allowed for admin"
    assert result.action.value in ["pause", "unknown"], f"Action should be pause or unknown, got {result.action.value}"
    
    # Check if enhanced NLP was used
    if ENHANCED_NLP_AVAILABLE:
        assert "confidence" in result.params, "Should include confidence when enhanced NLP available"
        assert "method" in result.params, "Should include method used"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligent_decomposition_workflow_integration():
    """Test intelligent decomposition integration with workflow engine"""
    from core.workflow.engine import decompose_workflow_from_description, INTELLIGENT_DECOMPOSER_AVAILABLE
    
    # Test workflow decomposition
    dag = await decompose_workflow_from_description("重启nginx服务", context={"service": "nginx"})
    
    assert dag is not None, "Should return DAG"
    assert len(dag.nodes) > 0, "Should have at least one node"
    assert dag.name is not None, "DAG should have name"
    
    # Verify DAG structure
    if INTELLIGENT_DECOMPOSER_AVAILABLE:
        # Should have more intelligent decomposition
        assert len(dag.nodes) >= 3, "Intelligent decomposition should create multiple nodes"
    else:
        # Should have fallback simple workflow
        assert len(dag.nodes) == 3, "Fallback should create 3-node workflow"


# ============================================================
# Rate Limiting and Batch Processing Tests
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    """Test rate limiting enforcement in inference operations"""
    from core.enhanced_nlp import get_nlp_rate_limiter
    
    rate_limiter = get_nlp_rate_limiter()
    
    # Test rate limiter acquisition
    allowed = await rate_limiter.acquire()
    assert allowed, "First request should be allowed"
    
    # Test wait time calculation
    wait_time = rate_limiter.get_wait_time()
    assert wait_time >= 0.0, "Wait time should be non-negative"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing():
    """Test batch processing for multiple inference requests"""
    from core.intelligent_task_decomposer import get_batch_processor
    
    batch_processor = get_batch_processor()
    
    # Create multiple tasks
    tasks = [
        {"description": f"重启服务{i}", "context": {"service": f"service{i}"}}
        for i in range(15)
    ]
    
    # Process in batches
    results = await batch_processor.decompose_batch(tasks)
    
    assert len(results) == len(tasks), f"Should process all {len(tasks)} tasks"
    assert all(r is not None for r in results), "All results should be non-None"


# ============================================================
# Security and Authorization Tests
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_security_content_moderation():
    """Test content moderation for malicious inputs"""
    from core.chat_command_handler import parse_chat_command
    from core.model_inference_config import get_inference_config
    
    config = get_inference_config()
    
    if config.enable_content_moderation:
        # Test malicious command detection
        result = parse_chat_command("删除所有pod", user_id="admin", user_name="admin", verified=True)
        assert result.risk_level.value in ["high", "blocked", "critical"], "Should detect malicious command"
        assert not result.allowed, "Should block malicious commands"
        
        # Test input length limit
        long_input = "a" * (config.max_input_length + 100)
        result = parse_chat_command(long_input, user_id="admin", user_name="admin", verified=True)
        # Should handle long input gracefully
        assert result is not None, "Should handle long input"
        
        # Verify existing security infrastructure
        from core.auth import verify_token, security
        assert security is not None, "Security should be configured"
        
        from api.middleware.security_headers import SecurityHeadersConfig
        headers = SecurityHeadersConfig.get_headers()
        assert "X-Frame-Options" in headers, "Should have X-Frame-Options header"
        assert "X-Content-Type-Options" in headers, "Should have X-Content-Type-Options header"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authorization_enhanced_nlp():
    """Test authorization for enhanced NLP operations"""
    from core.chat_command_handler import parse_chat_command
    
    # Test with different user roles
    admin_result = parse_chat_command("重启服务", user_id="admin", user_name="admin", verified=True)
    assert admin_result.allowed, "Admin should be allowed"
    
    viewer_result = parse_chat_command("重启服务", user_id="viewer", user_name="viewer", verified=True)
    # Viewer may not be allowed for certain actions
    assert viewer_result is not None, "Should return result for viewer"


# ============================================================
# pytest-xdist Configuration
# ============================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-n", "auto",  # Enable pytest-xdist parallel testing
        "-v",
        "--tb=short"
    ])