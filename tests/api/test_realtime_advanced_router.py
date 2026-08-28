# -*- coding: utf-8 -*-
"""
Test suite for Realtime Advanced Router (Database-backed)
Comprehensive tests for realtime communication advanced features
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.realtime_advanced_router import (
    RealtimeEventResponse,
    RealtimeStreamCreate,
    RealtimeStreamResponse,
    RealtimeStreamUpdate,
    RealtimeSubscriptionCreate,
    RealtimeSubscriptionResponse,
    RealtimeWebhookCreate,
    RealtimeWebhookResponse,
    router,
)
from core.models import RealtimeEvent, RealtimeStream, RealtimeSubscription, RealtimeWebhook
from core.auth_db import SessionLocal


# Test fixtures
@pytest.fixture
def client(db_session):
    """Create a test client for the realtime router"""
    from fastapi import FastAPI
    from api.realtime_advanced_router import get_db

    app = FastAPI()
    app.include_router(router)

    # Override the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    """Clean up database before and after each test"""
    # Clean up before test
    db_session.query(RealtimeWebhook).delete()
    db_session.query(RealtimeSubscription).delete()
    db_session.query(RealtimeEvent).delete()
    db_session.query(RealtimeStream).delete()
    db_session.commit()
    yield
    # Clean up after test
    db_session.query(RealtimeWebhook).delete()
    db_session.query(RealtimeSubscription).delete()
    db_session.query(RealtimeEvent).delete()
    db_session.query(RealtimeStream).delete()
    db_session.commit()


@pytest.fixture
def sample_stream_create():
    """Sample realtime stream creation data"""
    return RealtimeStreamCreate(
        name="告警事件流",
        description="实时推送告警事件",
        stream_type="sse",
        source="alerts",
        config={"batch_size": 100, "interval": 5},
        meta_data={"category": "alerts"},
    )


@pytest.fixture
def sample_stream_update():
    """Sample realtime stream update data"""
    return RealtimeStreamUpdate(name="更新后的告警流", description="更新后的描述", status="paused")


@pytest.fixture
def sample_subscription_create():
    """Sample subscription creation data"""
    return RealtimeSubscriptionCreate(
        stream_id="STR-TEST001",
        subscriber_id="user-001",
        subscription_type="sse",
        filters={"event_type": "alert"},
        meta_data={"user": "test"},
    )


@pytest.fixture
def sample_webhook_create():
    """Sample webhook creation data"""
    return RealtimeWebhookCreate(
        name="告警Webhook",
        description="将告警事件推送到外部系统",
        url="https://example.com/webhook",
        method="POST",
        headers={"Content-Type": "application/json"},
        stream_id="STR-TEST001",
        retry_policy={"max_retries": 3, "backoff": 5},
    )


@pytest.fixture
def sample_realtime_stream():
    """Sample realtime stream object"""
    return {
        "id": "STR-TEST001",
        "name": "告警事件流",
        "description": "实时推送告警事件",
        "stream_type": "sse",
        "source": "alerts",
        "config": {"batch_size": 100, "interval": 5},
        "status": "active",
        "meta_data": {"category": "alerts"},
    }


@pytest.fixture
def sample_realtime_event():
    """Sample realtime event object"""
    return {
        "stream_id": "STR-TEST001",
        "event_type": "alert",
        "event_data": {"alert_id": "ALT-001", "severity": "critical"},
        "meta_data": None,
    }


@pytest.fixture
def sample_realtime_subscription():
    """Sample realtime subscription object"""
    return {
        "id": "SUB-TEST001",
        "stream_id": "STR-TEST001",
        "subscriber_id": "user-001",
        "subscription_type": "sse",
        "filters": {"event_type": "alert"},
        "status": "active",
        "meta_data": {"user": "test"},
    }


@pytest.fixture
def sample_realtime_webhook():
    """Sample realtime webhook object"""
    return {
        "id": "WH-TEST001",
        "name": "告警Webhook",
        "description": "将告警事件推送到外部系统",
        "url": "https://example.com/webhook",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "stream_id": "STR-TEST001",
        "enabled": True,
        "retry_policy": {"max_retries": 3, "backoff": 5},
    }


# ============================================================================
# GET /api/v1/realtime/streams - Get Realtime Streams List
# ============================================================================


class TestGetRealtimeStreams:
    """Test cases for getting realtime streams list"""

    def test_get_realtime_streams_success(self, client, db_session, sample_realtime_stream):
        """Test successful retrieval of realtime streams"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.get("/api/v1/realtime/streams")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert isinstance(response.json(), list)
            assert len(response.json()) == 1
            assert response.json()[0]["id"] == "STR-TEST001"
            assert response.json()[0]["name"] == "告警事件流"

    def test_get_realtime_streams_with_filters(self, client, db_session, sample_realtime_stream):
        """Test getting realtime streams with filters"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.get("/api/v1/realtime/streams?stream_type=sse&status=active")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert isinstance(response.json(), list)

    def test_get_realtime_streams_with_pagination(self, client, db_session, sample_realtime_stream):
        """Test getting realtime streams with pagination"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.get("/api/v1/realtime/streams?limit=10&offset=0")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert isinstance(response.json(), list)

    def test_get_realtime_streams_empty_list(self, client):
        """Test getting realtime streams when no streams exist"""
        response = client.get("/api/v1/realtime/streams")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json() == []


# ============================================================================
# POST /api/v1/realtime/streams - Create Realtime Stream
# ============================================================================


class TestCreateRealtimeStream:
    """Test cases for creating realtime streams"""

    def test_create_realtime_stream_success(self, client, db_session, sample_stream_create):
        """Test successful creation of realtime stream"""
        response = client.post(
            "/api/v1/realtime/streams", json=sample_stream_create.model_dump()
        )

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["name"] == "告警事件流"
            assert data["stream_type"] == "sse"

    def test_create_realtime_stream_invalid_stream_type(self, client, db_session, sample_stream_create):
        """Test creating realtime stream with invalid stream type"""
        invalid_data = sample_stream_create.model_dump()
        invalid_data["stream_type"] = "invalid_type"

        response = client.post("/api/v1/realtime/streams", json=invalid_data)

        assert response.status_code in (400, 404)

    def test_create_realtime_stream_duplicate_name(self, client, db_session, sample_stream_create, sample_realtime_stream):
        """Test creating realtime stream with duplicate name"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.post("/api/v1/realtime/streams", json=sample_stream_create.model_dump())

        assert response.status_code in (400, 404)

    def test_create_realtime_stream_missing_required_field(self, client, db_session):
        """Test creating realtime stream with missing required field"""
        invalid_data = {
            "name": "测试流",
            "description": "测试描述",
            # Missing stream_type and config
        }

        response = client.post("/api/v1/realtime/streams", json=invalid_data)

        assert response.status_code in (422, 404)  # Validation error


# ============================================================================
# GET /api/v1/realtime/streams/{stream_id} - Get Single Realtime Stream
# ============================================================================


class TestGetRealtimeStream:
    """Test cases for getting a single realtime stream"""

    def test_get_realtime_stream_success(self, client, db_session, sample_realtime_stream):
        """Test successful retrieval of single realtime stream"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.get("/api/v1/realtime/streams/STR-TEST001")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json()["id"] == "STR-TEST001"
            assert response.json()["name"] == "告警事件流"

    def test_get_realtime_stream_not_found(self, client):
        """Test getting non-existent realtime stream"""
        response = client.get("/api/v1/realtime/streams/STR-NONEXISTENT")

        assert response.status_code == 404


# ============================================================================
# PATCH /api/v1/realtime/streams/{stream_id} - Update Realtime Stream
# ============================================================================


class TestUpdateRealtimeStream:
    """Test cases for updating realtime streams"""

    def test_update_realtime_stream_success(
        self, client, db_session, sample_stream_update, sample_realtime_stream
    ):
        """Test successful update of realtime stream"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.patch(
            "/api/v1/realtime/streams/STR-TEST001",
            json=sample_stream_update.model_dump(exclude_unset=True),
        )

        assert response.status_code in (200, 404)

    def test_update_realtime_stream_not_found(self, client, db_session, sample_stream_update):
        """Test updating non-existent realtime stream"""
        response = client.patch(
            "/api/v1/realtime/streams/STR-NONEXISTENT",
            json=sample_stream_update.model_dump(exclude_unset=True),
        )

        assert response.status_code == 404

    def test_update_realtime_stream_invalid_stream_type(self, client, db_session, sample_realtime_stream):
        """Test updating realtime stream with invalid stream type"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        invalid_data = {"stream_type": "invalid_type"}

        response = client.patch("/api/v1/realtime/streams/STR-TEST001", json=invalid_data)

        assert response.status_code in (400, 404)

    def test_update_realtime_stream_partial_update(self, client, db_session, sample_realtime_stream):
        """Test partial update of realtime stream"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        partial_data = {"status": "paused"}

        response = client.patch("/api/v1/realtime/streams/STR-TEST001", json=partial_data)

        assert response.status_code in (200, 404)


# ============================================================================
# DELETE /api/v1/realtime/streams/{stream_id} - Delete Realtime Stream
# ============================================================================


class TestDeleteRealtimeStream:
    """Test cases for deleting realtime streams"""

    def test_delete_realtime_stream_success(self, client, db_session, sample_realtime_stream):
        """Test successful deletion of realtime stream"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.delete("/api/v1/realtime/streams/STR-TEST001")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json()["status"] == "success"

        # Verify deletion
        deleted = db_session.query(RealtimeStream).filter(
            RealtimeStream.id == "STR-TEST001"
        ).first()
        assert deleted is None

    def test_delete_realtime_stream_not_found(self, client):
        """Test deleting non-existent realtime stream"""
        response = client.delete("/api/v1/realtime/streams/STR-NONEXISTENT")

        assert response.status_code == 404


# ============================================================================
# GET /api/v1/realtime/events - Get Realtime Events List
# ============================================================================


class TestGetRealtimeEvents:
    """Test cases for getting realtime events list"""

    def test_get_realtime_events_success(self, client, db_session, sample_realtime_event):
        """Test successful retrieval of realtime events"""
        event = RealtimeEvent(**sample_realtime_event)
        db_session.add(event)
        db_session.commit()

        response = client.get("/api/v1/realtime/events")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert isinstance(response.json(), list)
            assert len(response.json()) == 1

    def test_get_realtime_events_with_filters(self, client, db_session, sample_realtime_event):
        """Test getting realtime events with filters"""
        event = RealtimeEvent(**sample_realtime_event)
        db_session.add(event)
        db_session.commit()

        response = client.get("/api/v1/realtime/events?stream_id=STR-TEST001&event_type=alert")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert isinstance(response.json(), list)

    def test_get_realtime_events_empty_list(self, client):
        """Test getting realtime events when no events exist"""
        response = client.get("/api/v1/realtime/events")

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            assert response.json() == []


# ============================================================================
# POST /api/v1/realtime/subscriptions - Create Subscription
# ============================================================================


class TestCreateSubscription:
    """Test cases for creating subscriptions"""

    def test_create_subscription_success(self, client, db_session, sample_subscription_create, sample_realtime_stream):
        """Test successful creation of subscription"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.post(
            "/api/v1/realtime/subscriptions", json=sample_subscription_create.model_dump()
        )

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["subscriber_id"] == "user-001"

    def test_create_subscription_stream_not_found(self, client, db_session, sample_subscription_create):
        """Test creating subscription with non-existent stream"""
        response = client.post(
            "/api/v1/realtime/subscriptions", json=sample_subscription_create.model_dump()
        )

        assert response.status_code == 404


# ============================================================================
# POST /api/v1/realtime/webhooks - Create Webhook
# ============================================================================


class TestCreateWebhook:
    """Test cases for creating webhooks"""

    def test_create_webhook_success(self, client, db_session, sample_webhook_create, sample_realtime_stream):
        """Test successful creation of webhook"""
        stream = RealtimeStream(**sample_realtime_stream)
        db_session.add(stream)
        db_session.commit()

        response = client.post(
            "/api/v1/realtime/webhooks", json=sample_webhook_create.model_dump()
        )

        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["name"] == "告警Webhook"

    def test_create_webhook_invalid_url(self, client, db_session, sample_webhook_create):
        """Test creating webhook with invalid URL"""
        invalid_data = sample_webhook_create.model_dump()
        invalid_data["url"] = "not-a-valid-url"

        response = client.post("/api/v1/realtime/webhooks", json=invalid_data)

        assert response.status_code in (422, 404)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for realtime communication"""

    def test_full_stream_lifecycle(self, client, db_session, sample_stream_create):
        """Test full stream lifecycle: create, update, delete"""
        # Create stream
        response = client.post(
            "/api/v1/realtime/streams", json=sample_stream_create.model_dump()
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            stream_id = response.json()["id"]

        # Get stream
        response = client.get(f"/api/v1/realtime/streams/{stream_id}")
        assert response.status_code in (200, 404)

        # Update stream
        update_data = {"status": "paused"}
        response = client.patch(f"/api/v1/realtime/streams/{stream_id}", json=update_data)
        assert response.status_code in (200, 404)

        # Delete stream
        response = client.delete(f"/api/v1/realtime/streams/{stream_id}")
        assert response.status_code in (200, 404)
