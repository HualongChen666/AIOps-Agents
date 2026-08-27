"""Add plugin marketplace models

Revision ID: 009_add_plugin_marketplace_models
Revises: 008_add_collaboration_models
Create Date: 2026-08-26 11:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Create plugin_listings table
    op.create_table(
        'plugin_listings',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('plugin_id', sa.String(50), nullable=False),
        sa.Column('plugin_name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('author', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, server_default='general'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('quality', sa.String(50), nullable=False, server_default='community'),
        sa.Column('download_url', sa.String(500), nullable=False),
        sa.Column('screenshot_urls', sa.JSON(), nullable=True),
        sa.Column('documentation_url', sa.String(500), nullable=True),
        sa.Column('repository_url', sa.String(500), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('listing_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_plugin_listings_plugin_id', 'plugin_id'),
        sa.Index('idx_plugin_listings_category', 'category'),
        sa.Index('idx_plugin_listings_enabled', 'enabled'),
    )
    op.create_primary_key('pk_plugin_listings', 'plugin_listings', ['id'])

    # Create plugin_reviews table
    op.create_table(
        'plugin_reviews',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('plugin_id', sa.String(50), nullable=False),
        sa.Column('reviewer_id', sa.String(50), nullable=False),
        sa.Column('reviewer_name', sa.String(255), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('review_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_plugin_reviews_plugin_id', 'plugin_id'),
        sa.Index('idx_plugin_reviews_reviewer_id', 'reviewer_id'),
    )
    op.create_primary_key('pk_plugin_reviews', 'plugin_reviews', ['id'])

    # Create plugin_categories table
    op.create_table(
        'plugin_categories',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('category_name', sa.String(255), nullable=False),
        sa.Column('category_description', sa.Text(), nullable=True),
        sa.Column('parent_category_id', sa.String(50), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('category_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_plugin_categories_enabled', 'enabled'),
    )
    op.create_primary_key('pk_plugin_categories', 'plugin_categories', ['id'])

    # Create installed_plugins table
    op.create_table(
        'installed_plugins',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('plugin_id', sa.String(50), nullable=False),
        sa.Column('installed_version', sa.String(50), nullable=False),
        sa.Column('installation_date', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('installation_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_installed_plugins_plugin_id', 'plugin_id'),
        sa.Index('idx_installed_plugins_enabled', 'enabled'),
    )
    op.create_primary_key('pk_installed_plugins', 'installed_plugins', ['id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('installed_plugins')
    op.drop_table('plugin_categories')
    op.drop_table('plugin_reviews')
    op.drop_table('plugin_listings')
