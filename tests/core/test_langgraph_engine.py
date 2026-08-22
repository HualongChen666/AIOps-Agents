# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/analysis/l2/langgraph_engine.py
Target: 90%+ statement and branch coverage
"""

import pytest
import sys
import os
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from core.analysis.l2.langgraph_engine import (
    AnalysisState,
    AnalysisStep,
    LangGraphAnalysisEngine,
    LANGGRAPH_AVAILABLE,
)


class TestAnalysisState:
    """Test suite for AnalysisState TypedDict"""

    def test_analysis_state_structure(self):
        """Test that AnalysisState has correct structure"""
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        assert state["input"] == "test input"
        assert state["context"] == {}
        assert state["analysis_result"] is None
        assert state["tool_calls"] == []
        assert state["current_step"] == ""
        assert state["error"] is None


class TestAnalysisStep:
    """Test suite for AnalysisStep Enum"""

    def test_analysis_step_values(self):
        """Test that AnalysisStep has correct values"""
        assert AnalysisStep.INITIALIZE.value == "initialize"
        assert AnalysisStep.COLLECT_DATA.value == "collect_data"
        assert AnalysisStep.ANALYZE.value == "analyze"
        assert AnalysisStep.VALIDATE.value == "validate"
        assert AnalysisStep.FINALIZE.value == "finalize"


class TestLangGraphAnalysisEngine:
    """Test suite for LangGraphAnalysisEngine"""

    def test_init_with_config(self):
        """Test initialization with config"""
        config = {"timeout": 30}
        engine = LangGraphAnalysisEngine(config)
        assert engine.config == config
        assert engine._is_initialized == LANGGRAPH_AVAILABLE

    def test_init_without_config(self):
        """Test initialization without config"""
        engine = LangGraphAnalysisEngine()
        assert engine.config == {}
        assert engine._is_initialized == LANGGRAPH_AVAILABLE

    def test_init_when_langgraph_unavailable(self):
        """Test initialization when LangGraph is not available"""
        with patch('core.analysis.l2.langgraph_engine.LANGGRAPH_AVAILABLE', False):
            engine = LangGraphAnalysisEngine()
            assert engine._is_initialized is False

    def test_build_graph_success(self):
        """Test successful graph building"""
        if not LANGGRAPH_AVAILABLE:
            pytest.skip("LangGraph not available")
        
        engine = LangGraphAnalysisEngine()
        if LANGGRAPH_AVAILABLE:
            assert engine._is_initialized is True
            assert engine.graph is not None

    def test_build_graph_failure(self):
        """Test graph building failure"""
        if not LANGGRAPH_AVAILABLE:
            pytest.skip("LangGraph not available")
        
        with patch('core.analysis.l2.langgraph_engine.StateGraph', side_effect=Exception("Build error")):
            engine = LangGraphAnalysisEngine()
            assert engine._is_initialized is False

    def test_initialize_step(self):
        """Test initialize step"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._initialize_step(state)
        assert result["current_step"] == AnalysisStep.INITIALIZE.value
        assert result["context"] == {}
        assert result["analysis_result"] is None
        assert result["error"] is None

    def test_initialize_step_with_existing_context(self):
        """Test initialize step with existing context"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {"existing": "data"},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._initialize_step(state)
        assert result["context"] == {"existing": "data"}

    @pytest.mark.asyncio
    async def test_collect_data_step_success(self):
        """Test successful data collection step"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.get_l4_storage_manager') as mock_l4:
            mock_l4_instance = MagicMock()
            mock_l4.return_value = mock_l4_instance
            
            mock_vm = AsyncMock()
            mock_loki = AsyncMock()
            mock_l4_instance.get_victoriametrics.return_value = mock_vm
            mock_l4_instance.get_loki.return_value = mock_loki
            
            mock_vm.query_range = AsyncMock(return_value=[])
            mock_loki.query_range = AsyncMock(return_value=[])
            
            with patch('core.analysis.l2.langgraph_engine.get_cached_snapshot', return_value={}):
                with patch('core.analysis.l2.langgraph_engine.alert_history', []):
                    with patch('core.analysis.l2.langgraph_engine.config_manager') as mock_config:
                        mock_config._audit_log = []
                        with patch('core.analysis.l2.langgraph_engine.repair_history', []):
                            with patch('core.analysis.l2.langgraph_engine.root_cause_intelligence_engine') as mock_rc:
                                mock_rc.topology_graph = {}
                                
                                result = await engine._collect_data_step(state)
                                assert result["current_step"] == AnalysisStep.COLLECT_DATA.value

    @pytest.mark.asyncio
    async def test_collect_data_step_no_l4_manager(self):
        """Test data collection step without L4 manager"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.get_l4_storage_manager', return_value=None):
            with patch('core.analysis.l2.langgraph_engine.get_cached_snapshot', return_value={}):
                with patch('core.analysis.l2.langgraph_engine.alert_history', []):
                    with patch('core.analysis.l2.langgraph_engine.config_manager') as mock_config:
                        mock_config._audit_log = []
                        with patch('core.analysis.l2.langgraph_engine.repair_history', []):
                            with patch('core.analysis.l2.langgraph_engine.root_cause_intelligence_engine') as mock_rc:
                                mock_rc.topology_graph = {}
                                
                                result = await engine._collect_data_step(state)
                                assert result["current_step"] == AnalysisStep.COLLECT_DATA.value

    @pytest.mark.asyncio
    async def test_collect_data_step_exception(self):
        """Test data collection step with exception"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.get_l4_storage_manager', side_effect=Exception("L4 error")):
            result = await engine._collect_data_step(state)
            assert result["current_step"] == AnalysisStep.COLLECT_DATA.value
            assert result["error"] is not None

    def test_collect_extended_context(self):
        """Test extended context collection"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.get_cached_snapshot', return_value={"cpu": {"usage": 50}}):
            with patch('core.analysis.l2.langgraph_engine.alert_history', [{"level": "warning"}]):
                with patch('core.analysis.l2.langgraph_engine.config_manager') as mock_config:
                    mock_config._audit_log = [{"timestamp": "2024-01-01", "change": "test", "details": "test"}]
                    with patch('core.analysis.l2.langgraph_engine.repair_history', [{"action": "restart"}]):
                        with patch('core.analysis.l2.langgraph_engine.root_cause_intelligence_engine') as mock_rc:
                            mock_rc.topology_graph = {"service1": ["service2"]}
                            
                            engine._collect_extended_context(state)
                            
                            assert "infrastructure_metrics" in state["context"]
                            assert "recent_alerts" in state["context"]
                            assert "change_events" in state["context"]
                            assert "recent_repairs" in state["context"]
                            assert "topology" in state["context"]

    def test_collect_extended_context_exceptions(self):
        """Test extended context collection with exceptions"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.get_cached_snapshot', side_effect=Exception("Snapshot error")):
            with patch('core.analysis.l2.langgraph_engine.alert_history', side_effect=Exception("Alert error")):
                with patch('core.analysis.l2.langgraph_engine.config_manager', side_effect=Exception("Config error")):
                    with patch('core.analysis.l2.langgraph_engine.repair_history', side_effect=Exception("Repair error")):
                        with patch('core.analysis.l2.langgraph_engine.root_cause_intelligence_engine', side_effect=Exception("RC error")):
                            engine._collect_extended_context(state)
                            # Should not raise exception, just log warnings

    @pytest.mark.asyncio
    async def test_analyze_step_success(self):
        """Test successful analyze step"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.analyze', return_value={"result": "success"}):
            result = await engine._analyze_step(state)
            assert result["current_step"] == AnalysisStep.ANALYZE.value
            assert result["analysis_result"] == {"result": "success"}

    @pytest.mark.asyncio
    async def test_analyze_step_exception(self):
        """Test analyze step with exception"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        with patch('core.analysis.l2.langgraph_engine.analyze', side_effect=Exception("Analysis error")):
            result = await engine._analyze_step(state)
            assert result["current_step"] == AnalysisStep.ANALYZE.value
            assert result["error"] is not None
            assert result["analysis_result"]["error"] is not None

    def test_validate_step_success(self):
        """Test successful validation step"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": {
                "candidates": [
                    {
                        "root_cause": "test",
                        "confidence": 0.8,
                        "expected_observations_if_true": "test",
                        "missing_data": "none",
                        "is_verifiable": True,
                    }
                ],
                "escalation_recommended": False,
            },
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._validate_step(state)
        assert result["current_step"] == AnalysisStep.VALIDATE.value
        assert result["error"] is None

    def test_validate_step_no_result(self):
        """Test validation step with no result"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._validate_step(state)
        assert result["current_step"] == AnalysisStep.VALIDATE.value
        assert result["error"] is not None

    def test_validate_step_missing_candidates(self):
        """Test validation step with missing candidates"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": {"escalation_recommended": False},
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._validate_step(state)
        assert result["current_step"] == AnalysisStep.VALIDATE.value
        assert result["error"] is not None

    def test_validate_step_missing_escalation(self):
        """Test validation step with missing escalation field"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": {
                "candidates": [
                    {
                        "root_cause": "test",
                        "confidence": 0.8,
                        "expected_observations_if_true": "test",
                        "missing_data": "none",
                        "is_verifiable": True,
                    }
                ]
            },
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._validate_step(state)
        assert result["current_step"] == AnalysisStep.VALIDATE.value
        assert result["error"] is not None

    def test_validate_step_exception(self):
        """Test validation step with exception"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": "not a dict",
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._validate_step(state)
        assert result["current_step"] == AnalysisStep.VALIDATE.value
        assert result["error"] is not None

    def test_finalize_step(self):
        """Test finalize step"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": {"result": "success"},
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._finalize_step(state)
        assert result["current_step"] == AnalysisStep.FINALIZE.value
        assert "metadata" in result["analysis_result"]
        assert result["analysis_result"]["metadata"]["engine"] == "langgraph"

    def test_finalize_step_no_result(self):
        """Test finalize step with no result"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._finalize_step(state)
        assert result["current_step"] == AnalysisStep.FINALIZE.value
        assert result["analysis_result"] is None

    def test_should_retry_with_error(self):
        """Test should_retry with error"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": None,
            "tool_calls": [],
            "current_step": "",
            "error": "test error",
        }
        
        result = engine._should_retry(state)
        assert result == "retry"

    def test_should_retry_without_error(self):
        """Test should_retry without error"""
        engine = LangGraphAnalysisEngine()
        state: AnalysisState = {
            "input": "test input",
            "context": {},
            "analysis_result": {"result": "success"},
            "tool_calls": [],
            "current_step": "",
            "error": None,
        }
        
        result = engine._should_retry(state)
        assert result == "finalize"

    @pytest.mark.asyncio
    async def test_collect_metrics_success(self):
        """Test successful metrics collection"""
        engine = LangGraphAnalysisEngine()
        mock_vm = AsyncMock()
        mock_vm.query_range = AsyncMock(return_value=[])
        
        result = await engine._collect_metrics(mock_vm, "test query", datetime.now(), datetime.now())
        assert "query" in result
        assert "data" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_collect_metrics_exception(self):
        """Test metrics collection with exception"""
        engine = LangGraphAnalysisEngine()
        mock_vm = AsyncMock()
        mock_vm.query_range = AsyncMock(side_effect=Exception("Query error"))
        
        result = await engine._collect_metrics(mock_vm, "test query", datetime.now(), datetime.now())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_collect_logs_success(self):
        """Test successful logs collection"""
        engine = LangGraphAnalysisEngine()
        mock_loki = AsyncMock()
        mock_loki.query_range = AsyncMock(return_value=[])
        
        result = await engine._collect_logs(mock_loki, "test query", datetime.now(), datetime.now())
        assert "query" in result
        assert "data" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_collect_logs_exception(self):
        """Test logs collection with exception"""
        engine = LangGraphAnalysisEngine()
        mock_loki = AsyncMock()
        mock_loki.query_range = AsyncMock(side_effect=Exception("Query error"))
        
        result = await engine._collect_logs(mock_loki, "test query", datetime.now(), datetime.now())
        assert "error" in result

    def test_assess_completeness_both_ok(self):
        """Test completeness assessment with both sources OK"""
        engine = LangGraphAnalysisEngine()
        result = engine._assess_completeness({"data": "test"}, {"logs": "test"})
        assert result["metrics_available"] is True
        assert result["logs_available"] is True
        assert result["complete"] is True
        assert len(result["sources_missing"]) == 0

    def test_assess_completeness_metrics_failed(self):
        """Test completeness assessment with metrics failed"""
        engine = LangGraphAnalysisEngine()
        result = engine._assess_completeness({"_data_completeness": "failed"}, {"logs": "test"})
        assert result["metrics_available"] is False
        assert result["logs_available"] is True
        assert result["complete"] is False
        assert "metrics" in result["sources_missing"]

    def test_assess_completeness_logs_failed(self):
        """Test completeness assessment with logs failed"""
        engine = LangGraphAnalysisEngine()
        result = engine._assess_completeness({"data": "test"}, {"_data_completeness": "failed"})
        assert result["metrics_available"] is True
        assert result["logs_available"] is False
        assert result["complete"] is False
        assert "logs" in result["sources_missing"]

    def test_assess_completeness_both_failed(self):
        """Test completeness assessment with both sources failed"""
        engine = LangGraphAnalysisEngine()
        result = engine._assess_completeness({"_data_completeness": "failed"}, {"_data_completeness": "failed"})
        assert result["metrics_available"] is False
        assert result["logs_available"] is False
        assert result["complete"] is False
        assert len(result["sources_missing"]) == 2

    def test_assess_completeness_empty_results(self):
        """Test completeness assessment with empty results"""
        engine = LangGraphAnalysisEngine()
        result = engine._assess_completeness({}, {})
        assert result["metrics_available"] is False
        assert result["logs_available"] is False
        assert result["complete"] is False

    def test_build_analysis_prompt_basic(self):
        """Test basic analysis prompt building"""
        engine = LangGraphAnalysisEngine()
        context = {
            "metrics": "cpu: 80%",
            "logs": "error: connection failed",
        }
        
        prompt = engine._build_analysis_prompt("test input", context)
        assert "test input" in prompt
        assert "cpu: 80%" in prompt
        assert "error: connection failed" in prompt

    def test_build_analysis_prompt_with_completeness(self):
        """Test analysis prompt building with completeness info"""
        engine = LangGraphAnalysisEngine()
        context = {
            "metrics": "cpu: 80%",
            "_data_completeness": {"complete": True},
        }
        
        prompt = engine._build_analysis_prompt("test input", context)
        assert "test input" in prompt
        assert "Data completeness assessment" in prompt

    def test_build_promql_query_latency(self):
        """Test PromQL query building for latency"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("high latency response time")
        assert "histogram_quantile" in query or "request_duration" in query

    def test_build_promql_query_error(self):
        """Test PromQL query building for errors"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("high error rate 5xx failure")
        assert "http_requests_total" in query or "status" in query

    def test_build_promql_query_network(self):
        """Test PromQL query building for network"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("network packet drop")
        assert "network" in query or "drop" in query

    def test_build_promql_query_connection(self):
        """Test PromQL query building for connection pool"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("connection pool exhausted")
        assert "connection" in query or "pool" in query

    def test_build_promql_query_gc(self):
        """Test PromQL query building for GC"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("jvm gc garbage collection")
        assert "gc" in query or "jvm" in query

    def test_build_promql_query_dns(self):
        """Test PromQL query building for DNS"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("dns resolve failure")
        assert "dns" in query

    def test_build_promql_query_traffic(self):
        """Test PromQL query building for traffic"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("high traffic qps rps")
        assert "http_requests_total" in query or "rate" in query

    def test_build_promql_query_cpu(self):
        """Test PromQL query building for CPU"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("high cpu usage")
        assert "cpu" in query

    def test_build_promql_query_memory(self):
        """Test PromQL query building for memory"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("high memory usage")
        assert "memory" in query

    def test_build_promql_query_disk(self):
        """Test PromQL query building for disk"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("disk usage high")
        assert "disk" in query

    def test_build_promql_query_default(self):
        """Test PromQL query building for default case"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_promql_query("unknown issue")
        assert "up" in query or "__name__" in query

    def test_build_logql_query_with_keywords(self):
        """Test LogQL query building with keywords"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_logql_query("error connection failed timeout")
        assert "error" in query or "connection" in query or "failed" in query

    def test_build_logql_query_without_keywords(self):
        """Test LogQL query building without keywords"""
        engine = LangGraphAnalysisEngine()
        query = engine._build_logql_query("")
        assert "level" in query

    @pytest.mark.asyncio
    async def test_analyze_success(self):
        """Test successful analysis"""
        if not LANGGRAPH_AVAILABLE:
            pytest.skip("LangGraph not available")
        
        engine = LangGraphAnalysisEngine()
        if not engine._is_initialized:
            pytest.skip("Engine not initialized")
        
        with patch.object(engine.graph, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {
                "input": "test",
                "context": {},
                "analysis_result": {"result": "success"},
                "tool_calls": [],
                "current_step": "finalize",
                "error": None,
            }
            
            result = await engine.analyze("test input")
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_analyze_not_initialized(self):
        """Test analysis when engine not initialized"""
        engine = LangGraphAnalysisEngine()
        engine._is_initialized = False
        
        with patch('core.analysis.l2.langgraph_engine.analyze', return_value={"result": "fallback"}):
            result = await engine.analyze("test input")
            assert result == {"result": "fallback"}

    @pytest.mark.asyncio
    async def test_analyze_exception(self):
        """Test analysis with exception"""
        if not LANGGRAPH_AVAILABLE:
            pytest.skip("LangGraph not available")
        
        engine = LangGraphAnalysisEngine()
        if not engine._is_initialized:
            pytest.skip("Engine not initialized")
        
        with patch.object(engine.graph, 'ainvoke', side_effect=Exception("Analysis error")):
            with patch('core.analysis.l2.langgraph_engine.analyze', return_value={"result": "fallback"}):
                result = await engine.analyze("test input")
                assert result == {"result": "fallback"}

    @pytest.mark.asyncio
    async def test_fallback_analyze_success(self):
        """Test successful fallback analysis"""
        engine = LangGraphAnalysisEngine()
        
        with patch('core.analysis.l2.langgraph_engine.analyze', return_value={"result": "fallback success"}):
            result = await engine._fallback_analyze("test input")
            assert result == {"result": "fallback success"}

    @pytest.mark.asyncio
    async def test_fallback_analyze_exception(self):
        """Test fallback analysis with exception"""
        engine = LangGraphAnalysisEngine()
        
        with patch('core.analysis.l2.langgraph_engine.analyze', side_effect=Exception("Fallback error")):
            result = await engine._fallback_analyze("test input")
            assert "error" in result

    def test_get_status(self):
        """Test getting engine status"""
        engine = LangGraphAnalysisEngine()
        status = engine.get_status()
        assert "initialized" in status
        assert "langgraph_available" in status
        assert "config" in status
        assert status["langgraph_available"] == LANGGRAPH_AVAILABLE


class TestLangGraphAvailability:
    """Test suite for LangGraph availability"""

    def test_langgraph_available_constant(self):
        """Test LANGGRAPH_AVAILABLE constant"""
        assert isinstance(LANGGRAPH_AVAILABLE, bool)
