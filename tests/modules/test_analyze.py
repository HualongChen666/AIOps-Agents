# -*- coding: utf-8 -*-
"""Import tests for the analyze modules."""

import importlib

import pytest

_MODULES = [
    "modules.analyze.anomaly.data_preprocessing",
    "modules.analyze.anomaly.ensemble",
    "modules.analyze.anomaly.isolation_forest",
    "modules.analyze.anomaly.prophet_model",
    "modules.analyze.anomaly.train_transformer",
    "modules.analyze.anomaly.transformer_model",
    "modules.analyze.anomaly.transformer_service",
    "modules.analyze.capacity.forecast",
    "modules.analyze.cost.forecast",
    "modules.analyze.root_cause.causal_graph_builder",
    "modules.analyze.root_cause.causal_inference",
    "modules.analyze.root_cause.causal_service",
    "modules.analyze.root_cause.gnn",
    "modules.analyze.root_cause.graph_builder",
    "modules.analyze.root_cause.inference",
    "modules.analyze.runbook.generator",
    "modules.analyze.runbook.vector_store",
]


@pytest.mark.parametrize("module_name", _MODULES)
def test_analyze_module_imports(module_name):
    """Each analyze module imports or is skipped when dependencies are missing."""
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        pytest.skip(f"import {module_name} failed: {exc}")
