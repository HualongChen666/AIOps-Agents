# -*- coding: utf-8 -*-
"""Causal analysis service router tests (with heavy deps mocked)."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock heavy / uninstalled dependencies before importing the router module
_mocked_module_names = [
    "numpy",
    "pandas",
    "modules.analyze.root_cause.causal_graph_builder",
    "modules.analyze.root_cause.causal_inference",
    "modules.analyze.root_cause.gnn",
    "modules.analyze.root_cause.graph_builder",
    "modules.analyze.root_cause.inference",
]
_original_modules = {name: sys.modules.get(name) for name in _mocked_module_names}
sys.modules.update({name: MagicMock() for name in _mocked_module_names})
# Treat DataFrame as a plain dict so FastAPI can bind JSON bodies for DataFrame-typed params
sys.modules["pandas"].DataFrame = dict

from modules.analyze.root_cause.causal_service import create_router  # noqa: E402

# Restore original module entries so other tests see the real numpy/pandas
for name, mod in _original_modules.items():
    if mod is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = mod
del _original_modules, _mocked_module_names

pytestmark = pytest.mark.core


@pytest.fixture
def client():
    mock_service = MagicMock()
    mock_service.is_initialized = False
    mock_service.discovery_method = "pc"
    mock_service.initialize.return_value = True
    mock_service.identify_root_cause.return_value = [{"var": "service_A"}]
    mock_service.explain_root_cause.return_value = {"explanation": "test"}
    mock_service.estimate_causal_effect.return_value = {"effect": 0.5}
    mock_service.counterfactual_query.return_value = {"result": 0.1}
    mock_service.save_model.return_value = "/models/causal/causal_graph.json"
    mock_service.load_model.return_value = True

    with patch("modules.analyze.root_cause.causal_service.get_service", return_value=mock_service):
        app = FastAPI()
        app.include_router(create_router())
        yield TestClient(app)


class TestCausalServiceRouter:
    def test_initialize(self, client):
        response = client.post(
            "/root-cause/causal/initialize",
            json={"service_A": [1.0], "service_B": [2.0]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_root_cause(self, client):
        response = client.post(
            "/root-cause/causal/root-cause",
            params={"alert_var": "service_C"},
            json={"A": [1.0]},
        )
        assert response.status_code == 200

    def test_explain(self, client):
        response = client.post(
            "/root-cause/causal/explain",
            params={"alert_var": "service_C"},
            json={"root_cause": {}, "current_data": {"A": [1.0]}},
        )
        assert response.status_code == 200

    def test_causal_effect(self, client):
        response = client.post(
            "/root-cause/causal/causal-effect",
            params={"treatment": "A", "outcome": "C"},
            json={
                "data": {"A": [1.0], "C": [2.0]},
                "treatment_values": [0.0, 1.0],
            },
        )
        assert response.status_code == 200

    def test_counterfactual(self, client):
        response = client.post(
            "/root-cause/causal/counterfactual",
            params={"outcome_var": "C"},
            json={
                "factual": {"A": 1.0},
                "intervention": {"A": 2.0},
                "data": {"A": [1.0], "C": [2.0]},
            },
        )
        assert response.status_code == 200

    def test_model_save(self, client):
        response = client.post("/root-cause/causal/model/save")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_model_load(self, client):
        response = client.post("/root-cause/causal/model/load")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_status(self, client):
        response = client.get("/root-cause/causal/status")
        assert response.status_code == 200
        assert "initialized" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
