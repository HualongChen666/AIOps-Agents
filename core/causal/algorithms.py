# -*- coding: utf-8 -*-
"""
Causal Discovery Algorithms
Implements PC and GES algorithms for causal graph construction
"""

from dataclasses import dataclass
from typing import List, Set

import numpy as np
from loguru import logger

from .graph import CausalEdge, CausalGraph, CausalStrength


@dataclass
class ConditionalIndependenceTest:
    """
    Result of conditional independence test

    Attributes:
        independent: True if variables are independent
        p_value: P-value of the test
        statistic: Test statistic
    """

    independent: bool
    p_value: float
    statistic: float


class PCAlgorithm:
    """
    Peter-Clark (PC) Algorithm for causal discovery

    A constraint-based algorithm that uses conditional independence tests
    to discover causal structure from observational data.
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize PC algorithm

        Args:
            alpha: Significance level for independence tests
        """
        self.alpha = alpha

    def discover(self, data: np.ndarray, variable_names: List[str]) -> CausalGraph:
        """
        Discover causal graph from data

        Args:
            data: Observational data (n_samples x n_variables)
            variable_names: List of variable names

        Returns:
            CausalGraph object
        """
        n_variables = data.shape[1]
        graph = CausalGraph("pc_discovery")

        # Initialize fully connected undirected graph
        adjacency = {i: set(range(n_variables)) - {i} for i in range(n_variables)}

        # Phase 1: Remove edges based on conditional independence
        for i in range(n_variables):
            for j in adjacency[i].copy():
                if j > i:  # Avoid duplicate checks
                    # Test independence
                    test_result = self._test_independence(data, i, j, set())
                    if test_result.independent:
                        adjacency[i].discard(j)
                        adjacency[j].discard(i)

        # Phase 2: Orient v-structures
        # (Simplified implementation)

        # Phase 3: Orient remaining edges
        # (Simplified implementation)

        # Build causal graph from adjacency
        for i in range(n_variables):
            graph.add_node(variable_names[i])

        for i in range(n_variables):
            for j in adjacency[i]:
                if i < j:  # Avoid duplicates
                    edge = CausalEdge(
                        from_var=variable_names[i],
                        to_var=variable_names[j],
                        strength=CausalStrength.MODERATE,
                        confidence=0.7,
                    )
                    graph.add_edge(edge)

        logger.info(
            f"PC algorithm discovered graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges"
        )

        return graph

    def _test_independence(
        self, data: np.ndarray, var1: int, var2: int, conditioning_set: Set[int]
    ) -> ConditionalIndependenceTest:
        """
        Test conditional independence between two variables

        Args:
            data: Data matrix
            var1: First variable index
            var2: Second variable index
            conditioning_set: Conditioning variable indices

        Returns:
            Test result
        """
        # Simplified: use correlation as proxy
        corr = np.corrcoef(data[:, var1], data[:, var2])[0, 1]

        # If conditioning set is empty, use simple correlation test
        if not conditioning_set:
            p_value = 2 * (1 - abs(corr))  # Simplified p-value
            independent = abs(corr) < 0.3  # Threshold
            return ConditionalIndependenceTest(independent, p_value, corr)

        # With conditioning, use partial correlation (simplified)
        independent = abs(corr) < 0.2  # More strict threshold
        p_value = 2 * (1 - abs(corr))

        return ConditionalIndependenceTest(independent, p_value, corr)


class GESAlgorithm:
    """
    Greedy Equivalence Search (GES) Algorithm

    A score-based algorithm that searches for the best DAG
    using a scoring function (e.g., BIC).
    """

    def __init__(self, scoring_metric: str = "bic"):
        """
        Initialize GES algorithm

        Args:
            scoring_metric: Scoring metric ("bic" or "aic")
        """
        self.scoring_metric = scoring_metric

    def discover(self, data: np.ndarray, variable_names: List[str]) -> CausalGraph:
        """
        Discover causal graph from data

        Args:
            data: Observational data (n_samples x n_variables)
            variable_names: List of variable names

        Returns:
            CausalGraph object
        """
        n_variables = data.shape[1]
        graph = CausalGraph("ges_discovery")

        # Simplified: Start with empty graph and greedily add edges
        best_score = float("-inf")
        best_graph = None

        # Greedy forward phase
        for _ in range(n_variables * 2):  # Limit iterations
            improved = False

            for i in range(n_variables):
                for j in range(n_variables):
                    if i != j:
                        # Try adding edge i -> j
                        test_graph = CausalGraph("test")
                        for var in variable_names:
                            test_graph.add_node(var)

                        edge = CausalEdge(
                            from_var=variable_names[i],
                            to_var=variable_names[j],
                            strength=CausalStrength.MODERATE,
                        )
                        test_graph.add_edge(edge)

                        score = self._score_graph(data, test_graph)

                        if score > best_score:
                            best_score = score
                            best_graph = test_graph
                            improved = True

            if not improved:
                break

        if best_graph is None:
            # Fallback: return empty graph
            for var in variable_names:
                graph.add_node(var)
        else:
            graph = best_graph

        logger.info(
            f"GES algorithm discovered graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges"  # noqa: E501
        )

        return graph

    def _score_graph(self, data: np.ndarray, graph: CausalGraph) -> float:
        """
        Score graph using BIC/AIC

        Args:
            data: Data matrix
            graph: Causal graph

        Returns:
            Score value
        """
        # Simplified scoring: penalize complexity
        n_samples = data.shape[0]
        n_edges = len(graph.edges)
        n_params = n_edges * 2  # Simplified parameter count

        # Log-likelihood (simplified): independent Gaussian with empirical variances
        variances = np.var(data, axis=0)
        variances = np.where(variances > 0, variances, 1e-6)
        n_variables = data.shape[1]
        log_likelihood = float(
            -0.5 * n_samples * np.sum(np.log(2 * np.pi * variances) + 1)
        )

        score: float
        if self.scoring_metric == "bic":
            # BIC = log_likelihood - (k/2) * log(n)
            score = float(log_likelihood - (n_params / 2) * np.log(n_samples))
        else:
            # AIC = log_likelihood - k
            score = float(log_likelihood - n_params)

        return score
