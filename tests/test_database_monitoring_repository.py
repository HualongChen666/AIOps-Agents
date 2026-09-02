# -*- coding: utf-8 -*-
"""
Unit tests for Database Monitoring Repository
Tests database operations for database monitoring entities
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine
from core.models import (
    DatabaseMetricThresholdDB,
    DatabaseMonitoringConfigDB,
    DatabasePerformanceBaselineDB,
    DatabaseAlertRuleDB,
    DatabaseMonitoringStatusDB,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test"""
    # Create all tables
    from core.models import Base

    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


class TestDatabaseMonitoringConfigDB:
    """Test monitoring configuration database model"""

    def test_create_config(self, db_session: Session):
        """Test creating a monitoring configuration"""
        config = DatabaseMonitoringConfigDB(
            enabled=True,
            collection_interval=60,
            retention_days=30,
            enable_realtime=True,
            enable_slow_query_log=True,
            slow_query_threshold=1.0,
            enable_connection_monitoring=True,
            max_connections_threshold=100,
            enable_deadlock_detection=True,
            updated_by="test_user",
        )

        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        assert config is not None
        assert config.enabled is True
        assert config.collection_interval == 60
        assert config.id is not None
        assert config.updated_by == "test_user"

    def test_get_config(self, db_session: Session):
        """Test getting monitoring configuration"""
        config = DatabaseMonitoringConfigDB(
            enabled=True,
            collection_interval=60,
            retention_days=30,
            enable_realtime=True,
            enable_slow_query_log=True,
            slow_query_threshold=1.0,
            enable_connection_monitoring=True,
            max_connections_threshold=100,
            enable_deadlock_detection=True,
        )

        db_session.add(config)
        db_session.commit()

        retrieved_config = db_session.query(DatabaseMonitoringConfigDB).first()

        assert retrieved_config is not None
        assert retrieved_config.id == config.id
        assert retrieved_config.enabled is True


class TestDatabaseMetricThresholdDB:
    """Test metric threshold database model"""

    def test_create_threshold(self, db_session: Session):
        """Test creating a metric threshold"""
        threshold = DatabaseMetricThresholdDB(
            metric_type="query_time",
            warning_threshold=100.0,
            critical_threshold=500.0,
            enabled=True,
            description="Query time threshold",
            created_by="test_user",
        )

        db_session.add(threshold)
        db_session.commit()
        db_session.refresh(threshold)

        assert threshold is not None
        assert threshold.metric_type == "query_time"
        assert threshold.warning_threshold == 100.0
        assert threshold.critical_threshold == 500.0
        assert threshold.enabled is True
        assert threshold.id is not None

    def test_get_all_thresholds(self, db_session: Session):
        """Test getting all metric thresholds"""
        # Create multiple thresholds
        threshold1 = DatabaseMetricThresholdDB(
            metric_type="query_time",
            warning_threshold=100.0,
            critical_threshold=500.0,
            enabled=True,
        )
        threshold2 = DatabaseMetricThresholdDB(
            metric_type="connection_count",
            warning_threshold=80.0,
            critical_threshold=95.0,
            enabled=True,
        )

        db_session.add(threshold1)
        db_session.add(threshold2)
        db_session.commit()

        thresholds = db_session.query(DatabaseMetricThresholdDB).all()

        assert len(thresholds) == 2
        assert any(t.metric_type == "query_time" for t in thresholds)
        assert any(t.metric_type == "connection_count" for t in thresholds)


class TestDatabasePerformanceBaselineDB:
    """Test performance baseline database model"""

    def test_create_baseline(self, db_session: Session):
        """Test creating a performance baseline"""
        baseline = DatabasePerformanceBaselineDB(
            baseline_name="test_baseline",
            avg_query_time=45.0,
            p95_query_time=120.0,
            p99_query_time=250.0,
            avg_connection_count=35.0,
            peak_connection_count=65,
            cache_hit_ratio=0.92,
            database_size_mb=1024.0,
            description="Test baseline",
            created_by="test_user",
        )

        db_session.add(baseline)
        db_session.commit()
        db_session.refresh(baseline)

        assert baseline is not None
        assert baseline.baseline_name == "test_baseline"
        assert baseline.avg_query_time == 45.0
        assert baseline.p95_query_time == 120.0
        assert baseline.id is not None


class TestDatabaseAlertRuleDB:
    """Test alert rule database model"""

    def test_create_alert_rule(self, db_session: Session):
        """Test creating an alert rule"""
        rule = DatabaseAlertRuleDB(
            rule_id="test_rule",
            rule_name="Test Alert Rule",
            metric_type="query_time",
            condition="query_time > 500",
            severity="warning",
            enabled=True,
            notification_channels=["email", "slack"],
            cooldown_minutes=5,
            description="Test alert rule",
            created_by="test_user",
        )

        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        assert rule is not None
        assert rule.rule_id == "test_rule"
        assert rule.rule_name == "Test Alert Rule"
        assert rule.metric_type == "query_time"
        assert rule.severity == "warning"
        assert rule.enabled is True
        assert rule.id is not None


class TestDatabaseMonitoringStatusDB:
    """Test monitoring status database model"""

    def test_create_status(self, db_session: Session):
        """Test creating monitoring status"""
        status = DatabaseMonitoringStatusDB(
            monitoring_enabled=True,
            active_alerts=0,
            total_metrics_collected=0,
            database_health="healthy",
            uptime_percentage=100.0,
        )

        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)

        assert status is not None
        assert status.monitoring_enabled is True
        assert status.active_alerts == 0
        assert status.database_health == "healthy"
        assert status.uptime_percentage == 100.0
        assert status.id is not None
