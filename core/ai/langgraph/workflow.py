# -*- coding: utf-8 -*-
"""
LangGraph Workflow State Machine
Implements state machine for AI workflow orchestration
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class WorkflowState(Enum):
    """Workflow state enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowContext:
    """Workflow execution context"""

    input_data: Dict[str, Any] = field(default_factory=dict)
    state_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context"""
        return self.state_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in context"""
        self.state_data[key] = value

    def add_history(self, node_name: str, result: Any) -> None:
        """Add execution history entry"""
        self.history.append(
            {
                "node": node_name,
                "result": result,
                "timestamp": str(__import__("datetime").datetime.now()),
            }
        )


@dataclass
class WorkflowNode(ABC):
    """Base workflow node"""

    name: str
    node_type: str = "base"
    config: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> Any:
        """Execute node logic"""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary"""
        return {"name": self.name, "type": self.node_type, "config": self.config}


@dataclass
class WorkflowEdge:
    """Workflow edge between nodes"""

    from_node: str
    to_node: str
    condition: Optional[Callable[[WorkflowContext], bool]] = None

    def should_traverse(self, context: WorkflowContext) -> bool:
        """Check if edge should be traversed"""
        if self.condition is None:
            return True
        return self.condition(context)


class Workflow:
    """
    Workflow state machine for AI orchestration
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize workflow

        Args:
            name: Workflow name
            description: Workflow description
        """
        self.name = name
        self.description = description
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.start_node: Optional[str] = None
        self.end_nodes: List[str] = []
        self.state = WorkflowState.PENDING
        self.context: Optional[WorkflowContext] = None

    def add_node(self, node: WorkflowNode) -> None:
        """
        Add node to workflow

        Args:
            node: Workflow node to add
        """
        self.nodes[node.name] = node
        logger.debug(f"Added node: {node.name}")

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable[[WorkflowContext], bool]] = None,
    ) -> None:
        """
        Add edge between nodes

        Args:
            from_node: Source node name
            to_node: Target node name
            condition: Optional condition for traversal
        """
        edge = WorkflowEdge(from_node, to_node, condition)
        self.edges.append(edge)
        logger.debug(f"Added edge: {from_node} -> {to_node}")

    def set_start_node(self, node_name: str) -> None:
        """
        Set workflow start node

        Args:
            node_name: Start node name
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} not found in workflow")
        self.start_node = node_name

    def add_end_node(self, node_name: str) -> None:
        """
        Add end node to workflow

        Args:
            node_name: End node name
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} not found in workflow")
        if node_name not in self.end_nodes:
            self.end_nodes.append(node_name)

    def validate(self) -> bool:
        """
        Validate workflow structure

        Returns:
            True if workflow is valid
        """
        if not self.start_node:
            logger.error("Workflow has no start node")
            return False

        if self.start_node not in self.nodes:
            logger.error(f"Start node {self.start_node} not found")
            return False

        if not self.end_nodes:
            logger.warning("Workflow has no end nodes")

        # Check all edges reference valid nodes
        for edge in self.edges:
            if edge.from_node not in self.nodes:
                logger.error(f"Edge references unknown node: {edge.from_node}")
                return False
            if edge.to_node not in self.nodes:
                logger.error(f"Edge references unknown node: {edge.to_node}")
                return False

        logger.info(f"Workflow {self.name} validation passed")
        return True

    async def execute(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute workflow

        Args:
            input_data: Initial input data

        Returns:
            Execution result
        """
        if not self.validate():
            raise ValueError("Workflow validation failed")

        # Initialize context
        self.context = WorkflowContext(input_data=input_data or {})
        self.state = WorkflowState.RUNNING

        logger.info(f"Starting workflow: {self.name}")

        try:
            # Execute from start node
            current_node = self.start_node
            visited = set()

            while current_node and current_node not in visited:
                visited.add(current_node)

                # Execute current node
                node = self.nodes[current_node]
                logger.info(f"Executing node: {current_node}")

                result = await node.execute(self.context)
                self.context.add_history(current_node, result)

                # Check if this is an end node
                if current_node in self.end_nodes:
                    logger.info(f"Reached end node: {current_node}")
                    break

                # Find next node
                current_node = self._get_next_node(current_node)

            self.state = WorkflowState.COMPLETED
            logger.info(f"Workflow {self.name} completed successfully")

            return {
                "status": "completed",
                "context": self.context.state_data,
                "history": self.context.history,
            }

        except Exception as e:
            self.state = WorkflowState.FAILED
            logger.error(f"Workflow {self.name} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "context": self.context.state_data if self.context else {},
            }

    def _get_next_node(self, current_node: str) -> Optional[str]:
        """
        Get next node to execute

        Args:
            current_node: Current node name

        Returns:
            Next node name or None
        """
        for edge in self.edges:
            if edge.from_node == current_node:
                if self.context and edge.should_traverse(self.context):
                    return edge.to_node
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert workflow to dictionary

        Returns:
            Workflow dictionary representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()},
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "has_condition": edge.condition is not None,
                }
                for edge in self.edges
            ],
            "start_node": self.start_node,
            "end_nodes": self.end_nodes,
            "state": self.state.value,
        }

    def to_mermaid(self) -> str:
        """
        Generate Mermaid diagram

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        # Add nodes
        for node_name, node in self.nodes.items():
            node_id = node_name.replace(" ", "_")
            lines.append(f"  {node_id}[{node_name}]")

        # Add edges
        for edge in self.edges:
            from_id = edge.from_node.replace(" ", "_")
            to_id = edge.to_node.replace(" ", "_")
            lines.append(f"  {from_id} --> {to_id}")

        # Mark start and end nodes
        if self.start_node:
            start_id = self.start_node.replace(" ", "_")
            lines.append(f"  {start_id}:::start")

        for end_node in self.end_nodes:
            end_id = end_node.replace(" ", "_")
            lines.append(f"  {end_id}:::end")

        return "\n".join(lines)


__all__ = ["Workflow", "WorkflowContext", "WorkflowEdge", "WorkflowNode", "WorkflowState"]
