# -*- coding: utf-8 -*-
"""
Integration tests for Infrastructure Service Layer

Tests for:
- InfrastructureKafkaService
- InfrastructureFlinkService
- InfrastructureStorageService
- InfrastructureConfigService
- InfrastructureDataFlowService
- InfrastructureMonitoringService
- InfrastructureService (main service)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.infrastructure_service import (
    InfrastructureConfigService,
    InfrastructureDataFlowService,
    InfrastructureFlinkService,
    InfrastructureKafkaService,
    InfrastructureMonitoringService,
    InfrastructureService,
    get_infrastructure_service,
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


class TestInfrastructureKafkaService:
    """Tests for InfrastructureKafkaService"""

    def test_send_message_success(self, in_memory_db):
        """Test sending a Kafka message successfully"""
        service = InfrastructureKafkaService(in_memory_db)
        result = service.send_message(
            topic="test-topic", key="test-key", value={"data": "test"}
        )

        assert result["success"] is True
        assert "message_id" in result
        assert result["topic"] == "test-topic"
        assert result["status"] == "sent"

    def test_send_message_with_headers(self, in_memory_db):
        """Test sending a Kafka message with headers"""
        service = InfrastructureKafkaService(in_memory_db)
        result = service.send_message(
            topic="test-topic", key="test-key", value={"data": "test"}, headers={"header": "value"}
        )

        assert result["success"] is True
        assert result["status"] == "sent"

    def test_get_status(self, in_memory_db):
        """Test getting Kafka status"""
        service = InfrastructureKafkaService(in_memory_db)
        service.send_message(topic="topic1", key="key1", value={"data": "test1"})
        service.send_message(topic="topic2", key="key2", value={"data": "test2"})

        status = service.get_status()
        assert "connected" in status
        assert "total_messages" in status
        assert "topics" in status
        assert status["total_messages"] >= 2


class TestInfrastructureFlinkService:
    """Tests for InfrastructureFlinkService"""

    def test_create_job(self, in_memory_db):
        """Test creating a Flink job"""
        service = InfrastructureFlinkService(in_memory_db)
        result = service.create_job(
            job_name="test-job", job_type="metrics_aggregation", parallelism=4
        )

        assert result["job_id"] is not None
        assert result["job_name"] == "test-job"
        assert result["job_type"] == "metrics_aggregation"
        assert result["parallelism"] == 4
        assert result["status"] == "created"

    def test_list_jobs(self, in_memory_db):
        """Test listing Flink jobs"""
        service = InfrastructureFlinkService(in_memory_db)
        service.create_job(job_name="job1", job_type="metrics_aggregation")
        service.create_job(job_name="job2", job_type="anomaly_detection")

        jobs = service.list_jobs()
        assert len(jobs) == 2
        assert all("job_id" in job for job in jobs)
        assert all("job_name" in job for job in jobs)

    def test_get_job_status(self, in_memory_db):
        """Test getting job status"""
        service = InfrastructureFlinkService(in_memory_db)
        created = service.create_job(job_name="test-job", job_type="metrics_aggregation")

        status = service.get_job_status(created["job_id"])
        assert status is not None
        assert status["job_name"] == "test-job"
        assert status["status"] == "created"

    def test_update_job_status(self, in_memory_db):
        """Test updating job status"""
        service = InfrastructureFlinkService(in_memory_db)
        created = service.create_job(job_name="test-job", job_type="metrics_aggregation")

        success = service.update_job_status(created["job_id"], "running")
        assert success is True

        status = service.get_job_status(created["job_id"])
        assert status["status"] == "running"


class TestInfrastructureConfigService:
    """Tests for InfrastructureConfigService"""

    def test_set_config_new(self, in_memory_db):
        """Test setting a new configuration"""
        service = InfrastructureConfigService(in_memory_db)
        result = service.set_config(
            key="test.config", value={"setting": "value"}, category="test"
        )

        assert result["key"] == "test.config"
        assert result["value"] == {"setting": "value"}
        assert result["version"] == 1
        assert result["category"] == "test"

    def test_set_config_update(self, in_memory_db):
        """Test updating an existing configuration"""
        service = InfrastructureConfigService(in_memory_db)
        service.set_config(key="test.config", value={"setting": "value1"})

        updated = service.set_config(key="test.config", value={"setting": "value2"})
        assert updated["version"] == 2
        assert updated["value"] == {"setting": "value2"}

    def test_get_config(self, in_memory_db):
        """Test getting configuration by key"""
        service = InfrastructureConfigService(in_memory_db)
        service.set_config(key="test.config", value={"setting": "value"})

        result = service.get_config("test.config")
        assert result is not None
        assert result["key"] == "test.config"
        assert result["value"] == {"setting": "value"}

    def test_get_all_configs(self, in_memory_db):
        """Test getting all configurations"""
        service = InfrastructureConfigService(in_memory_db)
        service.set_config(key="config1", value={"setting": "value1"}, category="cat1")
        service.set_config(key="config2", value={"setting": "value2"}, category="cat1")

        configs = service.get_all_configs()
        assert len(configs) == 2

        cat1_configs = service.get_all_configs(category="cat1")
        assert len(cat1_configs) == 2


class TestInfrastructureDataFlowService:
    """Tests for InfrastructureDataFlowService"""

    def test_get_data_flow_stats(self, in_memory_db):
        """Test getting data flow statistics"""
        service = InfrastructureDataFlowService(in_memory_db)
        stats = service.get_data_flow_stats()

        assert "total_processed" in stats
        assert "total_analyzed" in stats
        assert "total_errors" in stats
        assert "error_rate" in stats
        assert "analysis_rate" in stats

    def test_start_data_flow(self, in_memory_db):
        """Test starting a data flow"""
        service = InfrastructureDataFlowService(in_memory_db)
        success = service.start_data_flow()
        assert success is True

    def test_stop_data_flow(self, in_memory_db):
        """Test stopping a data flow"""
        service = InfrastructureDataFlowService(in_memory_db)
        service.start_data_flow()
        success = service.stop_data_flow()
        assert success is True


class TestInfrastructureMonitoringService:
    """Tests for InfrastructureMonitoringService"""

    def test_get_monitoring_status(self, in_memory_db):
        """Test getting monitoring status"""
        service = InfrastructureMonitoringService(in_memory_db)
        status = service.get_monitoring_status()

        assert "total_components" in status
        assert "healthy_components" in status
        assert "overall_status" in status

    def test_record_metric(self, in_memory_db):
        """Test recording a metric"""
        service = InfrastructureMonitoringService(in_memory_db)
        # This should not raise an exception
        service.record_metric("test_metric", 42.0, labels={"label": "value"})


class TestInfrastructureService:
    """Tests for main InfrastructureService"""

    def test_get_infrastructure_service(self, in_memory_db):
        """Test getting infrastructure service instance"""
        service = get_infrastructure_service(in_memory_db)
        assert service is not None
        assert hasattr(service, "kafka")
        assert hasattr(service, "flink")
        assert hasattr(service, "storage")
        assert hasattr(service, "config")
        assert hasattr(service, "data_flow")
        assert hasattr(service, "monitoring")

    def test_get_health(self, in_memory_db):
        """Test getting overall infrastructure health"""
        service = get_infrastructure_service(in_memory_db)
        health = service.get_health()

        assert "kafka" in health
        assert "flink" in health
        assert "monitoring" in health
        assert "overall_status" in health

    def test_service_integration(self, in_memory_db):
        """Test integration between all sub-services"""
        service = get_infrastructure_service(in_memory_db)

        # Create a config
        service.config.set_config(key="test.config", value={"setting": "value"})

        # Create a Flink job
        service.flink.create_job(job_name="test-job", job_type="metrics_aggregation")

        # Send a Kafka message
        service.kafka.send_message(topic="test-topic", key="test-key", value={"data": "test"})

        # Get health status
        health = service.get_health()
        assert health["overall_status"] in ["healthy", "degraded", "unhealthy"]
