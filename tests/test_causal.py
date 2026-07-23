# -*- coding: utf-8 -*-
"""
Causal Graph Analysis Tests
"""

import numpy as np
import pandas as pd
import pytest  # noqa: F401

from core.causal import (  # noqa: F401
    CausalEdge,
    CausalGraph,
    CausalPredictor,
    CausalStrength,
    GESAlgorithm,
    ImpactAnalyzer,
    PCAlgorithm,
    RootCauseInference,
    TimeSeriesPreprocessor,
)


class TestCausalGraph:
    """Test causal graph implementation"""

    def test_add_node(self):
        """Test adding nodes"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        assert "cpu" in graph.nodes

    def test_add_edge(self):
        """Test adding edges"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        edge = CausalEdge(from_var="cpu", to_var="latency")
        graph.add_edge(edge)
        assert len(graph.edges) == 1

    def test_get_parents(self):
        """Test getting parent nodes"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        graph.add_edge(CausalEdge(from_var="cpu", to_var="latency"))
        parents = graph.get_parents("latency")
        assert "cpu" in parents

    def test_find_causal_paths(self):
        """Test finding causal paths"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        graph.add_node("errors")
        graph.add_edge(CausalEdge(from_var="cpu", to_var="latency"))
        graph.add_edge(CausalEdge(from_var="latency", to_var="errors"))

        paths = graph.find_causal_paths("cpu", "errors")
        assert len(paths) == 1
        assert paths[0] == ["cpu", "latency", "errors"]


class TestPCAlgorithm:
    """Test PC algorithm"""

    def test_discover_graph(self):
        """Test graph discovery"""
        np.random.seed(42)
        data = np.random.randn(100, 3)
        variable_names = ["cpu", "memory", "latency"]

        algorithm = PCAlgorithm()
        graph = algorithm.discover(data, variable_names)

        assert graph.name == "pc_discovery"
        assert len(graph.nodes) == 3


class TestTimeSeriesPreprocessor:
    """Test time series preprocessor"""

    def test_preprocess(self):
        """Test preprocessing"""
        data = pd.DataFrame({"cpu": [10, 20, 30, 40, 50], "memory": [50, 60, 70, 80, 90]})

        preprocessor = TimeSeriesPreprocessor()
        processed = preprocessor.preprocess(data)

        assert processed.shape == (5, 2)

    def test_select_lags(self):
        """Test lag selection"""
        data = np.random.randn(100, 3)
        preprocessor = TimeSeriesPreprocessor()
        lags = preprocessor.select_lags(data, max_lag=5)
        assert isinstance(lags, list)


class TestRootCauseInference:
    """Test root cause inference"""

    def test_infer_root_causes(self):
        """Test root cause inference"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        graph.add_node("errors")
        graph.add_edge(CausalEdge(from_var="cpu", to_var="latency"))
        graph.add_edge(CausalEdge(from_var="latency", to_var="errors"))

        inference = RootCauseInference(graph)
        hypotheses = inference.infer_root_causes({"errors"})

        assert len(hypotheses) > 0


class TestImpactAnalyzer:
    """Test impact analyzer"""

    def test_analyze_change_impact(self):
        """Test change impact analysis"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        graph.add_edge(CausalEdge(from_var="cpu", to_var="latency"))

        analyzer = ImpactAnalyzer(graph)
        assessment = analyzer.analyze_change_impact({"cpu"})

        assert len(assessment.affected_nodes) > 0


class TestCausalPredictor:
    """Test causal predictor"""

    def test_fit(self):
        """Test model fitting"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        graph.add_edge(CausalEdge(from_var="cpu", to_var="latency"))

        data = np.random.randn(100, 2)
        variable_names = ["cpu", "latency"]

        predictor = CausalPredictor(graph)
        predictor.fit(data, variable_names)

        assert len(predictor._coefficients) > 0

    def test_predict(self):
        """Test prediction"""
        graph = CausalGraph("test")
        graph.add_node("cpu")
        graph.add_node("latency")
        graph.add_edge(CausalEdge(from_var="cpu", to_var="latency"))

        data = np.random.randn(100, 2)
        variable_names = ["cpu", "latency"]

        predictor = CausalPredictor(graph)
        predictor.fit(data, variable_names)

        current_state = {"cpu": 0.5, "latency": 0.3}
        prediction = predictor.predict("latency", current_state)

        assert prediction.target_node == "latency"
