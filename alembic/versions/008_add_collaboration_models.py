"""Add collaboration management models

Revision ID: 008_add_collaboration_models
Revises: 007_add_ai_advanced_models
Create Date: 2026-08-26 11:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '008_add_collaboration_models'
down_revision = '007_add_ai_advanced_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create collaboration_teams table
    op.create_table(
        'collaboration_teams',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('team_name', sa.String(255), nullable=False),
        sa.Column('team_description', sa.Text(), nullable=True),
        sa.Column('team_status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('team_lead_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('team_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_collaboration_teams_status', 'team_status'),
    )
    op.create_primary_key('pk_collaboration_teams', 'collaboration_teams', ['id'])

    # Create collaboration_members table
    op.create_table(
        'collaboration_members',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('member_name', sa.String(255), nullable=False),
        sa.Column('member_email', sa.String(255), nullable=True),
        sa.Column('member_role', sa.String(50), nullable=False),
        sa.Column('member_status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('member_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_collaboration_members_team_id', 'team_id'),
        sa.Index('idx_collaboration_members_status', 'member_status'),
    )
    op.create_primary_key('pk_collaboration_members', 'collaboration_members', ['id'])

    # Create collaboration_permissions table
    op.create_table(
        'collaboration_permissions',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('member_id', sa.String(50), nullable=False),
        sa.Column('permission_type', sa.String(50), nullable=False),
        sa.Column('permission_level', sa.String(50), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('permission_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_collaboration_permissions_team_id', 'team_id'),
        sa.Index('idx_collaboration_permissions_member_id', 'member_id'),
    )
    op.create_primary_key('pk_collaboration_permissions', 'collaboration_permissions', ['id'])

    # Create collaboration_activities table
    op.create_table(
        'collaboration_activities',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('member_id', sa.String(50), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('activity_description', sa.Text(), nullable=True),
        sa.Column('activity_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('activity_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_collaboration_activities_team_id', 'team_id'),
        sa.Index('idx_collaboration_activities_member_id', 'member_id'),
        sa.Index('idx_collaboration_activities_created_at', 'created_at'),
    )
    op.create_primary_key('pk_collaboration_activities', 'collaboration_activities', ['id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('collaboration_activities')
    op.drop_table('collaboration_permissions')
    op.drop_table('collaboration_members')
    op.drop_table('collaboration_teams')
