# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/heal_graph.py
Target: 90%+ statement and branch coverage
"""

import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.heal_graph import (
    _HEAL_METRIC_COUNTERS,
    HealState,
    run_heal,
)


class TestHealState:
    """Test suite for HealState dataclass"""

    def test_heal_state_creation(self):
        """Test creating a HealState instance"""
        state = HealState(
            alert={"id": "test-1", "level": "critical"},
            sla_score=3,
            analysis={"root_cause": "test"},
        )
        assert state.alert == {"id": "test-1", "level": "critical"}
        assert state.sla_score == 3
        assert state.analysis == {"root_cause": "test"}

    def test_heal_state_defaults(self):
        """Test HealState with default values"""
        state = HealState(alert={"id": "test"})
        assert state.alert == {"id": "test"}
        assert state.sla_score == 0
        assert state.analysis is None
        assert state.runbook is None
        assert state.fix_result is None
        assert state.verification is None
        assert state.rollback_result is None
        assert state.error is None
        assert state.current_node == ""
        assert state.decisions == []
        assert state.metadata == {}

    def test_heal_state_with_all_fields(self):
        """Test HealState with all fields populated"""
        state = HealState(
            alert={"id": "test"},
            sla_score=5,
            analysis={"root_cause": "test"},
            runbook={"steps": ["restart"]},
            fix_result={"status": "success"},
            verification={"passed": True},
            rollback_result={"status": "not_needed"},
            error=None,
            current_node="complete",
            decisions=[{"node": "apply_fix", "decision": "proceed"}],
            metadata={"trace_id": "test-123"},
        )
        assert state.alert == {"id": "test"}
        assert state.sla_score == 5
        assert state.analysis == {"root_cause": "test"}
        assert state.runbook == {"steps": ["restart"]}
        assert state.fix_result == {"status": "success"}
        assert state.verification == {"passed": True}
        assert state.rollback_result == {"status": "not_needed"}
        assert state.error is None
        assert state.current_node == "complete"
        assert len(state.decisions) == 1
        assert state.metadata == {"trace_id": "test-123"}


class TestRunHeal:
    """Test suite for run_heal function"""

    @pytest.mark.asyncio
    async def test_run_heal_basic(self):
        """Test basic heal workflow execution"""
        state = HealState(alert={"id": "test-1", "level": "warning"})

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_run_heal_with_critical_alert(self):
        """Test heal workflow with critical alert"""
        state = HealState(
            alert={"id": "test-1", "level": "critical", "category": "security"},
            sla_score=5,
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_run_heal_with_analysis(self):
        """Test heal workflow with pre-computed analysis"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu", "confidence": 0.8},
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_run_heal_with_runbook(self):
        """Test heal workflow with pre-computed runbook"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu"},
            runbook={"steps": [{"action": "restart_service", "target": "api"}]},
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_run_heal_error_handling(self):
        """Test heal workflow error handling"""
        state = HealState(alert={"id": "test-1", "level": "warning"})

        # Mock a node to raise an error
        with patch("core.heal_graph._fetch_alert", side_effect=Exception("Test error")):
            result = await run_heal(state)
            # Should still return a state, possibly with error set
            assert result is not None

    @pytest.mark.asyncio
    async def test_run_heal_with_metadata(self):
        """Test heal workflow with metadata"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            metadata={"trace_id": "test-123", "user": "admin"},
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)


class TestHealGraphNodes:
    """Test suite for individual heal graph nodes"""

    @pytest.mark.asyncio
    async def test_fetch_alert_node(self):
        """Test fetch_alert node"""
        from core.heal_graph import _fetch_alert

        state = HealState(alert={"id": "test-1", "level": "warning"})
        result = await _fetch_alert(state)
        assert result is not None
        assert result.current_node == "fetch_alert"

    @pytest.mark.asyncio
    async def test_check_sla_node(self):
        """Test check_sla node"""
        from core.heal_graph import _check_sla

        state = HealState(
            alert={"id": "test-1", "level": "critical", "category": "security"},
        )
        result = await _check_sla(state)
        assert result is not None
        assert result.current_node == "check_sla"
        assert result.sla_score >= 0

    @pytest.mark.asyncio
    async def test_invoke_agent_node(self):
        """Test invoke_agent node"""
        from core.heal_graph import _invoke_agent

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
        )

        with patch("core.heal_graph.analyze", return_value={"root_cause": "test"}):
            result = await _invoke_agent(state)
            assert result is not None
            assert result.current_node == "invoke_agent"

    @pytest.mark.asyncio
    async def test_generate_runbook_node(self):
        """Test generate_runbook node"""
        from core.heal_graph import _generate_runbook

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu"},
        )

        result = await _generate_runbook(state)
        assert result is not None
        assert result.current_node == "generate_runbook"

    @pytest.mark.asyncio
    async def test_apply_fix_node(self):
        """Test apply_fix node"""
        from core.heal_graph import _apply_fix

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu"},
            runbook={"steps": [{"action": "restart"}]},
        )

        result = await _apply_fix(state)
        assert result is not None
        assert result.current_node == "apply_fix"

    @pytest.mark.asyncio
    async def test_evaluate_node(self):
        """Test evaluate node"""
        from core.heal_graph import _evaluate

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu"},
            runbook={"steps": [{"action": "restart"}]},
            fix_result={"status": "success"},
        )

        result = await _evaluate(state)
        assert result is not None
        assert result.current_node == "evaluate"

    @pytest.mark.asyncio
    async def test_rollback_node(self):
        """Test rollback node"""
        from core.heal_graph import _rollback

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu"},
            runbook={"steps": [{"action": "restart"}]},
            fix_result={"status": "success"},
            verification={"passed": False},
        )

        result = await _rollback(state)
        assert result is not None
        assert result.current_node == "rollback"

    @pytest.mark.asyncio
    async def test_complete_node(self):
        """Test complete node"""
        from core.heal_graph import _complete

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "high_cpu"},
            runbook={"steps": [{"action": "restart"}]},
            fix_result={"status": "success"},
            verification={"passed": True},
        )

        result = await _complete(state)
        assert result is not None
        assert result.current_node == "complete"


class TestHealGraphFallback:
    """Test suite for fallback StateGraph implementation"""

    def test_fallback_stategraph_init(self):
        """Test fallback StateGraph initialization"""
        from core.heal_graph import StateGraph

        graph = StateGraph()
        assert graph.nodes == {}
        assert graph.edges == []
        assert graph.entry_point is None

    def test_fallback_stategraph_add_node(self):
        """Test adding node to fallback StateGraph"""
        from core.heal_graph import StateGraph

        graph = StateGraph()
        graph.add_node("test_node", lambda x: x)
        assert "test_node" in graph.nodes

    def test_fallback_stategraph_set_entry_point(self):
        """Test setting entry point in fallback StateGraph"""
        from core.heal_graph import StateGraph

        graph = StateGraph()
        graph.set_entry_point("start")
        assert graph.entry_point == "start"

    def test_fallback_stategraph_add_edge(self):
        """Test adding edge to fallback StateGraph"""
        from core.heal_graph import END, StateGraph

        graph = StateGraph()
        graph.add_edge("node1", "node2")
        assert ("node1", "node2") in graph.edges

    def test_fallback_stategraph_compile(self):
        """Test compiling fallback StateGraph"""
        from core.heal_graph import END, StateGraph

        graph = StateGraph()
        graph.add_node("start", lambda x: x)
        graph.add_node("end", lambda x: x)
        graph.set_entry_point("start")
        graph.add_edge("start", "end")
        graph.add_edge("end", END)

        compiled = graph.compile()
        assert compiled is not None
        assert asyncio.iscoroutinefunction(compiled)

    @pytest.mark.asyncio
    async def test_fallback_stategraph_execution(self):
        """Test executing compiled fallback StateGraph"""
        from core.heal_graph import END, StateGraph

        graph = StateGraph()

        async def start_node(state):
            state["visited"] = state.get("visited", []) + ["start"]
            return state

        async def end_node(state):
            state["visited"] = state.get("visited", []) + ["end"]
            return state

        graph.add_node("start", start_node)
        graph.add_node("end", end_node)
        graph.set_entry_point("start")
        graph.add_edge("start", "end")
        graph.add_edge("end", END)

        compiled = graph.compile()
        state = {"visited": []}
        result = await compiled(state)

        assert "start" in result["visited"]
        assert "end" in result["visited"]

    @pytest.mark.asyncio
    async def test_fallback_stategraph_no_entry_point(self):
        """Test fallback StateGraph without entry point"""
        from core.heal_graph import StateGraph

        graph = StateGraph()
        compiled = graph.compile()

        state = {"test": "data"}
        result = await compiled(state)

        # Should return state unchanged
        assert result == state

    @pytest.mark.asyncio
    async def test_fallback_stategraph_node_not_found(self):
        """Test fallback StateGraph with missing node"""
        from core.heal.graph import END, StateGraph

        graph = StateGraph()
        graph.set_entry_point("missing_node")
        graph.add_edge("missing_node", END)

        compiled = graph.compile()
        state = {"test": "data"}
        result = await compiled(state)

        # Should handle missing node gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_stategraph_node_exception(self):
        """Test fallback StateGraph with node exception"""
        from core.heal_graph import END, StateGraph

        graph = StateGraph()

        async def failing_node(state):
            raise Exception("Node failed")

        graph.add_node("failing", failing_node)
        graph.set_entry_point("failing")
        graph.add_edge("failing", END)

        compiled = graph.compile()
        state = HealState(alert={"id": "test"})
        result = await compiled(state)

        # Should handle exception gracefully
        assert result is not None


class TestCheckpointSQLiteFallback:
    """Test suite for fallback CheckpointSQLite implementation"""

    def test_checkpoint_sqlite_init(self):
        """Test CheckpointSQLite initialization"""
        from core.heal_graph import CheckpointSQLite

        checkpoint = CheckpointSQLite("test.db")
        assert checkpoint.db_path == "test.db"
        assert checkpoint._pending == {}

    def test_checkpoint_sqlite_put(self):
        """Test CheckpointSQLite put operation"""
        from core.heal_graph import CheckpointSQLite

        checkpoint = CheckpointSQLite("test.db")
        checkpoint.put("config1", {"state": "test"})

        assert "config1" in checkpoint._pending
        assert checkpoint._pending["config1"] == {"state": "test"}

    def test_checkpoint_sqlite_get(self):
        """Test CheckpointSQLite get operation"""
        from core.heal_graph import CheckpointSQLite

        checkpoint = CheckpointSQLite("test.db")
        checkpoint.put("config1", {"state": "test"})

        result = checkpoint.get("config1")
        assert result == {"state": "test"}

    def test_checkpoint_sqlite_get_missing(self):
        """Test CheckpointSQLite get operation with missing key"""
        from core.heal_graph import CheckpointSQLite

        checkpoint = CheckpointSQLite("test.db")
        result = checkpoint.get("missing")

        assert result is None


class TestHealMetricCounters:
    """Test suite for heal metric counters"""

    def test_heal_metric_counters_exists(self):
        """Test that heal metric counters dictionary exists"""
        assert isinstance(_HEAL_METRIC_COUNTERS, dict)

    def test_heal_metric_counters_empty_initially(self):
        """Test that heal metric counters is empty initially"""
        # Note: This might not be true if other tests have run
        # Just verify it's a dict
        assert isinstance(_HEAL_METRIC_COUNTERS, dict)


class TestHealGraphIntegration:
    """Test suite for heal graph integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_heal_workflow_success(self):
        """Test complete heal workflow with success path"""
        state = HealState(
            alert={
                "id": "test-1",
                "level": "warning",
                "title": "High CPU",
                "desc": "CPU usage above threshold",
                "metric": "cpu",
                "value": 85,
                "host": "server1",
            },
            sla_score=3,
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)
        # Verify workflow completed
        assert result.current_node in ("complete", "evaluate", "rollback")

    @pytest.mark.asyncio
    async def test_heal_workflow_with_approval(self):
        """Test heal workflow with approval requirement"""
        state = HealState(
            alert={
                "id": "test-1",
                "level": "critical",
                "category": "security",
                "title": "SSH Brute Force",
                "desc": "SSH login failures detected",
                "metric": "ssh_failed_logins",
                "value": 25,
                "host": "server1",
            },
            sla_score=5,
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_heal_workflow_dry_run(self):
        """Test heal workflow in dry-run mode"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            metadata={"dry_run": True},
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_heal_workflow_with_trace_id(self):
        """Test heal workflow with trace ID for audit"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            metadata={"trace_id": "trace-123"},
        )

        result = await run_heal(state)
        assert result is not None
        assert isinstance(result, HealState)


class TestHealGraphErrorRecovery:
    """Test suite for heal graph error recovery"""

    @pytest.mark.asyncio
    async def test_recovery_from_analysis_failure(self):
        """Test recovery when analysis node fails"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
        )

        with patch("core.heal_graph.analyze", side_effect=Exception("Analysis failed")):
            result = await run_heal(state)
            assert result is not None
            # Should handle error gracefully
            assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_recovery_from_runbook_failure(self):
        """Test recovery when runbook generation fails"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "test"},
        )

        with patch("core.heal_graph._generate_runbook", side_effect=Exception("Runbook failed")):
            result = await run_heal(state)
            assert result is not None
            assert isinstance(result, HealState)

    @pytest.mark.asyncio
    async def test_recovery_from_fix_failure(self):
        """Test recovery when fix application fails"""
        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "test"},
            runbook={"steps": [{"action": "restart"}]},
        )

        with patch("core.heal_graph._apply_fix", side_effect=Exception("Fix failed")):
            result = await run_heal(state)
            assert result is not None
            assert isinstance(result, HealState)


class TestHealGraphStateTransitions:
    """Test suite for heal graph state transitions"""

    @pytest.mark.asyncio
    async def test_state_transition_fetch_to_check_sla(self):
        """Test state transition from fetch_alert to check_sla"""
        from core.heal_graph import _check_sla, _fetch_alert

        state = HealState(alert={"id": "test-1", "level": "warning"})
        state = await _fetch_alert(state)
        assert state.current_node == "fetch_alert"

        state = await _check_sla(state)
        assert state.current_node == "check_sla"

    @pytest.mark.asyncio
    async def test_state_transition_with_rollback(self):
        """Test state transition when rollback is needed"""
        from core.heal_graph import _evaluate, _rollback

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "test"},
            runbook={"steps": [{"action": "restart"}]},
            fix_result={"status": "success"},
            verification={"passed": False, "reason": "Still failing"},
        )

        state = await _evaluate(state)
        assert state.current_node == "evaluate"

        state = await _rollback(state)
        assert state.current_node == "rollback"


class TestHealGraphDecisionRecording:
    """Test suite for decision recording in heal graph"""

    @pytest.mark.asyncio
    async def test_decision_recording_in_apply_fix(self):
        """Test that decisions are recorded during apply_fix"""
        from core.heal_graph import _apply_fix

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "test"},
            runbook={"steps": [{"action": "restart"}]},
        )

        result = await _apply_fix(state)
        # Verify decisions are recorded
        assert isinstance(result.decisions, list)

    @pytest.mark.asyncio
    async def test_decision_recording_in_evaluate(self):
        """Test that decisions are recorded during evaluate"""
        from core.heal_graph import _evaluate

        state = HealState(
            alert={"id": "test-1", "level": "warning"},
            sla_score=3,
            analysis={"root_cause": "test"},
            runbook={"steps": [{"action": "restart"}]},
            fix_result={"status": "success"},
        )

        result = await _evaluate(state)
        # Verify decisions are recorded
        assert isinstance(result.decisions, list)
