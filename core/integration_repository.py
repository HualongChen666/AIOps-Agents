# -*- coding: utf-8 -*-
"""
Integration Repository Module
============================

Repository layer for Integration Ecosystem database operations.
Provides data access methods for integrations, webhooks, webhook events, and notification channels.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger
from sqlalchemy.orm import Session

from core.models import (
    IntegrationDB,
    WebhookDB,
    WebhookEventDB,
    IntegrationNotificationChannelDB,
    IntegrationNotificationMessageDB,
)


class IntegrationRepository:
    """Repository for Integration database operations"""

    def __init__(self, db: Session):
        """
        Initialize Integration repository

        Args:
            db: Database session
        """
        self.db = db

    def create(
        self,
        integration_type: str,
        name: str,
        config: Dict[str, Any],
        enabled: bool = True,
        created_by: Optional[str] = None,
    ) -> IntegrationDB:
        """
        Create a new integration

        Args:
            integration_type: Type of integration
            name: Integration name
            config: Integration configuration
            enabled: Whether integration is enabled
            created_by: User who created the integration

        Returns:
            IntegrationDB object
        """
        integration_id = f"int_{uuid4().hex[:16]}"
        
        integration = IntegrationDB(
            id=integration_id,
            integration_type=integration_type,
            name=name,
            config=config,
            enabled=enabled,
            status="configuring",
            created_by=created_by,
        )
        
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        
        logger.info(f"Created integration: {integration_id}")
        return integration

    def get_by_id(self, integration_id: str) -> Optional[IntegrationDB]:
        """
        Get integration by ID

        Args:
            integration_id: Integration identifier

        Returns:
            IntegrationDB object or None
        """
        return self.db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()

    def get_all(
        self,
        integration_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntegrationDB]:
        """
        Get all integrations with optional filters

        Args:
            integration_type: Filter by integration type
            enabled: Filter by enabled status
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of IntegrationDB objects
        """
        query = self.db.query(IntegrationDB)
        
        if integration_type:
            query = query.filter(IntegrationDB.integration_type == integration_type)
        if enabled is not None:
            query = query.filter(IntegrationDB.enabled == enabled)
        if status:
            query = query.filter(IntegrationDB.status == status)
        
        return query.order_by(IntegrationDB.created_at.desc()).limit(limit).offset(offset).all()

    def update(
        self,
        integration_id: str,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        status: Optional[str] = None,
        last_tested: Optional[datetime] = None,
        last_error: Optional[str] = None,
        integration_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntegrationDB]:
        """
        Update integration

        Args:
            integration_id: Integration identifier
            config: New configuration
            enabled: New enabled status
            status: New status
            last_tested: Last tested timestamp
            last_error: Last error message
            integration_metadata: New metadata

        Returns:
            Updated IntegrationDB object or None
        """
        integration = self.get_by_id(integration_id)
        if not integration:
            return None
        
        if config is not None:
            integration.config = config
        if enabled is not None:
            integration.enabled = enabled
        if status is not None:
            integration.status = status
        if last_tested is not None:
            integration.last_tested = last_tested
        if last_error is not None:
            integration.last_error = last_error
        if integration_metadata is not None:
            integration.integration_metadata = integration_metadata
        
        integration.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(integration)
        
        logger.info(f"Updated integration: {integration_id}")
        return integration

    def delete(self, integration_id: str) -> bool:
        """
        Delete integration

        Args:
            integration_id: Integration identifier

        Returns:
            True if deleted, False if not found
        """
        integration = self.get_by_id(integration_id)
        if not integration:
            return False
        
        self.db.delete(integration)
        self.db.commit()
        
        logger.info(f"Deleted integration: {integration_id}")
        return True

    def count(
        self,
        integration_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        Count integrations with optional filters

        Args:
            integration_type: Filter by integration type
            enabled: Filter by enabled status
            status: Filter by status

        Returns:
            Count of integrations
        """
        query = self.db.query(IntegrationDB)
        
        if integration_type:
            query = query.filter(IntegrationDB.integration_type == integration_type)
        if enabled is not None:
            query = query.filter(IntegrationDB.enabled == enabled)
        if status:
            query = query.filter(IntegrationDB.status == status)
        
        return query.count()


class WebhookRepository:
    """Repository for Webhook database operations"""

    def __init__(self, db: Session):
        """
        Initialize Webhook repository

        Args:
            db: Database session
        """
        self.db = db

    def create(
        self,
        source: str,
        event_type: str,
        endpoint: str,
        secret: Optional[str] = None,
        enabled: bool = True,
        created_by: Optional[str] = None,
    ) -> WebhookDB:
        """
        Create a new webhook

        Args:
            source: Webhook source identifier
            event_type: Type of events to receive
            endpoint: Webhook endpoint URL
            secret: Webhook secret for signature validation
            enabled: Whether webhook is enabled
            created_by: User who created the webhook

        Returns:
            WebhookDB object
        """
        webhook_id = f"webhook_{uuid4().hex[:16]}"
        
        webhook = WebhookDB(
            id=webhook_id,
            source=source,
            event_type=event_type,
            endpoint=endpoint,
            secret=secret,
            enabled=enabled,
            created_by=created_by,
        )
        
        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)
        
        logger.info(f"Created webhook: {webhook_id}")
        return webhook

    def get_by_id(self, webhook_id: str) -> Optional[WebhookDB]:
        """
        Get webhook by ID

        Args:
            webhook_id: Webhook identifier

        Returns:
            WebhookDB object or None
        """
        return self.db.query(WebhookDB).filter(WebhookDB.id == webhook_id).first()

    def get_all(
        self,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WebhookDB]:
        """
        Get all webhooks with optional filters

        Args:
            source: Filter by source
            event_type: Filter by event type
            enabled: Filter by enabled status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of WebhookDB objects
        """
        query = self.db.query(WebhookDB)
        
        if source:
            query = query.filter(WebhookDB.source == source)
        if event_type:
            query = query.filter(WebhookDB.event_type == event_type)
        if enabled is not None:
            query = query.filter(WebhookDB.enabled == enabled)
        
        return query.order_by(WebhookDB.created_at.desc()).limit(limit).offset(offset).all()

    def update(
        self,
        webhook_id: str,
        endpoint: Optional[str] = None,
        secret: Optional[str] = None,
        enabled: Optional[bool] = None,
        webhook_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WebhookDB]:
        """
        Update webhook

        Args:
            webhook_id: Webhook identifier
            endpoint: New endpoint URL
            secret: New secret
            enabled: New enabled status
            webhook_metadata: New metadata

        Returns:
            Updated WebhookDB object or None
        """
        webhook = self.get_by_id(webhook_id)
        if not webhook:
            return None
        
        if endpoint is not None:
            webhook.endpoint = endpoint
        if secret is not None:
            webhook.secret = secret
        if enabled is not None:
            webhook.enabled = enabled
        if webhook_metadata is not None:
            webhook.webhook_metadata = webhook_metadata
        
        webhook.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(webhook)
        
        logger.info(f"Updated webhook: {webhook_id}")
        return webhook

    def delete(self, webhook_id: str) -> bool:
        """
        Delete webhook

        Args:
            webhook_id: Webhook identifier

        Returns:
            True if deleted, False if not found
        """
        webhook = self.get_by_id(webhook_id)
        if not webhook:
            return False
        
        self.db.delete(webhook)
        self.db.commit()
        
        logger.info(f"Deleted webhook: {webhook_id}")
        return True


class WebhookEventRepository:
    """Repository for Webhook Event database operations"""

    def __init__(self, db: Session):
        """
        Initialize Webhook Event repository

        Args:
            db: Database session
        """
        self.db = db

    def create(
        self,
        webhook_id: str,
        source: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> WebhookEventDB:
        """
        Create a new webhook event

        Args:
            webhook_id: Webhook identifier
            source: Event source
            event_type: Event type
            payload: Event payload

        Returns:
            WebhookEventDB object
        """
        event_id = f"event_{uuid4().hex[:16]}"
        
        event = WebhookEventDB(
            id=event_id,
            webhook_id=webhook_id,
            source=source,
            event_type=event_type,
            payload=payload,
            processed=False,
            retry_count=0,
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Created webhook event: {event_id}")
        return event

    def get_by_id(self, event_id: str) -> Optional[WebhookEventDB]:
        """
        Get webhook event by ID

        Args:
            event_id: Event identifier

        Returns:
            WebhookEventDB object or None
        """
        return self.db.query(WebhookEventDB).filter(WebhookEventDB.id == event_id).first()

    def get_all(
        self,
        webhook_id: Optional[str] = None,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        processed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WebhookEventDB]:
        """
        Get all webhook events with optional filters

        Args:
            webhook_id: Filter by webhook ID
            source: Filter by source
            event_type: Filter by event type
            processed: Filter by processed status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of WebhookEventDB objects
        """
        query = self.db.query(WebhookEventDB)
        
        if webhook_id:
            query = query.filter(WebhookEventDB.webhook_id == webhook_id)
        if source:
            query = query.filter(WebhookEventDB.source == source)
        if event_type:
            query = query.filter(WebhookEventDB.event_type == event_type)
        if processed is not None:
            query = query.filter(WebhookEventDB.processed == processed)
        
        return query.order_by(WebhookEventDB.timestamp.desc()).limit(limit).offset(offset).all()

    def update(
        self,
        event_id: str,
        processed: Optional[bool] = None,
        retry_count: Optional[int] = None,
        processing_result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        processed_at: Optional[datetime] = None,
    ) -> Optional[WebhookEventDB]:
        """
        Update webhook event

        Args:
            event_id: Event identifier
            processed: New processed status
            retry_count: New retry count
            processing_result: Processing result details
            error_message: Error message
            processed_at: Processed timestamp

        Returns:
            Updated WebhookEventDB object or None
        """
        event = self.get_by_id(event_id)
        if not event:
            return None
        
        if processed is not None:
            event.processed = processed
        if retry_count is not None:
            event.retry_count = retry_count
        if processing_result is not None:
            event.processing_result = processing_result
        if error_message is not None:
            event.error_message = error_message
        if processed_at is not None:
            event.processed_at = processed_at
        
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Updated webhook event: {event_id}")
        return event

    def delete(self, event_id: str) -> bool:
        """
        Delete webhook event

        Args:
            event_id: Event identifier

        Returns:
            True if deleted, False if not found
        """
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        self.db.delete(event)
        self.db.commit()
        
        logger.info(f"Deleted webhook event: {event_id}")
        return True

    def delete_old_events(self, days: int = 30) -> int:
        """
        Delete old webhook events

        Args:
            days: Delete events older than this many days

        Returns:
            Number of events deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = self.db.query(WebhookEventDB).filter(
            WebhookEventDB.timestamp < cutoff_date
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Deleted {deleted} old webhook events")
        return deleted


class NotificationChannelRepository:
    """Repository for Notification Channel database operations"""

    def __init__(self, db: Session):
        """
        Initialize Notification Channel repository

        Args:
            db: Database session
        """
        self.db = db

    def create(
        self,
        name: str,
        channel_type: str,
        config: Dict[str, Any],
        enabled: bool = True,
        priority: int = 0,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> IntegrationNotificationChannelDB:
        """
        Create a new notification channel

        Args:
            name: Channel name
            channel_type: Channel type
            config: Channel configuration
            enabled: Whether channel is enabled
            priority: Channel priority
            description: Channel description
            created_by: User who created the channel

        Returns:
            IntegrationNotificationChannelDB object
        """
        channel_id = f"channel_{uuid4().hex[:16]}"
        
        channel = IntegrationNotificationChannelDB(
            id=channel_id,
            name=name,
            channel_type=channel_type,
            config=config,
            enabled=enabled,
            priority=priority,
            description=description,
            created_by=created_by,
        )
        
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        
        logger.info(f"Created notification channel: {channel_id}")
        return channel

    def get_by_id(self, channel_id: str) -> Optional[IntegrationNotificationChannelDB]:
        """
        Get notification channel by ID

        Args:
            channel_id: Channel identifier

        Returns:
            IntegrationNotificationChannelDB object or None
        """
        return self.db.query(IntegrationNotificationChannelDB).filter(
            IntegrationNotificationChannelDB.id == channel_id
        ).first()

    def get_by_name(self, name: str) -> Optional[IntegrationNotificationChannelDB]:
        """
        Get notification channel by name

        Args:
            name: Channel name

        Returns:
            IntegrationNotificationChannelDB object or None
        """
        return self.db.query(IntegrationNotificationChannelDB).filter(
            IntegrationNotificationChannelDB.name == name
        ).first()

    def get_all(
        self,
        channel_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntegrationNotificationChannelDB]:
        """
        Get all notification channels with optional filters

        Args:
            channel_type: Filter by channel type
            enabled: Filter by enabled status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of IntegrationNotificationChannelDB objects
        """
        query = self.db.query(IntegrationNotificationChannelDB)
        
        if channel_type:
            query = query.filter(IntegrationNotificationChannelDB.channel_type == channel_type)
        if enabled is not None:
            query = query.filter(IntegrationNotificationChannelDB.enabled == enabled)
        
        return query.order_by(IntegrationNotificationChannelDB.priority.desc()).limit(limit).offset(offset).all()

    def update(
        self,
        channel_id: str,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        priority: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Optional[IntegrationNotificationChannelDB]:
        """
        Update notification channel

        Args:
            channel_id: Channel identifier
            config: New configuration
            enabled: New enabled status
            priority: New priority
            description: New description

        Returns:
            Updated IntegrationNotificationChannelDB object or None
        """
        channel = self.get_by_id(channel_id)
        if not channel:
            return None
        
        if config is not None:
            channel.config = config
        if enabled is not None:
            channel.enabled = enabled
        if priority is not None:
            channel.priority = priority
        if description is not None:
            channel.description = description
        
        channel.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(channel)
        
        logger.info(f"Updated notification channel: {channel_id}")
        return channel

    def delete(self, channel_id: str) -> bool:
        """
        Delete notification channel

        Args:
            channel_id: Channel identifier

        Returns:
            True if deleted, False if not found
        """
        channel = self.get_by_id(channel_id)
        if not channel:
            return False
        
        self.db.delete(channel)
        self.db.commit()
        
        logger.info(f"Deleted notification channel: {channel_id}")
        return True


class NotificationMessageRepository:
    """Repository for Notification Message database operations"""

    def __init__(self, db: Session):
        """
        Initialize Notification Message repository

        Args:
            db: Database session
        """
        self.db = db

    def create(
        self,
        channel_id: str,
        recipient: str,
        subject: str,
        body: str,
        priority: str = "normal",
        message_metadata: Optional[Dict[str, Any]] = None,
    ) -> IntegrationNotificationMessageDB:
        """
        Create a new notification message

        Args:
            channel_id: Channel identifier
            recipient: Message recipient
            subject: Message subject
            body: Message body
            priority: Message priority
            message_metadata: Message metadata

        Returns:
            IntegrationNotificationMessageDB object
        """
        message_id = f"msg_{uuid4().hex[:16]}"
        
        message = IntegrationNotificationMessageDB(
            id=message_id,
            channel_id=channel_id,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
            sent=False,
            message_metadata=message_metadata,
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        logger.info(f"Created notification message: {message_id}")
        return message

    def get_by_id(self, message_id: str) -> Optional[IntegrationNotificationMessageDB]:
        """
        Get notification message by ID

        Args:
            message_id: Message identifier

        Returns:
            IntegrationNotificationMessageDB object or None
        """
        return self.db.query(IntegrationNotificationMessageDB).filter(
            IntegrationNotificationMessageDB.id == message_id
        ).first()

    def get_all(
        self,
        channel_id: Optional[str] = None,
        sent: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[IntegrationNotificationMessageDB]:
        """
        Get all notification messages with optional filters

        Args:
            channel_id: Filter by channel ID
            sent: Filter by sent status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of IntegrationNotificationMessageDB objects
        """
        query = self.db.query(IntegrationNotificationMessageDB)
        
        if channel_id:
            query = query.filter(IntegrationNotificationMessageDB.channel_id == channel_id)
        if sent is not None:
            query = query.filter(IntegrationNotificationMessageDB.sent == sent)
        
        return query.order_by(IntegrationNotificationMessageDB.timestamp.desc()).limit(limit).offset(offset).all()

    def update(
        self,
        message_id: str,
        sent: Optional[bool] = None,
        error: Optional[str] = None,
        sent_at: Optional[datetime] = None,
    ) -> Optional[IntegrationNotificationMessageDB]:
        """
        Update notification message

        Args:
            message_id: Message identifier
            sent: New sent status
            error: Error message
            sent_at: Sent timestamp

        Returns:
            Updated IntegrationNotificationMessageDB object or None
        """
        message = self.get_by_id(message_id)
        if not message:
            return None
        
        if sent is not None:
            message.sent = sent
        if error is not None:
            message.error = error
        if sent_at is not None:
            message.sent_at = sent_at
        
        self.db.commit()
        self.db.refresh(message)
        
        logger.info(f"Updated notification message: {message_id}")
        return message

    def delete(self, message_id: str) -> bool:
        """
        Delete notification message

        Args:
            message_id: Message identifier

        Returns:
            True if deleted, False if not found
        """
        message = self.get_by_id(message_id)
        if not message:
            return False
        
        self.db.delete(message)
        self.db.commit()
        
        logger.info(f"Deleted notification message: {message_id}")
        return True

    def delete_old_messages(self, days: int = 30) -> int:
        """
        Delete old notification messages

        Args:
            days: Delete messages older than this many days

        Returns:
            Number of messages deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = self.db.query(IntegrationNotificationMessageDB).filter(
            IntegrationNotificationMessageDB.timestamp < cutoff_date
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Deleted {deleted} old notification messages")
        return deleted
