# -*- coding: utf-8 -*-
"""
LangGraph Workflow Definition DSL
Domain-specific language for defining workflows
"""

from typing import Callable, List, Optional

from .nodes import ConditionalNode, LLMNode, ParallelNode, ToolNode
from .workflow import Workflow, WorkflowContext, WorkflowNode


class WorkflowBuilder:
    """
    Builder for creating workflows using DSL
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize workflow builder

        Args:
            name: Workflow name
            description: Workflow description
        """
        self.workflow = Workflow(name, description)

    def llm_node(
        self, name: str, model: str = "gpt-4", prompt: str = "", system_prompt: str = "", **kwargs
    ) -> "WorkflowBuilder":
        """
        Add LLM node to workflow

        Args:
            name: Node name
            model: LLM model name
            prompt: Prompt template
            system_prompt: System prompt
            **kwargs: Additional arguments

        Returns:
            Self for chaining
        """
        node = LLMNode(
            name=name,
            model_name=model,
            prompt_template=prompt,
            system_prompt=system_prompt,
            **kwargs,
        )
        self.workflow.add_node(node)
        return self

    def tool_node(self, name: str, tool_func: Callable, **kwargs) -> "WorkflowBuilder":
        """
        Add tool node to workflow

        Args:
            name: Node name
            tool_func: Tool function
            **kwargs: Additional arguments

        Returns:
            Self for chaining
        """
        node = ToolNode(name=name, tool_function=tool_func, **kwargs)
        self.workflow.add_node(node)
        return self

    def conditional_node(
        self,
        name: str,
        condition: Callable[[WorkflowContext], bool],
        true_branch: str,
        false_branch: str,
    ) -> "WorkflowBuilder":
        """
        Add conditional node to workflow

        Args:
            name: Node name
            condition: Condition function
            true_branch: True branch node name
            false_branch: False branch node name

        Returns:
            Self for chaining
        """
        node = ConditionalNode(name, condition, true_branch, false_branch)
        self.workflow.add_node(node)
        return self

    def parallel_node(self, name: str, child_nodes: List[WorkflowNode]) -> "WorkflowBuilder":
        """
        Add parallel node to workflow

        Args:
            name: Node name
            child_nodes: Child nodes

        Returns:
            Self for chaining
        """
        node = ParallelNode(name, child_nodes)
        self.workflow.add_node(node)
        return self

    def edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable[[WorkflowContext], bool]] = None,
    ) -> "WorkflowBuilder":
        """
        Add edge between nodes

        Args:
            from_node: Source node
            to_node: Target node
            condition: Optional condition

        Returns:
            Self for chaining
        """
        self.workflow.add_edge(from_node, to_node, condition)
        return self

    def start(self, node_name: str) -> "WorkflowBuilder":
        """
        Set start node

        Args:
            node_name: Start node name

        Returns:
            Self for chaining
        """
        self.workflow.set_start_node(node_name)
        return self

    def end(self, node_name: str) -> "WorkflowBuilder":
        """
        Add end node

        Args:
            node_name: End node name

        Returns:
            Self for chaining
        """
        self.workflow.add_end_node(node_name)
        return self

    def build(self) -> Workflow:
        """
        Build and return workflow

        Returns:
            Configured workflow
        """
        if not self.workflow.validate():
            raise ValueError("Workflow validation failed")
        return self.workflow


def define_workflow(name: str, description: str = "") -> WorkflowBuilder:
    """
    Start defining a workflow

    Args:
        name: Workflow name
        description: Workflow description

    Returns:
        Workflow builder
    """
    return WorkflowBuilder(name, description)


# Example DSL usage
async def example_dsl_usage():
    """
    Example of DSL usage
    """
    # Define workflow using DSL
    workflow = (
        define_workflow("incident_analysis", "Analyze and resolve incidents")
        .llm_node(
            "analyze",
            model="gpt-4",
            prompt="Analyze this incident: {incident_data}",
            system_prompt="You are an incident analyzer",
        )
        .tool_node("execute_repair", tool_func=lambda ctx: {"repair_status": "executed"})
        .edge("analyze", "execute_repair")
        .start("analyze")
        .end("execute_repair")
        .build()
    )

    # Execute workflow
    result = await workflow.execute({"incident_data": "Server down"})
    print(result)


__all__ = ["WorkflowBuilder", "define_workflow"]
