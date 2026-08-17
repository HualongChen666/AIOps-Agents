# -*- coding: utf-8 -*-
"""
Batch 18-C core module coverage tests.

Targets:
- core/frontend_performance_optimizer.py
- core/l5l6_execution_integrator.py
- core/request_tracking.py
- core/exceptions/business.py
- core/l4l5_data_integrator.py
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

from core.exceptions.business import (
    BusinessException,
    BusinessLogicException,
    QuotaExceededException,
    ResourceNotFoundException,
    StateInvalidException,
    ValidationException,
    WorkflowException,
)
from core.frontend_performance_optimizer import (
    FrontendPerformanceOptimizer,
    OptimizationRule,
    OptimizationType,
    PerformanceMetric,
    get_frontend_performance_optimizer,
)
from core.l4l5_data_integrator import (
    DataQuality,
    DataStream,
    DataTransformation,
    DataType,
    L4L5DataIntegrator,
    ProcessingMode,
    get_l4l5_data_integrator,
)
from core.l5l6_execution_integrator import (
    ExecutionMode,
    ExecutionPriority,
    ExecutionRequest,
    ExecutionResult,
    ExecutionTrigger,
    KnowledgeBasedAction,
    L5L6ExecutionIntegrator,
    get_l5l6_execution_integrator,
)
from core.request_tracking import (
    RequestContextManager,
    RequestTrackingMiddleware,
    get_request_id,
    request_context_manager,
    set_request_id,
)

pytestmark = [pytest.mark.core]


class TestFrontendPerformanceOptimizer:
    async def test_analyze_and_report(self):
        opt = FrontendPerformanceOptimizer()
        report = await opt.analyze_performance("https://example.com")

        assert report.url == "https://example.com"
        assert report.score > 0
        assert len(opt.performance_reports) == 1

        reports = opt.get_performance_reports(limit=5)
        assert len(reports) == 1
        assert reports[0]["report_id"] == report.report_id

        stats = opt.get_statistics()
        assert stats["total_optimizations"] == 0
        assert stats["active_rules"] == len(opt.optimization_rules)

    async def test_apply_optimization_all_paths(self, monkeypatch):
        opt = FrontendPerformanceOptimizer()

        # Successful optimization
        result = await opt.apply_optimization(OptimizationType.BUNDLE_COMPRESSION)  # noqa: F841  # Variable for test verification
        assert result.success is True
        assert result.compression_ratio == 0.3

        # Disabled rule path
        opt.optimization_rules["bundle_compression"].enabled = False
        disabled = await opt.apply_optimization(OptimizationType.BUNDLE_COMPRESSION)
        assert disabled.success is False
        assert "Rule not found or disabled" in disabled.metadata["error"]
        opt.optimization_rules["bundle_compression"].enabled = True

        # Rule not found path
        del opt.optimization_rules["bundle_compression"]
        missing = await opt.apply_optimization(OptimizationType.BUNDLE_COMPRESSION)
        assert missing.success is False

        # Exception path
        monkeypatch.setattr(
            opt,
            "_execute_optimization",
            AsyncMock(side_effect=RuntimeError("optimization crashed")),
        )
        failed = await opt.apply_optimization(OptimizationType.IMAGE_OPTIMIZATION)
        assert failed.success is False
        assert "optimization crashed" in failed.metadata["error"]

    def test_recommendations_and_scoring(self):
        opt = FrontendPerformanceOptimizer({"performance_threshold": 90.0})

        score = opt._calculate_performance_score(
            {
                PerformanceMetric.FIRST_CONTENTFUL_PAINT.value: 2.5,
                PerformanceMetric.LARGEST_CONTENTFUL_PAINT.value: 3.0,
                PerformanceMetric.FIRST_INPUT_DELAY.value: 0.2,
                PerformanceMetric.CUMULATIVE_LAYOUT_SHIFT.value: 0.3,
                PerformanceMetric.TIME_TO_INTERACTIVE.value: 5.0,
            }
        )
        assert 0 <= score <= 100

        metrics = {
            PerformanceMetric.FIRST_CONTENTFUL_PAINT.value: 2.5,
            PerformanceMetric.LARGEST_CONTENTFUL_PAINT.value: 3.0,
            PerformanceMetric.FIRST_INPUT_DELAY.value: 0.2,
            PerformanceMetric.CUMULATIVE_LAYOUT_SHIFT.value: 0.3,
        }
        recommendations = opt._generate_recommendations(metrics, 70.0)
        assert len(recommendations) > 0
        assert "Apply comprehensive optimization strategy" in recommendations

    async def test_auto_optimize(self):
        opt = FrontendPerformanceOptimizer({"performance_threshold": 95.0})
        summary = await opt.auto_optimize("https://example.com")

        assert summary["status"] == "optimized"
        assert summary["optimizations_applied"] > 0

        opt_no_auto = FrontendPerformanceOptimizer({"auto_optimize": False})
        disabled = await opt_no_auto.auto_optimize("https://example.com")
        assert disabled["status"] == "disabled"

        opt_no_need = FrontendPerformanceOptimizer({"performance_threshold": 50.0})
        no_need = await opt_no_need.auto_optimize("https://example.com")
        assert no_need["status"] == "no_optimization_needed"

    def test_rule_management_and_statistics(self):
        opt = FrontendPerformanceOptimizer()

        rules = opt.get_optimization_rules()
        assert "code_splitting" in rules

        custom = OptimizationRule(
            rule_id="custom_rule",
            rule_name="Custom Rule",
            optimization_type=OptimizationType.LAZY_LOADING,
            priority=2,
        )
        opt.register_optimization_rule(custom)
        assert "custom_rule" in opt.get_optimization_rules()


class TestL5L6ExecutionIntegrator:
    @pytest.fixture
    def integrator(self, monkeypatch):
        inst = L5L6ExecutionIntegrator({"max_concurrent_executions": 5})
        monkeypatch.setattr("core.l5l6_execution_integrator.asyncio.sleep", AsyncMock())
        monkeypatch.setattr(
            "core.l5l6_execution_integrator.asyncio.create_task",
            lambda coro: coro.close(),
        )
        return inst

    async def test_register_and_trigger(self, integrator):
        action = KnowledgeBasedAction(
            action_id="action_1",
            action_name="Test Action",
            knowledge_type="alert",
            execution_trigger=ExecutionTrigger.MANUAL,
            execution_priority=ExecutionPriority.HIGH,
            execution_mode=ExecutionMode.SYNCHRONOUS,
        )
        integrator.register_action(action)

        request = ExecutionRequest(
            request_id="req_1",
            action_id="action_1",
            knowledge_data={"key": "value"},
        )
        request_id = await integrator.trigger_execution(request)
        assert request_id == "req_1"

        with pytest.raises(ValueError):
            bad = ExecutionRequest(
                request_id="req_bad",
                action_id="missing",
                knowledge_data={},
            )
            await integrator.trigger_execution(bad)

    async def test_execute_request_success_and_history(self, integrator):
        action = KnowledgeBasedAction(
            action_id="action_1",
            action_name="Test Action",
            knowledge_type="metric",
            execution_trigger=ExecutionTrigger.SCHEDULED,
        )
        integrator.register_action(action)

        request = ExecutionRequest(
            request_id="req_1",
            action_id="action_1",
            knowledge_data={"metric": "cpu"},
        )
        integrator.execution_queue[request.priority].put_nowait(request)
        await integrator._execute_request(request)

        status = await integrator.get_execution_status("req_1")
        assert status is not None
        assert status["status"] == "completed"

    async def test_execute_request_skipped(self, integrator):
        action = KnowledgeBasedAction(
            action_id="action_1",
            action_name="Test Action",
            knowledge_type="log",
            execution_trigger=ExecutionTrigger.ANOMALY_DETECTED,
        )
        integrator.register_action(action)
        integrator._check_conditions = lambda *args, **kwargs: False

        request = ExecutionRequest(
            request_id="req_2",
            action_id="action_1",
            knowledge_data={},
        )
        await integrator._execute_request(request)

        status = await integrator.get_execution_status("req_2")
        assert status["status"] == "skipped"

    async def test_execute_request_failure(self, integrator):
        action = KnowledgeBasedAction(
            action_id="action_1",
            action_name="Test Action",
            knowledge_type="event",
            execution_trigger=ExecutionTrigger.EVENT_DRIVEN,
        )
        integrator.register_action(action)
        integrator._execute_action = AsyncMock(side_effect=RuntimeError("boom"))

        request = ExecutionRequest(
            request_id="req_3",
            action_id="action_1",
            knowledge_data={},
        )
        await integrator._execute_request(request)

        status = await integrator.get_execution_status("req_3")
        assert status["status"] == "failed"
        assert "boom" in status["error"]

    async def test_cancel_execution(self, integrator):
        result = ExecutionResult(request_id="req_x", action_id="action_x", status="pending")  # noqa: F841  # Variable for test verification
        integrator.active_executions["req_x"] = result
        assert await integrator.cancel_execution("req_x") is True
        assert await integrator.cancel_execution("missing") is False

    async def test_start_processor_and_getters(self, integrator):
        action = KnowledgeBasedAction(
            action_id="action_1",
            action_name="Test Action",
            knowledge_type="metric",
            execution_trigger=ExecutionTrigger.SCHEDULED,
        )
        integrator.register_action(action)

        await integrator.start_execution_processor()

        config = integrator.get_action_config("action_1")
        assert config is not None
        assert config["action_id"] == "action_1"
        assert integrator.get_action_config("missing") is None

        stats = integrator.get_statistics()
        assert "total_executions" in stats


class TestRequestTracking:
    async def test_middleware_uses_existing_request_id(self):
        class FakeResponse:
            headers = {}

        app = MagicMock()
        middleware = RequestTrackingMiddleware(app, header_name="X-Request-ID")

        request = MagicMock()
        request.headers = {"X-Request-ID": "provided-id"}
        request.state = SimpleNamespace()

        call_next = AsyncMock(return_value=FakeResponse())
        response = await middleware.dispatch(request, call_next)

        assert request.state.request_id == "provided-id"
        assert response.headers["X-Request-ID"] == "provided-id"
        assert get_request_id() == "provided-id"

    async def test_middleware_generates_request_id(self):
        class FakeResponse:
            headers = {}

        app = MagicMock()
        middleware = RequestTrackingMiddleware(app, header_name="X-Request-ID")

        request = MagicMock()
        request.headers = {}
        request.state = SimpleNamespace()

        call_next = AsyncMock(return_value=FakeResponse())
        response = await middleware.dispatch(request, call_next)

        generated = request.state.request_id
        assert generated
        assert response.headers["X-Request-ID"] == generated

    def test_request_id_helpers(self):
        set_request_id("manual-id")
        assert get_request_id() == "manual-id"

    def test_request_context_manager(self):
        manager = RequestContextManager()
        manager.create_context(request_id="ctx_1", user_id="user_a", client_ip="192.168.1.1")
        manager.set_start_time("ctx_1")
        manager.add_metadata("ctx_1", "key", "value")
        manager.set_end_time("ctx_1")

        context = manager.get_context("ctx_1")
        assert context["user_id"] == "user_a"
        assert context["metadata"]["key"] == "value"
        assert manager.get_duration("ctx_1") >= 0

        manager.remove_context("ctx_1")
        assert manager.get_context("ctx_1") is None
        assert manager.get_duration("ctx_1") == 0.0

    def test_global_request_context_manager(self):
        request_context_manager.create_context("global_1")
        request_context_manager.set_start_time("global_1")
        request_context_manager.set_end_time("global_1")
        assert request_context_manager.get_duration("global_1") >= 0
        request_context_manager.remove_context("global_1")


class TestBusinessExceptions:
    def test_business_exception(self):
        exc = BusinessException("business error", context={"ref": "abc"})
        assert exc.error_code == "01_04_0001"
        assert exc.context == {"ref": "abc"}
        assert "business error" in str(exc)

    def test_validation_exception(self):
        exc = ValidationException(
            "invalid input", field="age", value=-5, context={"form": "signup"}
        )
        assert exc.error_code == "01_01_0001"
        assert exc.context["field"] == "age"
        assert exc.context["value"] == -5
        assert exc.severity.value == "warning"

    def test_resource_not_found_exception(self):
        exc = ResourceNotFoundException("not found", resource_type="user", resource_id=123)
        assert exc.context["resource_type"] == "user"
        assert exc.context["resource_id"] == "123"
        assert exc.resource_id == 123

    def test_business_logic_exception(self):
        exc = BusinessLogicException("rule violated", operation="transfer")
        assert exc.context["operation"] == "transfer"
        assert exc.operation == "transfer"

    def test_state_invalid_exception(self):
        exc = StateInvalidException("bad state", current_state="draft", required_state="published")
        assert exc.context["current_state"] == "draft"
        assert exc.context["required_state"] == "published"

    def test_workflow_exception(self):
        exc = WorkflowException("workflow failed", workflow_id="wf_1", step="validation")
        assert exc.context["workflow_id"] == "wf_1"
        assert exc.context["step"] == "validation"

    def test_quota_exceeded_exception(self):
        exc = QuotaExceededException(
            "quota exceeded",
            quota_type="api_calls",
            current_usage=101.0,
            quota_limit=100.0,
        )
        assert exc.context["quota_type"] == "api_calls"
        assert exc.current_usage == 101.0


class TestL4L5DataIntegrator:
    @pytest.fixture
    def integrator(self, monkeypatch):
        inst = L4L5DataIntegrator({"max_buffer_size": 50})
        monkeypatch.setattr("core.l4l5_data_integrator.asyncio.sleep", AsyncMock())
        monkeypatch.setattr(
            "core.l4l5_data_integrator.asyncio.create_task",
            lambda coro: coro.close(),
        )
        return inst

    async def test_register_and_ingest(self, integrator):
        stream = DataStream(
            stream_id="metrics_1",
            data_type=DataType.METRICS,
            source="prometheus",
            destination="knowledge",
            processing_mode=ProcessingMode.REALTIME,
            batch_size=1,
        )
        integrator.register_data_stream(stream)

        transformation = DataTransformation(
            transformation_id="t1",
            name="Add labels",
            transformation_type="enrichment",
        )
        integrator.register_transformation(transformation)

        assert await integrator.ingest_data("metrics_1", {"cpu": 0.5}) is True
        assert await integrator.ingest_data("missing", {}) is False

    async def test_query_and_metrics(self, integrator):
        stream = DataStream(
            stream_id="logs_1",
            data_type=DataType.LOGS,
            source="loki",
            destination="knowledge",
            quality_threshold=DataQuality.HIGH,
        )
        integrator.register_data_stream(stream)

        assert await integrator.query_data("logs_1", {"level": "error"}) == []
        assert await integrator.query_data("missing", {}) == []

        metrics = integrator.get_stream_metrics("logs_1")
        assert metrics is not None
        assert metrics["stream_id"] == "logs_1"

    async def test_process_batch_success_and_failure(self, integrator):
        stream = DataStream(
            stream_id="events_1",
            data_type=DataType.EVENTS,
            source="kafka",
            destination="knowledge",
            batch_size=10,
        )
        integrator.register_data_stream(stream)

        batch = [{"data": 1, "metadata": {}, "timestamp": 1}]

        # Successful batch processing
        await integrator._process_batch("events_1", batch)
        assert integrator.stream_metrics["events_1"].processed_records == 1

        # Failure path
        integrator._store_to_knowledge_layer = AsyncMock(side_effect=RuntimeError("db down"))
        await integrator._process_batch("events_1", batch)
        assert integrator.stream_metrics["events_1"].failed_records == 1

    async def test_start_stop_realtime_processing(self, integrator):
        stream = DataStream(
            stream_id="alerts_1",
            data_type=DataType.ALERTS,
            source="source",
            destination="knowledge",
            batch_size=100,
        )
        integrator.register_data_stream(stream)

        await integrator.ingest_data("alerts_1", {"alert": "high"})
        await integrator.start_realtime_processing()
        await integrator.stop_realtime_processing()

        assert integrator.stream_metrics["alerts_1"].total_records == 1

    def test_get_statistics_and_factory(self):
        inst = get_l4l5_data_integrator({"max_buffer_size": 10})
        assert isinstance(inst, L4L5DataIntegrator)

        stats = inst.get_statistics()
        assert "total_streams" in stats
        assert "active_streams" in stats


def test_factories():
    assert isinstance(get_frontend_performance_optimizer(), FrontendPerformanceOptimizer)
    assert isinstance(get_l5l6_execution_integrator({}), L5L6ExecutionIntegrator)
    assert isinstance(get_l4l5_data_integrator({}), L4L5DataIntegrator)
