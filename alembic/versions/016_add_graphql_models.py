# -*- coding: utf-8 -*-
"""
Add GraphQL Models

This migration adds GraphQL-related tables to support GraphQL query management:
- graphql_query_configs: Stores GraphQL query configurations with permissions and performance settings
- graphql_query_history: Stores GraphQL query execution history for auditing and analysis
- graphql_performance_stats: Stores aggregated GraphQL performance statistics

This model supports the new endpoints:
- GET /api/graphql/graphql-query: Returns GraphQL query configuration, history, and performance stats
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, Index


# revision identifiers
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    """Add GraphQL-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Create graphql_query_configs table
    if 'graphql_query_configs' not in tables:
        op.create_table(
            'graphql_query_configs',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('config_name', sa.String(200), nullable=False),
            sa.Column('query_template', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('required_roles', sa.JSON(), nullable=True),
            sa.Column('required_permissions', sa.JSON(), nullable=True),
            sa.Column('max_complexity', sa.Integer(), nullable=True),
            sa.Column('max_depth', sa.Integer(), nullable=True),
            sa.Column('timeout_ms', sa.Integer(), nullable=True),
            sa.Column('cache_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('cache_ttl_seconds', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('updated_by', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
            sa.Column('meta_data', sa.JSON(), nullable=True),
        )

        # Create indexes for graphql_query_configs
        op.create_index('idx_graphql_query_configs_name', 'graphql_query_configs', ['config_name'])
        op.create_index('idx_graphql_query_configs_active', 'graphql_query_configs', ['is_active'])

    # Create graphql_query_history table
    if 'graphql_query_history' not in tables:
        op.create_table(
            'graphql_query_history',
            sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
            sa.Column('query_id', sa.String(100), nullable=True),
            sa.Column('query_string', sa.Text(), nullable=False),
            sa.Column('variables', sa.JSON(), nullable=True),
            sa.Column('operation_name', sa.String(100), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('username', sa.String(50), nullable=True),
            sa.Column('tenant_id', sa.String(50), nullable=True),
            sa.Column('execution_time_ms', sa.Float(), nullable=True),
            sa.Column('complexity_score', sa.Integer(), nullable=True),
            sa.Column('depth', sa.Integer(), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('error_code', sa.String(50), nullable=True),
            sa.Column('result_size_bytes', sa.Integer(), nullable=True),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.String(500), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        )

        # Create indexes for graphql_query_history
        op.create_index('idx_graphql_query_history_query_id', 'graphql_query_history', ['query_id'])
        op.create_index('idx_graphql_query_history_user_id', 'graphql_query_history', ['user_id'])
        op.create_index('idx_graphql_query_history_tenant_id', 'graphql_query_history', ['tenant_id'])
        op.create_index('idx_graphql_query_history_success', 'graphql_query_history', ['success'])
        op.create_index('idx_graphql_query_history_created_at', 'graphql_query_history', ['created_at'])

    # Create graphql_performance_stats table
    if 'graphql_performance_stats' not in tables:
        op.create_table(
            'graphql_performance_stats',
            sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
            sa.Column('stat_type', sa.String(50), nullable=False),
            sa.Column('stat_key', sa.String(200), nullable=False),
            sa.Column('tenant_id', sa.String(50), nullable=True),
            sa.Column('window_start', sa.DateTime(), nullable=False),
            sa.Column('window_end', sa.DateTime(), nullable=False),
            sa.Column('total_executions', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('successful_executions', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('failed_executions', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('avg_execution_time_ms', sa.Float(), nullable=True),
            sa.Column('min_execution_time_ms', sa.Float(), nullable=True),
            sa.Column('max_execution_time_ms', sa.Float(), nullable=True),
            sa.Column('p50_execution_time_ms', sa.Float(), nullable=True),
            sa.Column('p95_execution_time_ms', sa.Float(), nullable=True),
            sa.Column('p99_execution_time_ms', sa.Float(), nullable=True),
            sa.Column('avg_complexity', sa.Float(), nullable=True),
            sa.Column('avg_depth', sa.Integer(), nullable=True),
            sa.Column('avg_result_size_bytes', sa.Float(), nullable=True),
            sa.Column('total_result_size_bytes', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('error_rate', sa.Float(), nullable=True),
            sa.Column('common_errors', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        )

        # Create indexes for graphql_performance_stats
        op.create_index('idx_graphql_performance_stats_type_key', 'graphql_performance_stats', ['stat_type', 'stat_key'])
        op.create_index('idx_graphql_performance_stats_tenant', 'graphql_performance_stats', ['tenant_id'])
        op.create_index('idx_graphql_performance_stats_window', 'graphql_performance_stats', ['window_start', 'window_end'])


def downgrade():
    """Remove GraphQL-related tables"""

    # Check if tables exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'graphql_performance_stats' in tables:
        # Drop indexes first
        try:
            op.drop_index('idx_graphql_performance_stats_window', 'graphql_performance_stats')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_performance_stats_tenant', 'graphql_performance_stats')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_performance_stats_type_key', 'graphql_performance_stats')
        except Exception:
            pass
        op.drop_table('graphql_performance_stats')
    
    if 'graphql_query_history' in tables:
        try:
            op.drop_index('idx_graphql_query_history_created_at', 'graphql_query_history')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_query_history_success', 'graphql_query_history')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_query_history_tenant_id', 'graphql_query_history')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_query_history_user_id', 'graphql_query_history')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_query_history_query_id', 'graphql_query_history')
        except Exception:
            pass
        op.drop_table('graphql_query_history')
    
    if 'graphql_query_configs' in tables:
        try:
            op.drop_index('idx_graphql_query_configs_active', 'graphql_query_configs')
        except Exception:
            pass
        try:
            op.drop_index('idx_graphql_query_configs_name', 'graphql_query_configs')
        except Exception:
            pass
        op.drop_table('graphql_query_configs')
