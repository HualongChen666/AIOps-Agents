# -*- coding: utf-8 -*-
"""
Log Router for AIOps Platform
Routes logs from various sources to Loki and other destinations
Supports Fluent-Bit integration and log forwarding
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

from config import DEFAULT_LOG_HOST, ELASTICSEARCH_URL, KAFKA_BROKERS, LOKI_URL

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogDestination(Enum):
    """Log destination enumeration"""

    LOKI = "loki"
    ELASTICSEARCH = "elasticsearch"
    KAFKA = "kafka"
    S3 = "s3"


@dataclass
class LogEntry:
    """Represents a log entry"""

    timestamp: datetime
    level: LogLevel
    message: str
    service: str
    host: str
    environment: str
    labels: Dict[str, str]
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization.

        Converts datetime to ISO format string and enum to value for
        API response compatibility.
        """
        log_dict = asdict(self)
        log_dict["timestamp"] = self.timestamp.isoformat()
        log_dict["level"] = self.level.value
        return log_dict

    def to_loki_format(self) -> Dict[str, Any]:
        """Convert log entry to Loki format"""
        return {
            "streams": [
                {
                    "stream": {
                        "service": self.service,
                        "host": self.host,
                        "environment": self.environment,
                        "level": self.level.value,
                        **self.labels,
                    },
                    "values": [[str(int(self.timestamp.timestamp() * 1e9)), self.message]],
                }
            ]
        }


class LogRouter:
    """
    Log Router for forwarding logs to various destinations.

    Primary destination: Loki for log aggregation.
    Secondary destinations: Elasticsearch, Kafka, S3 (optional).

    Args:
        config: Configuration dictionary containing destination settings.
                Expected keys: 'destinations', 'loki_url', 'elasticsearch_url',
                              'kafka_brokers', 's3_bucket'

    Attributes:
        config: Original configuration dictionary
        destinations: List of enabled log destinations
        loki_url: Loki endpoint URL
        elasticsearch_url: Elasticsearch endpoint URL
        kafka_brokers: Kafka broker addresses
        s3_bucket: S3 bucket name for log storage
        session: aiohttp.ClientSession for HTTP requests
        enabled: Whether the router is active

    Raises:
        ValueError: If configuration is invalid
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Log Router

        Args:
            config: Configuration dictionary containing destination settings
        """
        self.config = config
        self.destinations = config.get("destinations", [])
        self.loki_url = config.get("loki_url", LOKI_URL)
        self.elasticsearch_url = config.get("elasticsearch_url", ELASTICSEARCH_URL)
        self.kafka_brokers = config.get("kafka_brokers", KAFKA_BROKERS)
        self.s3_bucket = config.get("s3_bucket", "aiops-logs")

        self.session: Optional[aiohttp.ClientSession] = None
        self.enabled = True

        logger.info(f"Log Router initialized with destinations: {self.destinations}")

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def route_log(self, log_entry: LogEntry) -> bool:
        """
        Route a log entry to configured destinations

        Args:
            log_entry: LogEntry object to route

        Returns:
            True if routing successful, False otherwise
        """
        if not self.enabled:
            return False

        success = True

        # Route to all destinations in parallel for better performance
        tasks = []
        for destination in self.destinations:
            if destination == LogDestination.LOKI.value:
                tasks.append(self.send_to_loki(log_entry))
            elif destination == LogDestination.ELASTICSEARCH.value:
                tasks.append(self.send_to_elasticsearch(log_entry))
            elif destination == LogDestination.KAFKA.value:
                tasks.append(self.send_to_kafka(log_entry))
            elif destination == LogDestination.S3.value:
                tasks.append(self.send_to_s3(log_entry))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for dest, result in zip(self.destinations, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to route log to {dest}: {result}")
                    success = False

        return success

    async def send_to_loki(self, log_entry: LogEntry) -> bool:
        """
        Send log entry to Loki

        Args:
            log_entry: LogEntry object

        Returns:
            True if successful, False otherwise
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            loki_data = log_entry.to_loki_format()
            url = f"{self.loki_url}/loki/api/v1/push"

            async with self.session.post(
                url, json=loki_data, headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 204:
                    logger.debug(f"Successfully sent log to Loki: {log_entry.service}")
                    return True
                else:
                    logger.error(f"Failed to send log to Loki: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error sending log to Loki: {e}")
            return False

    async def send_to_elasticsearch(self, log_entry: LogEntry) -> bool:
        """
        Send log entry to Elasticsearch

        Args:
            log_entry: LogEntry object

        Returns:
            True if successful, False otherwise
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            index_name = f"aiops-logs-{log_entry.timestamp.strftime('%Y-%m-%d')}"
            url = f"{self.elasticsearch_url}/{index_name}/_doc"

            async with self.session.post(
                url, json=log_entry.to_dict(), headers={"Content-Type": "application/json"}
            ) as response:
                if response.status in [200, 201]:
                    logger.debug(f"Successfully sent log to Elasticsearch: {log_entry.service}")
                    return True
                else:
                    logger.error(f"Failed to send log to Elasticsearch: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error sending log to Elasticsearch: {e}")
            return False

    async def send_to_kafka(self, log_entry: LogEntry) -> bool:
        """
        Send log entry to Kafka

        Args:
            log_entry: LogEntry object

        Returns:
            True if successful, False otherwise
        """
        try:
            # This would require kafka-python or aiokafka
            # default_value implementation
            logger.debug(f"Would send log to Kafka: {log_entry.service}")
            return True

        except Exception as e:
            logger.error(f"Error sending log to Kafka: {e}")
            return False

    async def send_to_s3(self, log_entry: LogEntry) -> bool:
        """
        Send log entry to S3 (batched)

        Args:
            log_entry: LogEntry object

        Returns:
            True if successful, False otherwise
        """
        try:
            # This would require boto3
            # default_value implementation - logs should be batched before sending to S3
            logger.debug(f"Would send log to S3: {log_entry.service}")
            return True

        except Exception as e:
            logger.error(f"Error sending log to S3: {e}")
            return False

    async def batch_route_logs(self, log_entries: List[LogEntry]) -> Dict[str, Any]:
        """
        Route multiple log entries in batch

        Args:
            log_entries: List of LogEntry objects

        Returns:
            Dictionary with success/failure counts per destination
        """
        results: Dict[str, Any] = {
            "total": len(log_entries),
            "success": 0,
            "failed": 0,
            "by_destination": {},
        }

        for destination in self.destinations:
            results["by_destination"][destination] = {"success": 0, "failed": 0}

        for log_entry in log_entries:
            success = await self.route_log(log_entry)
            if success:
                results["success"] += 1
                for destination in self.destinations:
                    results["by_destination"][destination]["success"] += 1
            else:
                results["failed"] += 1
                for destination in self.destinations:
                    results["by_destination"][destination]["failed"] += 1

        return results

    def parse_fluent_bit_log(self, log_line: str) -> Optional[LogEntry]:
        """
        Parse log line from Fluent-Bit

        Args:
            log_line: Raw log line from Fluent-Bit

        Returns:
            LogEntry object or None if parsing fails
        """
        try:
            log_data = json.loads(log_line)

            return LogEntry(
                timestamp=datetime.fromisoformat(
                    log_data.get("timestamp", datetime.now(timezone.utc).isoformat())
                ),
                level=LogLevel(log_data.get("level", "info")),
                message=log_data.get("message", ""),
                service=log_data.get("service", "unknown"),
                host=log_data.get("host", "unknown"),
                environment=log_data.get("environment", "production"),
                labels=log_data.get("labels", {}),
                extra=log_data.get("extra", {}),
            )
        except Exception as e:
            logger.error(f"Failed to parse Fluent-Bit log: {e}")
            return None

    def create_log_entry(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        service: str = "aiops",
        host: Optional[str] = None,
        environment: str = "production",
        labels: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """
        Create a log entry

        Args:
            message: Log message
            level: Log level
            service: Service name
            host: Host name
            environment: Environment name
            labels: Additional labels
            extra: Extra fields

        Returns:
            LogEntry object
        """
        if host is None:
            host = DEFAULT_LOG_HOST

        return LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            service=service,
            host=host,
            environment=environment,
            labels=labels or {},
            extra=extra or {},
        )

    def enable(self):
        """Enable log routing"""
        self.enabled = True
        logger.info("Log routing enabled")

    def disable(self):
        """Disable log routing"""
        self.enabled = False
        logger.info("Log routing disabled")


class LogRouterManager:
    """
    Manager for multiple log routers
    Handles routing configuration and lifecycle
    """

    def __init__(self):
        self.routers: Dict[str, LogRouter] = {}
        self.default_router: Optional[LogRouter] = None

    def add_router(self, name: str, config: Dict[str, Any]) -> LogRouter:
        """
        Add a log router

        Args:
            name: Router name
            config: Router configuration

        Returns:
            LogRouter instance
        """
        router = LogRouter(config)
        self.routers[name] = router

        if self.default_router is None:
            self.default_router = router

        logger.info(f"Added log router: {name}")
        return router

    def get_router(self, name: str) -> Optional[LogRouter]:
        """
        Get a log router by name

        Args:
            name: Router name

        Returns:
            LogRouter instance or None
        """
        return self.routers.get(name)

    def remove_router(self, name: str) -> bool:
        """
        Remove a log router

        Args:
            name: Router name

        Returns:
            True if removed, False if not found
        """
        if name in self.routers:
            del self.routers[name]
            if self.default_router and self.default_router == self.routers.get(name):
                self.default_router = None
            logger.info(f"Removed log router: {name}")
            return True
        return False

    def set_default_router(self, name: str) -> bool:
        """
        Set default router

        Args:
            name: Router name

        Returns:
            True if set, False if not found
        """
        if name in self.routers:
            self.default_router = self.routers[name]
            logger.info(f"Set default router: {name}")
            return True
        return False


def create_log_router(config: Dict[str, Any]) -> LogRouter:
    """
    Factory function to create Log Router

    Args:
        config: Configuration dictionary

    Returns:
        LogRouter instance
    """
    return LogRouter(config)
