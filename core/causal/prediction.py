# -*- coding: utf-8 -*-
"""
Predictive Analysis Module
Performs predictive analysis using causal relationships
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
from loguru import logger

from .graph import CausalGraph


@dataclass
class PredictionResult:
    """
    Prediction result

    Attributes:
        target_node: Node being predicted
        predicted_value: Predicted value
        confidence: Prediction confidence (0-1)
        causal_explanation: Explanation based on causal relationships
    """

    target_node: str
    predicted_value: float
    confidence: float
    causal_explanation: str


class CausalPredictor:
    """
    Causal predictor for forecasting and what-if analysis

    Uses causal relationships to make predictions about
    future states or the effect of interventions.
    """

    def __init__(self, causal_graph: CausalGraph):
        """
        Initialize causal predictor

        Args:
            causal_graph: Causal graph for prediction
        """
        self.causal_graph = causal_graph
        self._coefficients: Dict[Tuple[str, str], float] = {}

    def fit(self, data: np.ndarray, variable_names: List[str]) -> None:
        """
        Fit causal model to data

        Args:
            data: Historical data
            variable_names: Variable names
        """
        # Simplified: compute regression coefficients
        # In practice, this would use proper causal inference methods
        n_variables = data.shape[1]

        for i in range(n_variables):
            for j in range(n_variables):
                if i != j:
                    # Compute simple regression coefficient
                    x = data[:, j]
                    y = data[:, i]

                    # Normalize
                    x = (x - x.mean()) / (x.std() + 1e-8)
                    y = (y - y.mean()) / (y.std() + 1e-8)

                    # Simple linear regression
                    coeff = np.cov(x, y)[0, 1] / (np.var(x) + 1e-8)

                    self._coefficients[(variable_names[j], variable_names[i])] = coeff

        logger.info(f"Fitted causal model with {len(self._coefficients)} coefficients")

    def predict(
        self, target_node: str, current_state: Dict[str, float], horizon: int = 1
    ) -> PredictionResult:
        """
        Predict future value of target node

        Args:
            target_node: Node to predict
            current_state: Current values of all nodes
            horizon: Prediction horizon (time steps)

        Returns:
            Prediction result
        """
        # Get parents (direct causes)
        parents = self.causal_graph.get_parents(target_node)

        if not parents:
            return PredictionResult(
                target_node=target_node,
                predicted_value=current_state.get(target_node, 0),
                confidence=0.0,
                causal_explanation="No causal parents found for prediction",
            )

        # Predict based on parent values and coefficients
        predicted_value = 0.0
        total_weight = 0.0

        explanations = []

        for parent in parents:
            if parent in current_state:
                coeff = self._coefficients.get((parent, target_node), 0.0)
                parent_value = current_state[parent]

                # Weighted contribution
                contribution = coeff * parent_value
                predicted_value += contribution
                total_weight += abs(coeff)

                explanations.append(f"{parent} contributes {contribution:.2f}")

        # Normalize
        if total_weight > 0:
            predicted_value /= total_weight

        # Confidence based on number of parents and coefficient strength
        confidence = min(1.0, total_weight / len(parents))

        causal_explanation = (
            "; ".join(explanations) if explanations else "No significant causal factors"
        )

        return PredictionResult(
            target_node=target_node,
            predicted_value=predicted_value,
            confidence=confidence,
            causal_explanation=causal_explanation,
        )

    def what_if(
        self,
        intervention_node: str,
        intervention_value: float,
        target_node: str,
        current_state: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        What-if analysis: predict effect of intervention

        Args:
            intervention_node: Node to intervene on
            intervention_value: Intervention value
            target_node: Node to predict effect on
            current_state: Current system state

        Returns:
            What-if analysis result
        """
        # Check if intervention affects target
        paths = self.causal_graph.find_causal_paths(intervention_node, target_node)

        if not paths:
            return {
                "has_effect": False,
                "reason": f"No causal path from {intervention_node} to {target_node}",
                "predicted_change": 0.0,
            }

        # Simulate intervention
        modified_state = current_state.copy()
        modified_state[intervention_node] = intervention_value

        # Predict target value with intervention
        prediction = self.predict(target_node, modified_state)

        # Predict target value without intervention
        baseline_prediction = self.predict(target_node, current_state)

        # Calculate change
        predicted_change = prediction.predicted_value - baseline_prediction.predicted_value

        return {
            "has_effect": True,
            "causal_path": min(paths, key=len),
            "baseline_value": baseline_prediction.predicted_value,
            "predicted_value": prediction.predicted_value,
            "predicted_change": predicted_change,
            "confidence": prediction.confidence,
        }

    def counterfactual(
        self,
        observed_outcome: float,
        target_node: str,
        intervention_node: str,
        current_state: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Counterfactual analysis: what would have happened if we intervened

        Args:
            observed_outcome: Actually observed outcome
            target_node: Target node
            intervention_node: Node to hypothetically intervene on
            current_state: System state at intervention time

        Returns:
            Counterfactual analysis result
        """
        # Predict outcome with intervention
        what_if_result = self.what_if(
            intervention_node,
            current_state[intervention_node] * 1.2,  # Hypothetical 20% increase
            target_node,
            current_state,
        )

        if not what_if_result["has_effect"]:
            return {"counterfactual_effect": None, "reason": "No causal relationship"}

        # Calculate difference from observed
        counterfactual_difference = what_if_result["predicted_change"]

        return {
            "counterfactual_effect": counterfactual_difference,
            "observed_outcome": observed_outcome,
            "counterfactual_outcome": observed_outcome + counterfactual_difference,
            "intervention_impact": abs(counterfactual_difference) / (abs(observed_outcome) + 1e-8),
        }
