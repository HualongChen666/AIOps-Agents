# -*- coding: utf-8 -*-
# Root conftest.py - Set up Python path before test collection
import logging
import os
import sys

# Add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Disable OpenTelemetry OTLP network exporters during tests to avoid gRPC hangs
# and post-test process stalls. This is applied before test collection.
try:
    import opentelemetry.exporter.otlp.proto.grpc.metric_exporter as _m
    import opentelemetry.exporter.otlp.proto.grpc.trace_exporter as _t
    from opentelemetry.sdk.metrics.export import MetricExportResult
    from opentelemetry.sdk.trace.export import SpanExportResult

    class _NoOpOTLPMetricExporter:
        def __init__(self, *args, **kwargs):
            pass

        def export(self, metrics, timeout_millis=0):
            return MetricExportResult.SUCCESS

        def shutdown(self, timeout_millis=0):
            pass

        def force_flush(self, timeout_millis=0):
            return True

    class _NoOpOTLPSpanExporter:
        def __init__(self, *args, **kwargs):
            pass

        def export(self, spans):
            return SpanExportResult.SUCCESS

        def shutdown(self):
            pass

    _m.OTLPMetricExporter = _NoOpOTLPMetricExporter
    _t.OTLPSpanExporter = _NoOpOTLPSpanExporter
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
