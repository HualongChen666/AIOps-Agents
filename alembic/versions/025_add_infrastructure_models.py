# -*- coding: utf-8 -*-
"""
Add Infrastructure Models

This migration adds Infrastructure-related tables to support infrastructure management:
- infrastructure_kafka_messages: Kafka message tracking
- infrastructure_flink_jobs: Flink job management
- infrastructure_storage: Storage configuration tracking
- infrastructure_configs: Configuration center storage
- infrastructure_data_flows: Data flow tracking
- infrastructure_monitoring: Monitoring component tracking

This model supports the Infrastructure API endpoints:
- Kafka: POST /api/v1/infrastructure/kafka/send, GET /api/v1/infrastructure/kafka/status
- Flink: POST /api/v1/infrastructure/flink/job, GET /api/v1/infrastructure/flink/jobs
- Storage: GET /api/v1/infrastructure/storage/*
- Config: POST /api/v1/infrastructure/config, GET /api/v1/infrastructure/config/*
- Data Flow: GET /api/v1/infrastructure/data-flow/stats
- Monitoring: GET /api/v1/infrastructure/monitoring/status
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade():
    """Add Infrastructure-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create infrastructure_kafka_messages table
    if 'infrastructure_kafka_messages' not in tables:
        op.create_table(
            'infrastructure_kafka_messages',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('topic', sa.String(200), nullable=False),
            sa.Column('key', sa.String(500), nullable=False),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.Column('headers', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='sent'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('sent_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('idx_infrastructure_kafka_topic', 'infrastructure_kafka_messages', ['topic'])
        op.create_index('idx_infrastructure_kafka_status', 'infrastructure_kafka_messages', ['status'])
        op.create_index('idx_infrastructure_kafka_sent_at', 'infrastructure_kafka_messages', ['sent_at'])

    # Create infrastructure_flink_jobs table
    if 'infrastructure_flink_jobs' not in tables:
        op.create_table(
            'infrastructure_flink_jobs',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('job_name', sa.String(200), nullable=False, unique=True),
            sa.Column('job_type', sa.String(50), nullable=False),
            sa.Column('parallelism', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('status', sa.String(20), nullable=False, server_default='created'),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('stopped_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_infrastructure_flink_job_name', 'infrastructure_flink_jobs', ['job_name'])
        op.create_index('idx_infrastructure_flink_job_type', 'infrastructure_flink_jobs', ['job_type'])
        op.create_index('idx_infrastructure_flink_status', 'infrastructure_flink_jobs', ['status'])

    # Create infrastructure_storage table
    if 'infrastructure_storage' not in tables:
        op.create_table(
            'infrastructure_storage',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('storage_type', sa.String(50), nullable=False),
            sa.Column('endpoint', sa.String(500), nullable=False),
            sa.Column('bucket_name', sa.String(200), nullable=False),
            sa.Column('access_key', sa.String(200), nullable=False),
            sa.Column('secret_key', sa.String(200), nullable=False),
            sa.Column('region', sa.String(50), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('health_status', sa.String(20), nullable=False, server_default='unknown'),
            sa.Column('last_health_check', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('idx_infrastructure_storage_type', 'infrastructure_storage', ['storage_type'])
        op.create_index('idx_infrastructure_storage_status', 'infrastructure_storage', ['status'])

    # Create infrastructure_configs table
    if 'infrastructure_configs' not in tables:
        op.create_table(
            'infrastructure_configs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('key', sa.String(200), unique=True, nullable=False),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('category', sa.String(50), nullable=True),
            sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('updated_by', sa.String(50), nullable=True),
        )
        op.create_index('idx_infrastructure_config_key', 'infrastructure_configs', ['key'])
        op.create_index('idx_infrastructure_config_category', 'infrastructure_configs', ['category'])

    # Create infrastructure_data_flows table
    if 'infrastructure_data_flows' not in tables:
        op.create_table(
            'infrastructure_data_flows',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('flow_name', sa.String(200), nullable=False, unique=True),
            sa.Column('flow_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='stopped'),
            sa.Column('total_processed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_analyzed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_errors', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('avg_processing_time_ms', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('stopped_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('idx_infrastructure_data_flow_name', 'infrastructure_data_flows', ['flow_name'])
        op.create_index('idx_infrastructure_data_flow_type', 'infrastructure_data_flows', ['flow_type'])
        op.create_index('idx_infrastructure_data_flow_status', 'infrastructure_data_flows', ['status'])

    # Create infrastructure_monitoring table
    if 'infrastructure_monitoring' not in tables:
        op.create_table(
            'infrastructure_monitoring',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('component_name', sa.String(200), nullable=False, unique=True),
            sa.Column('component_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('endpoint', sa.String(500), nullable=True),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('health_status', sa.String(20), nullable=False, server_default='unknown'),
            sa.Column('last_health_check', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('idx_infrastructure_monitoring_name', 'infrastructure_monitoring', ['component_name'])
        op.create_index('idx_infrastructure_monitoring_type', 'infrastructure_monitoring', ['component_type'])
        op.create_index('idx_infrastructure_monitoring_status', 'infrastructure_monitoring', ['status'])


def downgrade():
    """Remove Infrastructure-related tables"""

    # Drop indexes first
    op.drop_index('idx_infrastructure_monitoring_status', 'infrastructure_monitoring', checkfirst=True)
    op.drop_index('idx_infrastructure_monitoring_type', 'infrastructure_monitoring', checkfirst=True)
    op.drop_index('idx_infrastructure_monitoring_name', 'infrastructure_monitoring', checkfirst=True)
    op.drop_table('infrastructure_monitoring', checkfirst=True)

    op.drop_index('idx_infrastructure_data_flow_status', 'infrastructure_data_flows', checkfirst=True)
    op.drop_index('idx_infrastructure_data_flow_type', 'infrastructure_data_flows', checkfirst=True)
    op.drop_index('idx_infrastructure_data_flow_name', 'infrastructure_data_flows', checkfirst=True)
    op.drop_table('infrastructure_data_flows', checkfirst=True)

    op.drop_index('idx_infrastructure_config_category', 'infrastructure_configs', checkfirst=True)
    op.drop_index('idx_infrastructure_config_key', 'infrastructure_configs', checkfirst=True)
    op.drop_table('infrastructure_configs', checkfirst=True)

    op.drop_index('idx_infrastructure_storage_status', 'infrastructure_storage', checkfirst=True)
    op.drop_index('idx_infrastructure_storage_type', 'infrastructure_storage', checkfirst=True)
    op.drop_table('infrastructure_storage', checkfirst=True)

    op.drop_index('idx_infrastructure_flink_status', 'infrastructure_flink_jobs', checkfirst=True)
    op.drop_index('idx_infrastructure_flink_job_type', 'infrastructure_flink_jobs', checkfirst=True)
    op.drop_index('idx_infrastructure_flink_job_name', 'infrastructure_flink_jobs', checkfirst=True)
    op.drop_table('infrastructure_flink_jobs', checkfirst=True)

    op.drop_index('idx_infrastructure_kafka_sent_at', 'infrastructure_kafka_messages', checkfirst=True)
    op.drop_index('idx_infrastructure_kafka_status', 'infrastructure_kafka_messages', checkfirst=True)
    op.drop_index('idx_infrastructure_kafka_topic', 'infrastructure_kafka_messages', checkfirst=True)
    op.drop_table('infrastructure_kafka_messages', checkfirst=True)
