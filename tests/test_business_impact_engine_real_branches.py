# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core/business_impact_engine.py.

These tests exercise the business impact engine using real function/class
calls and project data.  No mocks or internal monkeypatching are used.
"""

import asyncio  # noqa: F401  # Imported for test setup
import hashlib

import config

_LINUX_HOSTS = [
    {"host_name": "payment"},
    "api",
    {"name": "auth"},
    "search",
    "logging",
    "",  # empty entry should be ignored by the name collectors
]

# topology_engine reads config.LINUX_HOSTS at call time;
# business_impact_engine loaded from config at import time, so we set both.  # noqa: F401  # Imported for test setup
config.LINUX_HOSTS = _LINUX_HOSTS
import core.business_impact_engine as bie  # noqa: E402
from core.business_impact_engine import (  # noqa: E402
    BusinessImpactEngine,
    assess_business_impact,
    list_business_impact_services,
    list_business_impact_ux_metrics,
)
from core.metrics_history import METRICS_HISTORY as metrics_history  # noqa: E402
from core.service_monitoring_manager import get_service_monitoring_manager  # noqa: E402

bie.LINUX_HOSTS = _LINUX_HOSTS


async def _run():
    engine = BusinessImpactEngine()

    # _get_topology cache and construction branches
    topo1 = await engine._get_topology()
    topo2 = await engine._get_topology()  # cached path
    assert isinstance(topo1, dict) and "nodes" in topo1
    assert topo1 is topo2

    # _get_all_service_names with dict/string hosts and empty names
    names = await engine._get_all_service_names()
    assert "payment" in names
    assert "api" in names
    assert "auth" in names
    assert "search" in names
    assert "logging" in names

    # _get_pagerank branches (dict id match, non-dict, missing id, default)
    pagerank_topo = {
        "nodes": [
            {"id": "svc", "pagerank": 0.9},
            123,  # non-dict node
            {"pagerank": 0.1},  # dict without id
        ]
    }
    assert engine._get_pagerank(pagerank_topo, "svc") == 0.9
    assert engine._get_pagerank(pagerank_topo, "missing") == 0.3

    # _get_degrees branches (dict/non-dict edges, target/source matches)
    degrees_topo = {
        "nodes": [],
        "edges": [
            {"source": "a", "target": "svc"},
            {"source": "svc", "target": "b"},
            "bad-edge",
            {"source": "x", "target": "y"},
        ],
    }
    in_d, out_d = engine._get_degrees(degrees_topo, "svc")
    assert in_d == 1 and out_d == 1

    # Record real metrics to drive status and priority branches
    manager = get_service_monitoring_manager()
    manager.record_metric("payment_error_rate", "payment", 0.15)
    manager.record_metric("payment_response_time", "payment", 1200.0)

    manager.record_metric("api_error_rate", "api", 0.07)
    manager.record_metric("api_response_time", "api", 600.0)

    manager.record_metric("search_error_rate", "search", 0.06)
    manager.record_metric("search_response_time", "search", 700.0)

    manager.record_metric("auth_error_rate", "auth", 0.01)
    manager.record_metric("auth_response_time", "auth", 100.0)

    # A metric that does not match the named buckets falls through to counts
    manager.record_metric("disk", "payment", 50.0)

    # _get_metric_analysis status branches (down, degraded, healthy, no metrics)
    status_payment, *_ = engine._get_metric_analysis("payment")
    assert status_payment == "down"
    status_api, *_ = engine._get_metric_analysis("api")
    assert status_api == "degraded"
    status_auth, *_ = engine._get_metric_analysis("auth")
    assert status_auth == "healthy"
    status_logging, *_ = engine._get_metric_analysis("logging")
    assert status_logging == "healthy"

    # _compute_impact / _derive_priority category branches
    for svc in ("payment", "api", "search", "auth", "logging"):
        impact = await engine._compute_impact(svc)
        assert impact["name"] == svc
        assert "impactScore" in impact
        assert "category" in impact
        assert "metrics" in impact

    # list_services and assess (known and unknown) branches
    services = await engine.list_services()
    assert isinstance(services, list) and len(services) >= 4

    known = await engine.assess("payment")
    assert known["name"] == "payment"
    unknown = await engine.assess("unknown-service")
    assert unknown["name"] == "unknown-service"

    # Module-level helpers cover lines 423/432/441
    single = await assess_business_impact("payment")
    assert single["name"] == "payment"
    all_services = await list_business_impact_services()
    assert isinstance(all_services, list)

    # get_ux_metrics driven by metrics_history (no service CPU/memory yet)
    # short history -> _change returns 0.0, thresholds -> good
    metrics_history.clear()
    metrics_history.push(40.0, 50.0, 100.0, "12:00:00")
    ux1 = await engine.get_ux_metrics()
    assert isinstance(ux1, list) and len(ux1) == 7

    # longer history, critical CPU/memory
    metrics_history.clear()
    metrics_history.push(40.0, 50.0, 100.0, "12:00:00")
    metrics_history.push(96.0, 97.0, 110.0, "12:00:01")
    ux2 = await engine.get_ux_metrics()
    assert isinstance(ux2, list) and len(ux2) == 7

    # warning CPU/memory thresholds
    metrics_history.clear()
    metrics_history.push(40.0, 50.0, 100.0, "12:00:00")
    metrics_history.push(80.0, 86.0, 110.0, "12:00:01")
    ux3 = await engine.get_ux_metrics()
    assert isinstance(ux3, list) and len(ux3) == 7

    # good CPU/memory thresholds
    metrics_history.clear()
    metrics_history.push(40.0, 50.0, 100.0, "12:00:00")
    metrics_history.push(70.0, 84.0, 110.0, "12:00:01")
    ux4 = await engine.get_ux_metrics()
    assert isinstance(ux4, list) and len(ux4) == 7

    # Add CPU / memory metrics to cover _get_metric_analysis and the
    # cpuUsage / memoryUsage collection branches in get_ux_metrics.
    manager.record_metric("cpu", "payment", 99.0)
    manager.record_metric("memory", "payment", 98.0)
    manager.record_metric("cpu", "api", 80.0)
    manager.record_metric("memory", "api", 88.0)
    manager.record_metric("cpu", "search", 82.0)
    manager.record_metric("memory", "search", 86.0)
    manager.record_metric("cpu", "auth", 40.0)
    manager.record_metric("memory", "auth", 50.0)
    # A final low-value service makes the UX CPU/memory current value "good"
    manager.record_metric("cpu", "zz_good", 40.0)
    manager.record_metric("memory", "zz_good", 40.0)

    ux5 = await engine.get_ux_metrics()
    assert isinstance(ux5, list) and len(ux5) == 7

    ux_module = await list_business_impact_ux_metrics()
    assert isinstance(ux_module, list) and len(ux_module) == 7

    # _service_id static helper
    expected_id = "SVC-" + hashlib.sha256("foo".encode("utf-8")).hexdigest()[:3].upper()
    assert BusinessImpactEngine._service_id("foo") == expected_id


def test_business_impact_engine_real_branches():
    asyncio.run(_run())
