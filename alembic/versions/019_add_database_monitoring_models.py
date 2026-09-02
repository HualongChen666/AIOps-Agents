# -*- coding: utf-8 -*-
"""
Add Database Monitoring Models

This migration adds Database Monitoring-related tables to support database monitoring:
- database_metric_thresholds: Stores metric threshold configurations
- database_monitoring_configs: Stores monitoring configuration
- database_performance_baselines: Stores performance baselines
- database_alert_rules: Stores alert rules
- database_monitoring_status: Stores monitoring status

This model supports the Database Monitoring API endpoints:
- GET/PUT /api/v1/database-monitoring/config
- GET/PUT /api/v1/database-monitoring/thresholds
- GET/POST /api/v1/database-monitoring/baselines
- GET/POST/PUT/DELETE /api/v1/database-monitoring/alert-rules
- GET /api/v1/database-monitoring/status
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    """Add Database Monitoring-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create database_metric_thresholds table
    if 'database_metric_thresholds' not in tables:
        op.create_table(
            'database_metric_thresholds',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('metric_type', sa.String(50), nullable=False),
            sa.Column('warning_threshold', sa.Float(), nullable=False),
            sa.Column('critical_threshold', sa.Float(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
        )

        # Create indexes for database_metric_thresholds
        op.create_index('idx_database_metric_thresholds_metric_type', 'database_metric_thresholds', ['metric_type'], unique=True)
        op.create_index('idx_database_metric_thresholds_enabled', 'database_metric_thresholds', ['enabled'])

    # Create database_monitoring_configs table
    if 'database_monitoring_configs' not in tables:
        op.create_table(
            'database_monitoring_configs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('collection_interval', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
            sa.Column('enable_realtime', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('enable_slow_query_log', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('slow_query_threshold', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('enable_connection_monitoring', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('max_connections_threshold', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('enable_deadlock_detection', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('updated_by', sa.String(50), nullable=True),
        )

        # Create indexes for database_monitoring_configs
        op.create_index('idx_database_monitoring_configs_enabled', 'database_monitoring_configs', ['enabled'])

    # Create database_performance_baselines table
    if 'database_performance_baselines' not in tables:
        op.create_table(
            'database_performance_baselines',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('baseline_name', sa.String(200), nullable=False),
            sa.Column('established_at', sa.DateTime(), nullable=False),
            sa.Column('avg_query_time', sa.Float(), nullable=False),
            sa.Column('p95_query_time', sa.Float(), nullable=False),
            sa.Column('p99_query_time', sa.Float(), nullable=False),
            sa.Column('avg_connection_count', sa.Float(), nullable=False),
            sa.Column('peak_connection_count', sa.Integer(), nullable=False),
            sa.Column('cache_hit_ratio', sa.Float(), nullable=False),
            sa.Column('database_size_mb', sa.Float(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
        )

        # Create indexes for database_performance_baselines
        op.create_index('idx_database_performance_baselines_name', 'database_performance_baselines', ['baseline_name'], unique=True)
        op.create_index('idx_database_performance_baselines_established_at', 'database_performance_baselines', ['established_at'])

    # Create database_alert_rules table
    if 'database_alert_rules' not in tables:
        op.create_table(
            'database_alert_rules',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('rule_id', sa.String(100), nullable=False),
            sa.Column('rule_name', sa.String(200), nullable=False),
            sa.Column('metric_type', sa.String(50), nullable=False),
            sa.Column('condition', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(20), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('notification_channels', sa.JSON(), nullable=True),
            sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='5'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('updated_by', sa.String(50), nullable=True),
        )

        # Create indexes for database_alert_rules
        op.create_index('idx_database_alert_rules_rule_id', 'database_alert_rules', ['rule_id'], unique=True)
        op.create_index('idx_database_alert_rules_metric_type', 'database_alert_rules', ['metric_type'])
        op.create_index('idx_database_alert_rules_severity', 'database_alert_rules', ['severity'])
        op.create_index('idx_database_alert_rules_enabled', 'database_alert_rules', ['enabled'])

    # Create database_monitoring_status table
    if 'database_monitoring_status' not in tables:
        op.create_table(
            'database_monitoring_status',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('monitoring_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('last_collection_time', sa.DateTime(), nullable=True),
            sa.Column('active_alerts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_metrics_collected', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('database_health', sa.String(20), nullable=False, server_default='healthy'),
            sa.Column('uptime_percentage', sa.Float(), nullable=False, server_default='100.0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

        # Create indexes for database_monitoring_status
        op.create_index('idx_database_monitoring_status_enabled', 'database_monitoring_status', ['monitoring_enabled'])
        op.create_index('idx_database_monitoring_status_last_collection', 'database_monitoring_status', ['last_collection_time'])


def downgrade():
    """Remove Database Monitoring-related tables"""

    # Drop indexes first
    try:
        op.drop_index('idx_database_monitoring_status_last_collection', 'database_monitoring_status')
        op.drop_index('idx_database_monitoring_status_enabled', 'database_monitoring_status')
    except Exception:
        pass  # Index may not exist

    try:
        op.drop_index('idx_database_alert_rules_enabled', 'database_alert_rules')
        op.drop_index('idx_database_alert_rules_severity', 'database_alert_rules')
        op.drop_index('idx_database_alert_rules_metric_type', 'database_alert_rules')
        op.drop_index('idx_database_alert_rules_rule_id', 'database_alert_rules')
    except Exception:
        pass  # Index may not exist

    try:
        op.drop_index('idx_database_performance_baselines_established_at', 'database_performance_baselines')
        op.drop_index('idx_database_performance_baselines_name', 'database_performance_baselines')
    except Exception:
        pass  # Index may not exist

    try:
        op.drop_index('idx_database_monitoring_configs_enabled', 'database_monitoring_configs')
    except Exception:
        pass  # Index may not exist

    try:
        op.drop_index('idx_database_metric_thresholds_enabled', 'database_metric_thresholds')
        op.drop_index('idx_database_metric_thresholds_metric_type', 'database_metric_thresholds')
    except Exception:
        pass  # Index may not exist

    # Drop tables
    try:
        op.drop_table('database_monitoring_status')
    except Exception:
        pass  # Table may not exist

    try:
        op.drop_table('database_alert_rules')
    except Exception:
        pass  # Table may not exist

    try:
        op.drop_table('database_performance_baselines')
    except Exception:
        pass  # Table may not exist

    try:
        op.drop_table('database_monitoring_configs')
    except Exception:
        pass  # Table may not exist

    try:
        op.drop_table('database_metric_thresholds')
    except Exception:
        pass  # Table may not exist
