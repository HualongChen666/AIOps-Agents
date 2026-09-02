# -*- coding: utf-8 -*-
"""
Infrastructure Repository Layer

Provides database persistence operations for Infrastructure components:
- Kafka message tracking
- Flink job management
- Storage configuration
- Configuration center
- Data flow tracking
- Monitoring components
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from core.models import (
    InfrastructureConfigDB,
    InfrastructureDataFlowDB,
    InfrastructureFlinkJobDB,
    InfrastructureKafkaMessageDB,
    InfrastructureMonitoringDB,
    InfrastructureStorageDB,
)

_logger = logging.getLogger(__name__)


class InfrastructureKafkaMessageRepository:
    """Repository for Kafka message operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_message(
        self,
        topic: str,
        key: str,
        value: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        status: str = "sent",
    ) -> InfrastructureKafkaMessageDB:
        """Create a new Kafka message record"""
        message = InfrastructureKafkaMessageDB(
            topic=topic,
            key=key,
            value=value,
            headers=headers,
            status=status,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        _logger.info(f"Created Kafka message record: {message.id} for topic: {topic}")
        return message

    def get_message_by_id(self, message_id: int) -> Optional[InfrastructureKafkaMessageDB]:
        """Get a message by ID"""
        return self.db.query(InfrastructureKafkaMessageDB).filter(
            InfrastructureKafkaMessageDB.id == message_id
        ).first()

    def get_messages_by_topic(
        self, topic: str, limit: int = 100, status: Optional[str] = None
    ) -> List[InfrastructureKafkaMessageDB]:
        """Get messages by topic"""
        query = self.db.query(InfrastructureKafkaMessageDB).filter(
            InfrastructureKafkaMessageDB.topic == topic
        )
        if status:
            query = query.filter(InfrastructureKafkaMessageDB.status == status)
        return query.order_by(InfrastructureKafkaMessageDB.sent_at.desc()).limit(limit).all()

    def get_all_topics(self) -> List[str]:
        """Get all unique topics"""
        topics = (
            self.db.query(InfrastructureKafkaMessageDB.topic)
            .distinct()
            .order_by(InfrastructureKafkaMessageDB.topic)
            .all()
        )
        return [topic[0] for topic in topics]

    def update_message_status(
        self, message_id: int, status: str, error_message: Optional[str] = None
    ) -> bool:
        """Update message status"""
        message = self.get_message_by_id(message_id)
        if not message:
            return False
        message.status = status
        if error_message:
            message.error_message = error_message
        self.db.commit()
        _logger.info(f"Updated Kafka message {message_id} status to: {status}")
        return True

    def count_messages_by_status(self, status: str) -> int:
        """Count messages by status"""
        return (
            self.db.query(InfrastructureKafkaMessageDB)
            .filter(InfrastructureKafkaMessageDB.status == status)
            .count()
        )


class InfrastructureFlinkJobRepository:
    """Repository for Flink job operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        job_name: str,
        job_type: str,
        parallelism: int = 2,
        config: Optional[Dict[str, Any]] = None,
    ) -> InfrastructureFlinkJobDB:
        """Create a new Flink job"""
        job = InfrastructureFlinkJobDB(
            id=str(uuid4()),
            job_name=job_name,
            job_type=job_type,
            parallelism=parallelism,
            config=config or {},
            status="created",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        _logger.info(f"Created Flink job: {job.id} with name: {job_name}")
        return job

    def get_job_by_id(self, job_id: str) -> Optional[InfrastructureFlinkJobDB]:
        """Get a job by ID"""
        return self.db.query(InfrastructureFlinkJobDB).filter(
            InfrastructureFlinkJobDB.id == job_id
        ).first()

    def get_job_by_name(self, job_name: str) -> Optional[InfrastructureFlinkJobDB]:
        """Get a job by name"""
        return self.db.query(InfrastructureFlinkJobDB).filter(
            InfrastructureFlinkJobDB.job_name == job_name
        ).first()

    def list_jobs(
        self, status: Optional[str] = None, job_type: Optional[str] = None, limit: int = 100
    ) -> List[InfrastructureFlinkJobDB]:
        """List jobs with optional filters"""
        query = self.db.query(InfrastructureFlinkJobDB)
        if status:
            query = query.filter(InfrastructureFlinkJobDB.status == status)
        if job_type:
            query = query.filter(InfrastructureFlinkJobDB.job_type == job_type)
        return query.order_by(InfrastructureFlinkJobDB.created_at.desc()).limit(limit).all()

    def update_job_status(
        self, job_id: str, status: str, error_message: Optional[str] = None
    ) -> bool:
        """Update job status"""
        job = self.get_job_by_id(job_id)
        if not job:
            return False
        job.status = status
        if error_message:
            job.error_message = error_message
        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        if status in ("stopped", "failed") and not job.stopped_at:
            job.stopped_at = datetime.utcnow()
        self.db.commit()
        _logger.info(f"Updated Flink job {job_id} status to: {status}")
        return True

    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        job = self.get_job_by_id(job_id)
        if not job:
            return False
        self.db.delete(job)
        self.db.commit()
        _logger.info(f"Deleted Flink job: {job_id}")
        return True


class InfrastructureStorageRepository:
    """Repository for storage configuration operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_storage(
        self,
        storage_type: str,
        endpoint: str,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> InfrastructureStorageDB:
        """Create a new storage configuration"""
        storage = InfrastructureStorageDB(
            id=str(uuid4()),
            storage_type=storage_type,
            endpoint=endpoint,
            bucket_name=bucket_name,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            config=config or {},
            status="active",
        )
        self.db.add(storage)
        self.db.commit()
        self.db.refresh(storage)
        _logger.info(f"Created storage configuration: {storage.id} of type: {storage_type}")
        return storage

    def get_storage_by_id(self, storage_id: str) -> Optional[InfrastructureStorageDB]:
        """Get storage by ID"""
        return self.db.query(InfrastructureStorageDB).filter(
            InfrastructureStorageDB.id == storage_id
        ).first()

    def list_storages(
        self, storage_type: Optional[str] = None, status: Optional[str] = None
    ) -> List[InfrastructureStorageDB]:
        """List storages with optional filters"""
        query = self.db.query(InfrastructureStorageDB)
        if storage_type:
            query = query.filter(InfrastructureStorageDB.storage_type == storage_type)
        if status:
            query = query.filter(InfrastructureStorageDB.status == status)
        return query.order_by(InfrastructureStorageDB.created_at.desc()).all()

    def update_health_status(
        self, storage_id: str, health_status: str
    ) -> bool:
        """Update storage health status"""
        storage = self.get_storage_by_id(storage_id)
        if not storage:
            return False
        storage.health_status = health_status
        storage.last_health_check = datetime.utcnow()
        self.db.commit()
        _logger.info(f"Updated storage {storage_id} health status to: {health_status}")
        return True

    def get_read_connection_info(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Get read connection info for storage"""
        storage = self.get_storage_by_id(storage_id)
        if not storage:
            return None
        return {
            "id": storage.id,
            "storage_type": storage.storage_type,
            "endpoint": storage.endpoint,
            "bucket_name": storage.bucket_name,
            "region": storage.region,
            "status": storage.status,
        }

    def get_write_connection_info(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Get write connection info for storage"""
        storage = self.get_storage_by_id(storage_id)
        if not storage:
            return None
        return {
            "id": storage.id,
            "storage_type": storage.storage_type,
            "endpoint": storage.endpoint,
            "bucket_name": storage.bucket_name,
            "access_key": storage.access_key,
            "region": storage.region,
            "status": storage.status,
        }

    def health_check(self, storage_id: str) -> Dict[str, Any]:
        """Perform health check on storage"""
        storage = self.get_storage_by_id(storage_id)
        if not storage:
            return {"status": "error", "message": "Storage not found"}
        # In production, this would perform actual connectivity checks
        return {
            "status": storage.health_status,
            "last_check": storage.last_health_check.isoformat() if storage.last_health_check else None,
            "storage_type": storage.storage_type,
            "endpoint": storage.endpoint,
        }


class InfrastructureConfigRepository:
    """Repository for configuration center operations"""

    def __init__(self, db: Session):
        self.db = db

    def set_config(
        self,
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
        category: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> InfrastructureConfigDB:
        """Set a configuration value"""
        existing = self.get_config_by_key(key)
        if existing:
            existing.value = value
            existing.version += 1
            existing.config_metadata = metadata  # Use config_metadata instead of metadata
            existing.category = category
            existing.updated_by = updated_by
            self.db.commit()
            self.db.refresh(existing)
            _logger.info(f"Updated config key: {key} to version: {existing.version}")
            return existing
        else:
            config = InfrastructureConfigDB(
                key=key,
                value=value,
                version=1,
                config_metadata=metadata or {},  # Use config_metadata instead of metadata
                category=category,
                updated_by=updated_by,
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            _logger.info(f"Created config key: {key} with version: 1")
            return config

    def get_config_by_key(self, key: str) -> Optional[InfrastructureConfigDB]:
        """Get configuration by key"""
        return self.db.query(InfrastructureConfigDB).filter(
            InfrastructureConfigDB.key == key
        ).first()

    def get_all_configs(self, category: Optional[str] = None) -> List[InfrastructureConfigDB]:
        """Get all configurations"""
        query = self.db.query(InfrastructureConfigDB)
        if category:
            query = query.filter(InfrastructureConfigDB.category == category)
        return query.order_by(InfrastructureConfigDB.key).all()

    def delete_config(self, key: str) -> bool:
        """Delete a configuration"""
        config = self.get_config_by_key(key)
        if not config:
            return False
        self.db.delete(config)
        self.db.commit()
        _logger.info(f"Deleted config key: {key}")
        return True


class InfrastructureDataFlowRepository:
    """Repository for data flow operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_flow(
        self,
        flow_name: str,
        flow_type: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> InfrastructureDataFlowDB:
        """Create a new data flow"""
        flow = InfrastructureDataFlowDB(
            id=str(uuid4()),
            flow_name=flow_name,
            flow_type=flow_type,
            config=config or {},
            status="stopped",
        )
        self.db.add(flow)
        self.db.commit()
        self.db.refresh(flow)
        _logger.info(f"Created data flow: {flow.id} with name: {flow_name}")
        return flow

    def get_flow_by_id(self, flow_id: str) -> Optional[InfrastructureDataFlowDB]:
        """Get flow by ID"""
        return self.db.query(InfrastructureDataFlowDB).filter(
            InfrastructureDataFlowDB.id == flow_id
        ).first()

    def get_flow_by_name(self, flow_name: str) -> Optional[InfrastructureDataFlowDB]:
        """Get flow by name"""
        return self.db.query(InfrastructureDataFlowDB).filter(
            InfrastructureDataFlowDB.flow_name == flow_name
        ).first()

    def update_flow_stats(
        self,
        flow_id: str,
        total_processed: int,
        total_analyzed: int,
        total_errors: int,
        avg_processing_time_ms: float,
    ) -> bool:
        """Update flow statistics"""
        flow = self.get_flow_by_id(flow_id)
        if not flow:
            return False
        flow.total_processed = total_processed
        flow.total_analyzed = total_analyzed
        flow.total_errors = total_errors
        flow.avg_processing_time_ms = avg_processing_time_ms
        self.db.commit()
        return True

    def start_flow(self, flow_id: str) -> bool:
        """Start a data flow"""
        flow = self.get_flow_by_id(flow_id)
        if not flow:
            return False
        flow.status = "running"
        flow.started_at = datetime.utcnow()
        self.db.commit()
        _logger.info(f"Started data flow: {flow_id}")
        return True

    def stop_flow(self, flow_id: str) -> bool:
        """Stop a data flow"""
        flow = self.get_flow_by_id(flow_id)
        if not flow:
            return False
        flow.status = "stopped"
        flow.stopped_at = datetime.utcnow()
        self.db.commit()
        _logger.info(f"Stopped data flow: {flow_id}")
        return True

    def get_data_flow_stats(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get data flow statistics"""
        flow = self.get_flow_by_id(flow_id)
        if not flow:
            return None
        return {
            "flow_id": flow.id,
            "flow_name": flow.flow_name,
            "flow_type": flow.flow_type,
            "status": flow.status,
            "total_processed": flow.total_processed,
            "total_analyzed": flow.total_analyzed,
            "total_errors": flow.total_errors,
            "avg_processing_time_ms": flow.avg_processing_time_ms,
            "error_rate": (
                flow.total_errors / flow.total_processed if flow.total_processed > 0 else 0.0
            ),
            "analysis_rate": (
                flow.total_analyzed / flow.total_processed if flow.total_processed > 0 else 0.0
            ),
        }


class InfrastructureMonitoringRepository:
    """Repository for monitoring component operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_component(
        self,
        component_name: str,
        component_type: str,
        endpoint: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> InfrastructureMonitoringDB:
        """Create a new monitoring component"""
        component = InfrastructureMonitoringDB(
            id=str(uuid4()),
            component_name=component_name,
            component_type=component_type,
            endpoint=endpoint,
            config=config or {},
            status="active",
        )
        self.db.add(component)
        self.db.commit()
        self.db.refresh(component)
        _logger.info(f"Created monitoring component: {component.id} with name: {component_name}")
        return component

    def get_component_by_id(self, component_id: str) -> Optional[InfrastructureMonitoringDB]:
        """Get component by ID"""
        return self.db.query(InfrastructureMonitoringDB).filter(
            InfrastructureMonitoringDB.id == component_id
        ).first()

    def get_component_by_name(self, component_name: str) -> Optional[InfrastructureMonitoringDB]:
        """Get component by name"""
        return self.db.query(InfrastructureMonitoringDB).filter(
            InfrastructureMonitoringDB.component_name == component_name
        ).first()

    def list_components(
        self, component_type: Optional[str] = None, status: Optional[str] = None
    ) -> List[InfrastructureMonitoringDB]:
        """List components with optional filters"""
        query = self.db.query(InfrastructureMonitoringDB)
        if component_type:
            query = query.filter(InfrastructureMonitoringDB.component_type == component_type)
        if status:
            query = query.filter(InfrastructureMonitoringDB.status == status)
        return query.order_by(InfrastructureMonitoringDB.created_at.desc()).all()

    def update_health_status(
        self, component_id: str, health_status: str
    ) -> bool:
        """Update component health status"""
        component = self.get_component_by_id(component_id)
        if not component:
            return False
        component.health_status = health_status
        component.last_health_check = datetime.utcnow()
        self.db.commit()
        _logger.info(f"Updated component {component_id} health status to: {health_status}")
        return True

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get overall monitoring status"""
        components = self.list_components()
        total = len(components)
        healthy = sum(1 for c in components if c.health_status == "healthy")
        unhealthy = sum(1 for c in components if c.health_status == "unhealthy")
        unknown = total - healthy - unhealthy

        return {
            "total_components": total,
            "healthy_components": healthy,
            "unhealthy_components": unhealthy,
            "unknown_components": unknown,
            "overall_status": "healthy" if unhealthy == 0 else "degraded" if healthy > 0 else "unhealthy",
            "components": [
                {
                    "id": c.id,
                    "name": c.component_name,
                    "type": c.component_type,
                    "status": c.status,
                    "health_status": c.health_status,
                    "last_health_check": c.last_health_check.isoformat() if c.last_health_check else None,
                }
                for c in components
            ],
        }
