# -*- coding: utf-8 -*-
"""Agent orchestration core logic for the microservice (tasks 33.2-33.10)."""

from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional, cast

from loguru import logger

from core.context_compression import compress_context

from . import metrics
from .cache import CacheManager
from .config import settings
from .retry import AgentRetryEngine
from .schemas import (
    AgentRequest,
    AgentResponse,
    AgentResult,
    AgentType,
    AggregateRequest,
    AggregateResponse,
    CollaborateRequest,
    CollaborateResponse,
    CoordinateRequest,
    CoordinateResponse,
    DecomposeRequest,
    DecomposeResponse,
    ErrorHandleRequest,
    ErrorHandleResponse,
    StatsResponse,
    SubTask,
)

try:
    from services.scenario_memory_service.schemas import (
        EventMemory,
        LearnExperienceRequest,
        StoreEventRequest,
    )
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    LearnExperienceRequest = None  # type: ignore
    StoreEventRequest = None  # type: ignore
    EventMemory = None  # type: ignore


class LangGraphAdapter:
    """Optional LangGraph integration with deterministic fallback."""

    async def execute(self, graph: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a LangGraph-compatible graph if available."""
        try:
            from langgraph.graph import StateGraph

            if isinstance(graph, StateGraph):
                compiled = graph.compile()
                return cast(Dict[str, Any], await compiled.ainvoke(inputs))
        except Exception as exc:
            logger.debug(f"LangGraph not available ({exc}); using fallback")

        return self._fallback_execute(inputs)

    @staticmethod
    def _fallback_execute(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback for graph execution."""
        return {
            "result": f"fallback result for task: {inputs.get('task', '')}",
            "agent_type": inputs.get("agent_type", AgentType.GENERIC.value),
        }


class AgentOrchestrator:
    """Multi-agent orchestration service implementing task 33."""

    def __init__(
        self,
        llm_model: Optional[Any] = None,
        cache: Optional[CacheManager] = None,
        retry_engine: Optional[AgentRetryEngine] = None,
        memory_orchestrator: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self._llm_model = llm_model
        self.cache = cache or CacheManager(settings.redis_url)
        self.retry_engine = retry_engine or AgentRetryEngine(settings.retry_policy)
        self.langgraph = LangGraphAdapter()
        self._request_counts: Dict[str, int] = {}

        # Cross-session memory integration (best-effort; degrades if unavailable)
        self.memory = memory_orchestrator
        if self.memory is None:
            try:
                from services.scenario_memory_service.cache import CacheManager as SMCache
                from services.scenario_memory_service.config import settings as sm_settings
                from services.scenario_memory_service.orchestrator import (
                    ScenarioMemoryOrchestrator,
                )

                self.memory = ScenarioMemoryOrchestrator(cache=SMCache(sm_settings.redis_url))
            except Exception as exc:
                logger.debug(f"Scenario memory not available for agent orchestrator: {exc}")
                self.memory = None

    # ------------------------------------------------------------------
    # Utility / lifecycle
    # ------------------------------------------------------------------
    def _plan_id(self) -> str:
        return str(uuid.uuid4())

    def _increment_count(self, operation: str) -> None:
        self._request_counts[operation] = self._request_counts.get(operation, 0) + 1

    async def get_stats(self) -> StatsResponse:
        return StatsResponse(
            service=self.settings.service_name,
            request_counts=self._request_counts.copy(),
            retry_policies=self.retry_engine.list_policies(),
            cache_size=len(self.cache._memory),
        )

    def list_methods(self) -> List[str]:
        return [
            "decompose_task",
            "run_agent",
            "coordinate",
            "collaborate",
            "aggregate",
            "handle_error",
            "monitor_agent",
            "diagnostic_agent",
            "repair_agent",
            "analysis_agent",
            "get_stats",
        ]

    # ------------------------------------------------------------------
    # 33.3 Task decomposition
    # ------------------------------------------------------------------
    async def decompose_task(self, request: DecomposeRequest) -> DecomposeResponse:
        """Decompose a high-level task into subtasks."""
        start = time.time()
        metrics.AGENT_REQUESTS_TOTAL.labels(
            operation="decompose",
            agent_type="planner",
        ).inc()

        subtasks = self._build_subtasks(request)

        latency = (time.time() - start) * 1000
        metrics.AGENT_REQUEST_LATENCY.labels(operation="decompose").observe(latency / 1000.0)
        self._increment_count("decompose")
        return DecomposeResponse(
            task=request.task,
            subtasks=subtasks,
            plan_id=self._plan_id(),
        )

    def _build_subtasks(self, request: DecomposeRequest) -> List[SubTask]:
        """Build subtasks using keyword heuristics."""
        task = request.task.lower()
        subtasks: List[SubTask] = []

        if any(k in task for k in ("monitor", "observe", "track", "collect")):
            subtasks.append(
                SubTask(
                    task_id="t1",
                    description="Collect and observe relevant metrics.",
                    agent_type=AgentType.MONITOR,
                )
            )
        if any(k in task for k in ("diagnose", "root cause", "analyse")):
            subtasks.append(
                SubTask(
                    task_id="t2",
                    description="Diagnose the root cause of the issue.",
                    agent_type=AgentType.DIAGNOSTIC,
                )
            )
        if any(k in task for k in ("repair", "fix", "remediate", "resolve")):
            subtasks.append(
                SubTask(
                    task_id="t3",
                    description="Execute remediation actions.",
                    agent_type=AgentType.REPAIR,
                )
            )
        if any(k in task for k in ("report", "summarize", "analysis", "assess")) or not subtasks:
            subtasks.append(
                SubTask(
                    task_id="t4",
                    description="Analyze results and produce a summary.",
                    agent_type=AgentType.ANALYSIS,
                )
            )

        # Limit and add sequential dependencies
        max_tasks = max(1, min(request.max_subtasks, self.settings.max_agents_per_plan))
        limited = subtasks[:max_tasks]
        for idx, st in enumerate(limited):
            if idx > 0 and not st.dependencies:
                st.dependencies = [limited[idx - 1].task_id]
        return limited

    # ------------------------------------------------------------------
    # 33.2 Multi-agent collaboration & single agent execution
    # ------------------------------------------------------------------
    async def run_agent(self, request: AgentRequest) -> AgentResponse:
        """Run a single agent by type with cross-session memory integration."""
        start = time.time()
        metrics.AGENT_REQUESTS_TOTAL.labels(
            operation="run_agent",
            agent_type=request.agent_type.value,
        ).inc()
        metrics.AGENT_ACTIVE_AGENTS.labels(agent_type=request.agent_type.value).inc()

        # Ensure session isolation.
        session_id = request.session_id or str(uuid.uuid4())
        request.context.setdefault("session_id", session_id)

        # Retrieve relevant cross-session experiences before reasoning.
        if request.enable_memory and self.memory is not None:
            try:
                task = request.input_data.get("task", "")
                relevant = await self.memory.find_experiences(
                    query=task,
                    top_k=3,
                    session_id=None,  # allow cross-session retrieval
                )
                if relevant:
                    request.context["relevant_experiences"] = [
                        {
                            "situation": e.situation,
                            "action": e.action,
                            "outcome": e.outcome,
                            "confidence": e.confidence,
                        }
                        for e in relevant
                    ]
            except Exception as exc:
                logger.debug(f"Experience retrieval failed: {exc}")

        if request.agent_type == AgentType.MONITOR:
            result = await self.monitor_agent(request)
        elif request.agent_type == AgentType.DIAGNOSTIC:
            result = await self.diagnostic_agent(request)
        elif request.agent_type == AgentType.REPAIR:
            result = await self.repair_agent(request)
        elif request.agent_type == AgentType.ANALYSIS:
            result = await self.analysis_agent(request)
        else:
            result = await self._generic_agent(request)

        # Persist experience from this agent run.
        if request.enable_memory and self.memory is not None:
            try:
                task = request.input_data.get("task", "")
                await self.memory.learn_experience(
                    request=LearnExperienceRequest(
                        situation=task[:200],
                        action=request.agent_type.value,
                        outcome=result.output[:500],
                        confidence=result.confidence,
                        session_id=session_id,
                    )
                )
            except Exception as exc:
                logger.debug(f"Experience save failed: {exc}")

        metrics.AGENT_ACTIVE_AGENTS.labels(agent_type=request.agent_type.value).dec()
        latency = (time.time() - start) * 1000
        metrics.AGENT_REQUEST_LATENCY.labels(operation="run_agent").observe(latency / 1000.0)
        self._increment_count("run_agent")
        return AgentResponse(agent_type=request.agent_type.value, result=result, latency_ms=latency)

    # ------------------------------------------------------------------
    # 33.7-33.10 Specific agents
    # ------------------------------------------------------------------
    async def monitor_agent(self, request: AgentRequest) -> AgentResult:
        """Monitoring agent logic."""
        output = await self._agent_llm_or_fallback(
            request.agent_type.value,
            "monitor",
            request,
        )
        return AgentResult(
            agent_type=request.agent_type.value,
            output=output,
            confidence=0.7,
            metadata={"metrics": request.input_data.get("metrics", [])},
        )

    async def diagnostic_agent(self, request: AgentRequest) -> AgentResult:
        """Diagnostic agent logic."""
        output = await self._agent_llm_or_fallback(
            request.agent_type.value,
            "diagnose",
            request,
        )
        return AgentResult(
            agent_type=request.agent_type.value,
            output=output,
            confidence=0.8,
            metadata={"symptoms": request.input_data.get("symptoms", [])},
        )

    async def repair_agent(self, request: AgentRequest) -> AgentResult:
        """Repair agent logic."""
        output = await self._agent_llm_or_fallback(
            request.agent_type.value,
            "repair",
            request,
        )
        return AgentResult(
            agent_type=request.agent_type.value,
            output=output,
            confidence=0.75,
            metadata={"actions": request.input_data.get("actions", [])},
        )

    async def analysis_agent(self, request: AgentRequest) -> AgentResult:
        """Analysis agent logic."""
        output = await self._agent_llm_or_fallback(
            request.agent_type.value,
            "analyze",
            request,
        )
        return AgentResult(
            agent_type=request.agent_type.value,
            output=output,
            confidence=0.85,
            metadata={"findings": request.input_data.get("findings", [])},
        )

    async def _generic_agent(self, request: AgentRequest) -> AgentResult:
        """Generic agent fallback."""
        output = await self._agent_llm_or_fallback(
            request.agent_type.value,
            "execute",
            request,
        )
        return AgentResult(
            agent_type=request.agent_type.value,
            output=output,
            confidence=0.6,
        )

    async def _agent_llm_or_fallback(
        self,
        agent_type: str,
        verb: str,
        request: AgentRequest,
    ) -> str:
        """Use an LLM if configured, otherwise a deterministic template."""
        if not self.settings.openai_api_key:
            return self._agent_fallback(agent_type, verb, request)

        try:
            from langchain.schema import HumanMessage
            from langchain_openai import ChatOpenAI

            # Compress context to a safe token budget for the chosen model.
            compressed_context = compress_context(
                request.context,
                max_tokens=3000,
                protected_keys={"session_id", "relevant_experiences"},
            )

            model = ChatOpenAI(  # type: ignore[call-arg]
                model="gpt-3.5-turbo",
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                openai_api_key=self.settings.openai_api_key or None,
            )
            prompt = (
                f"You are a {agent_type} agent. {verb} the following task.\n"
                f"Task: {request.input_data.get('task', '')}\n"
                f"Context: {compressed_context}\nAnswer:"
            )
            result = await model.ainvoke([HumanMessage(content=prompt)])
            return str(result.content if hasattr(result, "content") else result)
        except Exception as exc:
            logger.warning(f"LLM call failed for {agent_type} ({exc}); using fallback")

        return self._agent_fallback(agent_type, verb, request)

    @staticmethod
    def _agent_fallback(agent_type: str, verb: str, request: AgentRequest) -> str:
        """Deterministic fallback for agent output."""
        task = request.input_data.get("task", "")
        ctx = request.context
        return f"[{agent_type}] {verb} task: {task}. " f"Context keys: {list(ctx.keys())}"

    # ------------------------------------------------------------------
    # 33.4 Execution coordination
    # ------------------------------------------------------------------
    async def coordinate(self, request: CoordinateRequest) -> CoordinateResponse:
        """Coordinate a plan of subtasks."""
        start = time.time()
        metrics.AGENT_REQUESTS_TOTAL.labels(
            operation="coordinate",
            agent_type="planner",
        ).inc()
        metrics.AGENT_PLAN_SIZE.set(len(request.subtasks))

        completed: List[str] = []
        failed: List[str] = []
        results: List[AgentResult] = []
        plan_id = request.plan_id or self._plan_id()

        pending = {st.task_id: st for st in request.subtasks}
        while pending:
            ready = [st for st in pending.values() if all(d in completed for d in st.dependencies)]
            if not ready:
                failed.extend(pending.keys())
                break

            if request.run_parallel:
                batch_results = await self._run_subtasks_parallel(ready, request.context)
            else:
                batch_results = await self._run_subtasks_sequential(ready, request.context)

            for task_id, result, ok in batch_results:
                del pending[task_id]
                if ok:
                    completed.append(task_id)
                    results.append(result)
                else:
                    failed.append(task_id)

        latency = (time.time() - start) * 1000
        metrics.AGENT_REQUEST_LATENCY.labels(operation="coordinate").observe(latency / 1000.0)
        self._increment_count("coordinate")
        return CoordinateResponse(
            plan_id=plan_id,
            results=results,
            completed=completed,
            failed=failed,
            latency_ms=latency,
        )

    async def _run_subtasks_sequential(
        self,
        ready: List[SubTask],
        context: Dict[str, Any],
    ) -> List[tuple[str, AgentResult, bool]]:
        """Run ready subtasks sequentially."""
        out: List[tuple[str, AgentResult, bool]] = []
        for st in ready:
            result, ok = await self._execute_subtask(st, context)
            out.append((st.task_id, result, ok))
        return out

    async def _run_subtasks_parallel(
        self,
        ready: List[SubTask],
        context: Dict[str, Any],
    ) -> List[tuple[str, AgentResult, bool]]:
        """Run ready subtasks concurrently."""
        import asyncio

        tasks = [self._execute_subtask(st, context) for st in ready]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[tuple[str, AgentResult, bool]] = []
        for st, output in zip(ready, outputs):
            if isinstance(output, BaseException):
                logger.warning(f"Subtask {st.task_id} failed: {output}")
                empty = AgentResult(agent_type=st.agent_type.value, output="")
                out.append((st.task_id, empty, False))
            else:
                out.append((st.task_id, output[0], output[1]))
        return out

    async def _execute_subtask(
        self,
        subtask: SubTask,
        context: Dict[str, Any],
    ) -> tuple[AgentResult, bool]:
        """Execute a single subtask using the agent runner."""
        try:
            request = AgentRequest(
                agent_type=subtask.agent_type,
                input_data={"task": subtask.description, **subtask.input_data},
                context=context,
            )
            response = await self.run_agent(request)
            return response.result, True
        except Exception as exc:
            logger.warning(f"Agent {subtask.agent_type} failed: {exc}")
            result = AgentResult(agent_type=subtask.agent_type.value, output=str(exc))
            return result, False

    # ------------------------------------------------------------------
    # 33.2 / 33.5 Collaboration and aggregation
    # ------------------------------------------------------------------
    async def collaborate(self, request: CollaborateRequest) -> CollaborateResponse:
        """Multi-agent collaboration for a task."""
        start = time.time()
        metrics.AGENT_REQUESTS_TOTAL.labels(
            operation="collaborate",
            agent_type="multi",
        ).inc()

        decompose = await self.decompose_task(
            DecomposeRequest(task=request.task, context=request.context)
        )
        agent_types = request.agent_types or [st.agent_type for st in decompose.subtasks]

        results: List[AgentResult] = []
        if request.run_parallel:
            results = await self._run_agents_parallel(agent_types, request)
        else:
            results = await self._run_agents_sequential(agent_types, request)

        aggregated = await self.aggregate(
            AggregateRequest(results=results, strategy=request.aggregate_strategy)
        )

        latency = (time.time() - start) * 1000
        metrics.AGENT_REQUEST_LATENCY.labels(operation="collaborate").observe(latency / 1000.0)
        self._increment_count("collaborate")
        return CollaborateResponse(
            task=request.task,
            results=results,
            aggregated_output=aggregated.aggregated_output,
            plan_id=decompose.plan_id,
            latency_ms=latency,
        )

    async def _run_agents_sequential(
        self,
        agent_types: List[AgentType],
        request: CollaborateRequest,
    ) -> List[AgentResult]:
        """Run a list of agents sequentially."""
        results: List[AgentResult] = []
        for agent_type in agent_types:
            response = await self.run_agent(
                AgentRequest(
                    agent_type=agent_type,
                    input_data={"task": request.task},
                    context=request.context,
                )
            )
            results.append(response.result)
        return results

    async def _run_agents_parallel(
        self,
        agent_types: List[AgentType],
        request: CollaborateRequest,
    ) -> List[AgentResult]:
        """Run a list of agents in parallel."""
        import asyncio

        tasks = [
            self.run_agent(
                AgentRequest(
                    agent_type=agent_type,
                    input_data={"task": request.task},
                    context=request.context,
                )
            )
            for agent_type in agent_types
        ]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)
        results: List[AgentResult] = []
        for agent_type, output in zip(agent_types, outputs):
            if isinstance(output, BaseException):
                logger.warning(f"Agent {agent_type} failed: {output}")
                results.append(AgentResult(agent_type=agent_type.value, output=str(output)))
            else:
                results.append(output.result)
        return results

    async def aggregate(self, request: AggregateRequest) -> AggregateResponse:
        """Aggregate multiple agent results."""
        metrics.AGENT_REQUESTS_TOTAL.labels(
            operation="aggregate",
            agent_type="aggregator",
        ).inc()

        if request.strategy == "concat":
            output = "\n".join(f"[{r.agent_type}] {r.output}" for r in request.results)
        elif request.strategy == "merge":
            output = " ".join(r.output for r in request.results)
        elif request.strategy == "vote":
            output = self._vote_output(request.results)
        else:
            output = "\n".join(f"[{r.agent_type}] {r.output}" for r in request.results)

        self._increment_count("aggregate")
        return AggregateResponse(
            aggregated_output=output,
            result_count=len(request.results),
            strategy=request.strategy,
        )

    @staticmethod
    def _vote_output(results: List[AgentResult]) -> str:
        """Simple majority-vote aggregation of outputs."""
        if not results:
            return ""
        outputs = [r.output for r in results]
        counts: Counter[str] = Counter(outputs)
        return counts.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # 33.6 Error handling
    # ------------------------------------------------------------------
    async def handle_error(self, request: ErrorHandleRequest) -> ErrorHandleResponse:
        """Detect and recover from errors."""
        start = time.time()
        metrics.AGENT_REQUESTS_TOTAL.labels(
            operation="handle_error",
            agent_type="recovery",
        ).inc()

        error_text = request.error.lower()
        strategy = "retry"
        next_steps: List[str] = ["retry the operation"]

        if any(k in error_text for k in ("timeout", "connection", "refused")):
            strategy = "retry_with_backoff"
            next_steps = ["wait", "retry with exponential backoff", "verify network"]
        elif any(k in error_text for k in ("permission", "auth", "unauthorized")):
            strategy = "escalate"
            next_steps = ["check credentials", "escalate to security team"]
        elif any(k in error_text for k in ("not found", "404", "missing")):
            strategy = "verify_input"
            next_steps = ["verify resource exists", "update references"]
        elif any(k in error_text for k in ("rate limit", "quota", "throttle")):
            strategy = "throttle"
            next_steps = ["reduce request rate", "increase quota", "retry later"]
        else:
            strategy = "retry"
            next_steps = ["retry", "collect more diagnostics", "escalate if persists"]

        recovered = strategy not in ("escalate",)
        latency = (time.time() - start) * 1000
        metrics.AGENT_REQUEST_LATENCY.labels(operation="handle_error").observe(latency / 1000.0)
        metrics.AGENT_ERROR_RECOVERIES_TOTAL.labels(strategy=strategy).inc()
        self._increment_count("handle_error")
        return ErrorHandleResponse(
            recovered=recovered,
            strategy=strategy,
            next_steps=next_steps,
            message=f"Recovered={recovered} using strategy '{strategy}'",
        )