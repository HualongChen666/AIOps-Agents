# -*- coding: utf-8 -*-
"""
Unit tests for Infrastructure Repository Layer

Tests for:
- InfrastructureKafkaMessageRepository
- InfrastructureFlinkJobRepository
- InfrastructureStorageRepository
- InfrastructureConfigRepository
- InfrastructureDataFlowRepository
- InfrastructureMonitoringRepository
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.infrastructure_repository import (
    InfrastructureConfigRepository,
    InfrastructureDataFlowRepository,
    InfrastructureFlinkJobRepository,
    InfrastructureKafkaMessageRepository,
    InfrastructureMonitoringRepository,
    InfrastructureStorageRepository,
)
from core.models import (
    InfrastructureConfigDB,
    InfrastructureDataFlowDB,
    InfrastructureFlinkJobDB,
    InfrastructureKafkaMessageDB,
    InfrastructureMonitoringDB,
    InfrastructureStorageDB,
)


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestInfrastructureKafkaMessageRepository:
    """Tests for InfrastructureKafkaMessageRepository"""

    def test_create_message(self, in_memory_db):
        """Test creating a Kafka message"""
        repo = InfrastructureKafkaMessageRepository(in_memory_db)
        message = repo.create_message(
            topic="test-topic", key="test-key", value={"data": "test"}, headers={"header": "value"}
        )

        assert message.id is not None
        assert message.topic == "test-topic"
        assert message.key == "test-key"
        assert message.value == {"data": "test"}
        assert message.status == "sent"

    def test_get_message_by_id(self, in_memory_db):
        """Test getting a message by ID"""
        repo = InfrastructureKafkaMessageRepository(in_memory_db)
        created = repo.create_message(topic="test-topic", key="test-key", value={"data": "test"})

        retrieved = repo.get_message_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.topic == created.topic

    def test_get_messages_by_topic(self, in_memory_db):
        """Test getting messages by topic"""
        repo = InfrastructureKafkaMessageRepository(in_memory_db)
        repo.create_message(topic="topic1", key="key1", value={"data": "test1"})
        repo.create_message(topic="topic1", key="key2", value={"data": "test2"})
        repo.create_message(topic="topic2", key="key3", value={"data": "test3"})

        messages = repo.get_messages_by_topic("topic1")
        assert len(messages) == 2
        assert all(msg.topic == "topic1" for msg in messages)

    def test_get_all_topics(self, in_memory_db):
        """Test getting all unique topics"""
        repo = InfrastructureKafkaMessageRepository(in_memory_db)
        repo.create_message(topic="topic1", key="key1", value={"data": "test1"})
        repo.create_message(topic="topic2", key="key2", value={"data": "test2"})
        repo.create_message(topic="topic1", key="key3", value={"data": "test3"})

        topics = repo.get_all_topics()
        assert set(topics) == {"topic1", "topic2"}

    def test_update_message_status(self, in_memory_db):
        """Test updating message status"""
        repo = InfrastructureKafkaMessageRepository(in_memory_db)
        message = repo.create_message(topic="test-topic", key="test-key", value={"data": "test"})

        success = repo.update_message_status(message.id, "failed", "Test error")
        assert success is True

        updated = repo.get_message_by_id(message.id)
        assert updated.status == "failed"
        assert updated.error_message == "Test error"

    def test_count_messages_by_status(self, in_memory_db):
        """Test counting messages by status"""
        repo = InfrastructureKafkaMessageRepository(in_memory_db)
        repo.create_message(topic="test-topic", key="key1", value={"data": "test1"}, status="sent")
        repo.create_message(topic="test-topic", key="key2", value={"data": "test2"}, status="sent")
        repo.create_message(topic="test-topic", key="key3", value={"data": "test3"}, status="failed")

        sent_count = repo.count_messages_by_status("sent")
        failed_count = repo.count_messages_by_status("failed")

        assert sent_count == 2
        assert failed_count == 1


class TestInfrastructureFlinkJobRepository:
    """Tests for InfrastructureFlinkJobRepository"""

    def test_create_job(self, in_memory_db):
        """Test creating a Flink job"""
        repo = InfrastructureFlinkJobRepository(in_memory_db)
        job = repo.create_job(
            job_name="test-job", job_type="metrics_aggregation", parallelism=4
        )

        assert job.id is not None
        assert job.job_name == "test-job"
        assert job.job_type == "metrics_aggregation"
        assert job.parallelism == 4
        assert job.status == "created"

    def test_get_job_by_id(self, in_memory_db):
        """Test getting a job by ID"""
        repo = InfrastructureFlinkJobRepository(in_memory_db)
        created = repo.create_job(job_name="test-job", job_type="metrics_aggregation")

        retrieved = repo.get_job_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.job_name == created.job_name

    def test_get_job_by_name(self, in_memory_db):
        """Test getting a job by name"""
        repo = InfrastructureFlinkJobRepository(in_memory_db)
        created = repo.create_job(job_name="test-job", job_type="metrics_aggregation")

        retrieved = repo.get_job_by_name("test-job")
        assert retrieved is not None
        assert retrieved.job_name == "test-job"

    def test_list_jobs(self, in_memory_db):
        """Test listing jobs"""
        repo = InfrastructureFlinkJobRepository(in_memory_db)
        repo.create_job(job_name="job1", job_type="metrics_aggregation")
        repo.create_job(job_name="job2", job_type="anomaly_detection")
        repo.create_job(job_name="job3", job_type="metrics_aggregation")

        jobs = repo.list_jobs()
        assert len(jobs) == 3

        metrics_jobs = repo.list_jobs(job_type="metrics_aggregation")
        assert len(metrics_jobs) == 2

    def test_update_job_status(self, in_memory_db):
        """Test updating job status"""
        repo = InfrastructureFlinkJobRepository(in_memory_db)
        job = repo.create_job(job_name="test-job", job_type="metrics_aggregation")

        success = repo.update_job_status(job.id, "running")
        assert success is True

        updated = repo.get_job_by_id(job.id)
        assert updated.status == "running"
        assert updated.started_at is not None

    def test_delete_job(self, in_memory_db):
        """Test deleting a job"""
        repo = InfrastructureFlinkJobRepository(in_memory_db)
        job = repo.create_job(job_name="test-job", job_type="metrics_aggregation")

        success = repo.delete_job(job.id)
        assert success is True

        deleted = repo.get_job_by_id(job.id)
        assert deleted is None


class TestInfrastructureConfigRepository:
    """Tests for InfrastructureConfigRepository"""

    def test_set_config_new(self, in_memory_db):
        """Test setting a new configuration"""
        repo = InfrastructureConfigRepository(in_memory_db)
        config = repo.set_config(
            key="test.config", value={"setting": "value"}, category="test"
        )

        assert config.key == "test.config"
        assert config.value == {"setting": "value"}
        assert config.version == 1
        assert config.category == "test"

    def test_set_config_update(self, in_memory_db):
        """Test updating an existing configuration"""
        repo = InfrastructureConfigRepository(in_memory_db)
        repo.set_config(key="test.config", value={"setting": "value1"})

        updated = repo.set_config(key="test.config", value={"setting": "value2"})
        assert updated.version == 2
        assert updated.value == {"setting": "value2"}

    def test_get_config_by_key(self, in_memory_db):
        """Test getting configuration by key"""
        repo = InfrastructureConfigRepository(in_memory_db)
        created = repo.set_config(key="test.config", value={"setting": "value"})

        retrieved = repo.get_config_by_key("test.config")
        assert retrieved is not None
        assert retrieved.key == created.key
        assert retrieved.value == created.value

    def test_get_all_configs(self, in_memory_db):
        """Test getting all configurations"""
        repo = InfrastructureConfigRepository(in_memory_db)
        repo.set_config(key="config1", value={"setting": "value1"}, category="cat1")
        repo.set_config(key="config2", value={"setting": "value2"}, category="cat1")
        repo.set_config(key="config3", value={"setting": "value3"}, category="cat2")

        configs = repo.get_all_configs()
        assert len(configs) == 3

        cat1_configs = repo.get_all_configs(category="cat1")
        assert len(cat1_configs) == 2

    def test_delete_config(self, in_memory_db):
        """Test deleting a configuration"""
        repo = InfrastructureConfigRepository(in_memory_db)
        repo.set_config(key="test.config", value={"setting": "value"})

        success = repo.delete_config("test.config")
        assert success is True

        deleted = repo.get_config_by_key("test.config")
        assert deleted is None


class TestInfrastructureDataFlowRepository:
    """Tests for InfrastructureDataFlowRepository"""

    def test_create_flow(self, in_memory_db):
        """Test creating a data flow"""
        repo = InfrastructureDataFlowRepository(in_memory_db)
        flow = repo.create_flow(flow_name="test-flow", flow_type="l1l2")

        assert flow.id is not None
        assert flow.flow_name == "test-flow"
        assert flow.flow_type == "l1l2"
        assert flow.status == "stopped"

    def test_get_flow_by_id(self, in_memory_db):
        """Test getting a flow by ID"""
        repo = InfrastructureDataFlowRepository(in_memory_db)
        created = repo.create_flow(flow_name="test-flow", flow_type="l1l2")

        retrieved = repo.get_flow_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_update_flow_stats(self, in_memory_db):
        """Test updating flow statistics"""
        repo = InfrastructureDataFlowRepository(in_memory_db)
        flow = repo.create_flow(flow_name="test-flow", flow_type="l1l2")

        success = repo.update_flow_stats(
            flow.id, total_processed=100, total_analyzed=80, total_errors=5, avg_processing_time_ms=50.0
        )
        assert success is True

        updated = repo.get_flow_by_id(flow.id)
        assert updated.total_processed == 100
        assert updated.total_analyzed == 80
        assert updated.total_errors == 5
        assert updated.avg_processing_time_ms == 50.0

    def test_start_flow(self, in_memory_db):
        """Test starting a data flow"""
        repo = InfrastructureDataFlowRepository(in_memory_db)
        flow = repo.create_flow(flow_name="test-flow", flow_type="l1l2")

        success = repo.start_flow(flow.id)
        assert success is True

        updated = repo.get_flow_by_id(flow.id)
        assert updated.status == "running"
        assert updated.started_at is not None

    def test_stop_flow(self, in_memory_db):
        """Test stopping a data flow"""
        repo = InfrastructureDataFlowRepository(in_memory_db)
        flow = repo.create_flow(flow_name="test-flow", flow_type="l1l2")
        repo.start_flow(flow.id)

        success = repo.stop_flow(flow.id)
        assert success is True

        updated = repo.get_flow_by_id(flow.id)
        assert updated.status == "stopped"
        assert updated.stopped_at is not None

    def test_get_data_flow_stats(self, in_memory_db):
        """Test getting data flow statistics"""
        repo = InfrastructureDataFlowRepository(in_memory_db)
        flow = repo.create_flow(flow_name="test-flow", flow_type="l1l2")
        repo.update_flow_stats(
            flow.id, total_processed=100, total_analyzed=80, total_errors=5, avg_processing_time_ms=50.0
        )

        stats = repo.get_data_flow_stats(flow.id)
        assert stats is not None
        assert stats["total_processed"] == 100
        assert stats["total_analyzed"] == 80
        assert stats["total_errors"] == 5
        assert stats["error_rate"] == 0.05
        assert stats["analysis_rate"] == 0.8


class TestInfrastructureMonitoringRepository:
    """Tests for InfrastructureMonitoringRepository"""

    def test_create_component(self, in_memory_db):
        """Test creating a monitoring component"""
        repo = InfrastructureMonitoringRepository(in_memory_db)
        component = repo.create_component(
            component_name="prometheus", component_type="prometheus", endpoint="http://localhost:9090"
        )

        assert component.id is not None
        assert component.component_name == "prometheus"
        assert component.component_type == "prometheus"
        assert component.status == "active"

    def test_get_component_by_id(self, in_memory_db):
        """Test getting a component by ID"""
        repo = InfrastructureMonitoringRepository(in_memory_db)
        created = repo.create_component(component_name="prometheus", component_type="prometheus")

        retrieved = repo.get_component_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_list_components(self, in_memory_db):
        """Test listing components"""
        repo = InfrastructureMonitoringRepository(in_memory_db)
        repo.create_component(component_name="prometheus", component_type="prometheus")
        repo.create_component(component_name="grafana", component_type="grafana")
        repo.create_component(component_name="loki", component_type="loki")

        components = repo.list_components()
        assert len(components) == 3

        prometheus_components = repo.list_components(component_type="prometheus")
        assert len(prometheus_components) == 1

    def test_update_health_status(self, in_memory_db):
        """Test updating component health status"""
        repo = InfrastructureMonitoringRepository(in_memory_db)
        component = repo.create_component(component_name="prometheus", component_type="prometheus")

        success = repo.update_health_status(component.id, "healthy")
        assert success is True

        updated = repo.get_component_by_id(component.id)
        assert updated.health_status == "healthy"
        assert updated.last_health_check is not None

    def test_get_monitoring_status(self, in_memory_db):
        """Test getting overall monitoring status"""
        repo = InfrastructureMonitoringRepository(in_memory_db)
        repo.create_component(component_name="prometheus", component_type="prometheus")
        repo.update_health_status(repo.get_component_by_name("prometheus").id, "healthy")
        repo.create_component(component_name="grafana", component_type="grafana")
        repo.update_health_status(repo.get_component_by_name("grafana").id, "unhealthy")

        status = repo.get_monitoring_status()
        assert status["total_components"] == 2
        assert status["healthy_components"] == 1
        assert status["unhealthy_components"] == 1
        assert status["overall_status"] == "degraded"
