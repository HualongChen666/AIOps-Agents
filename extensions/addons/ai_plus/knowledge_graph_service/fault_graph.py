# -*- coding: utf-8 -*-
"""Fault propagation graph builder for the Knowledge Graph service."""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Set

from .builder import GraphBuilder
from .schemas import (
    FaultPropagationGraphRequest,
    FaultPropagationGraphResponse,
    FaultRule,
    FaultState,
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
)


class FaultPropagationGraphBuilder:
    """Construct fault propagation graphs from states and rules."""

    def __init__(self, graph_builder: GraphBuilder) -> None:
        self.graph_builder = graph_builder

    def _normalize(self, name: str) -> str:
        """Normalize a component identifier."""
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    def _rule_matches(self, state: FaultState, rule: FaultRule) -> bool:
        """Check if a fault rule applies to a given state."""
        source_match = self._normalize(state.component_id) == self._normalize(rule.source)
        condition_match = (
            rule.condition == "*"
            or rule.condition.lower() == state.fault_type.lower()
            or state.fault_type.lower() in rule.condition.lower().split(",")
        )
        return source_match and condition_match

    async def build(self, request: FaultPropagationGraphRequest) -> FaultPropagationGraphResponse:
        """Build a fault propagation graph."""
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_nodes: Dict[str, GraphNode] = {}

        for state in request.states:
            node_id = self._normalize(state.component_id)
            seen_nodes[node_id] = GraphNode(
                node_id=node_id,
                label=state.component_id,
                node_type="fault",
                properties={
                    "fault_type": state.fault_type,
                    "severity": state.severity,
                },
            )

        edge_id_set: Set[str] = set()
        impacted: Set[str] = set()

        queue: deque = deque([(self._normalize(s.component_id), s) for s in request.states])
        visited: Set[str] = set()

        while queue:
            current_id, current_state = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)

            for rule in request.rules:
                if not self._rule_matches(current_state, rule):
                    continue
                target_id = self._normalize(rule.target)
                if target_id not in seen_nodes:
                    seen_nodes[target_id] = GraphNode(
                        node_id=target_id,
                        label=rule.target,
                        node_type="fault",
                        properties={"impacted_by": current_id, "impact": rule.impact},
                    )
                    queue.append(
                        (
                            target_id,
                            FaultState(
                                component_id=rule.target,
                                fault_type=current_state.fault_type,
                                severity=current_state.severity,
                            ),
                        )
                    )
                edge_id = f"{current_id}__PROPAGATES_TO__{target_id}"
                if edge_id not in edge_id_set:
                    edge_id_set.add(edge_id)
                    edges.append(
                        GraphEdge(
                            edge_id=edge_id,
                            source_id=current_id,
                            target_id=target_id,
                            relation="PROPAGATES_TO",
                            properties={"impact": rule.impact, "condition": rule.condition},
                        )
                    )
                    impacted.add(target_id)

        nodes = list(seen_nodes.values())

        build_request = GraphBuildRequest(
            graph_name="fault-propagation-graph",
            nodes=nodes,
            edges=edges,
            source="fault_propagation",
        )
        graph = await self.graph_builder.build_graph(build_request)

        return FaultPropagationGraphResponse(
            graph_id=graph.graph_id,
            states_count=len(request.states),
            rules_count=len(request.rules),
            impacted_count=len(impacted),
            built=True,
        )
