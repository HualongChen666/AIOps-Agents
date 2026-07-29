# -*- coding: utf-8 -*-
"""
Core LangGraph-style workflow engine used by the core.ai.langgraph package.

This is a lightweight, test-compatible workflow DSL and executor.
It is intentionally dependency-free so it can be exercised without LangGraph installed.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


class WorkflowState(Enum):
    """Workflow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowContext:
    """Mutable execution context shared between workflow nodes."""

    def __init__(self, input_data: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = dict(input_data or {})
        self.history: List[Dict[str, Any]] = []

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def add_history(self, node: str, result: Any) -> None:
        self.history.append({"node": node, "result": result, "timestamp": time.time()})


class WorkflowEdge:
    """Directed edge between two workflow nodes with an optional condition."""

    def __init__(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable[[WorkflowContext], Any]] = None,
    ):
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition

    def should_traverse(self, ctx: WorkflowContext) -> bool:
        if self.condition is None:
            return True
        return bool(self.condition(ctx))


class WorkflowNode(ABC):
    """Base class for workflow nodes."""

    node_type: str = "base"

    def __init__(self, name: str, **kwargs: Any):
        self.name = name
        self.config = kwargs

    @abstractmethod
    async def execute(self, ctx: WorkflowContext) -> Any: ...


class LLMNode(WorkflowNode):
    """Simple LLM node that formats a prompt from context."""

    node_type = "llm"

    def __init__(
        self,
        name: str,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_template: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)
        self.model_name = model_name or model or kwargs.get("model") or "gpt-4"
        self.prompt_template = prompt_template or prompt or ""

    def _format_prompt(self, ctx: WorkflowContext) -> str:
        template = self.prompt_template
        if not template:
            return ""
        try:
            return template.format(**ctx._data)
        except (KeyError, ValueError):
            return template

    async def execute(self, ctx: WorkflowContext) -> str:
        prompt = self._format_prompt(ctx)
        return f"LLM response to: {prompt}"


class ToolNode(WorkflowNode):
    """Workflow node wrapping a callable tool."""

    node_type = "tool"

    def __init__(
        self,
        name: str,
        tool_function: Optional[Callable[..., Any]] = None,
        tool_func: Optional[Callable[..., Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)
        self.tool_function = tool_function or tool_func
        self.tool_config = tool_config or {}

    async def execute(self, ctx: WorkflowContext) -> Any:
        if self.tool_function is None:
            return None
        func = self.tool_function
        if asyncio.iscoroutinefunction(func):
            if self.tool_config:
                return await func(ctx, **self.tool_config)
            return await func(ctx)
        if self.tool_config:
            return func(ctx, **self.tool_config)
        return func(ctx)


class ConditionalNode(WorkflowNode):
    """Branching node that returns one of two branch names."""

    node_type = "conditional"

    def __init__(
        self,
        name: str,
        condition: Callable[[WorkflowContext], Any],
        true_branch: str,
        false_branch: str,
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)
        self.condition = condition
        self.true_branch = true_branch
        self.false_branch = false_branch

    async def execute(self, ctx: WorkflowContext) -> str:
        result = self.condition(ctx)
        if asyncio.iscoroutine(result):
            result = await result
        return self.true_branch if result else self.false_branch


class ParallelNode(WorkflowNode):
    """Node that executes child nodes concurrently."""

    node_type = "parallel"

    def __init__(self, name: str, nodes: Optional[List[WorkflowNode]] = None, **kwargs: Any):
        super().__init__(name, **kwargs)
        self.nodes = nodes or []

    async def execute(self, ctx: WorkflowContext) -> Dict[str, Any]:
        results = await asyncio.gather(*(node.execute(ctx) for node in self.nodes))
        return {node.name: result for node, result in zip(self.nodes, results)}


class AggregatorNode(WorkflowNode):
    """Node that aggregates context values with a function."""

    node_type = "aggregator"

    def __init__(
        self,
        name: str,
        aggregate_function: Callable[[List[Any]], Any],
        input_keys: List[str],
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)
        self.aggregate_function = aggregate_function
        self.input_keys = input_keys

    async def execute(self, ctx: WorkflowContext) -> Any:
        values = [ctx.get(key) for key in self.input_keys]
        result = self.aggregate_function(values)
        if asyncio.iscoroutine(result):
            result = await result
        return result


class Workflow:
    """A runnable workflow graph."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.state = WorkflowState.PENDING
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.start_node: Optional[str] = None
        self.end_nodes: Set[str] = set()

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes[node.name] = node

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable[[WorkflowContext], Any]] = None,
    ) -> None:
        self.edges.append(WorkflowEdge(from_node, to_node, condition))

    def set_start_node(self, name: str) -> None:
        if name not in self.nodes:
            raise ValueError(f"Node {name} not found")
        self.start_node = name

    def add_end_node(self, name: str) -> None:
        self.end_nodes.add(name)

    def validate(self) -> bool:
        if not self.start_node:
            return False
        if self.start_node not in self.nodes:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "start_node": self.start_node,
            "end_nodes": list(self.end_nodes),
            "nodes": list(self.nodes.keys()),
            "edges": [{"from": e.from_node, "to": e.to_node} for e in self.edges],
        }

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        for name in self.nodes:
            lines.append(f"    {name}[{name}]")
        for edge in self.edges:
            lines.append(f"    {edge.from_node}-->{edge.to_node}")
        return "\n".join(lines)

    async def execute(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.validate():
            self.state = WorkflowState.FAILED
            return {"status": "failed", "last_error": "Workflow validation failed"}

        self.state = WorkflowState.RUNNING
        ctx = WorkflowContext(input_data)
        history: List[Dict[str, Any]] = []

        try:
            current_nodes: List[str] = [self.start_node]
            visited: Set[str] = set()

            while current_nodes:
                next_nodes: List[str] = []
                for node_name in current_nodes:
                    if node_name in visited:
                        continue
                    visited.add(node_name)
                    node = self.nodes[node_name]

                    try:
                        result = await node.execute(ctx)
                    except Exception as exc:
                        self.state = WorkflowState.FAILED
                        return {
                            "status": "failed",
                            "error": str(exc),
                            "last_error": str(exc),
                            "history": history,
                        }

                    history.append({"node": node_name, "result": result})
                    ctx.add_history(node_name, result)

                    if node_name in self.end_nodes:
                        continue

                    if isinstance(node, ConditionalNode):
                        branch = result
                        if isinstance(branch, str) and branch in self.nodes:
                            next_nodes.append(branch)
                        continue

                    outgoing = [
                        e for e in self.edges if e.from_node == node_name and e.should_traverse(ctx)
                    ]
                    for edge in outgoing:
                        if edge.to_node not in visited:
                            next_nodes.append(edge.to_node)

                current_nodes = next_nodes

            self.state = WorkflowState.COMPLETED
            return {"status": "completed", "result": None, "history": history}
        except Exception as exc:
            self.state = WorkflowState.FAILED
            return {
                "status": "failed",
                "error": str(exc),
                "last_error": str(exc),
                "history": history,
            }


class WorkflowBuilder:
    """Fluent DSL builder for Workflows."""

    def __init__(self, name: str, description: str = ""):
        self.workflow = Workflow(name, description)

    def llm_node(
        self,
        name: str,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        self.workflow.add_node(
            LLMNode(
                name=name,
                model_name=model,
                prompt_template=prompt,
                **kwargs,
            )
        )
        return self

    def tool_node(
        self,
        name: str,
        tool_func: Optional[Callable[..., Any]] = None,
        tool_function: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        fn = tool_func or tool_function
        self.workflow.add_node(ToolNode(name, tool_function=fn, **kwargs))
        return self

    def conditional_node(
        self,
        name: str,
        condition: Callable[[WorkflowContext], Any],
        true_branch: str,
        false_branch: str,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        self.workflow.add_node(
            ConditionalNode(name, condition, true_branch, false_branch, **kwargs)
        )
        return self

    def parallel_node(
        self, name: str, nodes: List[WorkflowNode], **kwargs: Any
    ) -> "WorkflowBuilder":
        self.workflow.add_node(ParallelNode(name, nodes, **kwargs))
        return self

    def edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable[[WorkflowContext], Any]] = None,
    ) -> "WorkflowBuilder":
        self.workflow.add_edge(from_node, to_node, condition)
        return self

    def start(self, name: str) -> "WorkflowBuilder":
        self.workflow.set_start_node(name)
        return self

    def end(self, name: str) -> "WorkflowBuilder":
        self.workflow.add_end_node(name)
        return self

    def build(self) -> Workflow:
        if not self.workflow.validate():
            raise ValueError("Workflow validation failed")
        return self.workflow


def define_workflow(name: str, description: str = "") -> WorkflowBuilder:
    """Entry point for the workflow DSL."""
    return WorkflowBuilder(name, description)


class WorkflowExecutor:
    """Executes a workflow with optional retries and timeout."""

    def __init__(
        self,
        max_retries: int = 1,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    async def execute(
        self, workflow: Workflow, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        last_error: Optional[str] = None
        for attempt in range(self.max_retries):
            try:
                if self.timeout is not None:
                    result = await asyncio.wait_for(
                        workflow.execute(input_data), timeout=self.timeout
                    )
                else:
                    result = await workflow.execute(input_data)

                if result.get("status") == "completed":
                    return result

                last_error = result.get("last_error") or result.get("error") or "unknown"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
            except asyncio.TimeoutError:
                last_error = "timeout exceeded"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return {"status": "failed", "last_error": last_error}
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return {"status": "failed", "last_error": last_error}

        return {"status": "failed", "last_error": last_error or "unknown"}


class WorkflowOrchestrator:
    """Registry and executor for named workflows."""

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}

    def register_workflow(self, workflow: Workflow) -> None:
        self._workflows[workflow.name] = workflow

    def get_workflow(self, name: str) -> Optional[Workflow]:
        return self._workflows.get(name)

    def list_workflows(self) -> List[str]:
        return list(self._workflows.keys())

    async def execute_workflow(
        self, name: str, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        workflow = self.get_workflow(name)
        if workflow is None:
            raise ValueError(f"Workflow {name} not found")
        return await workflow.execute(input_data)


class WorkflowVisualizer:
    """Static helpers for visualizing a workflow."""

    @staticmethod
    def to_mermaid(workflow: Workflow) -> str:
        return workflow.to_mermaid()

    @staticmethod
    def to_graphviz(workflow: Workflow) -> str:
        lines = ["digraph workflow {"]
        for name in workflow.nodes:
            lines.append(f'    "{name}" [label="{name}"]')
        for edge in workflow.edges:
            lines.append(f'    "{edge.from_node}" -> "{edge.to_node}"')
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def to_ascii(workflow: Workflow) -> str:
        lines = [f"Workflow: {workflow.name}"]
        for name in workflow.nodes:
            lines.append(f"  - {name}")
        for edge in workflow.edges:
            lines.append(f"    {edge.from_node} -> {edge.to_node}")
        return "\n".join(lines)

    @staticmethod
    async def render_mermaid(workflow: Workflow, output_path: str) -> str:
        content = WorkflowVisualizer.to_mermaid(workflow)
        Path(output_path).write_text(content, encoding="utf-8")
        return content

    @staticmethod
    async def render_graphviz(workflow: Workflow, output_path: str) -> str:
        content = WorkflowVisualizer.to_graphviz(workflow)
        Path(output_path).write_text(content, encoding="utf-8")
        return content
