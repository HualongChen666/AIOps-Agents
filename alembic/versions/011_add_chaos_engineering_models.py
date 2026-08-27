# -*- coding: utf-8 -*-
"""add chaos engineering models

Revision ID: 011
Revises: 010
Create Date: 2026-08-26 17:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # Create chaos_experiments table
    op.create_table(
        'chaos_experiments',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('experiment_type', sa.String(50), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_chaos_experiments_name', 'name'),
        sa.Index('idx_chaos_experiments_status', 'status'),
        sa.Index('idx_chaos_experiments_severity', 'severity'),
        sa.Index('idx_chaos_experiments_created_at', 'created_at'),
    )

    # Create chaos_scenarios table
    op.create_table(
        'chaos_scenarios',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fault_types', sa.JSON(), nullable=False),
        sa.Column('target_services', sa.JSON(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('auto_rollback', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_chaos_scenarios_name', 'name'),
        sa.Index('idx_chaos_scenarios_created_at', 'created_at'),
    )

    # Create chaos_faults table
    op.create_table(
        'chaos_faults',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('fault_type', sa.String(50), nullable=False),
        sa.Column('target', sa.String(200), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_chaos_faults_fault_type', 'fault_type'),
        sa.Index('idx_chaos_faults_status', 'status'),
        sa.Index('idx_chaos_faults_created_at', 'created_at'),
    )


def downgrade():
    op.drop_table('chaos_faults')
    op.drop_table('chaos_scenarios')
    op.drop_table('chaos_experiments')