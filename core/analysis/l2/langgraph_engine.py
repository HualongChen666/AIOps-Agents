# -*- coding: utf-8 -*-
"""
L2 Analysis Layer - LangGraph-based Analysis Engine
Provides advanced AI orchestration using LangGraph for stateful, multi-step analysis
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from loguru import logger

# LangGraph imports (will be added to requirements)
try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available - L2 Analysis Layer will use fallback")


class AnalysisState(TypedDict):
    """State for LangGraph analysis workflow"""

    input: str
    context: Dict[str, Any]
    analysis_result: Optional[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    current_step: str
    error: Optional[str]


class AnalysisStep(Enum):
    """Analysis workflow steps"""

    INITIALIZE = "initialize"
    COLLECT_DATA = "collect_data"
    ANALYZE = "analyze"
    VALIDATE = "validate"
    FINALIZE = "finalize"


class LangGraphAnalysisEngine:
    """
    LangGraph-based analysis engine for L2 Analysis Layer

    This engine uses LangGraph to create stateful, multi-step analysis workflows
    that can:
    - Maintain conversation context
    - Chain multiple analysis steps
    - Use tools for data collection and validation
    - Handle errors and retries
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config
        self.graph: Any = None
        self._is_initialized = False

        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not installed - using fallback analysis engine")
            return

        self._build_graph()

    def _build_graph(self) -> None:
        """Build the LangGraph workflow"""
        try:
            workflow = StateGraph(AnalysisState)

            # Add nodes for each analysis step
            workflow.add_node("initialize", self._initialize_step)
            workflow.add_node("collect_data", self._collect_data_step)
            workflow.add_node("analyze", self._analyze_step)
            workflow.add_node("validate", self._validate_step)
            workflow.add_node("finalize", self._finalize_step)

            # Define edges
            workflow.set_entry_point("initialize")
            workflow.add_edge("initialize", "collect_data")
            workflow.add_edge("collect_data", "analyze")
            workflow.add_edge("analyze", "validate")
            workflow.add_conditional_edges(
                "validate", self._should_retry, {"retry": "analyze", "finalize": "finalize"}
            )
            workflow.add_edge("finalize", END)

            self.graph = workflow.compile()
            self._is_initialized = True
            logger.info("LangGraph analysis engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to build LangGraph: {e}")
            self._is_initialized = False

    def _initialize_step(self, state: AnalysisState) -> AnalysisState:
        """Initialize analysis state"""
        logger.info(f"Initializing analysis for: {state['input'][:50]}...")
        state["current_step"] = AnalysisStep.INITIALIZE.value
        state["context"] = state.get("context", {})
        state["analysis_result"] = None
        state["error"] = None
        return state

    def _collect_data_step(self, state: AnalysisState) -> AnalysisState:
        """Collect relevant data for analysis"""
        logger.info("Collecting data for analysis...")
        state["current_step"] = AnalysisStep.COLLECT_DATA.value

        try:
            # Collect metrics from L4 storage
            from core.storage.l4.storage_manager import get_l4_storage_manager

            l4_manager = get_l4_storage_manager()

            if l4_manager:
                vm_storage = l4_manager.get_victoriametrics()
                if vm_storage:
                    # Collect recent metrics
                    metrics = self._collect_metrics(vm_storage, state["input"])
                    state["context"]["metrics"] = metrics

                loki_storage = l4_manager.get_loki()
                if loki_storage:
                    # Collect relevant logs
                    logs = self._collect_logs(loki_storage, state["input"])
                    state["context"]["logs"] = logs

            logger.info("Data collection completed")

        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            state["error"] = str(e)

        return state

    def _analyze_step(self, state: AnalysisState) -> AnalysisState:
        """Perform analysis using AI engine"""
        logger.info("Performing analysis...")
        state["current_step"] = AnalysisStep.ANALYZE.value

        try:
            # Use existing AI engine for analysis
            from core.ai_engine import analyze

            # Prepare analysis prompt with context
            prompt = self._build_analysis_prompt(state["input"], state["context"])

            result = analyze(prompt)
            state["analysis_result"] = result

            logger.info("Analysis completed successfully")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            state["error"] = str(e)
            state["analysis_result"] = {"error": str(e)}

        return state

    def _validate_step(self, state: AnalysisState) -> AnalysisState:
        """Validate analysis results"""
        logger.info("Validating analysis results...")
        state["current_step"] = AnalysisStep.VALIDATE.value

        try:
            # Validate result structure
            if not state["analysis_result"]:
                state["error"] = "No analysis result to validate"
                return state

            # Check for required fields
            required_fields = ["root_cause", "severity", "recommendation"]
            missing_fields = [f for f in required_fields if f not in state["analysis_result"]]

            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                state["error"] = f"Missing fields: {missing_fields}"
            else:
                logger.info("Validation passed")

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state["error"] = str(e)

        return state

    def _finalize_step(self, state: AnalysisState) -> AnalysisState:
        """Finalize analysis and prepare output"""
        logger.info("Finalizing analysis...")
        state["current_step"] = AnalysisStep.FINALIZE.value

        # Add metadata
        if state["analysis_result"] is not None:
            state["analysis_result"]["metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "engine": "langgraph",
                "steps": [s.value for s in AnalysisStep],
            }

        return state

    def _should_retry(self, state: AnalysisState) -> str:
        """Determine whether to retry analysis"""
        if state.get("error"):
            logger.info("Error detected, retrying analysis...")
            return "retry"
        return "finalize"

    def _collect_metrics(self, vm_storage, query: str) -> Dict[str, Any]:
        """Collect metrics from VictoriaMetrics"""
        try:
            # Build PromQL query based on input
            promql_query = self._build_promql_query(query)

            # Query metrics
            result = vm_storage.query({"query": promql_query})

            return {"query": promql_query, "data": result, "count": len(result)}
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}

    def _collect_logs(self, loki_storage, query: str) -> Dict[str, Any]:
        """Collect logs from Loki"""
        try:
            # Build LogQL query based on input
            logql_query = self._build_logql_query(query)

            # Query logs
            result = loki_storage.query({"query": logql_query, "limit": 100})

            return {"query": logql_query, "data": result, "count": len(result)}
        except Exception as e:
            logger.error(f"Failed to collect logs: {e}")
            return {}

    def _build_analysis_prompt(self, input: str, context: Dict[str, Any]) -> str:
        """Build analysis prompt with context"""
        prompt = f"Analyze the following issue:\n{input}\n\n"

        if context.get("metrics"):
            prompt += f"Relevant metrics:\n{context['metrics']}\n\n"

        if context.get("logs"):
            prompt += f"Relevant logs:\n{context['logs']}\n\n"

        prompt += "Please provide:\n"
        prompt += "1. Root cause analysis\n"
        prompt += "2. Severity assessment\n"
        prompt += "3. Recommended actions\n"

        return prompt

    def _build_promql_query(self, input: str) -> str:
        """Build PromQL query from input"""
        # Simple keyword matching for now
        if "cpu" in input.lower():
            return "cpu.usage_percent"
        elif "memory" in input.lower():
            return "memory.used_gb"
        elif "disk" in input.lower():
            return "disk.used_gb"
        else:
            return "cpu.usage_percent"  # Default

    def _build_logql_query(self, input: str) -> str:
        """Build LogQL query from input"""
        # Simple keyword matching for now
        keywords = input.split()[:3]  # Take first 3 keywords
        query = "|".join([f'~"{kw}"' for kw in keywords if kw])
        return f"{{{query}}}"

    async def analyze(self, input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run analysis using LangGraph workflow

        Args:
            input: Analysis input/query
            context: Optional context data

        Returns:
            Analysis result
        """
        if not self._is_initialized:
            # Fallback to simple analysis
            logger.warning("LangGraph not initialized, using fallback")
            return await self._fallback_analyze(input, context)

        try:
            initial_state: AnalysisState = {
                "input": input,
                "context": context or {},
                "analysis_result": None,
                "tool_calls": [],
                "current_step": "",
                "error": None,
            }

            # Run the graph
            if self.graph is None:
                raise RuntimeError("Graph not initialized")
            final_state = self.graph.invoke(initial_state)

            return final_state["analysis_result"] or {"error": "Analysis failed"}

        except Exception as e:
            logger.error(f"LangGraph analysis failed: {e}")
            return await self._fallback_analyze(input, context)

    async def _fallback_analyze(
        self, input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fallback analysis when LangGraph is not available"""
        try:
            from core.ai_engine import analyze

            result = analyze(input)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "initialized": self._is_initialized,
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "config": self.config,
        }
