# -*- coding: utf-8 -*-
"""Real-data branch-coverage tests for modules/analyze/root_cause/causal_inference.py.

These tests use real NumPy/Pandas data and the actual CausalGraph / inference
classes (no mocks).  They target the currently missing branches in the file.
"""

import numpy as np
import pandas as pd
import pytest  # noqa: F401  # Imported for test setup

from modules.analyze.root_cause.causal_inference import (
    CausalDiscovery,
    CausalGraph,
    CausalRootCauseAnalyzer,
    CounterfactualReasoning,
    DoCalculus,
    create_causal_analyzer,
)


def _chain_data(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generate a simple A -> C chain where C = 2*A + small noise."""
    rng = np.random.default_rng(seed)
    a = np.linspace(5.0, 15.0, n)
    c = 2.0 * a + rng.normal(scale=0.1, size=n)
    b = rng.normal(size=n)
    return pd.DataFrame({"A": a, "B": b, "C": c})


def test_adjacency_matrix_custom_node_order_and_missing_nodes():
    """Exercise the node_order branch and the edge-skip branch in to_adjacency_matrix."""
    g = CausalGraph()
    g.add_edge("A", "B", 0.5)
    g.add_edge("B", "C", 0.3)
    g.add_node("D")

    # default order
    assert g.to_adjacency_matrix().shape == (4, 4)

    # explicit node_order bypasses the None branch (121->124)
    mat = g.to_adjacency_matrix(node_order=["A", "C", "B"])
    assert mat.shape == (3, 3)

    # order excludes an edge endpoint, so 131->130 (skip edge) is triggered
    mat_skip = g.to_adjacency_matrix(node_order=["A", "C"])
    assert mat_skip.shape == (2, 2)
    assert mat_skip.sum() == 0.0


def test_causal_graph_ancestor_descendant_and_cycle_detection():
    """Basic DAG traversal and cycle detection with real CausalGraph state."""
    g = CausalGraph()
    g.add_edge("A", "B", 0.8)
    g.add_edge("B", "C", 0.6)
    assert g.is_dag()
    assert g.get_ancestors("C") == {"A", "B"}
    assert g.get_descendants("A") == {"B", "C"}

    g2 = CausalGraph()
    g2.add_edge("A", "B")
    g2.add_edge("B", "C")
    g2.add_edge("C", "A")
    assert not g2.is_dag()


def test_causal_graph_diamond_branches():
    """Diamond DAG exercises the already-visited ancestor/descendant branches."""
    g = CausalGraph()
    g.add_edge("D", "A", 1.0)
    g.add_edge("D", "B", 1.0)
    g.add_edge("A", "C", 1.0)
    g.add_edge("B", "C", 1.0)
    assert g.get_ancestors("C") == {"A", "B", "D"}
    assert g.get_descendants("D") == {"A", "B", "C"}


def test_pc_algorithm_generates_causal_hypothesis():
    """PC algorithm should build a graph hypothesis from real correlated data."""
    data = _chain_data()
    graph = CausalDiscovery.pc_algorithm(data)
    assert set(graph.nodes) == set(data.columns)
    # A and C are strongly correlated, so an edge should be learned
    assert graph.edge_weights


def test_ges_scoring_handles_linear_regression_error():
    """GES BIC scoring falls into the exception branch for bad/NaN matrices (270-271)."""
    df = pd.DataFrame(
        {
            "A": [1.0, 2.0, np.nan],
            "B": [3.0, np.nan, 5.0],
            "C": [np.nan, 7.0, 8.0],
        }
    )
    graph = CausalDiscovery.ges_algorithm(df)
    assert isinstance(graph, CausalGraph)
    assert set(graph.nodes) == {"A", "B", "C"}


def test_do_calculus_ate_with_non_two_treatment_values():
    """estimate_causal_effect uses the else branch when treatment_values != 2."""
    g = CausalGraph()
    g.add_edge("A", "C", 1.0)
    a = np.linspace(0.0, 10.0, 30)
    data = pd.DataFrame({"A": a, "C": a + 0.5})
    calc = DoCalculus(g)
    effect = calc.estimate_causal_effect("A", "C", data, treatment_values=[0.0, 0.5, 1.0])
    assert "ate" in effect
    assert effect["ate"] == pytest.approx(1.0)


def test_do_calculus_skips_descendant_without_parents():
    """do_intervention takes the if parents False branch for an orphan child."""
    g = CausalGraph()
    g.add_node("A")
    g.add_node("B")
    # Deliberately inconsistent edge: A -> B exists but B has no recorded parents
    g.edges["A"] = {"B"}

    data = pd.DataFrame({"A": [1.0, 2.0], "B": [10.0, 20.0]})
    calc = DoCalculus(g)
    res = calc.do_intervention("A", 5.0, data)

    assert (res["A"] == 5.0).all()
    # B is unchanged because no parent edge is recorded in reverse_edges
    assert (res["B"] == data["B"]).all()


def test_necessary_causes_threshold_and_scoring():
    """compute_necessary_causes respects the 0.1 effect-size threshold."""
    g = CausalGraph()
    g.add_edge("A", "C", 1.0)
    a = np.linspace(0.0, 10.0, 30)
    c = 10.0 * a + 1.0
    data = pd.DataFrame({"A": a, "B": np.random.default_rng(0).normal(size=30), "C": c})

    cf = CounterfactualReasoning(g)
    causes = cf.compute_necessary_causes("C", data["C"].mean(), data)

    assert any(c["cause"] == "A" for c in causes)
    assert all(c["effect_size"] > 0.1 for c in causes)


def test_counterfactual_what_if_real_data():
    """Counterfactual what_if runs real do-interventions."""
    g = CausalGraph()
    g.add_edge("A", "C", 1.0)
    a = np.linspace(0.0, 10.0, 20)
    data = pd.DataFrame({"A": a, "C": a + 2.0})
    cf = CounterfactualReasoning(g)
    result = cf.what_if(
        {"A": 5.0, "C": 7.0}, {"A": 3.0}, "C", data
    )  # noqa: F841  # Variable for test verification
    assert result["counterfactual_outcome"] == pytest.approx(3.0)
    assert result["factual_outcome"] == 7.0


def test_analyzer_invalid_discovery_method_and_prelearn_errors():
    """Error branches for unknown method, unlearned graph, disabled counterfactual."""
    data = _chain_data()

    # Unknown discovery method -> 623
    with pytest.raises(ValueError, match="Unknown discovery method"):
        CausalRootCauseAnalyzer(discovery_method="foo").learn_causal_graph(data)

    # identify_root_cause before learning -> 658
    a = CausalRootCauseAnalyzer()
    with pytest.raises(RuntimeError, match="Causal graph not learned"):
        a.identify_root_cause("C", data)

    # use_counterfactual=False skips counterfactual init (627->630) and raises on identify -> 667
    a2 = CausalRootCauseAnalyzer(discovery_method="pc", use_counterfactual=False)
    a2.learn_causal_graph(data)
    assert a2.counterfactual is None
    with pytest.raises(RuntimeError, match="Counterfactual reasoning not initialized"):
        a2.identify_root_cause("C", data)

    # do_calculus manually cleared -> 679
    a3 = CausalRootCauseAnalyzer(discovery_method="pc", use_counterfactual=True)
    a3.learn_causal_graph(data)
    a3.do_calculus = None
    with pytest.raises(RuntimeError, match="Do-calculus not initialized"):
        a3.identify_root_cause("C", data)


def test_analyzer_identify_root_cause_necessary_and_causal():
    """End-to-end identify_root_cause covers necessary-cause and causal-effect scoring."""
    data = _chain_data()
    analyzer = create_causal_analyzer(discovery_method="pc", use_counterfactual=True)
    analyzer.learn_causal_graph(data)
    causes = analyzer.identify_root_cause("C", data, top_k=3)
    assert isinstance(causes, list)
    assert any(c["node"] == "A" for c in causes)

    explanation = analyzer.explain_root_cause(causes[0], "C", data)
    assert explanation["root_cause"] == causes[0]["node"]
    assert "causal_path" in explanation


def test_analyzer_confidence_threshold_and_dedup():
    """The 0.1 score threshold and deduplication loop are both exercised."""
    g = CausalGraph()
    g.add_edge("A", "C", 1.0)
    g.add_edge("B", "C", 0.0)  # B is an ancestor with zero causal effect on C

    a = np.linspace(0.0, 10.0, 30)
    b = np.random.default_rng(0).normal(size=30)
    c = a + 5.0  # intercept makes necessary-cause effect large
    data = pd.DataFrame({"A": a, "B": b, "C": c})

    analyzer = CausalRootCauseAnalyzer(discovery_method="pc", use_counterfactual=True)
    analyzer.causal_graph = g
    analyzer.do_calculus = DoCalculus(g)
    analyzer.counterfactual = CounterfactualReasoning(g)

    causes = analyzer.identify_root_cause("C", data, top_k=5)
    nodes = [c["node"] for c in causes]
    assert "A" in nodes
    # B has zero ATE, so it enters only via the necessary-cause path, not the
    # causal-effect threshold branch.
    assert any(c["node"] == "B" and c["method"] == "necessary_cause" for c in causes)


def test_explain_root_cause_causal_path_and_intervention():
    """explain_root_cause path-building and intervention branches."""
    g = CausalGraph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("B", "C", 1.0)
    data = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0], "C": [5.0, 6.0]})

    analyzer = CausalRootCauseAnalyzer(use_counterfactual=True)
    analyzer.causal_graph = g
    analyzer.do_calculus = DoCalculus(g)
    analyzer.counterfactual = CounterfactualReasoning(g)

    # cause is ancestor and path goes through intermediate (776 used)
    exp = analyzer.explain_root_cause({"node": "A", "method": "test"}, "C", data)
    assert exp["causal_path"] == ["A", "B", "C"]
    assert exp["intervention_effect"] is not None

    # cause is not an ancestor -> 767->785 (path block skipped, intervention still runs)
    exp2 = analyzer.explain_root_cause({"node": "C", "method": "test"}, "C", data)
    assert exp2["causal_path"] == []
    assert exp2["intervention_effect"] is not None

    # causal_graph is None and counterfactual disabled -> 765->785 and 785 false
    analyzer2 = CausalRootCauseAnalyzer(use_counterfactual=False)
    analyzer2.causal_graph = None
    exp3 = analyzer2.explain_root_cause({"node": "A", "method": "test"}, "C", data)
    assert exp3["causal_path"] == []
    assert exp3["intervention_effect"] is None


def test_explain_root_cause_dead_end_and_self_loop():
    """Path building handles a dead-end child and a cause that equals the alert."""
    # Dead-end child: A has children 'B' (sorted first) and 'leaf'; leaf -> C.
    # The first child doesn't lead to the alert, so the else/break is reached.
    g = CausalGraph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("A", "leaf", 1.0)
    g.add_edge("leaf", "C", 1.0)
    data = pd.DataFrame(
        {
            "A": [1.0, 2.0],
            "B": [3.0, 4.0],
            "leaf": [5.0, 6.0],
            "C": [7.0, 8.0],
        }
    )
    analyzer = CausalRootCauseAnalyzer(use_counterfactual=True)
    analyzer.causal_graph = g
    analyzer.do_calculus = DoCalculus(g)
    analyzer.counterfactual = CounterfactualReasoning(g)
    exp = analyzer.explain_root_cause({"node": "A", "method": "test"}, "C", data)
    assert exp["causal_path"] == ["A", "B"]

    # Self-loop: cause equals alert, while condition is false on entry (771->782)
    g2 = CausalGraph()
    g2.add_edge("A", "A", 1.0)
    data2 = pd.DataFrame({"A": [1.0, 2.0, 3.0]})
    analyzer2 = CausalRootCauseAnalyzer(use_counterfactual=True)
    analyzer2.causal_graph = g2
    analyzer2.do_calculus = DoCalculus(g2)
    analyzer2.counterfactual = CounterfactualReasoning(g2)
    exp2 = analyzer2.explain_root_cause({"node": "A", "method": "test"}, "A", data2)
    assert exp2["causal_path"] == ["A"]


def test_ges_algorithm_on_real_data():
    """GES algorithm with clean data reaches the successful BIC fit branches."""
    data = _chain_data(n=50)
    graph = CausalDiscovery.ges_algorithm(data)
    assert isinstance(graph, CausalGraph)
    assert "A" in graph.nodes


def test_analyzer_learn_with_ges():
    """CausalRootCauseAnalyzer covers the GES branch in learn_causal_graph."""
    data = _chain_data(n=50)
    analyzer = CausalRootCauseAnalyzer(discovery_method="ges", use_counterfactual=True)
    graph = analyzer.learn_causal_graph(data)
    assert graph is not None


def test_analyzer_counterfactual_reinit():
    """identify_root_cause re-initializes counterfactual when it is None."""
    data = _chain_data()
    analyzer = create_causal_analyzer(discovery_method="pc", use_counterfactual=True)
    analyzer.learn_causal_graph(data)
    analyzer.counterfactual = None
    causes = analyzer.identify_root_cause("C", data, top_k=3)
    assert isinstance(causes, list)
    assert any(c["node"] == "A" for c in causes)
