# -*- coding: utf-8 -*-
"""
Causal Graph Analysis Module
Implements causal inference for root cause analysis
"""

from enum import Enum

from .algorithms import GESAlgorithm, PCAlgorithm
from .graph import CausalEdge, CausalGraph
from .impact import ImpactAnalyzer
from .inference import RootCauseInference
from .prediction import CausalPredictor
from .preprocessing import TimeSeriesPreprocessor


# Causal strength levels for causal relationships
class CausalStrength(str, Enum):
    """Strength of causal relationship"""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


__all__ = [
    "CausalGraph",
    "CausalEdge",
    "CausalStrength",
    "PCAlgorithm",
    "GESAlgorithm",
    "TimeSeriesPreprocessor",
    "RootCauseInference",
    "ImpactAnalyzer",
    "CausalPredictor",
]
