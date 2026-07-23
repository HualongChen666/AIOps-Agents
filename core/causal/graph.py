# -*- coding: utf-8 -*-
"""
Causal Graph Data Structure
Represents causal relationships between variables
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CausalStrength(Enum):
    """Causal relationship strength"""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class CausalEdge:
    """
    Causal edge between two variables

    Attributes:
        from_var: Source variable
        to_var: Target variable
        strength: Relationship strength
        confidence: Statistical confidence (0-1)
        lag: Time lag (for temporal causal relationships)
        metadata: Additional metadata
    """

    from_var: str
    to_var: str
    strength: CausalStrength = CausalStrength.MODERATE
    confidence: float = 0.5
    lag: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary"""
        return {
            "from_var": self.from_var,
            "to_var": self.to_var,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "lag": self.lag,
            "metadata": self.metadata,
        }


class CausalGraph:
    """
    Causal graph representing causal relationships

    Supports:
    - Directed acyclic graphs (DAGs)
    - Temporal causal relationships
    - Causal strength estimation
    - Path analysis
    """

    def __init__(self, name: str):
        """
        Initialize causal graph

        Args:
            name: Graph name
        """
        self.name = name
        self.nodes: Set[str] = set()
        self.edges: List[CausalEdge] = []
        self._adjacency: Dict[str, Set[str]] = {}

    def add_node(self, node: str) -> None:
        """
        Add node to graph

        Args:
            node: Node identifier
        """
        self.nodes.add(node)
        if node not in self._adjacency:
            self._adjacency[node] = set()

    def add_edge(self, edge: CausalEdge) -> None:
        """
        Add causal edge to graph

        Args:
            edge: Causal edge
        """
        self.edges.append(edge)
        self.nodes.add(edge.from_var)
        self.nodes.add(edge.to_var)

        if edge.from_var not in self._adjacency:
            self._adjacency[edge.from_var] = set()
        self._adjacency[edge.from_var].add(edge.to_var)

    def get_parents(self, node: str) -> List[str]:
        """
        Get parent nodes (direct causes)

        Args:
            node: Target node

        Returns:
            List of parent node IDs
        """
        parents = []
        for edge in self.edges:
            if edge.to_var == node:
                parents.append(edge.from_var)
        return parents

    def get_children(self, node: str) -> List[str]:
        """
        Get child nodes (direct effects)

        Args:
            node: Source node

        Returns:
            List of child node IDs
        """
        return list(self._adjacency.get(node, set()))

    def get_ancestors(self, node: str) -> Set[str]:
        """
        Get all ancestor nodes (transitive causes)

        Args:
            node: Target node

        Returns:
            Set of ancestor node IDs
        """
        ancestors = set()
        visited = set()

        def dfs(current: str):
            if current in visited:
                return
            visited.add(current)
            for parent in self.get_parents(current):
                ancestors.add(parent)
                dfs(parent)

        dfs(node)
        return ancestors

    def get_descendants(self, node: str) -> Set[str]:
        """
        Get all descendant nodes (transitive effects)

        Args:
            node: Source node

        Returns:
            Set of descendant node IDs
        """
        descendants = set()
        visited = set()

        def dfs(current: str):
            if current in visited:
                return
            visited.add(current)
            for child in self.get_children(current):
                descendants.add(child)
                dfs(child)

        dfs(node)
        return descendants

    def find_causal_paths(self, from_node: str, to_node: str) -> List[List[str]]:
        """
        Find all causal paths between two nodes

        Args:
            from_node: Source node
            to_node: Target node

        Returns:
            List of paths (each path is a list of node IDs)
        """
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if current == to_node:
                paths.append(path.copy())
                return

            for child in self.get_children(current):
                if child not in visited:
                    visited.add(child)
                    path.append(child)
                    dfs(child, path, visited)
                    path.pop()
                    visited.remove(child)

        dfs(from_node, [from_node], {from_node})
        return paths

    def get_causal_strength(self, from_node: str, to_node: str) -> Optional[CausalStrength]:
        """
        Get causal strength between two nodes

        Args:
            from_node: Source node
            to_node: Target node

        Returns:
            Causal strength or None
        """
        for edge in self.edges:
            if edge.from_var == from_node and edge.to_var == to_node:
                return edge.strength
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary"""
        return {
            "name": self.name,
            "nodes": list(self.nodes),
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_json(self) -> str:
        """Convert graph to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
