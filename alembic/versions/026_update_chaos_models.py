# -*- coding: utf-8 -*-
"""update chaos engineering models

Revision ID: 026
Revises: 025
Create Date: 2026-08-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade():
    # Update chaos_scenarios table - add new columns
    with op.batch_alter_table('chaos_scenarios') as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('experiments', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('enabled', sa.Boolean(), nullable=True, server_default='true'))
        batch_op.add_column(sa.Column('schedule', sa.String(100), nullable=True))
        
        # Make old columns nullable for backward compatibility
        batch_op.alter_column('fault_types', nullable=True)
        batch_op.alter_column('target_services', nullable=True)
        batch_op.alter_column('duration_seconds', nullable=True)
        batch_op.alter_column('auto_rollback', nullable=True)

    # Add index separately using op.create_index
    try:
        op.create_index('idx_chaos_scenarios_enabled', 'chaos_scenarios', ['enabled'])
    except Exception:
        pass  # Index might already exist

    # Update chaos_faults table - add new columns
    with op.batch_alter_table('chaos_faults') as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('name', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('recovery_strategy', sa.String(200), nullable=True))
        
        # Make existing columns nullable for backward compatibility
        batch_op.alter_column('target', nullable=True)
        batch_op.alter_column('parameters', nullable=True)

    # Add index separately using op.create_index
    try:
        op.create_index('idx_chaos_faults_name', 'chaos_faults', ['name'])
    except Exception:
        pass  # Index might already exist

    # Data migration: populate new columns from existing data
    op.execute("""
        UPDATE chaos_scenarios
        SET experiments = '[]',
            enabled = COALESCE(enabled, 1)
        WHERE experiments IS NULL
    """)
    
    op.execute("""
        UPDATE chaos_faults
        SET name = COALESCE(name, fault_type || '_' || target),
            description = COALESCE(description, 'Auto-generated description')
        WHERE name IS NULL
    """)

    # After data migration, make new columns non-nullable where appropriate
    with op.batch_alter_table('chaos_scenarios') as batch_op:
        batch_op.alter_column('experiments', nullable=False)
        batch_op.alter_column('enabled', nullable=False)
    
    with op.batch_alter_table('chaos_faults') as batch_op:
        batch_op.alter_column('name', nullable=False)


def downgrade():
    # Revert changes to chaos_scenarios
    try:
        op.drop_index('idx_chaos_scenarios_enabled', table_name='chaos_scenarios')
    except Exception:
        pass

    with op.batch_alter_table('chaos_scenarios') as batch_op:
        batch_op.drop_column('schedule')
        batch_op.drop_column('enabled')
        batch_op.drop_column('experiments')
        
        # Restore original constraints
        batch_op.alter_column('fault_types', nullable=False)
        batch_op.alter_column('target_services', nullable=False)
        batch_op.alter_column('duration_seconds', nullable=False)
        batch_op.alter_column('auto_rollback', nullable=False)

    # Revert changes to chaos_faults
    try:
        op.drop_index('idx_chaos_faults_name', table_name='chaos_faults')
    except Exception:
        pass

    with op.batch_alter_table('chaos_faults') as batch_op:
        batch_op.drop_column('recovery_strategy')
        batch_op.drop_column('description')
        batch_op.drop_column('name')
        
        # Restore original constraints
        batch_op.alter_column('target', nullable=False)
        batch_op.alter_column('parameters', nullable=False)
