# -*- coding: utf-8 -*-
"""
Add Plugin System Models

This migration adds Plugin System-related tables to support plugin management:
- plugins: Plugin main table for plugin metadata and configuration
- plugin_executions: Plugin execution records for tracking plugin runs
- plugin_configs: Plugin configuration storage

This model supports the Plugin API endpoints:
- Plugin Management: GET/POST /api/plugins/*
- Plugin Execution: POST /api/plugins/{name}/run
- Plugin Configuration: GET/PUT /api/plugins/{name}/config
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    """Add Plugin System-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create plugins table
    if 'plugins' not in tables:
        op.create_table(
            'plugins',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('version', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('author', sa.String(200), nullable=True),
            sa.Column('plugin_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='inactive'),
            sa.Column('config_schema', sa.JSON(), nullable=True),
            sa.Column('default_config', sa.JSON(), nullable=True),
            sa.Column('dependencies', sa.JSON(), nullable=True),
            sa.Column('file_path', sa.String(500), nullable=True),
            sa.Column('entry_point', sa.String(200), nullable=True),
            sa.Column('plugin_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('installed_at', sa.DateTime(), nullable=True),
            sa.Column('last_loaded_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
            sa.Index('idx_plugins_name', 'name'),
            sa.Index('idx_plugins_type', 'plugin_type'),
            sa.Index('idx_plugins_status', 'status'),
            sa.Index('idx_plugins_version', 'version'),
        )

    # Create plugin_executions table
    if 'plugin_executions' not in tables:
        op.create_table(
            'plugin_executions',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('plugin_id', sa.String(100), nullable=False),
            sa.Column('plugin_name', sa.String(200), nullable=False),
            sa.Column('execution_type', sa.String(50), nullable=False),
            sa.Column('trigger_type', sa.String(50), nullable=False),
            sa.Column('input_data', sa.JSON(), nullable=True),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('output_data', sa.JSON(), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('error_traceback', sa.Text(), nullable=True),
            sa.Column('duration_ms', sa.Float(), nullable=True),
            sa.Column('memory_usage_mb', sa.Float(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('executed_by', sa.String(50), nullable=True),
            sa.Column('execution_metadata', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.Index('idx_plugin_executions_plugin_id', 'plugin_id'),
            sa.Index('idx_plugin_executions_plugin_name', 'plugin_name'),
            sa.Index('idx_plugin_executions_success', 'success'),
            sa.Index('idx_plugin_executions_started_at', 'started_at'),
            sa.Index('idx_plugin_executions_execution_type', 'execution_type'),
        )

    # Create plugin_configs table
    if 'plugin_configs' not in tables:
        op.create_table(
            'plugin_configs',
            sa.Column('id', sa.String(100), nullable=False),
            sa.Column('plugin_id', sa.String(100), nullable=False),
            sa.Column('plugin_name', sa.String(200), nullable=False),
            sa.Column('config_data', sa.JSON(), nullable=False),
            sa.Column('config_version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_by', sa.String(50), nullable=True),
            sa.Column('config_metadata', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('plugin_id'),
            sa.Index('idx_plugin_configs_plugin_id', 'plugin_id'),
            sa.Index('idx_plugin_configs_plugin_name', 'plugin_name'),
            sa.Index('idx_plugin_configs_is_active', 'is_active'),
        )


def downgrade():
    """Remove Plugin System-related tables"""

    # Drop tables in reverse order of creation (to handle foreign key constraints)
    op.drop_table('plugin_configs')
    op.drop_table('plugin_executions')
    op.drop_table('plugins')
