# -*- coding: utf-8 -*-
"""
L2 Analysis Layer - LangGraph-based Analysis Engine
Provides advanced AI orchestration using LangGraph for stateful, multi-step analysis
"""

import asyncio
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from loguru import logger

from core.observability_query import (
    DEFAULT_LATENCY_OFFSET_SECONDS,
    align_time_window,
    prepare_for_llm,
    sanitize_error_for_llm,
    validate_logql,
    validate_promql,
)

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

    async def _collect_data_step(self, state: AnalysisState) -> AnalysisState:
        """Collect relevant data for analysis with unified time window and safety guards."""
        logger.info("Collecting data for analysis...")
        state["current_step"] = AnalysisStep.COLLECT_DATA.value

        try:
            # Align time window across all observability sources and account for scrape/index delay.
            end = datetime.utcnow()
            start, end = align_time_window(
                end=end,
                duration_seconds=3600.0,
                latency_offset_seconds=DEFAULT_LATENCY_OFFSET_SECONDS,
            )

            # Collect metrics from L4 storage
            from core.storage.l4.storage_manager import get_l4_storage_manager

            l4_manager = get_l4_storage_manager()
            metrics_result: Any = {}
            logs_result: Any = {}

            if l4_manager:
                vm_storage = l4_manager.get_victoriametrics()
                loki_storage = l4_manager.get_loki()

                # Collect metrics and logs in parallel with a shared time window.
                coros: List[Any] = []
                if vm_storage:
                    coros.append(self._collect_metrics(vm_storage, state["input"], start, end))
                else:
                    coros.append(asyncio.sleep(0))
                if loki_storage:
                    coros.append(self._collect_logs(loki_storage, state["input"], start, end))
                else:
                    coros.append(asyncio.sleep(0))

                results = await asyncio.gather(*coros, return_exceptions=True)
                if vm_storage:
                    metrics_result = results[0] if not isinstance(results[0], Exception) else {}
                if loki_storage:
                    idx = 1 if vm_storage else 0
                    logs_result = results[idx] if not isinstance(results[idx], Exception) else {}

            # 扩展：从本地缓存、告警历史、配置审计日志、拓扑图收集更多维度
            self._collect_extended_context(state)

            # Redact PII, downsample, and enforce token budget before storing in context.
            state["context"]["metrics"] = prepare_for_llm(metrics_result)
            state["context"]["logs"] = prepare_for_llm(logs_result)
            state["context"]["_data_completeness"] = self._assess_completeness(
                metrics_result, logs_result
            )

            logger.info("Data collection completed")

        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            state["error"] = sanitize_error_for_llm(e)

        return state

    def _collect_extended_context(self, state: AnalysisState) -> None:
        """从引擎层缓存、告警、变更、拓扑等同步数据源补充上下文"""
        ctx = state["context"]
        try:
            from core.collector import get_cached_snapshot

            snap = get_cached_snapshot()
            if snap and isinstance(snap, dict):
                ctx["infrastructure_metrics"] = {
                    "cpu": snap.get("cpu", {}),
                    "memory": snap.get("memory", {}),
                    "disk": snap.get("disk", []),
                    "network": snap.get("network", {}),
                    "system": snap.get("system", {}),
                }
        except Exception as e:
            logger.warning(f"L2: infrastructure metrics collection failed: {e}")

        try:
            from core.alert_engine import alert_history

            alerts = [a for a in alert_history if isinstance(a, dict)]
            ctx["recent_alerts"] = alerts[:10]
            ctx["correlated_alerts"] = alerts[:20]
        except Exception as e:
            logger.warning(f"L2: alert collection failed: {e}")

        try:
            from core.config_manager import config_manager

            events = []
            for entry in getattr(config_manager, "_audit_log", [])[-10:]:
                if isinstance(entry, dict):
                    events.append(
                        {
                            "timestamp": entry.get("timestamp"),
                            "type": "config_change",
                            "target": entry.get("change", ""),
                            "description": str(entry.get("details", ""))[:200],
                        }
                    )
            ctx["change_events"] = events
        except Exception as e:
            logger.warning(f"L2: change event collection failed: {e}")

        try:
            from core.repair_engine import repair_history

            ctx["recent_repairs"] = list(repair_history)[:5]
        except Exception as e:
            logger.warning(f"L2: repair history collection failed: {e}")

        try:
            from core.root_cause_intelligence import root_cause_intelligence_engine

            topo_graph = getattr(root_cause_intelligence_engine, "topology_graph", {})
            dependencies: Dict[str, List[str]] = {}
            for node, deps in topo_graph.items():
                dependencies[str(node)] = [str(d) for d in deps]
            ctx["topology"] = {
                "nodes": list(topo_graph.keys()),
                "dependencies": dependencies,
            }
            ctx["dependencies"] = dependencies
        except Exception as e:
            logger.warning(f"L2: topology collection failed: {e}")

    def _analyze_step(self, state: AnalysisState) -> AnalysisState:
        """Perform analysis using AI engine"""
        logger.info("Performing analysis...")
        state["current_step"] = AnalysisStep.ANALYZE.value

        try:
            # Use existing AI engine for analysis
            from core.ai_engine import analyze

            # Prepare analysis prompt with context (sanitized and token-bounded)
            prompt = self._build_analysis_prompt(state["input"], state["context"])

            result = analyze(prompt)
            state["analysis_result"] = result

            logger.info("Analysis completed successfully")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            safe_error = sanitize_error_for_llm(e)
            state["error"] = safe_error
            state["analysis_result"] = {"error": safe_error}

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

            result = state["analysis_result"]
            missing_fields = []

            # 新 prompt 要求输出结构化候选列表
            if not isinstance(result, dict) or "candidates" not in result:
                missing_fields.append("candidates")
            else:
                candidates = result.get("candidates") or []
                if not candidates:
                    missing_fields.append("non-empty candidates")
                for i, c in enumerate(candidates):
                    for key in [
                        "root_cause",
                        "confidence",
                        "expected_observations_if_true",
                        "missing_data",
                        "is_verifiable",
                    ]:
                        if key not in c:
                            missing_fields.append(f"candidate[{i}].{key}")

            if "escalation_recommended" not in result:
                missing_fields.append("escalation_recommended")

            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                state["error"] = f"Missing fields: {missing_fields}"
            else:
                logger.info("Validation passed")

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state["error"] = sanitize_error_for_llm(e)

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

    async def _collect_metrics(
        self, vm_storage, query: str, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """Collect metrics from VictoriaMetrics over a bounded time window."""
        try:
            # Build and validate PromQL query based on input
            promql_query = self._build_promql_query(query)
            try:
                validate_promql(promql_query)
            except ValueError as exc:
                logger.warning("Built PromQL failed validation: %s; using safe fallback", exc)
                promql_query = "up"

            # Query metrics with range limits enforced by VM storage.
            result = await vm_storage.query_range(promql_query, start, end, step=60)

            data = prepare_for_llm(result) if isinstance(result, list) else result
            return {
                "query": promql_query,
                "data": data,
                "count": len(result) if isinstance(result, list) else 0,
            }
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {"_data_completeness": "failed", "error": sanitize_error_for_llm(e)}

    async def _collect_logs(
        self, loki_storage, query: str, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """Collect logs from Loki over a bounded time window."""
        try:
            # Build and validate LogQL query based on input
            logql_query = self._build_logql_query(query)
            try:
                validate_logql(logql_query)
            except ValueError as exc:
                logger.warning("Built LogQL failed validation: %s; using safe fallback", exc)
                logql_query = '{level=~"error|warn|warning"}'

            # Query logs with range limits enforced by Loki storage.
            result = await loki_storage.query_range(logql_query, start, end, limit=100)

            data = prepare_for_llm(result) if isinstance(result, list) else result
            return {
                "query": logql_query,
                "data": data,
                "count": len(result) if isinstance(result, list) else 0,
            }
        except Exception as e:
            logger.error(f"Failed to collect logs: {e}")
            return {"_data_completeness": "failed", "error": sanitize_error_for_llm(e)}

    def _assess_completeness(self, metrics_result: Any, logs_result: Any) -> Dict[str, Any]:
        """Assess observability data completeness for the LLM."""
        metrics_ok = (
            bool(metrics_result) and not metrics_result.get("_data_completeness") == "failed"
        )
        logs_ok = bool(logs_result) and not logs_result.get("_data_completeness") == "failed"
        return {
            "metrics_available": metrics_ok,
            "logs_available": logs_ok,
            "sources_missing": [
                name for name, ok in (("metrics", metrics_ok), ("logs", logs_ok)) if not ok
            ],
            "complete": metrics_ok and logs_ok,
        }

    def _build_analysis_prompt(self, input: str, context: Dict[str, Any]) -> str:
        """Build analysis prompt with context following the diagnostic checklist"""
        # Context values are already sanitized/prepare_for_llm'd; stringify safely.
        context_serialized = prepare_for_llm(context, max_tokens=12000)
        prompt = f"Analyze the following issue and produce a structured JSON response.\n{input}\n\n"

        if context_serialized.get("metrics"):
            prompt += f"Relevant metrics:\n{context_serialized['metrics']}\n\n"
        if context_serialized.get("logs"):
            prompt += f"Relevant logs:\n{context_serialized['logs']}\n\n"
        if context_serialized.get("service_metrics"):
            prompt += f"Service metrics:\n{context_serialized['service_metrics']}\n\n"
        if context_serialized.get("infrastructure_metrics"):
            prompt += f"Infrastructure metrics:\n{context_serialized['infrastructure_metrics']}\n\n"
        if context_serialized.get("dependencies"):
            prompt += f"Service dependencies/topology:\n{context_serialized['dependencies']}\n\n"
        if context_serialized.get("change_events"):
            prompt += f"Recent change events:\n{context_serialized['change_events']}\n\n"
        if context_serialized.get("correlated_alerts"):
            prompt += f"Correlated alerts:\n{context_serialized['correlated_alerts']}\n\n"

        completeness = context.get("_data_completeness", {})
        prompt += (
            f"Data completeness assessment: {completeness}\n"
            "If any source is missing or data is contradictory, set escalation_recommended to true and do not guess.\n\n"  # noqa: E501
        )

        prompt += "Please provide a JSON object with:\n"
        prompt += "- data_assessment: {reliability_score, reliability_concerns}\n"
        prompt += "- candidates: a list of 2-5 ranked root cause candidates, each with root_cause, confidence (0-1), expected_observations_if_true, missing_data, is_verifiable, evidence\n"  # noqa: E501
        prompt += (
            "- multi_root_cause_note: whether multiple factors are jointly causing the issue\n"
        )
        prompt += "- escalation_recommended: true/false\n"
        prompt += "- escalation_reason: required if escalation_recommended is true\n"
        prompt += "- recommended_action: concrete remediation step\n"
        prompt += "If confidence of all candidates is below 0.6 or data is missing/contradictory, set escalation_recommended to true and do not guess.\n"  # noqa: E501

        return prompt

    def _build_promql_query(self, input: str) -> str:
        """Build PromQL query from input covering more diagnostic dimensions"""
        text = input.lower()
        if any(k in text for k in ["latency", "response time", "slow"]):
            query = "histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))"
        elif any(k in text for k in ["error", "5xx", "failure rate"]):
            query = "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m])"
        elif any(k in text for k in ["packet", "drop", "network", "nic", "丢包"]):
            query = "rate(node_network_receive_drop_total[1m]) or rate(node_network_transmit_drop_total[1m])"  # noqa: E501
        elif any(k in text for k in ["connection", "pool", "连接池"]):
            query = "connection_pool_usage_percent"
        elif any(k in text for k in ["gc", "jvm", "garbage collection"]):
            query = "jvm_gc_pause_seconds"
        elif any(k in text for k in ["dns", "resolve"]):
            query = "dns_lookup_error_rate"
        elif any(k in text for k in ["traffic", "qps", "rps", "throughput"]):
            query = "rate(http_requests_total[5m])"
        elif "cpu" in text:
            query = "cpu.usage_percent"
        elif "memory" in text:
            query = "memory.used_gb"
        elif "disk" in text:
            query = "disk.used_gb"
        else:
            query = "{__name__=~'cpu.usage_percent|memory.used_gb|request_duration_seconds|http_requests_total'}"  # noqa: E501

        try:
            validate_promql(query)
        except ValueError as exc:
            logger.warning("PromQL template failed validation: %s; using safe fallback 'up'", exc)
            query = "up"
        return query

    def _build_logql_query(self, input: str) -> str:
        """Build LogQL query from input focusing on error/warn logs and service context"""
        # Sanitize keywords to safe log word characters before building the regex.
        allowed = re.compile(r"[^A-Za-z0-9_\-./@]")
        keywords = [allowed.sub("", kw) for kw in input.split()[:3] if allowed.sub("", kw)]
        if keywords:
            keyword_filter = ' |~ "' + "|".join(keywords) + '"'
        else:
            keyword_filter = ""
        return f'{{level=~"error|warn|warning"}}{keyword_filter}'

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

            # Run the graph (async invocation if the compiled graph supports it)
            if self.graph is None:
                raise RuntimeError("Graph not initialized")
            if hasattr(self.graph, "ainvoke"):
                final_state = await self.graph.ainvoke(initial_state)
            else:
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

            # Sanitize context before passing to the fallback engine if possible
            safe_context = prepare_for_llm(context or {}, max_tokens=12000)
            result = analyze(input, rich_context=safe_context)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return {"error": sanitize_error_for_llm(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "initialized": self._is_initialized,
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "config": self.config,
        }
