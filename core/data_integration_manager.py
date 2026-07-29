# -*- coding: utf-8 -*-
"""
Data Integration (Phase 4)
Enterprise-grade data integration with secure data management and privacy controls
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class DataType(Enum):
    """Data type for integration"""

    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    SEMI_STRUCTURED = "semi_structured"
    BINARY = "binary"


class DataSensitivity(Enum):
    """Data sensitivity level"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    CRITICAL = "critical"


class DataStatus(Enum):
    """Data status"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    QUARANTINED = "quarantined"


@dataclass
class DataSource:
    """Data source configuration"""

    source_id: str
    source_name: str
    source_type: str
    data_type: DataType
    endpoint: str
    sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    authentication: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataRecord:
    """Data record"""

    record_id: str
    source_id: str
    data_type: DataType
    sensitivity: DataSensitivity
    content: Dict[str, Any] = field(default_factory=dict)
    status: DataStatus = DataStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataPolicy:
    """Data policy configuration"""

    policy_id: str
    policy_name: str
    sensitivity: DataSensitivity
    retention_period: int = 365  # days
    encryption_required: bool = True
    access_logging: bool = True
    data_masking: bool = False
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataIntegrationManager:
    """Enterprise-grade data integration manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize data integration manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Data sources
        self.data_sources: Dict[str, DataSource] = {}
        self._initialize_default_sources()

        # Data records
        self.data_records: Dict[str, DataRecord] = {}

        # Data policies
        self.data_policies: Dict[str, DataPolicy] = {}
        self._initialize_default_policies()

        # Storage
        self.storage_dir = Path(self.config.get("storage_dir", "./data_integration"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Access handlers
        self.access_handlers: List[Callable] = []

        # Configuration
        self.max_records = self.config.get("max_records", 100000)
        self.auto_sync = self.config.get("auto_sync", True)
        self.sync_interval = self.config.get("sync_interval", 3600)

        # Statistics
        self.total_records = 0
        self.total_access = 0

        logger.info("Data integration manager initialized")

    def _initialize_default_sources(self):
        """Initialize default data sources"""
        # User data source
        self.data_sources["user_data"] = DataSource(
            source_id="user_data",
            source_name="User Data",
            source_type="database",
            data_type=DataType.STRUCTURED,
            endpoint="internal://user_db",
            sensitivity=DataSensitivity.CONFIDENTIAL,
            enabled=True,
        )

        # Log data source
        self.data_sources["log_data"] = DataSource(
            source_id="log_data",
            source_name="Application Logs",
            source_type="file",
            data_type=DataType.UNSTRUCTURED,
            endpoint="internal://log_files",
            sensitivity=DataSensitivity.INTERNAL,
            enabled=True,
        )

        # Metrics data source
        self.data_sources["metrics_data"] = DataSource(
            source_id="metrics_data",
            source_name="System Metrics",
            source_type="timeseries",
            data_type=DataType.STRUCTURED,
            endpoint="internal://metrics",
            sensitivity=DataSensitivity.INTERNAL,
            enabled=True,
        )

        # Configuration data source
        self.data_sources["config_data"] = DataSource(
            source_id="config_data",
            source_name="Configuration Data",
            source_type="file",
            data_type=DataType.STRUCTURED,
            endpoint="internal://config",
            sensitivity=DataSensitivity.RESTRICTED,
            enabled=True,
        )

        logger.info(f"Initialized {len(self.data_sources)} default data sources")

    def _initialize_default_policies(self):
        """Initialize default data policies"""
        # Public data policy
        self.data_policies["public_policy"] = DataPolicy(
            policy_id="public_policy",
            policy_name="Public Data Policy",
            sensitivity=DataSensitivity.PUBLIC,
            retention_period=365,
            encryption_required=False,
            access_logging=True,
            data_masking=False,
            enabled=True,
        )

        # Internal data policy
        self.data_policies["internal_policy"] = DataPolicy(
            policy_id="internal_policy",
            policy_name="Internal Data Policy",
            sensitivity=DataSensitivity.INTERNAL,
            retention_period=365,
            encryption_required=True,
            access_logging=True,
            data_masking=False,
            enabled=True,
        )

        # Confidential data policy
        self.data_policies["confidential_policy"] = DataPolicy(
            policy_id="confidential_policy",
            policy_name="Confidential Data Policy",
            sensitivity=DataSensitivity.CONFIDENTIAL,
            retention_period=2555,  # 7 years
            encryption_required=True,
            access_logging=True,
            data_masking=True,
            enabled=True,
        )

        # Restricted data policy
        self.data_policies["restricted_policy"] = DataPolicy(
            policy_id="restricted_policy",
            policy_name="Restricted Data Policy",
            sensitivity=DataSensitivity.RESTRICTED,
            retention_period=3650,  # 10 years
            encryption_required=True,
            access_logging=True,
            data_masking=True,
            enabled=True,
        )

        # Critical data policy
        self.data_policies["critical_policy"] = DataPolicy(
            policy_id="critical_policy",
            policy_name="Critical Data Policy",
            sensitivity=DataSensitivity.CRITICAL,
            retention_period=7300,  # 20 years
            encryption_required=True,
            access_logging=True,
            data_masking=True,
            enabled=True,
        )

        logger.info(f"Initialized {len(self.data_policies)} default data policies")

    def register_source(self, source: DataSource) -> None:
        """
        Register data source

        Args:
            source: Data source
        """
        self.data_sources[source.source_id] = source
        logger.info(f"Registered data source: {source.source_id}")

    def register_policy(self, policy: DataPolicy) -> None:
        """
        Register data policy

        Args:
            policy: Data policy
        """
        self.data_policies[policy.policy_id] = policy
        logger.info(f"Registered data policy: {policy.policy_id}")

    async def ingest_data(
        self, source_id: str, content: Dict[str, Any], sensitivity: Optional[DataSensitivity] = None
    ) -> str:
        """
        Ingest data from source

        Args:
            source_id: Source ID
            content: Data content
            sensitivity: Override sensitivity (optional)

        Returns:
            Record ID
        """
        if source_id not in self.data_sources:
            raise ValueError(f"Source not found: {source_id}")

        source = self.data_sources[source_id]

        # Use source sensitivity or override
        data_sensitivity = sensitivity or source.sensitivity

        # Apply data policy
        policy = self.data_policies.get(f"{data_sensitivity.value}_policy")

        if policy and policy.enabled:
            # Apply data masking if required
            if policy.data_masking:
                content = await self._apply_data_masking(content, data_sensitivity)

        record_id = f"record_{source_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

        record = DataRecord(
            record_id=record_id,
            source_id=source_id,
            data_type=source.data_type,
            sensitivity=data_sensitivity,
            content=content,
        )

        self.data_records[record_id] = record
        self.total_records += 1

        # Store record
        await self._store_record(record)

        logger.debug(f"Ingested data: {record_id}")

        return record_id

    async def _apply_data_masking(
        self, content: Dict[str, Any], sensitivity: DataSensitivity
    ) -> Dict[str, Any]:
        """
        Apply data masking

        Args:
            content: Data content
            sensitivity: Data sensitivity

        Returns:
            Masked content
        """
        # Simulate data masking
        # In real implementation, would apply actual masking rules
        masked_content = content.copy()

        if sensitivity in (
            DataSensitivity.CONFIDENTIAL,
            DataSensitivity.RESTRICTED,
            DataSensitivity.CRITICAL,
        ):
            # Mask sensitive fields
            for key in masked_content:
                if isinstance(masked_content[key], str):
                    if len(masked_content[key]) > 4:
                        masked_content[key] = (
                            masked_content[key][:2]
                            + "*" * (len(masked_content[key]) - 4)
                            + masked_content[key][-2:]
                        )

        return masked_content

    async def _store_record(self, record: DataRecord) -> None:
        """
        Store data record to persistent storage

        Args:
            record: Data record
        """
        record_path = (
            self.storage_dir / f"records_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        )

        record_dict = {
            "record_id": record.record_id,
            "source_id": record.source_id,
            "data_type": record.data_type.value,
            "sensitivity": record.sensitivity.value,
            "content": record.content,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

        with open(record_path, "a") as f:
            f.write(json.dumps(record_dict) + "\n")

        # Prune old records
        if len(self.data_records) > self.max_records:
            # Remove oldest records
            sorted_records = sorted(self.data_records.items(), key=lambda x: x[1].created_at)
            for i in range(len(sorted_records) - self.max_records):
                del self.data_records[sorted_records[i][0]]

    async def retrieve_data(
        self, record_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve data record

        Args:
            record_id: Record ID
            user_id: User ID for access logging

        Returns:
            Data record
        """
        if record_id not in self.data_records:
            return None

        record = self.data_records[record_id]

        # Update access tracking
        record.access_count += 1
        record.last_accessed = datetime.now(timezone.utc)
        self.total_access += 1

        # Log access if required by policy
        policy = self.data_policies.get(f"{record.sensitivity.value}_policy")
        if policy and policy.access_logging:
            await self._log_access(record, user_id)

        # Notify handlers
        await self._notify_access(record, user_id)

        return {
            "record_id": record.record_id,
            "source_id": record.source_id,
            "data_type": record.data_type.value,
            "sensitivity": record.sensitivity.value,
            "content": record.content,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "access_count": record.access_count,
            "last_accessed": record.last_accessed.isoformat() if record.last_accessed else None,
        }

    async def _log_access(self, record: DataRecord, user_id: Optional[str]) -> None:
        """
        Log data access

        Args:
            record: Data record
            user_id: User ID
        """
        # In real implementation, would log to audit system
        logger.debug(f"Data access logged: {record.record_id} by {user_id}")

    async def _notify_access(self, record: DataRecord, user_id: Optional[str]) -> None:
        """
        Notify about data access

        Args:
            record: Data record
            user_id: User ID
        """
        for handler in self.access_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(record, user_id)
                else:
                    handler(record, user_id)
            except Exception as e:
                logger.error(f"Access handler failed: {e}")

    def query_data(
        self,
        source_id: Optional[str] = None,
        sensitivity: Optional[DataSensitivity] = None,
        status: Optional[DataStatus] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query data records

        Args:
            source_id: Filter by source ID
            sensitivity: Filter by sensitivity
            status: Filter by status
            limit: Maximum number of records

        Returns:
            Query results
        """
        records = list(self.data_records.values())

        if source_id:
            records = [r for r in records if r.source_id == source_id]
        if sensitivity:
            records = [r for r in records if r.sensitivity == sensitivity]
        if status:
            records = [r for r in records if r.status == status]

        records = records[-limit:]

        return [
            {
                "record_id": r.record_id,
                "source_id": r.source_id,
                "data_type": r.data_type.value,
                "sensitivity": r.sensitivity.value,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "access_count": r.access_count,
            }
            for r in records
        ]

    async def sync_data(self, source_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync data from sources

        Args:
            source_id: Specific source ID (optional)

        Returns:
            Sync results
        """
        sync_results: Dict[str, Any] = {
            "sync_id": f"sync_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "sources": {},
            "total_records_synced": 0,
        }

        # Determine which sources to sync
        sources_to_sync = []
        if source_id:
            if source_id in self.data_sources:
                sources_to_sync.append(self.data_sources[source_id])
        else:
            sources_to_sync = [s for s in self.data_sources.values() if s.enabled]

        # Sync from each source
        for source in sources_to_sync:
            source_result = await self._sync_from_source(source)
            sync_results["sources"][source.source_id] = source_result
            sync_results["total_records_synced"] += source_result.get("records_synced", 0)

        sync_results["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Completed data sync: {sync_results['sync_id']}")

        return sync_results

    async def _sync_from_source(self, source: DataSource) -> Dict[str, Any]:
        """
        Sync from specific source

        Args:
            source: Data source

        Returns:
            Source sync results
        """
        try:
            # Simulate sync from source
            # In real implementation, would connect to actual data source
            await asyncio.sleep(1)

            # Simulate some records
            import random

            num_records = random.randint(0, 20)  # nosec B311

            for i in range(num_records):
                await self.ingest_data(
                    source.source_id,
                    {
                        "data": f"sample_data_{i}",
                        "value": random.randint(1, 100),  # nosec B311
                    },  # nosec B311  # noqa: E501
                )

            return {
                "source_id": source.source_id,
                "status": "success",
                "records_synced": num_records,
            }

        except Exception as e:
            logger.error(f"Sync failed for source {source.source_id}: {e}")
            return {
                "source_id": source.source_id,
                "status": "error",
                "error": str(e),
                "records_synced": 0,
            }

    async def start_auto_sync(self) -> None:
        """Start automatic data sync loop"""
        if not self.auto_sync:
            return

        async def sync_loop():
            while True:
                try:
                    await self.sync_data()
                    await asyncio.sleep(self.sync_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto sync loop error: {e}")
                    await asyncio.sleep(self.sync_interval)

        asyncio.create_task(sync_loop())
        logger.info("Auto data sync loop started")

    def register_access_handler(self, handler: Callable) -> None:
        """
        Register access handler

        Args:
            handler: Handler function
        """
        self.access_handlers.append(handler)
        logger.info("Registered data access handler")

    def get_statistics(self) -> Dict[str, Any]:
        """Get data integration statistics"""
        return {
            "total_sources": len(self.data_sources),
            "enabled_sources": len([s for s in self.data_sources.values() if s.enabled]),
            "total_policies": len(self.data_policies),
            "enabled_policies": len([p for p in self.data_policies.values() if p.enabled]),
            "total_records": self.total_records,
            "total_access": self.total_access,
            "record_retention_limit": self.max_records,
        }


def get_data_integration_manager(config: Optional[Dict[str, Any]] = None) -> DataIntegrationManager:
    """
    Factory function to get data integration manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        DataIntegrationManager: Manager instance
    """
    return DataIntegrationManager(config)
