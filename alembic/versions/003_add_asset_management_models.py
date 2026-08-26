"""Add asset management models

Revision ID: 003_add_asset_management_models
Revises: 002_add_ai_compliance_builder_models
Create Date: 2026-08-26 09:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '003_add_asset_management_models'
down_revision = '002_add_ai_compliance_builder_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create asset_inventory_metadata table
    op.create_table(
        'asset_inventory_metadata',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('inventory_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Index('idx_asset_inventory_metadata_asset_id', 'asset_id'),
    )
    op.create_primary_key('pk_asset_inventory_metadata', 'asset_inventory_metadata', ['id'])

    # Create asset_relationships table
    op.create_table(
        'asset_relationships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Index('idx_asset_relationships_source_id', 'source_id'),
        sa.Index('idx_asset_relationships_target_id', 'target_id'),
        sa.Index('idx_asset_relationships_type', 'relationship_type'),
    )
    op.create_primary_key('pk_asset_relationships', 'asset_relationships', ['id'])

    # Create asset_lifecycles table
    op.create_table(
        'asset_lifecycles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Index('idx_asset_lifecycles_asset_id', 'asset_id'),
        sa.Index('idx_asset_lifecycles_stage', 'stage'),
        sa.Index('idx_asset_lifecycles_status', 'status'),
    )
    op.create_primary_key('pk_asset_lifecycles', 'asset_lifecycles', ['id'])

    # Create asset_dependencies table
    op.create_table(
        'asset_dependencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=False),
        sa.Column('dependency_details', sa.JSON(), nullable=False),
        sa.Column('criticality', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Index('idx_asset_dependencies_asset_id', 'asset_id'),
        sa.Index('idx_asset_dependencies_type', 'dependency_type'),
        sa.Index('idx_asset_dependencies_criticality', 'criticality'),
    )
    op.create_primary_key('pk_asset_dependencies', 'asset_dependencies', ['id'])


def downgrade():
    # Drop asset_dependencies table
    op.drop_table('asset_dependencies')

    # Drop asset_lifecycles table
    op.drop_table('asset_lifecycles')

    # Drop asset_relationships table
    op.drop_table('asset_relationships')

    # Drop asset_inventory_metadata table
    op.drop_table('asset_inventory_metadata')
