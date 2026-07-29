# -*- coding: utf-8 -*-
"""
ClickHouse Storage Implementation for AIOps Platform
Provides high-performance columnar storage with S3 tiering for cold data
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.observability_query import (
    DEFAULT_MAX_LLM_ITEMS,
    QueryCache,
    build_clickhouse_query,
    cached_query,
    make_cache_key,
    validate_clickhouse_identifier,
    validate_clickhouse_metric_name,
    with_query_timeout,
)

logger = logging.getLogger(__name__)


@dataclass
class StorageTier:
    """Represents a storage tier"""

    name: str
    retention_days: int
    s3_enabled: bool
    s3_bucket: Optional[str] = None
    s3_path: Optional[str] = None


class ClickHouseStorage:
    """
    ClickHouse Storage with S3 Tiering

    Provides:
    - High-performance columnar storage for time-series and analytics data
    - Automatic data tiering to S3 for cold data
    - Multi-tier retention policies
    - Efficient compression and query performance
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ClickHouse Storage

        Args:
            config: Configuration dictionary containing:
                - host: ClickHouse host (default: localhost)
                - port: ClickHouse port (default: 8123)
                - database: Database name (default: aiops)
                - user: Username (default: default)
                - password: Password (default: "")
                - s3_enabled: Enable S3 tiering (default: false)
                - s3_bucket: S3 bucket name
                - s3_endpoint: S3 endpoint URL
                - aws_access_key: AWS access key
                - aws_secret_key: AWS secret key
        """
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8123)
        self.database = self.config.get("database", "aiops")
        self.user = self.config.get("user", "default")
        self.password = self.config.get("password", "")
        self.s3_enabled = self.config.get("s3_enabled", False)
        self.s3_bucket = self.config.get("s3_bucket")
        self.s3_endpoint = self.config.get("s3_endpoint", "https://s3.amazonaws.com")
        self.aws_access_key = self.config.get("aws_access_key")
        self.aws_secret_key = self.config.get("aws_secret_key")
        self.read_only = self.config.get("read_only")
        self.max_query_rows = self.config.get("max_query_rows", DEFAULT_MAX_LLM_ITEMS)

        if self.read_only is None:
            logger.warning(
                "ClickHouse storage created without explicit read_only flag; "
                "set read_only=True in production to enforce read-only credentials."
            )

        self._is_initialized = False
        self._is_connected = False
        self._query_cache = QueryCache()

        # Storage tiers
        self._tiers = {
            "hot": StorageTier(name="hot", retention_days=7, s3_enabled=False),
            "warm": StorageTier(
                name="warm",
                retention_days=30,
                s3_enabled=True,
                s3_bucket=self.s3_bucket,
                s3_path="warm",
            ),
            "cold": StorageTier(
                name="cold",
                retention_days=365,
                s3_enabled=True,
                s3_bucket=self.s3_bucket,
                s3_path="cold",
            ),
        }

        logger.info("ClickHouse Storage initialized")

    def initialize(self) -> bool:
        """
        Initialize ClickHouse storage

        Returns:
            True if initialization successful
        """
        try:
            # Create database
            self._create_database()

            # Create tables with tiering
            self._create_tables()

            # Configure S3 if enabled
            if self.s3_enabled:
                self._configure_s3()

            self._is_initialized = True
            self._is_connected = True
            logger.info("ClickHouse Storage initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse storage: {e}")  # noqa: F541
            return False

    def _create_database(self) -> None:
        """Create database if not exists"""
        query = f"CREATE DATABASE IF NOT EXISTS {self.database}"  # noqa: F541
        self._execute_query(query)
        logger.info(f"Created database: {self.database}")  # noqa: F541

    def _create_tables(self) -> None:
        """Create tables with tiering configuration"""
        # Metrics table
        metrics_table = f"""  # noqa: F541
        CREATE TABLE IF NOT EXISTS {self.database}.metrics (
            timestamp DateTime,
            metric_name String,
            metric_value Float64,
            labels Map(String, String),
            tier String DEFAULT 'hot'
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (metric_name, timestamp)
        TTL timestamp + INTERVAL 7 DAY TO DISK 'default',
            timestamp + INTERVAL 30 DAY TO VOLUME 's3_warm',
            timestamp + INTERVAL 365 DAY TO VOLUME 's3_cold'
        SETTINGS storage_policy = 'tiering_policy'
        """
        self._execute_query(metrics_table)

        # Anomalies table
        anomalies_table = f"""  # noqa: F541
        CREATE TABLE IF NOT EXISTS {self.database}.anomalies (
            timestamp DateTime,
            anomaly_id String,
            service String,
            severity String,
            description String,
            metadata String,
            tier String DEFAULT 'hot'
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (service, timestamp)
        TTL timestamp + INTERVAL 7 DAY TO DISK 'default',
            timestamp + INTERVAL 30 DAY TO VOLUME 's3_warm',
            timestamp + INTERVAL 365 DAY TO VOLUME 's3_cold'
        SETTINGS storage_policy = 'tiering_policy'
        """
        self._execute_query(anomalies_table)

        # Events table
        events_table = f"""  # noqa: F541
        CREATE TABLE IF NOT EXISTS {self.database}.events (
            timestamp DateTime,
            event_type String,
            source String,
            data String,
            tier String DEFAULT 'hot'
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (event_type, timestamp)
        TTL timestamp + INTERVAL 7 DAY TO DISK 'default',
            timestamp + INTERVAL 30 DAY TO VOLUME 's3_warm',
            timestamp + INTERVAL 365 DAY TO VOLUME 's3_cold'
        SETTINGS storage_policy = 'tiering_policy'
        """
        self._execute_query(events_table)

        logger.info("Created tables with tiering configuration")

    def _configure_s3(self) -> None:
        """Configure S3 storage volumes"""
        # Create storage policy with tiering
        storage_policy = f"""  # noqa: F541
        CREATE OR REPLACE STORAGE POLICY tiering_policy
        VOLUMES
            default
            s3_warm
            s3_cold
        """
        self._execute_query(storage_policy)

        # Create S3 volume configurations
        s3_warm_volume = f"""  # noqa: F541
        CREATE OR REPLACE VOLUME s3_warm
        STORAGE(
            type = 's3',
            url = '{self.s3_endpoint}/{self.s3_bucket}/warm/',
            access_key_id = '{self.aws_access_key}',
            secret_access_key = '{self.aws_secret_key}'
        )
        """
        self._execute_query(s3_warm_volume)

        s3_cold_volume = f"""  # noqa: F541
        CREATE OR REPLACE VOLUME s3_cold
        STORAGE(
            type = 's3',
            url = '{self.s3_endpoint}/{self.s3_bucket}/cold/',
            access_key_id = '{self.aws_access_key}',
            secret_access_key = '{self.aws_secret_key}'
        )
        """
        self._execute_query(s3_cold_volume)

        logger.info("Configured S3 storage volumes")

    def _execute_query(self, query: str, params: Optional[List[Any]] = None) -> None:
        """
        Execute ClickHouse query

        Args:
            query: SQL query
            params: Optional parameter values for the query
        """
        # This would use ClickHouse client
        # default_value implementation
        logger.debug(f"Executing query: {query[:100]}... params={params!r:50}")  # noqa: F541

    async def store_metric(
        self,
        metric_name: str,
        metric_value: float,
        labels: Dict[str, str],
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Store metric data

        Args:
            metric_name: Metric name
            metric_value: Metric value
            labels: Metric labels
            timestamp: Optional timestamp

        Returns:
            True if successful
        """
        if self.read_only is True:
            logger.warning("ClickHouse write rejected: storage is configured as read_only")
            return False

        try:
            if not self._is_initialized:
                raise RuntimeError("ClickHouse storage not initialized")

            validate_clickhouse_metric_name(metric_name)
            ts = timestamp or datetime.now()
            labels_json = json.dumps(labels)

            query = f"""  # noqa: F541
            INSERT INTO {self.database}.metrics
            (timestamp, metric_name, metric_value, labels)
            VALUES (?, ?, ?, ?)
            """

            self._execute_query(query, params=[ts, metric_name, metric_value, labels_json])
            logger.debug(f"Stored metric: {metric_name}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to store metric: {e}")  # noqa: F541
            return False

    async def store_anomaly(
        self,
        anomaly_id: str,
        service: str,
        severity: str,
        description: str,
        metadata: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Store anomaly data

        Args:
            anomaly_id: Anomaly ID
            service: Service name
            severity: Severity level
            description: Description
            metadata: Metadata dictionary
            timestamp: Optional timestamp

        Returns:
            True if successful
        """
        try:
            if not self._is_initialized:
                raise RuntimeError("ClickHouse storage not initialized")

            if self.read_only is True:
                logger.warning("ClickHouse write rejected: storage is configured as read_only")
                return False

            ts = timestamp or datetime.now()
            metadata_json = json.dumps(metadata)

            query = f"""  # noqa: F541
            INSERT INTO {self.database}.anomalies
            (timestamp, anomaly_id, service, severity, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """

            self._execute_query(
                query,
                params=[ts, anomaly_id, service, severity, description, metadata_json],
            )
            logger.debug(f"Stored anomaly: {anomaly_id}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to store anomaly: {e}")  # noqa: F541
            return False

    async def store_event(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Store event data

        Args:
            event_type: Event type
            source: Event source
            data: Event data
            timestamp: Optional timestamp

        Returns:
            True if successful
        """
        if self.read_only is True:
            logger.warning("ClickHouse write rejected: storage is configured as read_only")
            return False

        try:
            if not self._is_initialized:
                raise RuntimeError("ClickHouse storage not initialized")

            ts = timestamp or datetime.now()
            data_json = json.dumps(data)

            query = f"""  # noqa: F541
            INSERT INTO {self.database}.events
            (timestamp, event_type, source, data)
            VALUES (?, ?, ?, ?)
            """

            self._execute_query(query, params=[ts, event_type, source, data_json])
            logger.debug(f"Stored event: {event_type}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to store event: {e}")  # noqa: F541
            return False

    async def query_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query metrics data

        Args:
            metric_name: Metric name
            start_time: Start time
            end_time: End time
            filters: Optional label filters

        Returns:
            List of metric data points
        """
        try:
            if not self._is_initialized:
                raise RuntimeError("ClickHouse storage not initialized")

            validate_clickhouse_metric_name(metric_name)
            validate_clickhouse_identifier("metrics")
            validate_clickhouse_identifier("metric_name")
            validate_clickhouse_identifier("timestamp")

            columns = ["timestamp", "metric_name", "metric_value", "labels"]
            where_columns = ["metric_name", "timestamp", "timestamp"]
            where_values: List[Any] = [metric_name, start_time, end_time]

            # Additional filters with validated key names (values parameterized)
            extra_clauses: List[str] = []
            if filters:
                for key, value in filters.items():
                    validate_clickhouse_identifier(key)
                    extra_clauses.append(f" AND labels['{key}'] = ?")
                    where_values.append(value)

            sql, params = build_clickhouse_query(
                table="metrics",
                columns=columns,
                where_columns=where_columns,
                where_values=where_values,
                order_by="timestamp",
                limit=self.max_query_rows,
            )
            # Prepend database to table in a safe way (validated identifiers)
            validate_clickhouse_identifier(self.database)
            sql = sql.replace("FROM metrics", f"FROM {self.database}.metrics", 1)
            if extra_clauses:
                for clause in extra_clauses:
                    sql = sql.replace(" ORDER BY", f"{clause} ORDER BY", 1)

            cache_key = make_cache_key(
                "clickhouse_metrics",
                self.database,
                metric_name,
                start_time,
                end_time,
                filters,
                self.max_query_rows,
            )

            def _run():
                logger.debug(f"Querying metrics: {metric_name}")  # noqa: F541
                self._execute_query(sql, params=params)
                return []

            return await cached_query(self._query_cache, cache_key, with_query_timeout(_run()))

        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")  # noqa: F541
            return []

    async def query_anomalies(
        self,
        start_time: datetime,
        end_time: datetime,
        service: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query anomalies data

        Args:
            start_time: Start time
            end_time: End time
            service: Optional service filter
            severity: Optional severity filter

        Returns:
            List of anomaly data points
        """
        try:
            if not self._is_initialized:
                raise RuntimeError("ClickHouse storage not initialized")

            columns = ["timestamp", "anomaly_id", "service", "severity", "description", "metadata"]
            where_columns = ["timestamp", "timestamp"]
            where_values: List[Any] = [start_time, end_time]

            if service:
                validate_clickhouse_identifier("service")
                where_columns.append("service")
                where_values.append(service)
            if severity:
                validate_clickhouse_identifier("severity")
                where_columns.append("severity")
                where_values.append(severity)

            sql, params = build_clickhouse_query(
                table="anomalies",
                columns=columns,
                where_columns=where_columns,
                where_values=where_values,
                order_by="timestamp",
                limit=self.max_query_rows,
            )
            validate_clickhouse_identifier(self.database)
            sql = sql.replace("FROM anomalies", f"FROM {self.database}.anomalies", 1)

            cache_key = make_cache_key(
                "clickhouse_anomalies",
                self.database,
                start_time,
                end_time,
                service,
                severity,
                self.max_query_rows,
            )

            def _run():
                logger.debug("Querying anomalies")
                self._execute_query(sql, params=params)
                return []

            return await cached_query(self._query_cache, cache_key, with_query_timeout(_run()))

        except Exception as e:
            logger.error(f"Failed to query anomalies: {e}")  # noqa: F541
            return []

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Storage statistics dictionary
        """
        try:
            stats = {"database": self.database, "s3_enabled": self.s3_enabled, "tiers": {}}

            for tier_name, tier in self._tiers.items():
                stats["tiers"][tier_name] = {
                    "retention_days": tier.retention_days,
                    "s3_enabled": tier.s3_enabled,
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")  # noqa: F541
            return {}

    async def move_to_tier(self, table: str, tier: str, before_date: datetime) -> int:
        """
        Move data to a specific storage tier

        Args:
            table: Table name
            tier: Target tier
            before_date: Move data before this date

        Returns:
            Number of rows moved
        """
        if self.read_only is True:
            logger.warning("ClickHouse write rejected: storage is configured as read_only")
            return 0

        try:
            if not self._is_initialized:
                raise RuntimeError("ClickHouse storage not initialized")

            validate_clickhouse_identifier(table)
            validate_clickhouse_identifier(tier)

            query = f"""  # noqa: F541
            ALTER TABLE {self.database}.{table}
            UPDATE tier = ?
            WHERE timestamp < ?
            """

            self._execute_query(query, params=[tier, before_date])
            logger.info(f"Moved data to {tier} tier in table {table}")  # noqa: F541

            # This would return actual count
            return 0

        except Exception as e:
            logger.error(f"Failed to move data to tier: {e}")  # noqa: F541
            return 0

    def close(self) -> None:
        """Close ClickHouse storage"""
        self._is_connected = False
        logger.info("ClickHouse Storage closed")


def create_clickhouse_storage(
    config: Optional[Dict[str, Any]] = None,
) -> Optional[ClickHouseStorage]:
    """
    Factory function to create ClickHouse Storage

    Args:
        config: Configuration dictionary

    Returns:
        ClickHouseStorage instance or None if failed
    """
    try:
        storage = ClickHouseStorage(config)
        if storage.initialize():
            return storage
        return None
    except Exception as e:
        logger.error(f"Failed to create ClickHouse storage: {e}")  # noqa: F541
        return None
