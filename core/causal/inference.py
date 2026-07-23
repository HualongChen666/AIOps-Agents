# -*- coding: utf-8 -*-
"""
Root Cause Inference Engine
Infers root causes from causal graph and observed anomalies
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from .graph import CausalGraph, CausalStrength


@dataclass
class RootCauseHypothesis:
    """
    Root cause hypothesis

    Attributes:
        node: Suspected root cause node
        confidence: Confidence score (0-1)
        explanation: Explanation of why this is a root cause
        evidence: Supporting evidence
    """

    node: str
    confidence: float
    explanation: str
    evidence: Dict[str, Any]


class RootCauseInference:
    """
    Root cause inference engine

    Uses causal graph to identify most likely root causes
    of observed anomalies.
    """

    def __init__(self, causal_graph: CausalGraph):
        """
        Initialize inference engine

        Args:
            causal_graph: Causal graph for inference
        """
        self.causal_graph = causal_graph

    def infer_root_causes(
        self, anomaly_nodes: Set[str], context: Optional[Dict] = None
    ) -> List[RootCauseHypothesis]:
        """
        Infer root causes from observed anomalies

        Args:
            anomaly_nodes: Set of nodes with anomalies
            context: Additional context data

        Returns:
            List of root cause hypotheses ranked by confidence
        """
        hypotheses = []

        # For each anomaly, find potential root causes
        for anomaly_node in anomaly_nodes:
            # Get ancestors (potential causes)
            ancestors = self.causal_graph.get_ancestors(anomaly_node)

            for ancestor in ancestors:
                # Calculate confidence based on causal strength
                strength = self.causal_graph.get_causal_strength(ancestor, anomaly_node)

                # Higher strength = higher confidence
                strength_score = (
                    {
                        CausalStrength.WEAK: 0.3,
                        CausalStrength.MODERATE: 0.6,
                        CausalStrength.STRONG: 0.9,
                    }.get(strength, 0.5)
                    if strength is not None
                    else 0.5
                )

                # Check if ancestor is also anomalous
                is_anomalous = ancestor in anomaly_nodes

                # If ancestor is not anomalous, it might be the root cause
                if not is_anomalous:
                    confidence = strength_score
                else:
                    # If ancestor is also anomalous, look further upstream
                    confidence = strength_score * 0.7

                explanation = self._generate_explanation(
                    ancestor, anomaly_node, strength, is_anomalous
                )

                hypothesis = RootCauseHypothesis(
                    node=ancestor,
                    confidence=confidence,
                    explanation=explanation,
                    evidence={
                        "causal_strength": strength.value if strength else None,
                        "anomaly_node": anomaly_node,
                        "is_anomalous": is_anomalous,
                    },
                )

                hypotheses.append(hypothesis)

        # If no ancestors found, the anomaly nodes themselves might be root causes
        if not hypotheses:
            for node in anomaly_nodes:
                hypothesis = RootCauseHypothesis(
                    node=node,
                    confidence=0.5,
                    explanation=f"No upstream causes found; {node} may be the root cause",
                    evidence={"no_upstream": True},
                )
                hypotheses.append(hypothesis)

        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)

        logger.info(f"Inferred {len(hypotheses)} root cause hypotheses")

        return hypotheses

    def _generate_explanation(
        self, cause: str, effect: str, strength: Optional[CausalStrength], is_anomalous: bool
    ) -> str:
        """
        Generate explanation for root cause hypothesis

        Args:
            cause: Suspected cause node
            effect: Effect node
            strength: Causal strength
            is_anomalous: Whether cause is also anomalous

        Returns:
            Explanation string
        """
        strength_text = (
            {
                CausalStrength.WEAK: "weak",
                CausalStrength.MODERATE: "moderate",
                CausalStrength.STRONG: "strong",
            }.get(strength, "unknown")
            if strength is not None
            else "unknown"
        )

        if not is_anomalous:
            return (
                f"{cause} has a {strength_text} causal influence on {effect} "
                "and is not anomalous, suggesting it may be the root cause"
            )
        else:
            return (
                f"{cause} has a {strength_text} causal influence on {effect} "
                "but is also anomalous, indicating the root cause may be "
                "further upstream"
            )

    def trace_propagation_path(self, root_cause: str, target_node: str) -> List[str]:
        """
        Trace causal propagation path from root cause to target

        Args:
            root_cause: Root cause node
            target_node: Target node

        Returns:
            List of nodes in propagation path
        """
        paths = self.causal_graph.find_causal_paths(root_cause, target_node)

        if not paths:
            return []

        # Return the shortest path
        return min(paths, key=len)

    def estimate_impact(self, root_cause: str, affected_nodes: Set[str]) -> Dict[str, float]:
        """
        Estimate impact of root cause on affected nodes

        Args:
            root_cause: Root cause node
            affected_nodes: Set of affected nodes

        Returns:
            Dictionary mapping node to impact score
        """
        impact_scores = {}

        for node in affected_nodes:
            if node == root_cause:
                impact_scores[node] = 1.0
                continue

            # Get causal path
            paths = self.causal_graph.find_causal_paths(root_cause, node)

            if not paths:
                impact_scores[node] = 0.0
                continue

            # Calculate impact based on path length and edge strengths
            path = min(paths, key=len)
            path_length = len(path) - 1  # Number of edges

            # Impact decreases with path length
            base_impact = 1.0 / (path_length + 1)

            # Adjust by edge strengths
            strength_multiplier = 1.0
            for i in range(len(path) - 1):
                strength = self.causal_graph.get_causal_strength(path[i], path[i + 1])
                strength_value = (
                    {
                        CausalStrength.WEAK: 0.5,
                        CausalStrength.MODERATE: 1.0,
                        CausalStrength.STRONG: 1.5,
                    }.get(strength, 1.0)
                    if strength is not None
                    else 1.0
                )
                strength_multiplier *= strength_value

            impact_scores[node] = min(1.0, base_impact * strength_multiplier)

        return impact_scores
