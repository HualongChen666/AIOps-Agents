# -*- coding: utf-8 -*-
"""Unit tests for previously uncovered call chain and plugin marketplace modules."""

from datetime import datetime, timedelta, timezone

from core.call_chain_analysis import (
    CallChainAnalysisEngine,
    CallChainNode,
    get_call_chain_analysis_engine as get_legacy_call_chain_analysis_engine,
)
from core.call_chain_analysis_engine import (
    CallChainAnalysisEngine as ModernCallChainAnalysisEngine,
    Span,
    SpanKind,
    SpanStatus,
    Trace,
    get_call_chain_analysis_engine as get_modern_call_chain_analysis_engine,
)
from core.call_chain_search import (
    CallChainSearchManager,
    SearchCriteria,
    SearchFilter,
    SearchOperator,
    SearchResult,
    SortOrder,
    get_call_chain_search_manager,
)
from core.plugin_marketplace import (
    PluginMarketplace,
    PluginStatus,
    SecurityLevel,
    create_plugin_marketplace,
)


def test_call_chain_search_manager():
    manager = get_call_chain_search_manager({})
    assert isinstance(manager, CallChainSearchManager)

    trace_ok = {
        "trace_id": "trace-ok-1",
        "service_name": "checkout",
        "operation_name": "process",
        "status": "OK",
        "start_time": "2024-01-01T10:00:00+00:00",
        "end_time": "2024-01-01T10:00:01+00:00",
        "duration_ms": 1000.0,
        "tags": {"env": "prod"},
        "metadata": {"host": "srv1"},
    }
    trace_err = {
        "trace_id": "trace-err-1",
        "service_name": "checkout",
        "operation_name": "refund",
        "status": "ERROR",
        "start_time": "2024-01-01T10:00:02+00:00",
        "end_time": "2024-01-01T10:00:04+00:00",
        "duration_ms": 2500.0,
        "tags": {"env": "prod"},
        "metadata": {"host": "srv2"},
    }
    manager.add_call_chain(trace_ok)
    manager.add_call_chain(trace_err)

    assert manager.search_by_trace_id("trace-ok-1") is not None
    assert manager.search_by_trace_id("missing") is None

    service_results = manager.search_by_service_name("checkout")
    assert len(service_results) == 2

    criteria = SearchCriteria(
        service_name="checkout",
        min_duration_ms=500.0,
        max_duration_ms=1500.0,
        tags={"env": "prod"},
        limit=10,
        sort_by="duration_ms",
        sort_order=SortOrder.ASC,
    )
    results = manager.search_by_criteria(criteria)
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].trace_id == "trace-ok-1"
    assert results[0].status == "OK"

    error_criteria = SearchCriteria(
        service_name="checkout",
        custom_filters=[
            SearchFilter(field="status", operator=SearchOperator.EQUALS, value="ERROR")
        ],
    )
    error_results = manager.search_by_criteria(error_criteria)
    assert len(error_results) == 1
    assert error_results[0].trace_id == "trace-err-1"

    stats = manager.get_statistics()
    assert "total_searches" in stats
    assert stats["indexed_traces"] == 2


def test_legacy_call_chain_analysis_engine():
    engine = get_legacy_call_chain_analysis_engine({})
    assert isinstance(engine, CallChainAnalysisEngine)

    now = datetime.now(timezone.utc)
    service_name = "payment"
    operation_name = "charge"

    nodes = []
    for i in range(10):
        nodes.append(
            CallChainNode(
                span_id=f"span-{i}",
                parent_span_id=None,
                operation_name=operation_name,
                service_name=service_name,
                start_time=now,
                end_time=now,
                duration_ms=100.0,
                self_duration_ms=100.0,
                status="OK",
            )
        )
    # Outlier/error node triggers bottleneck, anomaly and root cause paths.
    nodes.append(
        CallChainNode(
            span_id="span-err",
            parent_span_id=None,
            operation_name=operation_name,
            service_name=service_name,
            start_time=now,
            end_time=now,
            duration_ms=5000.0,
            self_duration_ms=5000.0,
            status="ERROR",
            error_message="timeout connecting to upstream",
        )
    )

    engine.add_call_chain("trace-legacy-1", nodes)

    bottlenecks = engine.analyze_performance_bottlenecks()
    assert isinstance(bottlenecks, list)
    assert len(bottlenecks) >= 1

    anomalies = engine.analyze_anomalies(threshold=2.0)
    assert isinstance(anomalies, list)
    assert len(anomalies) >= 1

    root_causes = engine.analyze_root_causes("trace-legacy-1")
    assert isinstance(root_causes, list)
    assert len(root_causes) == 1
    assert root_causes[0].issue_type == "timeout_error"

    stats = engine.get_statistics()
    assert stats["total_analyses"] >= 3
    assert stats["bottlenecks_detected"] >= 1
    assert stats["root_causes_identified"] >= 1


def test_modern_call_chain_analysis_engine():
    engine = ModernCallChainAnalysisEngine()
    assert isinstance(get_modern_call_chain_analysis_engine(), ModernCallChainAnalysisEngine)

    start = datetime.now(timezone.utc)
    end = start + timedelta(milliseconds=3000)

    trace = Trace(
        trace_id="trace-modern-1",
        root_span_id="trace-root",
        start_time=start,
        end_time=end,
    )
    root = Span(
        span_id="root",
        trace_id="trace-modern-1",
        operation_name="root-op",
        start_time=start,
        end_time=end,
        duration_ms=3000.0,
        kind=SpanKind.SERVER,
        status=SpanStatus.OK,
        attributes={"service.name": "web"},
    )
    child = Span(
        span_id="child-1",
        trace_id="trace-modern-1",
        parent_span_id="root",
        operation_name="slow-db",
        start_time=start + timedelta(milliseconds=100),
        end_time=end,
        duration_ms=2500.0,
        kind=SpanKind.CLIENT,
        status=SpanStatus.ERROR,
        status_message="connection refused",
        attributes={"service.name": "db"},
        tags={"env": "prod"},
    )
    trace.add_span(root)
    trace.add_span(child)
    engine.add_trace(trace)

    analysis = engine.analyze_trace("trace-modern-1")
    assert isinstance(analysis, dict)
    assert analysis["trace_id"] == "trace-modern-1"
    assert analysis["total_spans"] == 2
    assert "performance_issues" in analysis
    assert "root_cause" in analysis

    agg = engine.aggregate_traces(["trace-modern-1"])
    assert isinstance(agg, dict)
    assert agg["trace_count"] == 1
    assert agg["total_errors"] == 1
    assert "db" in agg["unique_services"]

    bottlenecks = engine.identify_performance_bottlenecks()
    assert isinstance(bottlenecks, list)
    assert len(bottlenecks) >= 1
    assert bottlenecks[0].issue_type == "slow_operation"

    stats = engine.get_engine_statistics()
    assert stats["total_traces"] == 1
    assert stats["total_spans"] == 2

    found = engine.search_by_trace_id("trace-modern-1")
    assert found is not None
    assert found.trace_id == "trace-modern-1"

    by_service = engine.filter_by_service_name("web")
    assert len(by_service) == 1

    by_time = engine.filter_by_time_range(
        start - timedelta(seconds=1), end + timedelta(seconds=1)
    )
    assert len(by_time) == 1

    by_duration = engine.filter_by_duration(min_duration_ms=1000.0)
    assert len(by_duration) == 1

    by_tags = engine.filter_by_tags({"env": "prod"})
    assert len(by_tags) == 1

    error_traces = engine.filter_by_error_status()
    assert len(error_traces) == 1

    no_error_traces = engine.filter_by_error_status(has_errors=False)
    assert len(no_error_traces) == 0

    spans = engine.search_spans_by_operation("db")
    assert len(spans) == 1
    assert spans[0].operation_name == "slow-db"

    advanced = engine.advanced_search(
        service_name="web",
        min_duration_ms=1000.0,
        has_errors=True,
        operation_name="slow",
    )
    assert len(advanced) == 1


def test_plugin_marketplace():
    marketplace = create_plugin_marketplace(config={})
    assert isinstance(marketplace, PluginMarketplace)

    pkg_data = b"package-data-v1"
    plugin = marketplace.register_plugin(
        name="test-plugin",
        version="1.0.0",
        description="A test plugin",
        author="tester",
        download_url="http://example.com/plugin.zip",
        package_data=pkg_data,
        dependencies=[],
        metadata={"requires_network": True},
    )
    assert plugin is not None
    assert plugin.id == "test-plugin-1.0.0"
    assert plugin.status == PluginStatus.PENDING
    assert plugin.security_level == SecurityLevel.HIGH

    verified = marketplace.verify_plugin(plugin.id, pkg_data)
    assert verified is True

    approved = marketplace.approve_plugin(plugin.id)
    assert approved is True
    assert marketplace.get_plugin(plugin.id)["status"] == PluginStatus.APPROVED.value

    plugins = marketplace.list_plugins(status=PluginStatus.APPROVED)
    assert len(plugins) == 1

    search_results = marketplace.search_plugins("test")
    assert len(search_results) >= 1

    versions = marketplace.get_plugin_versions("test-plugin")
    assert len(versions) >= 1
    assert versions[0]["name"] == "test-plugin"

    dep_plugin = marketplace.register_plugin(
        name="dep-plugin",
        version="1.0.0",
        description="Depends on test plugin",
        author="tester",
        download_url="http://example.com/dep.zip",
        package_data=b"dep-package",
        dependencies=[plugin.id],
    )
    dep_check = marketplace.check_dependencies(dep_plugin.id)
    assert dep_check["valid"] is True
    assert plugin.id in dep_check["available"]

    stats = marketplace.get_statistics()
    assert stats["total_plugins"] == 2
    assert "status_counts" in stats
    assert "security_counts" in stats

    rejected = marketplace.reject_plugin(plugin.id, "bad signature")
    assert rejected is True
    assert marketplace.get_plugin(plugin.id)["status"] == PluginStatus.REJECTED.value

    deprecated = marketplace.deprecate_plugin(dep_plugin.id)
    assert deprecated is True
    assert marketplace.get_plugin(dep_plugin.id)["status"] == PluginStatus.DEPRECATED.value
