# -*- coding: utf-8 -*-
"""
Directed Acyclic Graph (DAG) Implementation
Core data structures for workflow graph representation
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeStatus(Enum):
    """Node execution status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGNode:
    """
    DAG Node representing a workflow step

    Attributes:
        id: Unique node identifier
        name: Human-readable name
        type: Node type (task, condition, parallel, etc.)
        config: Node configuration
        dependencies: List of node IDs this node depends on
        status: Current execution status
        result: Execution result
        error: Error message if failed
    """

    id: str
    name: str
    type: str = "task"
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "config": self.config,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class Edge:
    """
    Edge connecting two nodes in the DAG

    Attributes:
        from_node: Source node ID
        to_node: Target node ID
        condition: Optional condition for edge traversal
    """

    from_node: str
    to_node: str
    condition: Optional[str] = None


class DAG:
    """
    Directed Acyclic Graph for workflow representation

    Supports:
    - Topological sorting for execution order
    - Dependency tracking
    - Cycle detection
    - Parallel execution planning
    """

    def __init__(self, name: str):
        """
        Initialize DAG

        Args:
            name: DAG/workflow name
        """
        self.name = name
        self.nodes: Dict[str, DAGNode] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, Set[str]] = {}
        self._reverse_adjacency: Dict[str, Set[str]] = {}

    def add_node(self, node: DAGNode) -> None:
        """
        Add node to DAG

        Args:
            node: DAGNode to add
        """
        self.nodes[node.id] = node
        self._adjacency[node.id] = set()
        self._reverse_adjacency[node.id] = set()

    def add_edge(self, edge: Edge) -> None:
        """
        Add edge to DAG

        Args:
            edge: Edge to add
        """
        self.edges.append(edge)
        self._adjacency[edge.from_node].add(edge.to_node)
        self._reverse_adjacency[edge.to_node].add(edge.from_node)

        # Update node dependencies
        if edge.to_node in self.nodes:
            if edge.from_node not in self.nodes[edge.to_node].dependencies:
                self.nodes[edge.to_node].dependencies.append(edge.from_node)

    def remove_node(self, node_id: str) -> None:
        """
        Remove node from DAG

        Args:
            node_id: Node ID to remove
        """
        if node_id in self.nodes:
            # Remove edges
            self.edges = [e for e in self.edges if e.from_node != node_id and e.to_node != node_id]

            # Update adjacency
            for neighbor in self._adjacency.get(node_id, set()):
                self._reverse_adjacency[neighbor].discard(node_id)

            for neighbor in self._reverse_adjacency.get(node_id, set()):
                self._adjacency[neighbor].discard(node_id)

            del self.nodes[node_id]
            del self._adjacency[node_id]
            del self._reverse_adjacency[node_id]

    def get_dependencies(self, node_id: str) -> List[str]:
        """
        Get dependencies for a node

        Args:
            node_id: Node ID

        Returns:
            List of dependency node IDs
        """
        return self.nodes.get(node_id, DAGNode("", "")).dependencies

    def get_dependents(self, node_id: str) -> List[str]:
        """
        Get nodes that depend on this node

        Args:
            node_id: Node ID

        Returns:
            List of dependent node IDs
        """
        return list(self._reverse_adjacency.get(node_id, set()))

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort to determine execution order

        Returns:
            List of node IDs in topological order

        Raises:
            ValueError: If cycle detected
        """
        in_degree = {node_id: 0 for node_id in self.nodes}

        # Calculate in-degree for each node
        for edge in self.edges:
            in_degree[edge.to_node] += 1

        # Start with nodes with no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            # Reduce in-degree for dependents
            for dependent in self._adjacency.get(node_id, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in DAG")

        return result

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the DAG

        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in self._adjacency.get(node_id, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Cycle found
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            rec_stack.remove(node_id)
            path.pop()
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def get_ready_nodes(self) -> List[str]:
        """
        Get nodes that are ready to execute (all dependencies satisfied)

        Returns:
            List of ready node IDs
        """
        ready = []
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.PENDING:
                deps_satisfied = all(
                    self.nodes[dep_id].status == NodeStatus.SUCCESS
                    for dep_id in node.dependencies
                    if dep_id in self.nodes
                )
                if deps_satisfied:
                    ready.append(node_id)
        return ready

    def to_dict(self) -> Dict[str, Any]:
        """Convert DAG to dictionary"""
        return {
            "name": self.name,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [
                {"from": edge.from_node, "to": edge.to_node, "condition": edge.condition}
                for edge in self.edges
            ],
        }

    def to_json(self) -> str:
        """Convert DAG to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
