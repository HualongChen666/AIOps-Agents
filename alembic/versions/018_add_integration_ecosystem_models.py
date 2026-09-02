# -*- coding: utf-8 -*-
"""
Add Integration Ecosystem Models

This migration adds Integration Ecosystem-related tables to support the integration module:
- integrations: Stores integration configurations (monitoring, cloud, cicd, itsm, notification, webhook, custom)
- webhooks: Stores webhook registrations for external system integration
- webhook_events: Stores webhook event history for tracking and debugging
- integration_notification_channels: Stores notification channel configurations
- integration_notification_messages: Stores notification message history

This model supports the Integration API endpoints:
- POST/GET/DELETE /api/v1/integration/register
- GET /api/v1/integration/list
- POST /api/v1/integration/test/{integration_id}
- POST /api/v1/integration/notification/send
- GET /api/v1/integration/notification/channels
- POST /api/v1/integration/webhook/register
- POST /api/v1/integration/webhook/handle
- GET /api/v1/integration/webhooks
- GET /api/v1/integration/events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    """Add Integration Ecosystem-related tables"""

    # Check if tables exist (SQLite doesn't support IF NOT EXISTS in create_table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create integrations table
    if 'integrations' not in tables:
        op.create_table(
            'integrations',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('integration_type', sa.String(50), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('config', sa.JSON(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('status', sa.String(20), nullable=False, server_default='inactive'),
            sa.Column('last_tested', sa.DateTime(), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('integration_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
        )

        # Create indexes for integrations
        op.create_index('idx_integrations_type', 'integrations', ['integration_type'])
        op.create_index('idx_integrations_name', 'integrations', ['name'])
        op.create_index('idx_integrations_enabled', 'integrations', ['enabled'])
        op.create_index('idx_integrations_status', 'integrations', ['status'])
        op.create_index('idx_integrations_created_at', 'integrations', ['created_at'])

    # Create webhooks table
    if 'webhooks' not in tables:
        op.create_table(
            'webhooks',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('source', sa.String(100), nullable=False),
            sa.Column('event_type', sa.String(100), nullable=False),
            sa.Column('endpoint', sa.String(500), nullable=False),
            sa.Column('secret', sa.String(255), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('webhook_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
        )

        # Create indexes for webhooks
        op.create_index('idx_webhooks_source', 'webhooks', ['source'])
        op.create_index('idx_webhooks_event_type', 'webhooks', ['event_type'])
        op.create_index('idx_webhooks_enabled', 'webhooks', ['enabled'])
        op.create_index('idx_webhooks_created_at', 'webhooks', ['created_at'])

    # Create webhook_events table
    if 'webhook_events' not in tables:
        op.create_table(
            'webhook_events',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('webhook_id', sa.String(100), nullable=False),
            sa.Column('source', sa.String(100), nullable=False),
            sa.Column('event_type', sa.String(100), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=False),
            sa.Column('processed', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('processing_result', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('processed_at', sa.DateTime(), nullable=True),
        )

        # Create indexes for webhook_events
        op.create_index('idx_webhook_events_webhook_id', 'webhook_events', ['webhook_id'])
        op.create_index('idx_webhook_events_source', 'webhook_events', ['source'])
        op.create_index('idx_webhook_events_event_type', 'webhook_events', ['event_type'])
        op.create_index('idx_webhook_events_processed', 'webhook_events', ['processed'])
        op.create_index('idx_webhook_events_timestamp', 'webhook_events', ['timestamp'])

    # Create integration_notification_channels table
    if 'integration_notification_channels' not in tables:
        op.create_table(
            'integration_notification_channels',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False, unique=True),
            sa.Column('channel_type', sa.String(50), nullable=False),
            sa.Column('config', sa.JSON(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(50), nullable=True),
        )

        # Create indexes for integration_notification_channels
        op.create_index('idx_integration_notification_channels_name', 'integration_notification_channels', ['name'])
        op.create_index('idx_integration_notification_channels_type', 'integration_notification_channels', ['channel_type'])
        op.create_index('idx_integration_notification_channels_enabled', 'integration_notification_channels', ['enabled'])

    # Create integration_notification_messages table
    if 'integration_notification_messages' not in tables:
        op.create_table(
            'integration_notification_messages',
            sa.Column('id', sa.String(100), primary_key=True, nullable=False),
            sa.Column('channel_id', sa.String(100), nullable=False),
            sa.Column('recipient', sa.String(255), nullable=False),
            sa.Column('subject', sa.String(500), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('priority', sa.String(20), nullable=False, server_default='normal'),
            sa.Column('sent', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('sent_at', sa.DateTime(), nullable=True),
            sa.Column('message_metadata', sa.JSON(), nullable=True),
        )

        # Create indexes for integration_notification_messages
        op.create_index('idx_integration_notification_messages_channel_id', 'integration_notification_messages', ['channel_id'])
        op.create_index('idx_integration_notification_messages_sent', 'integration_notification_messages', ['sent'])
        op.create_index('idx_integration_notification_messages_timestamp', 'integration_notification_messages', ['timestamp'])


def downgrade():
    """Remove Integration Ecosystem-related tables"""

    # Check if tables exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'integration_notification_messages' in tables:
        try:
            op.drop_index('idx_integration_notification_messages_timestamp', 'integration_notification_messages')
        except Exception:
            pass
        try:
            op.drop_index('idx_integration_notification_messages_sent', 'integration_notification_messages')
        except Exception:
            pass
        try:
            op.drop_index('idx_integration_notification_messages_channel_id', 'integration_notification_messages')
        except Exception:
            pass
        op.drop_table('integration_notification_messages')

    if 'integration_notification_channels' in tables:
        try:
            op.drop_index('idx_integration_notification_channels_enabled', 'integration_notification_channels')
        except Exception:
            pass
        try:
            op.drop_index('idx_integration_notification_channels_type', 'integration_notification_channels')
        except Exception:
            pass
        try:
            op.drop_index('idx_integration_notification_channels_name', 'integration_notification_channels')
        except Exception:
            pass
        op.drop_table('integration_notification_channels')

    if 'webhook_events' in tables:
        try:
            op.drop_index('idx_webhook_events_timestamp', 'webhook_events')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhook_events_processed', 'webhook_events')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhook_events_event_type', 'webhook_events')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhook_events_source', 'webhook_events')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhook_events_webhook_id', 'webhook_events')
        except Exception:
            pass
        op.drop_table('webhook_events')

    if 'webhooks' in tables:
        try:
            op.drop_index('idx_webhooks_created_at', 'webhooks')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhooks_enabled', 'webhooks')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhooks_event_type', 'webhooks')
        except Exception:
            pass
        try:
            op.drop_index('idx_webhooks_source', 'webhooks')
        except Exception:
            pass
        op.drop_table('webhooks')

    if 'integrations' in tables:
        try:
            op.drop_index('idx_integrations_created_at', 'integrations')
        except Exception:
            pass
        try:
            op.drop_index('idx_integrations_status', 'integrations')
        except Exception:
            pass
        try:
            op.drop_index('idx_integrations_enabled', 'integrations')
        except Exception:
            pass
        try:
            op.drop_index('idx_integrations_name', 'integrations')
        except Exception:
            pass
        try:
            op.drop_index('idx_integrations_type', 'integrations')
        except Exception:
            pass
        op.drop_table('integrations')
