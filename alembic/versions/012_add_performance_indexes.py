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
    
    # Get the bind to check existing tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Priority 1: Alert table additional indexes (some already exist)
    if 'alerts' in existing_tables:
        try:
            op.create_index(
                'idx_alerts_host_detected_at',
                'alerts',
                ['host', 'detected_at']
            )
        except Exception as e:
            print(f"Warning: Could not create index on alerts table: {e}")
    
    # Priority 2: RepairRecord table indexes
    if 'repair_records' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on repair_records table: {e}")
    
    # Priority 3: Metrics table indexes
    if 'metrics' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on metrics table: {e}")
    
    # Priority 4: Workflow table indexes
    if 'workflows' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on workflows table: {e}")
    
    # Priority 5: User table indexes
    if 'users' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on users table: {e}")
    
    # Priority 6: AuditLog table indexes
    if 'audit_logs' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on audit_logs table: {e}")
    
    # Priority 7: WorkflowExecution table indexes
    if 'workflow_executions' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on workflow_executions table: {e}")
    
    # Priority 8: PendingApproval table indexes
    if 'pending_approvals' in existing_tables:
        try:
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
        except Exception as e:
            print(f"Warning: Could not create indexes on pending_approvals table: {e}")


def downgrade():
    """Remove performance indexes"""
    
    # Get the bind to check existing tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Alert table additional indexes
    if 'alerts' in existing_tables:
        try:
            op.drop_index('idx_alerts_host_detected_at', table_name='alerts')
        except Exception as e:
            print(f"Warning: Could not drop index on alerts table: {e}")
    
    # RepairRecord table indexes
    if 'repair_records' in existing_tables:
        try:
            op.drop_index('idx_repair_records_alert_id', table_name='repair_records')
            op.drop_index('idx_repair_records_status', table_name='repair_records')
            op.drop_index('idx_repair_records_repair_time', table_name='repair_records')
        except Exception as e:
            print(f"Warning: Could not drop indexes on repair_records table: {e}")
    
    # Metrics table indexes
    if 'metrics' in existing_tables:
        try:
            op.drop_index('idx_metrics_timestamp', table_name='metrics')
            op.drop_index('idx_metrics_name_timestamp', table_name='metrics')
        except Exception as e:
            print(f"Warning: Could not drop indexes on metrics table: {e}")
    
    # Workflow table indexes
    if 'workflows' in existing_tables:
        try:
            op.drop_index('idx_workflows_status', table_name='workflows')
            op.drop_index('idx_workflows_created_at', table_name='workflows')
        except Exception as e:
            print(f"Warning: Could not drop indexes on workflows table: {e}")
    
    # User table indexes
    if 'users' in existing_tables:
        try:
            op.drop_index('idx_users_last_login_at', table_name='users')
            op.drop_index('idx_users_role_disabled', table_name='users')
        except Exception as e:
            print(f"Warning: Could not drop indexes on users table: {e}")
    
    # AuditLog table indexes
    if 'audit_logs' in existing_tables:
        try:
            op.drop_index('idx_audit_logs_resource_id', table_name='audit_logs')
            op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
        except Exception as e:
            print(f"Warning: Could not drop indexes on audit_logs table: {e}")
    
    # WorkflowExecution table indexes
    if 'workflow_executions' in existing_tables:
        try:
            op.drop_index('idx_workflow_executions_workflow_id', table_name='workflow_executions')
            op.drop_index('idx_workflow_executions_status', table_name='workflow_executions')
        except Exception as e:
            print(f"Warning: Could not drop indexes on workflow_executions table: {e}")
    
    # PendingApproval table indexes
    if 'pending_approvals' in existing_tables:
        try:
            op.drop_index('idx_pending_approvals_alert_id', table_name='pending_approvals')
            op.drop_index('idx_pending_approvals_status', table_name='pending_approvals')
        except Exception as e:
            print(f"Warning: Could not drop indexes on pending_approvals table: {e}")