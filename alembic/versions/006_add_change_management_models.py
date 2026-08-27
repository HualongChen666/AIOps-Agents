"""Add change management models

Revision ID: 006_add_change_management_models
Revises: 005_add_cost_management_models
Create Date: 2026-08-26 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create change_approvals table
    op.create_table(
        'change_approvals',
        sa.Column('id', sa.String(20), nullable=False),
        sa.Column('request_id', sa.String(50), nullable=False),
        sa.Column('approver', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approval_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_change_approvals_request_id', 'request_id'),
        sa.Index('idx_change_approvals_status', 'status'),
    )
    op.create_primary_key('pk_change_approvals', 'change_approvals', ['id'])

    # Create change_schedules table
    op.create_table(
        'change_schedules',
        sa.Column('id', sa.String(20), nullable=False),
        sa.Column('request_id', sa.String(50), nullable=False),
        sa.Column('scheduled_start', sa.DateTime(), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(), nullable=False),
        sa.Column('maintenance_window', sa.String(50), nullable=False),
        sa.Column('timezone', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='scheduled'),
        sa.Column('schedule_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_change_schedules_request_id', 'request_id'),
        sa.Index('idx_change_schedules_status', 'status'),
    )
    op.create_primary_key('pk_change_schedules', 'change_schedules', ['id'])

    # Create change_rollback_plans table
    op.create_table(
        'change_rollback_plans',
        sa.Column('id', sa.String(20), nullable=False),
        sa.Column('request_id', sa.String(50), nullable=False),
        sa.Column('rollback_steps', sa.JSON(), nullable=False),
        sa.Column('data_consistency_checks', sa.JSON(), nullable=False),
        sa.Column('rollback_triggers', sa.JSON(), nullable=False),
        sa.Column('validation_after_rollback', sa.JSON(), nullable=False),
        sa.Column('estimated_rollback_time', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='ready'),
        sa.Column('rollback_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_change_rollback_plans_request_id', 'request_id'),
        sa.Index('idx_change_rollback_plans_status', 'status'),
    )
    op.create_primary_key('pk_change_rollback_plans', 'change_rollback_plans', ['id'])


def downgrade():
    # Drop change_rollback_plans table
    op.drop_table('change_rollback_plans')

    # Drop change_schedules table
    op.drop_table('change_schedules')

    # Drop change_approvals table
    op.drop_table('change_approvals')
