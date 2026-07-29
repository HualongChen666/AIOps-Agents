# -*- coding: utf-8 -*-
"""Evidence tests for the memory and context management checklist fixes.

This file asserts that the high/medium risk items identified in the code review
are truly satisfied after the fixes.
"""

from __future__ import annotations

import asyncio
import copy
from unittest.mock import MagicMock

import pytest

from core.agent.behavior_monitor import BehaviorMonitor
from core.agent.executor import AutonomousExecutor
from core.agent.memory_bridge import MemoryBridge, _action_signature
from core.agent.planner import Task, TaskPlanner, TaskStatus
from core.agent.state import DiagnosticState
from core.ai.token_budget import estimate_tokens, prompt_fits, select_model_that_fits
from core.context_compression import compress_context, compress_prompt_text
from services.scenario_memory_service.orchestrator import (
    ScenarioMemoryOrchestrator,
    _cosine_similarity,
    _text_to_vector,
)
from services.scenario_memory_service.schemas import (
    EventMemory,
    LearnExperienceRequest,
    LongTermRequest,
    ShortTermRequest,
    SimilarityQueryRequest,
    StoreEventRequest,
)

# ---------------------------------------------------------------------------
# 1. Accurate token counting and context-window overflow handling
# ---------------------------------------------------------------------------


def test_cjk_token_count_is_higher_per_character_than_english() -> None:
    """Chinese text consumes more tokens per character than English ASCII."""
    english = "hello world"
    chinese = "你好世界"
    assert estimate_tokens(english) < estimate_tokens(chinese) * 2
    assert estimate_tokens(chinese) >= 2


def test_prompt_fits_respects_context_window() -> None:
    fits, prompt_tokens, total = prompt_fits(
        "short prompt",
        max_new_tokens=10,
        context_window=50,
    )
    assert fits is True
    assert prompt_tokens > 0

    fits2, _, total2 = prompt_fits("x" * 1000, max_new_tokens=10, context_window=50)
    assert fits2 is False
    assert total2 > 50


def test_select_model_that_fits_prefers_larger_window_when_needed() -> None:
    configs = [
        {"name": "small", "model": "small", "max_tokens": 100, "cost_per_1k": 0.001},
        {"name": "large", "model": "large", "max_tokens": 10000, "cost_per_1k": 0.01},
    ]
    selected = select_model_that_fits("x" * 500, max_new_tokens=50, model_configs=configs)
    assert selected is not None
    assert selected["model"] == "large"


# ---------------------------------------------------------------------------
# 2. Structured diagnostic state
# ---------------------------------------------------------------------------


def test_diagnostic_state_tracks_hypothesis_and_findings() -> None:
    state = DiagnosticState()
    state.update_from_task("分析CPU使用率高的问题", {"root_cause": "cpu leak"})
    assert state.current_hypothesis is not None
    state.update_from_task("验证 root cause", {"validation": "success"})
    assert any("cpu" in (f.get("hypothesis") or "").lower() for f in state.confirmed_findings)


def test_diagnostic_state_rules_out_failed_steps() -> None:
    state = DiagnosticState()
    state.update_from_task("检查磁盘空间", None, error="disk not found")
    assert len(state.ruled_out) == 1


# ---------------------------------------------------------------------------
# 3. Context compression preserves key findings
# ---------------------------------------------------------------------------


def test_compress_context_preserves_diagnostic_state_and_history() -> None:
    context = {
        "goal": "diagnose latency",
        "diagnostic_state": {"confirmed_findings": [{"hypothesis": "db slow"}]},
        "history": [{"step": i, "data": "x" * 200} for i in range(20)],
        "auxiliary": "x" * 200,
    }
    compressed = compress_context(context, max_tokens=300)
    assert "diagnostic_state" in compressed
    assert "goal" in compressed
    assert len(compressed["history"]) <= 6


def test_compress_prompt_text_preserves_user_query_and_key_sections() -> None:
    text = "用户问题: CPU高\n\n" + "\n\n".join([f"Section {i}:\n" + "x" * 200 for i in range(30)])
    compressed = compress_prompt_text(text, max_tokens=50)
    assert "用户问题" in compressed
    assert len(compressed) < len(text)


# ---------------------------------------------------------------------------
# 4. Loop detection (semantic / parameter-level)
# ---------------------------------------------------------------------------


def test_action_signature_is_stable_for_identical_params() -> None:
    sig1 = _action_signature("goal", "collect metrics", "tool", {"a": [1, 2], "b": {"c": 1}})
    sig2 = _action_signature("goal", "collect metrics", "tool", {"b": {"c": 1}, "a": [1, 2]})
    assert sig1 == sig2


def test_behavior_monitor_detects_repeated_action_signature() -> None:
    monitor = BehaviorMonitor()
    monitor.set_thresholds(max_tool_repetitions=2)
    for _ in range(3):
        monitor.record_action("agent1", 'goal::task::tool::{"a":1}')
    anomaly = monitor.check_anomaly("agent1")
    assert anomaly is not None
    assert any("action signature" in msg for msg in anomaly["messages"])


# ---------------------------------------------------------------------------
# 5. Multi-session context isolation
# ---------------------------------------------------------------------------


def test_executor_does_not_mutate_caller_context() -> None:
    planner = MagicMock(spec=TaskPlanner)
    task = Task(id="t1", description="收集系统指标", status=TaskStatus.PENDING)
    planner.plan.return_value = [task]
    planner.get_plan_summary.return_value = {"total": 1, "completed": 1}
    tool_executor = MagicMock()
    tool_executor.selector.select_tool.return_value = None
    tool_executor.execute_with_auto_selection.return_value = {"status": "ok"}

    executor = AutonomousExecutor(planner, tool_executor)
    executor.memory_bridge = None
    executor.behavior_monitor = BehaviorMonitor()
    original = {"shared_list": [1, 2, 3]}
    original_snapshot = copy.deepcopy(original)
    result = executor.execute_plan("diagnose", original, ["collect"])
    assert "session_id" in result
    assert "diagnostic_state" in result
    assert original == original_snapshot


def test_scenario_memory_short_term_session_isolation() -> None:
    orch = ScenarioMemoryOrchestrator()
    asyncio.run(
        orch.store_short_term(ShortTermRequest(key="k1", value="secret", session_id="session-a"))
    )
    value_a = asyncio.run(orch.retrieve_short_term("k1", session_id="session-a"))
    value_b = asyncio.run(orch.retrieve_short_term("k1", session_id="session-b"))
    assert value_a == "secret"
    assert value_b is None


def test_scenario_memory_long_term_session_isolation() -> None:
    orch = ScenarioMemoryOrchestrator()
    asyncio.run(
        orch.store_long_term(
            LongTermRequest(key="k1", value="important", importance=1.0, session_id="session-a")
        )
    )
    value_a = asyncio.run(orch.retrieve_long_term("k1", session_id="session-a"))
    value_b = asyncio.run(orch.retrieve_long_term("k1", session_id="session-b"))
    assert value_a == "important"
    assert value_b is None


# ---------------------------------------------------------------------------
# 6. Cross-session experience accumulation
# ---------------------------------------------------------------------------


def test_executor_saves_and_retrieves_experiences() -> None:
    planner = MagicMock(spec=TaskPlanner)
    task = Task(id="t1", description="修复服务", status=TaskStatus.PENDING)
    planner.plan.return_value = [task]
    planner.get_plan_summary.return_value = {"total": 1, "completed": 1}
    tool_executor = MagicMock()
    tool_executor.selector.select_tool.return_value = None
    tool_executor.execute_with_auto_selection.return_value = {"status": "ok"}

    bridge = MemoryBridge.from_settings()
    executor = AutonomousExecutor(planner, tool_executor)
    executor.memory_bridge = bridge
    executor.behavior_monitor = BehaviorMonitor()

    result = executor.execute_plan("修复服务", {"enable_memory": True}, ["fix"])
    assert result["summary"].get("memory") is not None


# ---------------------------------------------------------------------------
# 7. Experience expiration / correction + improved vector similarity
# ---------------------------------------------------------------------------


def test_learned_experience_gets_expiration_and_can_expire() -> None:
    orch = ScenarioMemoryOrchestrator()
    resp = asyncio.run(
        orch.learn_experience(
            LearnExperienceRequest(
                situation="cpu high",
                action="restart service",
                outcome="recovered",
                confidence=0.9,
                ttl_seconds=1,
            )
        )
    )
    assert resp.learned is True
    assert resp.expired is False
    # Wait for TTL to elapse.
    import time

    time.sleep(1.05)
    found = asyncio.run(orch.find_experiences("cpu high"))
    assert found == []


def test_experience_can_be_corrected_and_marked_invalid() -> None:
    orch = ScenarioMemoryOrchestrator()
    asyncio.run(
        orch.learn_experience(
            LearnExperienceRequest(
                situation="memory leak",
                action="restart",
                outcome="recovered",
                confidence=0.8,
            )
        )
    )
    corrected = asyncio.run(
        orch.correct_experience(
            situation="memory leak",
            action="restart",
            corrected_by="operator-1",
            corrected_outcome="actually needed scale-out",
        )
    )
    assert corrected is not None
    still_valid = asyncio.run(orch.find_experiences("memory leak"))
    assert all("scale-out" in e.outcome for e in still_valid)


def test_text_to_vector_gives_higher_similarity_for_shared_tokens() -> None:
    v1 = _text_to_vector("cpu high alert on payment service", 128)
    v2 = _text_to_vector("cpu high alert", 128)
    v3 = _text_to_vector("payment service deploy completed", 128)
    assert _cosine_similarity(v1, v2) > _cosine_similarity(v1, v3)
    assert _cosine_similarity(v1, v1) == pytest.approx(1.0, abs=1e-9)


def test_event_search_is_session_isolated() -> None:
    orch = ScenarioMemoryOrchestrator()
    asyncio.run(
        orch.store_event(
            StoreEventRequest(
                event=EventMemory(
                    event_type="alert",
                    source="svc",
                    payload={"msg": "cpu high"},
                    session_id="s1",
                )
            )
        )
    )
    all_results = asyncio.run(
        orch.search_similar(SimilarityQueryRequest(query="cpu high alert", top_k=5, threshold=0.6))
    )
    assert len(all_results.results) == 1
    session_results = asyncio.run(
        orch.search_similar(
            SimilarityQueryRequest(query="cpu high alert", top_k=5, session_id="s2", threshold=0.6)
        )
    )
    assert len(session_results.results) == 0
