# -*- coding: utf-8 -*-
"""
Add Frontend Management Models

This migration adds Frontend Management-related tables to support frontend features:
- frontend_components: Frontend component management (CRUD)
- frontend_themes: Theme management (light, dark, custom)
- frontend_layouts: Layout management (dashboard, page, modal)
- frontend_user_preferences: User preference settings
- frontend_dashboard_widgets: Dashboard widget configuration
- frontend_report_templates: Report template management
- frontend_localizations: Localization and i18n support

This model supports the Frontend Enhancement API endpoints:
- Components: GET/POST/PATCH/DELETE /api/v1/frontend/components
- Themes: GET/POST/PATCH/DELETE /api/v1/frontend/themes
- Layouts: GET/POST/PATCH/DELETE /api/v1/frontend/layouts
- User Preferences: GET/PUT /api/v1/frontend/preferences/{user_id}
- Dashboard Widgets: GET/POST/PUT/DELETE /api/v1/frontend/dashboard/widget
- Report Templates: GET/POST /api/v1/frontend/reports/templates
- Localization: GET/PUT /api/v1/frontend/localization
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '021a'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    """Add Frontend Management-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create frontend_components table
    if 'frontend_components' not in tables:
        op.create_table(
            'frontend_components',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('category', sa.String(50), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('props', sa.JSON(), nullable=True),
            sa.Column('code', sa.Text(), nullable=False),
            sa.Column('dependencies', sa.JSON(), nullable=True),
            sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_components_name', 'frontend_components', ['name'])
        op.create_index('idx_frontend_components_type', 'frontend_components', ['type'])
        op.create_index('idx_frontend_components_category', 'frontend_components', ['category'])
        op.create_index('idx_frontend_components_status', 'frontend_components', ['status'])
        op.create_index('idx_frontend_components_created_by', 'frontend_components', ['created_by'])

    # Create frontend_themes table
    if 'frontend_themes' not in tables:
        op.create_table(
            'frontend_themes',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('base_theme', sa.String(20), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('colors', sa.JSON(), nullable=False),
            sa.Column('fonts', sa.JSON(), nullable=True),
            sa.Column('spacing', sa.JSON(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_themes_name', 'frontend_themes', ['name'])
        op.create_index('idx_frontend_themes_base_theme', 'frontend_themes', ['base_theme'])
        op.create_index('idx_frontend_themes_is_default', 'frontend_themes', ['is_default'])
        op.create_index('idx_frontend_themes_created_by', 'frontend_themes', ['created_by'])

    # Create frontend_layouts table
    if 'frontend_layouts' not in tables:
        op.create_table(
            'frontend_layouts',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('structure', sa.JSON(), nullable=False),
            sa.Column('breakpoints', sa.JSON(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_layouts_name', 'frontend_layouts', ['name'])
        op.create_index('idx_frontend_layouts_type', 'frontend_layouts', ['type'])
        op.create_index('idx_frontend_layouts_is_default', 'frontend_layouts', ['is_default'])
        op.create_index('idx_frontend_layouts_created_by', 'frontend_layouts', ['created_by'])

    # Create frontend_user_preferences table
    if 'frontend_user_preferences' not in tables:
        op.create_table(
            'frontend_user_preferences',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.String(50), nullable=False),
            sa.Column('theme', sa.String(20), nullable=False, server_default='auto'),
            sa.Column('language', sa.String(10), nullable=False, server_default='zh-CN'),
            sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
            sa.Column('date_format', sa.String(20), nullable=False, server_default='YYYY-MM-DD'),
            sa.Column('time_format', sa.String(20), nullable=False, server_default='HH:mm:ss'),
            sa.Column('view_mode', sa.String(20), nullable=False, server_default='grid'),
            sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('notification_sound', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('auto_refresh_interval', sa.Integer(), nullable=False, server_default='30'),
            sa.Column('dashboard_layout', sa.JSON(), nullable=True),
            sa.Column('custom_colors', sa.JSON(), nullable=True),
            sa.Column('accessibility_settings', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_user_preferences_user_id', 'frontend_user_preferences', ['user_id'], unique=True)

    # Create frontend_dashboard_widgets table
    if 'frontend_dashboard_widgets' not in tables:
        op.create_table(
            'frontend_dashboard_widgets',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('dashboard_id', sa.String(100), nullable=False),
            sa.Column('widget_id', sa.String(100), nullable=False),
            sa.Column('widget_type', sa.String(50), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('position', sa.JSON(), nullable=False),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('data_source', sa.String(200), nullable=True),
            sa.Column('refresh_interval', sa.Integer(), nullable=False, server_default='30'),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_dashboard_widgets_dashboard_id', 'frontend_dashboard_widgets', ['dashboard_id'])
        op.create_index('idx_frontend_dashboard_widgets_widget_id', 'frontend_dashboard_widgets', ['widget_id'])
        op.create_index('idx_frontend_dashboard_widgets_widget_type', 'frontend_dashboard_widgets', ['widget_type'])
        op.create_index('idx_frontend_dashboard_widgets_created_by', 'frontend_dashboard_widgets', ['created_by'])

    # Create frontend_report_templates table
    if 'frontend_report_templates' not in tables:
        op.create_table(
            'frontend_report_templates',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('data_sources', sa.JSON(), nullable=False),
            sa.Column('filters', sa.JSON(), nullable=True),
            sa.Column('visualization_config', sa.JSON(), nullable=True),
            sa.Column('format', sa.String(20), nullable=False, server_default='pdf'),
            sa.Column('schedule', sa.String(100), nullable=True),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_report_templates_name', 'frontend_report_templates', ['name'])
        op.create_index('idx_frontend_report_templates_created_by', 'frontend_report_templates', ['created_by'])

    # Create frontend_localizations table
    if 'frontend_localizations' not in tables:
        op.create_table(
            'frontend_localizations',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('language', sa.String(10), nullable=False),
            sa.Column('translation_key', sa.String(200), nullable=False),
            sa.Column('translation_value', sa.Text(), nullable=False),
            sa.Column('context', sa.String(100), nullable=True),
            sa.Column('created_by', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_frontend_localizations_language', 'frontend_localizations', ['language'])
        op.create_index('idx_frontend_localizations_translation_key', 'frontend_localizations', ['translation_key'])


def downgrade():
    """Remove Frontend Management-related tables"""

    # Drop tables in reverse order of creation
    op.drop_table('frontend_localizations')
    op.drop_table('frontend_report_templates')
    op.drop_table('frontend_dashboard_widgets')
    op.drop_table('frontend_user_preferences')
    op.drop_table('frontend_layouts')
    op.drop_table('frontend_themes')
    op.drop_table('frontend_components')
