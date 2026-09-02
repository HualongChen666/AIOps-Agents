# -*- coding: utf-8 -*-
"""
Add Workflow Persistence Tables

This migration ensures workflow-related tables are properly created for database persistence:
- workflows: Workflow definitions (replacing in-memory storage)
- workflow_executions: Workflow execution records

This migration supports the Workflow module completeness fix:
- Replaces in-memory storage with database persistence
- Ensures zero data loss during migration
- Provides audit trail for workflow operations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    """Add workflow persistence tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create workflows table
    if 'workflows' not in tables:
        op.create_table(
            'workflows',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('definition', sa.JSON(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='active', index=True),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_by', sa.String(50), nullable=True, index=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('idx_workflows_status', 'workflows', ['status'])
        op.create_index('idx_workflows_created_by', 'workflows', ['created_by'])
        op.create_index('idx_workflows_created_at', 'workflows', ['created_at'])

    # Create workflow_executions table
    if 'workflow_executions' not in tables:
        op.create_table(
            'workflow_executions',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('workflow_id', sa.String(100), nullable=False, index=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='running', index=True),
            sa.Column('result', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), server_default=sa.func.now(), index=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('duration_sec', sa.Float(), nullable=True),
            sa.Column('triggered_by', sa.String(50), nullable=True),
            sa.Column('trigger_source', sa.String(100), nullable=True),
            sa.Column('executor', sa.String(50), nullable=True),
        )
        op.create_index('idx_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
        op.create_index('idx_workflow_executions_status', 'workflow_executions', ['status'])
        op.create_index('idx_workflow_executions_started_at', 'workflow_executions', ['started_at'])


def downgrade():
    """Remove workflow persistence tables"""
    op.drop_index('idx_workflow_executions_started_at', 'workflow_executions')
    op.drop_index('idx_workflow_executions_status', 'workflow_executions')
    op.drop_index('idx_workflow_executions_workflow_id', 'workflow_executions')
    op.drop_table('workflow_executions')
    
    op.drop_index('idx_workflows_created_at', 'workflows')
    op.drop_index('idx_workflows_created_by', 'workflows')
    op.drop_index('idx_workflows_status', 'workflows')
    op.drop_table('workflows')
