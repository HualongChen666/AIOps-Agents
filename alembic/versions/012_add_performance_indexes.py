# -*- coding: utf-8 -*-
"""
Add Performance Indexes for Query Optimization

This migration adds performance indexes to optimize database queries
based on the query analysis results. Priority is given to frequently
queried columns and foreign key relationships.

Target: Add 10+ indexes for query optimization
Expected improvement: 40-60% query time reduction
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


# revision identifiers
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for query optimization"""
    
    # Priority 1: Alert table additional indexes (some already exist)
    op.create_index(
        'idx_alerts_host_detected_at',
        'alerts',
        ['host', 'detected_at']
    )
    
    # Priority 2: RepairRecord table indexes
    op.create_index(
        'idx_repair_records_alert_id',
        'repair_records',
        ['alert_id']
    )
    
    op.create_index(
        'idx_repair_records_status',
        'repair_records',
        ['status']
    )
    
    op.create_index(
        'idx_repair_records_repair_time',
        'repair_records',
        ['repair_time']
    )
    
    # Priority 3: Metrics table indexes
    op.create_index(
        'idx_metrics_timestamp',
        'metrics',
        ['timestamp']
    )
    
    op.create_index(
        'idx_metrics_name_timestamp',
        'metrics',
        ['name', 'timestamp']
    )
    
    # Priority 4: Workflow table indexes
    op.create_index(
        'idx_workflows_status',
        'workflows',
        ['status']
    )
    
    op.create_index(
        'idx_workflows_created_at',
        'workflows',
        ['created_at']
    )
    
    # Priority 5: User table indexes
    op.create_index(
        'idx_users_last_login_at',
        'users',
        ['last_login_at']
    )
    
    op.create_index(
        'idx_users_role_disabled',
        'users',
        ['role', 'disabled']
    )
    
    # Priority 6: AuditLog table indexes
    op.create_index(
        'idx_audit_logs_resource_id',
        'audit_logs',
        ['resource_id']
    )
    
    op.create_index(
        'idx_audit_logs_created_at',
        'audit_logs',
        ['created_at']
    )
    
    # Priority 7: WorkflowExecution table indexes
    op.create_index(
        'idx_workflow_executions_workflow_id',
        'workflow_executions',
        ['workflow_id']
    )
    
    op.create_index(
        'idx_workflow_executions_status',
        'workflow_executions',
        ['status']
    )
    
    # Priority 8: PendingApproval table indexes
    op.create_index(
        'idx_pending_approvals_alert_id',
        'pending_approvals',
        ['alert_id']
    )
    
    op.create_index(
        'idx_pending_approvals_status',
        'pending_approvals',
        ['status']
    )


def downgrade():
    """Remove performance indexes"""
    
    # Alert table additional indexes
    op.drop_index('idx_alerts_host_detected_at', table_name='alerts')
    
    # RepairRecord table indexes
    op.drop_index('idx_repair_records_alert_id', table_name='repair_records')
    op.drop_index('idx_repair_records_status', table_name='repair_records')
    op.drop_index('idx_repair_records_repair_time', table_name='repair_records')
    
    # Metrics table indexes
    op.drop_index('idx_metrics_timestamp', table_name='metrics')
    op.drop_index('idx_metrics_name_timestamp', table_name='metrics')
    
    # Workflow table indexes
    op.drop_index('idx_workflows_status', table_name='workflows')
    op.drop_index('idx_workflows_created_at', table_name='workflows')
    
    # User table indexes
    op.drop_index('idx_users_last_login_at', table_name='users')
    op.drop_index('idx_users_role_disabled', table_name='users')
    
    # AuditLog table indexes
    op.drop_index('idx_audit_logs_resource_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    
    # WorkflowExecution table indexes
    op.drop_index('idx_workflow_executions_workflow_id', table_name='workflow_executions')
    op.drop_index('idx_workflow_executions_status', table_name='workflow_executions')
    
    # PendingApproval table indexes
    op.drop_index('idx_pending_approvals_alert_id', table_name='pending_approvals')
    op.drop_index('idx_pending_approvals_status', table_name='pending_approvals')