# -*- coding: utf-8 -*-
"""Transformer anomaly service router tests (with heavy deps mocked)."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock heavy / uninstalled dependencies before importing the router module
_mocked_module_names = [
    "torch",
    "numpy",
    "pandas",
    "modules.analyze.anomaly.data_preprocessing",
    "modules.analyze.anomaly.transformer_model",
    "modules.analyze.anomaly.ensemble",
    "modules.analyze.anomaly.isolation_forest",
    "modules.analyze.anomaly.prophet_model",
]
_original_modules = {name: sys.modules.get(name) for name in _mocked_module_names}
sys.modules.update({name: MagicMock() for name in _mocked_module_names})

from modules.analyze.anomaly.transformer_service import create_router  # noqa: E402

# Restore original module entries so other tests see the real numpy/pandas/torch
for name, mod in _original_modules.items():
    if mod is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = mod
del _original_modules, _mocked_module_names

pytestmark = pytest.mark.core


@pytest.fixture
def client():
    mock_manager = MagicMock()
    mock_manager.is_loaded = False
    mock_manager.device = "cpu"
    mock_manager.load_model.return_value = True
    mock_manager.unload_model.return_value = None

    mock_service = MagicMock()
    mock_service.detect_single.return_value = {"is_anomaly": False}
    mock_service.detect_batch.return_value = [{"series_id": 0, "is_anomaly": False}]

    with (
        patch(
            "modules.analyze.anomaly.transformer_service.get_model_manager",
            return_value=mock_manager,
        ),
        patch(
            "modules.analyze.anomaly.transformer_service.get_service",
            return_value=mock_service,
        ),
    ):
        app = FastAPI()
        app.include_router(create_router())
        yield TestClient(app)


class TestTransformerServiceRouter:
    def test_detect(self, client):
        response = client.post("/anomaly/transformer/detect", json=[1.0, 2.0, 3.0])
        assert response.status_code == 200

    def test_detect_batch(self, client):
        response = client.post("/anomaly/transformer/detect-batch", json=[[1.0, 2.0], [3.0, 4.0]])
        assert response.status_code == 200

    def test_model_load(self, client):
        response = client.post("/anomaly/transformer/model/load")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_model_unload(self, client):
        response = client.post("/anomaly/transformer/model/unload")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_model_status(self, client):
        response = client.get("/anomaly/transformer/model/status")
        assert response.status_code == 200
        assert "loaded" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
