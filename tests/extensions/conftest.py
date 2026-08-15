# -*- coding: utf-8 -*-
"""Shared fixtures for extension tests."""

import pytest


@pytest.fixture(autouse=True)
def _no_prometheus_duplicates(monkeypatch):
    """Disable Prometheus metric registration to avoid duplicate name errors."""
    import prometheus_client

    monkeypatch.setattr(prometheus_client.REGISTRY, "register", lambda *a, **k: None)
