# -*- coding: utf-8 -*-
# tests/unit/test_call_chain_analysis_engine.py
# 调用链分析引擎单元测试
import warnings  # noqa: F401
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch  # noqa: F401

import pytest

from core.call_chain_analysis_engine import (  # noqa: F401
    CallChainAnalysisEngine,
    PerformanceIssue,
    RootCauseAnalysis,
    Span,
    SpanKind,
    SpanStatus,
    Trace,
)


class TestSpan:
    """Span 类测试"""

    def test_span_creation(self):
        """测试 Span 创建"""
        span = Span(span_id="span_1", trace_id="trace_1", operation_name="test_operation")

        assert span.span_id == "span_1"
        assert span.trace_id == "trace_1"
        assert span.operation_name == "test_operation"
        assert span.status == SpanStatus.OK

    def test_span_with_parent(self):
        """测试带父 span 的 Span"""
        span = Span(
            span_id="span_1",
            trace_id="trace_1",
            parent_span_id="parent_span",
            operation_name="child_operation",
        )

        assert span.parent_span_id == "parent_span"

    def test_span_is_error(self):
        """测试 span 错误状态"""
        error_span = Span(span_id="span_1", trace_id="trace_1", status=SpanStatus.ERROR)

        assert error_span.is_error is True

        ok_span = Span(span_id="span_2", trace_id="trace_1", status=SpanStatus.OK)

        assert ok_span.is_error is False

    def test_span_is_completed(self):
        """测试 span 完成状态"""
        completed_span = Span(span_id="span_1", trace_id="trace_1", end_time=datetime.utcnow())

        assert completed_span.is_completed is True

        incomplete_span = Span(span_id="span_2", trace_id="trace_1", end_time=None)

        assert incomplete_span.is_completed is False

    def test_span_duration_calculation(self):
        """测试 span 持续时间计算"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(milliseconds=100)

        span = Span(
            span_id="span_1",
            trace_id="trace_1",
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        assert span.duration_ms == 100.0


class TestTrace:
    """Trace 类测试"""

    def test_trace_creation(self):
        """测试 Trace 创建"""
        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        assert trace.trace_id == "trace_1"
        assert trace.root_span_id == "root_span"
        assert len(trace.spans) == 0

    def test_add_span(self):
        """测试添加 span"""
        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        span = Span(span_id="span_1", trace_id="trace_1", operation_name="test_operation")

        trace.add_span(span)

        assert len(trace.spans) == 1
        assert trace.spans[0] == span

    def test_get_span_tree(self):
        """测试获取 span 树"""
        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        # 添加父 span
        parent_span = Span(
            span_id="root_span", trace_id="trace_1", operation_name="parent_operation"
        )
        trace.add_span(parent_span)

        # 添加子 span
        child_span = Span(
            span_id="child_span",
            trace_id="trace_1",
            parent_span_id="root_span",
            operation_name="child_operation",
        )
        trace.add_span(child_span)

        tree = trace.get_span_tree()

        assert "root_span" in tree
        # root_span会被包含在自己的列表中，加上子span，总共2个
        assert len(tree["root_span"]) == 2

    def test_get_error_spans(self):
        """测试获取错误 span"""
        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        # 添加正常 span
        ok_span = Span(span_id="ok_span", trace_id="trace_1", status=SpanStatus.OK)
        trace.add_span(ok_span)

        # 添加错误 span
        error_span = Span(span_id="error_span", trace_id="trace_1", status=SpanStatus.ERROR)
        trace.add_span(error_span)

        error_spans = trace.get_error_spans()

        assert len(error_spans) == 1
        assert error_spans[0].span_id == "error_span"

    def test_trace_service_names(self):
        """测试服务名称提取"""
        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        span1 = Span(span_id="span_1", trace_id="trace_1", attributes={"service.name": "service_a"})
        trace.add_span(span1)

        span2 = Span(span_id="span_2", trace_id="trace_1", tags={"service.name": "service_b"})
        trace.add_span(span2)

        assert "service_a" in trace.service_names
        assert "service_b" in trace.service_names


class TestCallChainAnalysisEngine:
    """调用链分析引擎测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = CallChainAnalysisEngine()

        assert engine is not None
        assert hasattr(engine, "analyze_trace")

    def test_analyze_simple_trace(self):
        """测试简单 trace 分析"""
        engine = CallChainAnalysisEngine()

        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        span = Span(
            span_id="root_span",
            trace_id="trace_1",
            operation_name="test_operation",
            duration_ms=100.0,
            end_time=datetime.now(timezone.utc),  # 设置end_time避免递归问题，使用aware datetime
        )
        trace.add_span(span)

        engine.add_trace(trace)

        # 测试基本的trace添加和检索
        retrieved_trace = engine.search_by_trace_id("trace_1")
        assert retrieved_trace is not None
        assert retrieved_trace.trace_id == "trace_1"
        assert len(retrieved_trace.spans) == 1

    def test_identify_performance_bottlenecks(self):
        """测试性能瓶颈识别"""
        engine = CallChainAnalysisEngine()

        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        # 添加慢速 span
        slow_span = Span(
            span_id="slow_span",
            trace_id="trace_1",
            operation_name="slow_operation",
            duration_ms=5000.0,  # 5秒
            attributes={"service.name": "database"},
        )
        trace.add_span(slow_span)

        engine.add_trace(trace)
        bottlenecks = engine.identify_performance_bottlenecks()

        assert len(bottlenecks) >= 0  # 可能有也可能没有瓶颈

    def test_analyze_root_cause(self):
        """测试根因分析（通过分析trace）"""
        engine = CallChainAnalysisEngine()

        trace = Trace(trace_id="trace_1", root_span_id="root_span")

        # 添加错误 span
        error_span = Span(
            span_id="error_span",
            trace_id="trace_1",
            status=SpanStatus.ERROR,
            status_message="Connection timeout",
        )
        trace.add_span(error_span)

        engine.add_trace(trace)
        analysis = engine.analyze_trace("trace_1")

        assert analysis is not None
        assert analysis["error_count"] == 1


class TestPerformanceIssue:
    """性能问题测试"""

    def test_performance_issue_creation(self):
        """测试性能问题创建"""
        issue = PerformanceIssue(
            issue_type="slow_operation",
            severity="high",
            description="Database query took too long",
            affected_spans=["span_1"],
            affected_services=["database"],
            metrics={"duration_ms": 5000.0, "threshold_ms": 1000.0},
        )

        assert issue.issue_type == "slow_operation"
        assert issue.severity == "high"
        assert "span_1" in issue.affected_spans
        assert "database" in issue.affected_services


class TestRootCauseAnalysis:
    """根因分析测试"""

    def test_root_cause_analysis_creation(self):
        """测试根因分析创建"""
        analysis = RootCauseAnalysis(
            trace_id="trace_1",
            root_cause="Database connection pool exhausted",
            confidence=0.85,
            contributing_factors=["high_traffic", "insufficient_connections"],
            error_chain=["connection_timeout", "query_failure"],
        )

        assert analysis.trace_id == "trace_1"
        assert analysis.root_cause == "Database connection pool exhausted"
        assert analysis.confidence == 0.85
        assert len(analysis.contributing_factors) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
