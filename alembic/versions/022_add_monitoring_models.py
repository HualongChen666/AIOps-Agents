# -*- coding: utf-8 -*-
"""
Add Monitoring Models

This migration adds Monitoring-related tables to support monitoring features:
- monitoring_alert_rules: Alert rule management
- monitoring_log_patterns: Log pattern tracking
- monitoring_traces: Distributed trace storage
- monitoring_service_calls: Service call statistics
- monitoring_metrics: Metric data storage
- monitoring_integrations: External monitoring system integrations
- monitoring_dashboards: Dashboard configuration
- monitoring_anomalies: Anomaly detection results

This model supports the Monitoring Enhancement API endpoints:
- Alert Rules: GET/POST/PUT/DELETE /api/v1/monitoring/log-alerting
- Log Patterns: GET/POST /api/v1/monitoring/log-analysis
- Traces: GET /api/v1/monitoring/tempo, /api/v1/monitoring/tracing-visualization
- Service Calls: GET /api/v1/monitoring/cross-service-tracing
- Metrics: GET /api/v1/monitoring/metrics-converter
- Integrations: GET/POST/PUT/DELETE /api/v1/monitoring/integrations
- Dashboards: GET/POST/PUT/DELETE /api/v1/monitoring/dashboards
- Anomalies: GET/POST /api/v1/monitoring/anomaly-detection
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade():
    """Add Monitoring-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create monitoring_alert_rules table
    if 'monitoring_alert_rules' not in tables:
        op.create_table(
            'monitoring_alert_rules',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('rule_id', sa.String(100), nullable=False),
            sa.Column('rule_name', sa.String(200), nullable=False),
            sa.Column('pattern', sa.String(500), nullable=False),
            sa.Column('severity', sa.String(20), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('triggered_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_triggered', sa.DateTime(), nullable=True),
            sa.Column('notification_channels', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('rule_id'),
            sa.Index('idx_monitoring_alert_rules_rule_id', 'rule_id'),
            sa.Index('idx_monitoring_alert_rules_name', 'rule_name'),
            sa.Index('idx_monitoring_alert_rules_severity', 'severity'),
            sa.Index('idx_monitoring_alert_rules_status', 'status'),
        )

    # Create monitoring_log_patterns table
    if 'monitoring_log_patterns' not in tables:
        op.create_table(
            'monitoring_log_patterns',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('pattern_id', sa.String(100), nullable=False),
            sa.Column('pattern', sa.String(500), nullable=False),
            sa.Column('severity', sa.String(20), nullable=False),
            sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('frequency', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('first_seen', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('last_seen', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('pattern_id'),
            sa.Index('idx_monitoring_log_patterns_pattern_id', 'pattern_id'),
            sa.Index('idx_monitoring_log_patterns_severity', 'severity'),
            sa.Index('idx_monitoring_log_patterns_last_seen', 'last_seen'),
        )

    # Create monitoring_traces table
    if 'monitoring_traces' not in tables:
        op.create_table(
            'monitoring_traces',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('trace_id', sa.String(100), nullable=False),
            sa.Column('service', sa.String(100), nullable=False),
            sa.Column('start_time', sa.DateTime(), nullable=False),
            sa.Column('duration_ms', sa.Integer(), nullable=False),
            sa.Column('span_count', sa.Integer(), nullable=False),
            sa.Column('root_span', sa.String(100), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('trace_id'),
            sa.Index('idx_monitoring_traces_trace_id', 'trace_id'),
            sa.Index('idx_monitoring_traces_service', 'service'),
            sa.Index('idx_monitoring_traces_start_time', 'start_time'),
        )

    # Create monitoring_service_calls table
    if 'monitoring_service_calls' not in tables:
        op.create_table(
            'monitoring_service_calls',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('from_service', sa.String(100), nullable=False),
            sa.Column('to_service', sa.String(100), nullable=False),
            sa.Column('call_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('avg_latency_ms', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('error_rate', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.Index('idx_monitoring_service_calls_from', 'from_service'),
            sa.Index('idx_monitoring_service_calls_to', 'to_service'),
        )

    # Create monitoring_metrics table
    if 'monitoring_metrics' not in tables:
        op.create_table(
            'monitoring_metrics',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('metric_name', sa.String(100), nullable=False),
            sa.Column('metric_type', sa.String(50), nullable=False),
            sa.Column('value', sa.Float(), nullable=False),
            sa.Column('labels', sa.JSON(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.Index('idx_monitoring_metrics_name', 'metric_name'),
            sa.Index('idx_monitoring_metrics_timestamp', 'timestamp'),
        )

    # Create monitoring_integrations table
    if 'monitoring_integrations' not in tables:
        op.create_table(
            'monitoring_integrations',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('integration_id', sa.String(100), nullable=False),
            sa.Column('integration_name', sa.String(200), nullable=False),
            sa.Column('integration_type', sa.String(50), nullable=False),
            sa.Column('config', sa.JSON(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('health_status', sa.String(20), nullable=False, server_default='unknown'),
            sa.Column('last_health_check', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('integration_id'),
            sa.Index('idx_monitoring_integrations_id', 'integration_id'),
            sa.Index('idx_monitoring_integrations_type', 'integration_type'),
            sa.Index('idx_monitoring_integrations_enabled', 'enabled'),
        )

    # Create monitoring_dashboards table
    if 'monitoring_dashboards' not in tables:
        op.create_table(
            'monitoring_dashboards',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('dashboard_id', sa.String(100), nullable=False),
            sa.Column('dashboard_name', sa.String(200), nullable=False),
            sa.Column('panels', sa.JSON(), nullable=False),
            sa.Column('refresh_interval', sa.String(20), nullable=False, server_default='30s'),
            sa.Column('time_range', sa.String(20), nullable=False, server_default='1h'),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('dashboard_id'),
            sa.Index('idx_monitoring_dashboards_id', 'dashboard_id'),
            sa.Index('idx_monitoring_dashboards_enabled', 'enabled'),
        )

    # Create monitoring_anomalies table
    if 'monitoring_anomalies' not in tables:
        op.create_table(
            'monitoring_anomalies',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('anomaly_id', sa.String(100), nullable=False),
            sa.Column('metric_name', sa.String(100), nullable=False),
            sa.Column('service_name', sa.String(100), nullable=False),
            sa.Column('anomaly_score', sa.Float(), nullable=False),
            sa.Column('expected_value', sa.Float(), nullable=False),
            sa.Column('actual_value', sa.Float(), nullable=False),
            sa.Column('is_anomaly', sa.Boolean(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('detected_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('anomaly_id'),
            sa.Index('idx_monitoring_anomalies_id', 'anomaly_id'),
            sa.Index('idx_monitoring_anomalies_metric', 'metric_name'),
            sa.Index('idx_monitoring_anomalies_service', 'service_name'),
            sa.Index('idx_monitoring_anomalies_detected_at', 'detected_at'),
        )


def downgrade():
    """Remove Monitoring-related tables"""

    # Drop tables in reverse order of creation
    op.drop_table('monitoring_anomalies')
    op.drop_table('monitoring_dashboards')
    op.drop_table('monitoring_integrations')
    op.drop_table('monitoring_metrics')
    op.drop_table('monitoring_service_calls')
    op.drop_table('monitoring_traces')
    op.drop_table('monitoring_log_patterns')
    op.drop_table('monitoring_alert_rules')
