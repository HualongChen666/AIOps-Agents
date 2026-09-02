# -*- coding: utf-8 -*-
"""
Integration Repository Unit Tests
================================

Unit tests for the Integration Repository layer.
Tests CRUD operations, filtering, and data validation.
"""

import logging
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from core.database import SessionLocal, engine, Base
from core.integration_repository import (
    IntegrationRepository,
    WebhookRepository,
    WebhookEventRepository,
    NotificationChannelRepository,
    NotificationMessageRepository,
)
from core.models import (
    IntegrationDB,
    WebhookDB,
    WebhookEventDB,
    IntegrationNotificationChannelDB,
    IntegrationNotificationMessageDB,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create all tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
    
    # Create session
    db = SessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()
        # Drop all tables after test
        try:
            Base.metadata.drop_all(bind=engine)
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")


class TestIntegrationRepository:
    """Test IntegrationRepository CRUD operations"""

    def test_create_integration(self, db_session: Session):
        """Test creating a new integration"""
        repo = IntegrationRepository(db_session)
        
        integration = repo.create(
            integration_type="monitoring",
            name="Test Prometheus",
            config={"url": "http://localhost:9090"},
            enabled=True,
            created_by="test_user",
        )
        
        assert integration is not None
        assert integration.id is not None
        assert integration.integration_type == "monitoring"
        assert integration.name == "Test Prometheus"
        assert integration.enabled is True
        assert integration.status == "configuring"

    def test_get_integration_by_id(self, db_session: Session):
        """Test getting integration by ID"""
        repo = IntegrationRepository(db_session)
        
        # Create integration
        created = repo.create(
            integration_type="monitoring",
            name="Test Prometheus",
            config={"url": "http://localhost:9090"},
        )
        
        # Get by ID
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Prometheus"

    def test_get_all_integrations(self, db_session: Session):
        """Test getting all integrations"""
        repo = IntegrationRepository(db_session)
        
        # Create multiple integrations
        repo.create(integration_type="monitoring", name="Prometheus", config={"url": "http://localhost:9090"})
        repo.create(integration_type="cicd", name="Jenkins", config={"url": "http://localhost:8080"})
        repo.create(integration_type="itsm", name="Jira", config={"url": "http://localhost:8085"})
        
        # Get all
        integrations = repo.get_all()
        
        assert len(integrations) == 3

    def test_get_all_integrations_with_filters(self, db_session: Session):
        """Test getting integrations with filters"""
        repo = IntegrationRepository(db_session)
        
        # Create integrations with different types
        repo.create(integration_type="monitoring", name="Prometheus", config={"url": "http://localhost:9090"}, enabled=True)
        repo.create(integration_type="monitoring", name="Grafana", config={"url": "http://localhost:3000"}, enabled=False)
        repo.create(integration_type="cicd", name="Jenkins", config={"url": "http://localhost:8080"}, enabled=True)
        
        # Filter by type
        monitoring_integrations = repo.get_all(integration_type="monitoring")
        assert len(monitoring_integrations) == 2
        
        # Filter by enabled
        enabled_integrations = repo.get_all(enabled=True)
        assert len(enabled_integrations) == 2

    def test_update_integration(self, db_session: Session):
        """Test updating integration"""
        repo = IntegrationRepository(db_session)
        
        # Create integration
        created = repo.create(
            integration_type="monitoring",
            name="Test Prometheus",
            config={"url": "http://localhost:9090"},
        )
        
        # Update
        updated = repo.update(
            integration_id=created.id,
            status="active",
            last_tested=datetime.utcnow(),
        )
        
        assert updated is not None
        assert updated.status == "active"
        assert updated.last_tested is not None

    def test_delete_integration(self, db_session: Session):
        """Test deleting integration"""
        repo = IntegrationRepository(db_session)
        
        # Create integration
        created = repo.create(
            integration_type="monitoring",
            name="Test Prometheus",
            config={"url": "http://localhost:9090"},
        )
        
        # Delete
        result = repo.delete(created.id)
        
        assert result is True
        
        # Verify deletion
        retrieved = repo.get_by_id(created.id)
        assert retrieved is None

    def test_count_integrations(self, db_session: Session):
        """Test counting integrations"""
        repo = IntegrationRepository(db_session)
        
        # Create integrations
        repo.create(integration_type="monitoring", name="Prometheus", config={"url": "http://localhost:9090"})
        repo.create(integration_type="monitoring", name="Grafana", config={"url": "http://localhost:3000"})
        repo.create(integration_type="cicd", name="Jenkins", config={"url": "http://localhost:8080"})
        
        # Count all
        total_count = repo.count()
        assert total_count == 3
        
        # Count by type
        monitoring_count = repo.count(integration_type="monitoring")
        assert monitoring_count == 2


class TestWebhookRepository:
    """Test WebhookRepository CRUD operations"""

    def test_create_webhook(self, db_session: Session):
        """Test creating a new webhook"""
        repo = WebhookRepository(db_session)
        
        webhook = repo.create(
            source="github",
            event_type="push",
            endpoint="http://localhost:8000/webhook/github",
            secret="test_secret",
            enabled=True,
        )
        
        assert webhook is not None
        assert webhook.id is not None
        assert webhook.source == "github"
        assert webhook.event_type == "push"
        assert webhook.enabled is True

    def test_get_webhook_by_id(self, db_session: Session):
        """Test getting webhook by ID"""
        repo = WebhookRepository(db_session)
        
        # Create webhook
        created = repo.create(
            source="github",
            event_type="push",
            endpoint="http://localhost:8000/webhook/github",
        )
        
        # Get by ID
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.source == "github"

    def test_get_all_webhooks(self, db_session: Session):
        """Test getting all webhooks"""
        repo = WebhookRepository(db_session)
        
        # Create multiple webhooks
        repo.create(source="github", event_type="push", endpoint="http://localhost:8000/webhook/github")
        repo.create(source="gitlab", event_type="push", endpoint="http://localhost:8000/webhook/gitlab")
        repo.create(source="jenkins", event_type="build", endpoint="http://localhost:8000/webhook/jenkins")
        
        # Get all
        webhooks = repo.get_all()
        
        assert len(webhooks) == 3

    def test_update_webhook(self, db_session: Session):
        """Test updating webhook"""
        repo = WebhookRepository(db_session)
        
        # Create webhook
        created = repo.create(
            source="github",
            event_type="push",
            endpoint="http://localhost:8000/webhook/github",
        )
        
        # Update
        updated = repo.update(
            webhook_id=created.id,
            enabled=False,
        )
        
        assert updated is not None
        assert updated.enabled is False

    def test_delete_webhook(self, db_session: Session):
        """Test deleting webhook"""
        repo = WebhookRepository(db_session)
        
        # Create webhook
        created = repo.create(
            source="github",
            event_type="push",
            endpoint="http://localhost:8000/webhook/github",
        )
        
        # Delete
        result = repo.delete(created.id)
        
        assert result is True
        
        # Verify deletion
        retrieved = repo.get_by_id(created.id)
        assert retrieved is None


class TestWebhookEventRepository:
    """Test WebhookEventRepository CRUD operations"""

    def test_create_webhook_event(self, db_session: Session):
        """Test creating a new webhook event"""
        repo = WebhookEventRepository(db_session)
        
        event = repo.create(
            webhook_id="webhook_123",
            source="github",
            event_type="push",
            payload={"action": "push", "repository": "test"},
        )
        
        assert event is not None
        assert event.id is not None
        assert event.webhook_id == "webhook_123"
        assert event.processed is False
        assert event.retry_count == 0

    def test_get_webhook_event_by_id(self, db_session: Session):
        """Test getting webhook event by ID"""
        repo = WebhookEventRepository(db_session)
        
        # Create event
        created = repo.create(
            webhook_id="webhook_123",
            source="github",
            event_type="push",
            payload={"action": "push"},
        )
        
        # Get by ID
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.source == "github"

    def test_update_webhook_event(self, db_session: Session):
        """Test updating webhook event"""
        repo = WebhookEventRepository(db_session)
        
        # Create event
        created = repo.create(
            webhook_id="webhook_123",
            source="github",
            event_type="push",
            payload={"action": "push"},
        )
        
        # Update
        updated = repo.update(
            event_id=created.id,
            processed=True,
            processed_at=datetime.utcnow(),
        )
        
        assert updated is not None
        assert updated.processed is True
        assert updated.processed_at is not None

    def test_delete_old_events(self, db_session: Session):
        """Test deleting old webhook events"""
        repo = WebhookEventRepository(db_session)
        
        # Create old event
        old_event = repo.create(
            webhook_id="webhook_123",
            source="github",
            event_type="push",
            payload={"action": "push"},
        )
        
        # Manually set old timestamp
        old_event.timestamp = datetime.utcnow() - timedelta(days=35)
        db_session.commit()
        
        # Delete old events
        deleted_count = repo.delete_old_events(days=30)
        
        assert deleted_count >= 1


class TestNotificationChannelRepository:
    """Test NotificationChannelRepository CRUD operations"""

    def test_create_notification_channel(self, db_session: Session):
        """Test creating a new notification channel"""
        repo = NotificationChannelRepository(db_session)
        
        channel = repo.create(
            name="Test Slack",
            channel_type="slack",
            config={"webhook_url": "http://localhost:8000/webhook/slack"},
            enabled=True,
            priority=10,
        )
        
        assert channel is not None
        assert channel.id is not None
        assert channel.name == "Test Slack"
        assert channel.channel_type == "slack"
        assert channel.enabled is True
        assert channel.priority == 10

    def test_get_channel_by_name(self, db_session: Session):
        """Test getting channel by name"""
        repo = NotificationChannelRepository(db_session)
        
        # Create channel
        created = repo.create(
            name="Test Slack",
            channel_type="slack",
            config={"webhook_url": "http://localhost:8000/webhook/slack"},
        )
        
        # Get by name
        retrieved = repo.get_by_name("Test Slack")
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Slack"

    def test_get_all_channels(self, db_session: Session):
        """Test getting all notification channels"""
        repo = NotificationChannelRepository(db_session)
        
        # Create multiple channels
        repo.create(name="Slack", channel_type="slack", config={"webhook_url": "http://localhost:8000/slack"})
        repo.create(name="Teams", channel_type="teams", config={"webhook_url": "http://localhost:8000/teams"})
        repo.create(name="Email", channel_type="email", config={"smtp_server": "localhost"})
        
        # Get all
        channels = repo.get_all()
        
        assert len(channels) == 3

    def test_update_notification_channel(self, db_session: Session):
        """Test updating notification channel"""
        repo = NotificationChannelRepository(db_session)
        
        # Create channel
        created = repo.create(
            name="Test Slack",
            channel_type="slack",
            config={"webhook_url": "http://localhost:8000/webhook/slack"},
        )
        
        # Update
        updated = repo.update(
            channel_id=created.id,
            priority=20,
        )
        
        assert updated is not None
        assert updated.priority == 20

    def test_delete_notification_channel(self, db_session: Session):
        """Test deleting notification channel"""
        repo = NotificationChannelRepository(db_session)
        
        # Create channel
        created = repo.create(
            name="Test Slack",
            channel_type="slack",
            config={"webhook_url": "http://localhost:8000/webhook/slack"},
        )
        
        # Delete
        result = repo.delete(created.id)
        
        assert result is True
        
        # Verify deletion
        retrieved = repo.get_by_id(created.id)
        assert retrieved is None


class TestNotificationMessageRepository:
    """Test NotificationMessageRepository CRUD operations"""

    def test_create_notification_message(self, db_session: Session):
        """Test creating a new notification message"""
        repo = NotificationMessageRepository(db_session)
        
        message = repo.create(
            channel_id="channel_123",
            recipient="test@example.com",
            subject="Test Subject",
            body="Test Body",
            priority="high",
        )
        
        assert message is not None
        assert message.id is not None
        assert message.channel_id == "channel_123"
        assert message.recipient == "test@example.com"
        assert message.sent is False

    def test_get_notification_message_by_id(self, db_session: Session):
        """Test getting notification message by ID"""
        repo = NotificationMessageRepository(db_session)
        
        # Create message
        created = repo.create(
            channel_id="channel_123",
            recipient="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )
        
        # Get by ID
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.recipient == "test@example.com"

    def test_update_notification_message(self, db_session: Session):
        """Test updating notification message"""
        repo = NotificationMessageRepository(db_session)
        
        # Create message
        created = repo.create(
            channel_id="channel_123",
            recipient="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )
        
        # Update
        updated = repo.update(
            message_id=created.id,
            sent=True,
            sent_at=datetime.utcnow(),
        )
        
        assert updated is not None
        assert updated.sent is True
        assert updated.sent_at is not None

    def test_delete_old_messages(self, db_session: Session):
        """Test deleting old notification messages"""
        repo = NotificationMessageRepository(db_session)
        
        # Create old message
        old_message = repo.create(
            channel_id="channel_123",
            recipient="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )
        
        # Manually set old timestamp
        old_message.timestamp = datetime.utcnow() - timedelta(days=35)
        db_session.commit()
        
        # Delete old messages
        deleted_count = repo.delete_old_messages(days=30)
        
        assert deleted_count >= 1
