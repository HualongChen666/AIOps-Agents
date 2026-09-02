# -*- coding: utf-8 -*-
"""
Infrastructure Service Layer

Provides business logic for Infrastructure components:
- Kafka message management
- Flink job management
- Storage configuration management
- Configuration center management
- Data flow management
- Monitoring component management
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.infrastructure_repository import (
    InfrastructureConfigRepository,
    InfrastructureDataFlowRepository,
    InfrastructureFlinkJobRepository,
    InfrastructureKafkaMessageRepository,
    InfrastructureMonitoringRepository,
    InfrastructureStorageRepository,
)
from core.kafka_stream_processor import get_kafka_processor
from core.monitoring_infrastructure import get_monitoring_infrastructure

_logger = logging.getLogger(__name__)


class InfrastructureKafkaService:
    """Service for Kafka message operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = InfrastructureKafkaMessageRepository(db)
        self.kafka_processor = get_kafka_processor()

    def send_message(
        self,
        topic: str,
        key: str,
        value: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send a Kafka message and track it in database"""
        try:
            # Send message via Kafka processor
            success = self.kafka_processor.send_message(
                topic=topic, key=key, value=value, headers=headers
            )

            # Track in database
            status = "sent" if success else "failed"
            message_record = self.repository.create_message(
                topic=topic, key=key, value=value, headers=headers, status=status
            )

            if not success:
                self.repository.update_message_status(
                    message_record.id, "failed", "Kafka processor returned False"
                )

            _logger.info(f"Kafka message sent: {message_record.id}, success: {success}")
            return {
                "success": success,
                "message_id": message_record.id,
                "topic": topic,
                "status": status,
            }
        except Exception as e:
            _logger.error(f"Error sending Kafka message: {e}")
            # Create failed record
            message_record = self.repository.create_message(
                topic=topic, key=key, value=value, headers=headers, status="failed"
            )
            self.repository.update_message_status(message_record.id, "failed", str(e))
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get Kafka status with message statistics"""
        try:
            messages = self.kafka_processor.get_cached_messages()
            topics = self.repository.get_all_topics()

            total_sent = self.repository.count_messages_by_status("sent")
            total_failed = self.repository.count_messages_by_status("failed")

            return {
                "connected": hasattr(self.kafka_processor, "producer") and self.kafka_processor.producer is not None,
                "total_messages": len(messages),
                "topics": topics,
                "total_sent": total_sent,
                "total_failed": total_failed,
                "recent_messages": [
                    {
                        "id": msg.id,
                        "topic": msg.topic,
                        "key": msg.key,
                        "status": msg.status,
                        "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
                    }
                    for msg in self.repository.get_messages_by_topic(
                        topics[0] if topics else "", limit=10
                    )
                ],
            }
        except Exception as e:
            _logger.error(f"Error getting Kafka status: {e}")
            return {
                "connected": False,
                "total_messages": 0,
                "topics": [],
                "total_sent": 0,
                "total_failed": 0,
                "error": str(e),
            }


class InfrastructureFlinkService:
    """Service for Flink job operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = InfrastructureFlinkJobRepository(db)

    def create_job(
        self,
        job_name: str,
        job_type: str,
        parallelism: int = 2,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new Flink job"""
        try:
            job = self.repository.create_job(
                job_name=job_name, job_type=job_type, parallelism=parallelism, config=config
            )
            _logger.info(f"Flink job created: {job.id} with name: {job_name}")
            return {
                "job_id": job.id,
                "job_name": job.job_name,
                "job_type": job.job_type,
                "parallelism": job.parallelism,
                "status": job.status,
            }
        except Exception as e:
            _logger.error(f"Error creating Flink job: {e}")
            raise

    def list_jobs(
        self, status: Optional[str] = None, job_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List Flink jobs"""
        try:
            jobs = self.repository.list_jobs(status=status, job_type=job_type)
            return [
                {
                    "job_id": job.id,
                    "job_name": job.job_name,
                    "job_type": job.job_type,
                    "parallelism": job.parallelism,
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "stopped_at": job.stopped_at.isoformat() if job.stopped_at else None,
                }
                for job in jobs
            ]
        except Exception as e:
            _logger.error(f"Error listing Flink jobs: {e}")
            raise

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        try:
            job = self.repository.get_job_by_id(job_id)
            if not job:
                return None
            return {
                "job_id": job.id,
                "job_name": job.job_name,
                "job_type": job.job_type,
                "parallelism": job.parallelism,
                "status": job.status,
                "config": job.config,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "stopped_at": job.stopped_at.isoformat() if job.stopped_at else None,
            }
        except Exception as e:
            _logger.error(f"Error getting job status: {e}")
            raise

    def update_job_status(
        self, job_id: str, status: str, error_message: Optional[str] = None
    ) -> bool:
        """Update job status"""
        try:
            return self.repository.update_job_status(job_id, status, error_message)
        except Exception as e:
            _logger.error(f"Error updating job status: {e}")
            raise


class InfrastructureStorageService:
    """Service for storage configuration operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = InfrastructureStorageRepository(db)

    def create_storage(
        self,
        storage_type: str,
        endpoint: str,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new storage configuration"""
        try:
            storage = self.repository.create_storage(
                storage_type=storage_type,
                endpoint=endpoint,
                bucket_name=bucket_name,
                access_key=access_key,
                secret_key=secret_key,
                region=region,
                config=config,
            )
            _logger.info(f"Storage configuration created: {storage.id}")
            return {
                "storage_id": storage.id,
                "storage_type": storage.storage_type,
                "endpoint": storage.endpoint,
                "bucket_name": storage.bucket_name,
                "region": storage.region,
                "status": storage.status,
            }
        except Exception as e:
            _logger.error(f"Error creating storage configuration: {e}")
            raise

    def get_read_connection(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Get read connection info"""
        try:
            return self.repository.get_read_connection_info(storage_id)
        except Exception as e:
            _logger.error(f"Error getting read connection: {e}")
            raise

    def get_write_connection(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Get write connection info"""
        try:
            return self.repository.get_write_connection_info(storage_id)
        except Exception as e:
            _logger.error(f"Error getting write connection: {e}")
            raise

    def health_check(self, storage_id: str) -> Dict[str, Any]:
        """Perform health check on storage"""
        try:
            return self.repository.health_check(storage_id)
        except Exception as e:
            _logger.error(f"Error performing health check: {e}")
            raise


class InfrastructureConfigService:
    """Service for configuration center operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = InfrastructureConfigRepository(db)

    def set_config(
        self,
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
        category: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set a configuration value"""
        try:
            config = self.repository.set_config(
                key=key, value=value, metadata=metadata, category=category, updated_by=updated_by
            )
            _logger.info(f"Configuration set: {key}, version: {config.version}")
            return {
                "key": config.key,
                "value": config.value,
                "version": config.version,
                "category": config.category,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            }
        except Exception as e:
            _logger.error(f"Error setting configuration: {e}")
            raise

    def get_config(self, key: str) -> Optional[Dict[str, Any]]:
        """Get configuration by key"""
        try:
            config = self.repository.get_config_by_key(key)
            if not config:
                return None
            return {
                "key": config.key,
                "value": config.value,
                "version": config.version,
                "category": config.category,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            }
        except Exception as e:
            _logger.error(f"Error getting configuration: {e}")
            raise

    def get_all_configs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all configurations"""
        try:
            configs = self.repository.get_all_configs(category=category)
            return [
                {
                    "key": config.key,
                    "value": config.value,
                    "version": config.version,
                    "category": config.category,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
                for config in configs
            ]
        except Exception as e:
            _logger.error(f"Error getting all configurations: {e}")
            raise


class InfrastructureDataFlowService:
    """Service for data flow operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = InfrastructureDataFlowRepository(db)

    def get_data_flow_stats(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get data flow statistics"""
        try:
            # If no flow_id provided, get default L1L2 flow
            if not flow_id:
                flow = self.repository.get_flow_by_name("l1l2_default")
                if not flow:
                    # Create default flow if it doesn't exist
                    flow = self.repository.create_flow("l1l2_default", "l1l2")
                flow_id = flow.id

            stats = self.repository.get_data_flow_stats(flow_id)
            if not stats:
                return {
                    "total_processed": 0,
                    "total_analyzed": 0,
                    "total_errors": 0,
                    "avg_processing_time_ms": 0.0,
                    "error_rate": 0.0,
                    "analysis_rate": 0.0,
                }
            return stats
        except Exception as e:
            _logger.error(f"Error getting data flow stats: {e}")
            raise

    def start_data_flow(self, flow_id: Optional[str] = None) -> bool:
        """Start a data flow"""
        try:
            if not flow_id:
                flow = self.repository.get_flow_by_name("l1l2_default")
                if not flow:
                    flow = self.repository.create_flow("l1l2_default", "l1l2")
                flow_id = flow.id
            return self.repository.start_flow(flow_id)
        except Exception as e:
            _logger.error(f"Error starting data flow: {e}")
            raise

    def stop_data_flow(self, flow_id: Optional[str] = None) -> bool:
        """Stop a data flow"""
        try:
            if not flow_id:
                flow = self.repository.get_flow_by_name("l1l2_default")
                if not flow:
                    return False
                flow_id = flow.id
            return self.repository.stop_flow(flow_id)
        except Exception as e:
            _logger.error(f"Error stopping data flow: {e}")
            raise


class InfrastructureMonitoringService:
    """Service for monitoring component operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = InfrastructureMonitoringRepository(db)
        self.monitoring_infrastructure = get_monitoring_infrastructure()

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get overall monitoring status"""
        try:
            # Get status from repository
            repo_status = self.repository.get_monitoring_status()

            # Get status from monitoring infrastructure
            infra_status = self.monitoring_infrastructure.get_monitoring_status()

            # Merge statuses
            return {
                **repo_status,
                "infrastructure_status": infra_status,
            }
        except Exception as e:
            _logger.error(f"Error getting monitoring status: {e}")
            raise

    def record_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric"""
        try:
            # Use set_gauge which is available in EnhancedMetricsCollector
            self.monitoring_infrastructure.metrics_collector.set_gauge(
                metric_name, value, labels=labels or {}
            )
            _logger.info(f"Metric recorded: {metric_name} = {value}")
        except Exception as e:
            _logger.error(f"Error recording metric: {e}")
            raise


class InfrastructureService:
    """Main Infrastructure service that aggregates all sub-services"""

    def __init__(self, db: Session):
        self.db = db
        self.kafka = InfrastructureKafkaService(db)
        self.flink = InfrastructureFlinkService(db)
        self.storage = InfrastructureStorageService(db)
        self.config = InfrastructureConfigService(db)
        self.data_flow = InfrastructureDataFlowService(db)
        self.monitoring = InfrastructureMonitoringService(db)

    def get_health(self) -> Dict[str, Any]:
        """Get overall infrastructure health"""
        try:
            kafka_status = self.kafka.get_status()
            flink_jobs = self.flink.list_jobs()
            monitoring_status = self.monitoring.get_monitoring_status()

            return {
                "kafka": {
                    "connected": kafka_status.get("connected", False),
                    "total_messages": kafka_status.get("total_messages", 0),
                    "total_failed": kafka_status.get("total_failed", 0),
                },
                "flink": {
                    "total_jobs": len(flink_jobs),
                    "running_jobs": sum(1 for j in flink_jobs if j["status"] == "running"),
                },
                "monitoring": {
                    "total_components": monitoring_status.get("total_components", 0),
                    "healthy_components": monitoring_status.get("healthy_components", 0),
                    "overall_status": monitoring_status.get("overall_status", "unknown"),
                },
                "overall_status": (
                    "healthy"
                    if kafka_status.get("connected", False)
                    and monitoring_status.get("overall_status") == "healthy"
                    else "degraded"
                ),
            }
        except Exception as e:
            _logger.error(f"Error getting infrastructure health: {e}")
            return {
                "kafka": {"connected": False, "total_messages": 0, "total_failed": 0},
                "flink": {"total_jobs": 0, "running_jobs": 0},
                "monitoring": {"total_components": 0, "healthy_components": 0, "overall_status": "unknown"},
                "overall_status": "unhealthy",
                "error": str(e),
            }


def get_infrastructure_service(db: Session) -> InfrastructureService:
    """Get Infrastructure service instance"""
    return InfrastructureService(db)
