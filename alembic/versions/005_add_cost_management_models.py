"""Add cost management models

Revision ID: 005_add_cost_management_models
Revises: 004_add_capacity_planning_models
Create Date: 2026-08-26 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '005_add_cost_management_models'
down_revision = '004_add_capacity_planning_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create cost_budgets table
    op.create_table(
        'cost_budgets',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('spent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('remaining', sa.Float(), nullable=False),
        sa.Column('period', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='on_track'),
        sa.Column('alerts_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('budget_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_cost_budgets_service', 'service'),
        sa.Index('idx_cost_budgets_status', 'status'),
    )
    op.create_primary_key('pk_cost_budgets', 'cost_budgets', ['id'])

    # Create cost_optimizations table
    op.create_table(
        'cost_optimizations',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('optimization_type', sa.String(50), nullable=False),
        sa.Column('potential_savings', sa.Float(), nullable=False),
        sa.Column('implementation_effort', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('opt_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_cost_optimizations_service', 'service'),
        sa.Index('idx_cost_optimizations_priority', 'priority'),
        sa.Index('idx_cost_optimizations_status', 'status'),
    )
    op.create_primary_key('pk_cost_optimizations', 'cost_optimizations', ['id'])

    # Create cost_anomalies table
    op.create_table(
        'cost_anomalies',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('anomaly_type', sa.String(50), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('affected_amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('anomaly_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_cost_anomalies_service', 'service'),
        sa.Index('idx_cost_anomalies_severity', 'severity'),
        sa.Index('idx_cost_anomalies_status', 'status'),
    )
    op.create_primary_key('pk_cost_anomalies', 'cost_anomalies', ['id'])

    # Create cost_alerts table
    op.create_table(
        'cost_alerts',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('notification_channels', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('alert_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_cost_alerts_service', 'service'),
        sa.Index('idx_cost_alerts_status', 'status'),
    )
    op.create_primary_key('pk_cost_alerts', 'cost_alerts', ['id'])

    # Create cost_reports table
    op.create_table(
        'cost_reports',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='completed'),
        sa.Column('report_data', sa.JSON(), nullable=False),
        sa.Column('report_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_cost_reports_type', 'report_type'),
        sa.Index('idx_cost_reports_status', 'status'),
    )
    op.create_primary_key('pk_cost_reports', 'cost_reports', ['id'])


def downgrade():
    # Drop cost_reports table
    op.drop_table('cost_reports')

    # Drop cost_alerts table
    op.drop_table('cost_alerts')

    # Drop cost_anomalies table
    op.drop_table('cost_anomalies')

    # Drop cost_optimizations table
    op.drop_table('cost_optimizations')

    # Drop cost_budgets table
    op.drop_table('cost_budgets')
