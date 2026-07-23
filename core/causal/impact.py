# -*- coding: utf-8 -*-
"""
Impact Analysis Module
Analyzes the impact of changes and anomalies in the system
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from loguru import logger

from .graph import CausalGraph, CausalStrength


@dataclass
class ImpactAssessment:
    """
    Impact assessment result

    Attributes:
        affected_nodes: Nodes affected by the change
        impact_scores: Impact scores for each node
        total_impact: Total system impact score
        critical_path: Most critical propagation path
    """

    affected_nodes: Set[str]
    impact_scores: Dict[str, float]
    total_impact: float
    critical_path: List[str]


class ImpactAnalyzer:
    """
    Impact analyzer for causal graphs

    Analyzes how changes propagate through the system
    and estimates their impact on various components.
    """

    def __init__(self, causal_graph: CausalGraph):
        """
        Initialize impact analyzer

        Args:
            causal_graph: Causal graph for analysis
        """
        self.causal_graph = causal_graph

    def analyze_change_impact(
        self, changed_nodes: Set[str], change_magnitude: float = 1.0
    ) -> ImpactAssessment:
        """
        Analyze impact of changes in specific nodes

        Args:
            changed_nodes: Set of nodes that changed
            change_magnitude: Magnitude of change (0-1)

        Returns:
            Impact assessment
        """
        affected_nodes = set()
        impact_scores = {}

        # Find all descendants of changed nodes
        for node in changed_nodes:
            descendants = self.causal_graph.get_descendants(node)
            affected_nodes.update(descendants)

        # Calculate impact scores
        for node in affected_nodes:
            # Find shortest path from any changed node
            min_path_length = float("inf")
            source_node = None

            for changed_node in changed_nodes:
                paths = self.causal_graph.find_causal_paths(changed_node, node)
                if paths:
                    path_length = len(min(paths, key=len)) - 1
                    if path_length < min_path_length:
                        min_path_length = path_length
                        source_node = changed_node

            if min_path_length < float("inf") and source_node:
                # Impact decreases with path length
                base_impact = change_magnitude / (min_path_length + 1)

                # Adjust by causal strength
                strength = self.causal_graph.get_causal_strength(source_node, node)
                strength_multiplier = (
                    {
                        CausalStrength.WEAK: 0.5,
                        CausalStrength.MODERATE: 1.0,
                        CausalStrength.STRONG: 1.5,
                    }.get(strength, 1.0)
                    if strength
                    else 1.0
                )

                impact_scores[node] = min(1.0, base_impact * strength_multiplier)
            else:
                impact_scores[node] = 0.0

        # Calculate total impact
        total_impact = sum(impact_scores.values()) / max(1, len(affected_nodes))

        # Find critical path (path with highest cumulative impact)
        critical_path = self._find_critical_path(changed_nodes, impact_scores)

        return ImpactAssessment(
            affected_nodes=affected_nodes,
            impact_scores=impact_scores,
            total_impact=total_impact,
            critical_path=critical_path,
        )

    def _find_critical_path(
        self, source_nodes: Set[str], impact_scores: Dict[str, float]
    ) -> List[str]:
        """
        Find the most critical propagation path

        Args:
            source_nodes: Source nodes
            impact_scores: Impact scores

        Returns:
            Critical path
        """
        if not impact_scores:
            return []

        # Find node with highest impact
        max_impact_node = max(impact_scores.items(), key=lambda x: x[1])[0]

        # Find path from source to this node
        best_path = []
        best_path_impact = 0.0

        for source in source_nodes:
            paths = self.causal_graph.find_causal_paths(source, max_impact_node)
            for path in paths:
                # Calculate path impact
                path_impact = sum(impact_scores.get(node, 0) for node in path)
                if path_impact > best_path_impact:
                    best_path = path
                    best_path_impact = path_impact

        return best_path

    def predict_cascade_failure(
        self, initial_failures: Set[str], failure_threshold: float = 0.8
    ) -> List[str]:
        """
        Predict cascade failure propagation

        Args:
            initial_failures: Initial failed nodes
            failure_threshold: Impact threshold for failure

        Returns:
            List of nodes predicted to fail in cascade
        """
        failed_nodes = set(initial_failures)
        new_failures = set(initial_failures)

        while new_failures:
            next_failures = set()

            for failed_node in new_failures:
                # Check if failure propagates to children
                for child in self.causal_graph.get_children(failed_node):
                    if child not in failed_nodes:
                        # Estimate impact
                        strength = self.causal_graph.get_causal_strength(failed_node, child)
                        impact = (
                            {
                                CausalStrength.WEAK: 0.3,
                                CausalStrength.MODERATE: 0.6,
                                CausalStrength.STRONG: 0.9,
                            }.get(strength, 0.5)
                            if strength
                            else 0.5
                        )

                        if impact >= failure_threshold:
                            next_failures.add(child)

            if not next_failures:
                break

            failed_nodes.update(next_failures)
            new_failures = next_failures

        logger.warning(f"Predicted cascade failure: {len(failed_nodes)} nodes may fail")

        return list(failed_nodes)

    def identify_critical_nodes(self) -> List[Tuple[str, float]]:
        """
        Identify critical nodes based on their impact on the system

        Returns:
            List of (node, criticality_score) tuples sorted by criticality
        """
        criticality_scores = {}

        for node in self.causal_graph.nodes:
            # Calculate criticality based on:
            # 1. Number of descendants (downstream impact)
            # 2. Average causal strength to descendants
            descendants = self.causal_graph.get_descendants(node)

            if not descendants:
                criticality_scores[node] = 0.0
                continue

            # Downstream impact
            downstream_score = len(descendants)

            # Average causal strength
            strengths = []
            for desc in descendants:
                strength = self.causal_graph.get_causal_strength(node, desc)
                strength_value = (
                    {
                        CausalStrength.WEAK: 1,
                        CausalStrength.MODERATE: 2,
                        CausalStrength.STRONG: 3,
                    }.get(strength, 2)
                    if strength
                    else 2
                )
                strengths.append(strength_value)

            avg_strength = sum(strengths) / len(strengths) if strengths else 0

            # Combined criticality score
            criticality_scores[node] = downstream_score * avg_strength / 10.0

        # Sort by criticality
        sorted_nodes = sorted(criticality_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_nodes
