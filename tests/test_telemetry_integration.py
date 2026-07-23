# -*- coding: utf-8 -*-
# tests/test_telemetry_integration.py
import sys

import pytest  # noqa: F401

from core.telemetry import get_apm_metrics, reset_apm_metrics

sys.path.insert(0, "C://AIOps_Agent_bak")


def test_apm_metrics():
    # Test getting APM metrics
    metrics = get_apm_metrics()
    assert metrics is not None
    assert "request_count" in metrics


def test_reset_apm_metrics():
    # Test resetting APM metrics
    reset_apm_metrics()
    metrics = get_apm_metrics()
    assert metrics["request_count"] == 0  # Should be reset
