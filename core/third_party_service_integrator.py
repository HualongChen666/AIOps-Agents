# -*- coding: utf-8 -*-
"""
Third-Party Service Integration (Phase 3)
Enterprise-grade third-party service integration (Neo4j, Consul)
"""

import asyncio
import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

try:
    from neo4j import AsyncGraphDatabase

    NEO4J_AVAILABLE = True
except Exception:
    NEO4J_AVAILABLE = False


class ServiceType(Enum):
    """Third-party service type"""

    NEO4J = "neo4j"
    CONSUL = "consul"
    ELASTICSEARCH = "elasticsearch"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"


class ServiceStatus(Enum):
    """Service status"""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


@dataclass
class ServiceConfig:
    """Service configuration"""

    service_type: ServiceType
    host: str = "localhost"
    port: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    connection_pool_size: int = 10
    timeout: int = 30
    ssl_enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceConnection:
    """Service connection information"""

    service_id: str
    service_type: ServiceType
    status: ServiceStatus = ServiceStatus.DISCONNECTED
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThirdPartyServiceIntegrator:
    """Enterprise-grade third-party service integrator"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize third-party service integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        self.service_connections: Dict[str, ServiceConnection] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}

        self.service_clients: Dict[str, Any] = {}

        self.health_check_interval = self.config.get("health_check_interval", 60)
        self.health_check_enabled = self.config.get("health_check_enabled", True)

        self.total_connections = 0
        self.active_connections = 0

        logger.info("Third-party service integrator initialized")

    async def connect_service(self, service_config: ServiceConfig) -> str:
        """
        Connect to third-party service

        Args:
            service_config: Service configuration

        Returns:
            Service ID
        """
        service_id = (
            f"{service_config.service_type.value}_{service_config.host}_{service_config.port}"
        )

        self.service_configs[service_id] = service_config

        connection = ServiceConnection(
            service_id=service_id,
            service_type=service_config.service_type,
            status=ServiceStatus.CONNECTING,
        )

        self.service_connections[service_id] = connection

        try:
            client = await self._connect_to_service(service_config)
            self.service_clients[service_id] = client

            connection.status = ServiceStatus.CONNECTED
            connection.connected_at = datetime.now(timezone.utc)
            connection.last_activity = datetime.now(timezone.utc)

            self.total_connections += 1
            self.active_connections += 1

            logger.info(f"Connected to service: {service_id}")

        except Exception as e:
            connection.status = ServiceStatus.ERROR
            connection.error_message = str(e)
            logger.error(f"Failed to connect to service {service_id}: {e}")

        return service_id

    async def _connect_to_service(self, config: ServiceConfig) -> Any:
        """
        Connect to specific service

        Args:
            config: Service configuration

        Returns:
            Service client
        """
        if config.service_type == ServiceType.NEO4J:
            return await self._connect_neo4j(config)
        elif config.service_type == ServiceType.CONSUL:
            return await self._connect_consul(config)
        else:
            raise ValueError(f"Unsupported service type: {config.service_type}")

    async def _connect_neo4j(self, config: ServiceConfig) -> Any:
        """
        Connect to Neo4j

        Args:
            config: Service configuration

        Returns:
            Neo4j client
        """
        if not NEO4J_AVAILABLE:
            raise RuntimeError("neo4j driver not installed")

        uri = f"neo4j://{config.host}:{config.port}"
        auth = (config.username, config.password) if config.username else None
        return AsyncGraphDatabase.driver(uri, auth=auth)

    async def _connect_consul(self, config: ServiceConfig) -> Any:
        """
        Connect to Consul

        Args:
            config: Service configuration

        Returns:
            Consul client
        """
        client = httpx.AsyncClient(
            base_url=f"http://{config.host}:{config.port}",
            timeout=config.timeout,
        )
        response = await client.get("/v1/status/leader")
        response.raise_for_status()
        return client

    async def disconnect_service(self, service_id: str) -> bool:
        """
        Disconnect from service

        Args:
            service_id: Service ID

        Returns:
            Success status
        """
        if service_id not in self.service_connections:
            return False

        connection = self.service_connections[service_id]

        try:
            if service_id in self.service_clients:
                await self._close_service_client(service_id)
                del self.service_clients[service_id]

            connection.status = ServiceStatus.DISCONNECTED
            self.active_connections -= 1

            logger.info(f"Disconnected from service: {service_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disconnect from service {service_id}: {e}")
            return False

    async def _close_service_client(self, service_id: str) -> None:
        """Close service client connection"""
        client = self.service_clients.get(service_id)
        if client is None:
            return

        if hasattr(client, "aclose"):
            await client.aclose()
        elif hasattr(client, "close"):
            await client.close()

    async def execute_neo4j_query(
        self, service_id: str, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute Neo4j query

        Args:
            service_id: Service ID
            query: Cypher query
            parameters: Query parameters

        Returns:
            Query results
        """
        if not NEO4J_AVAILABLE:
            raise RuntimeError("neo4j driver not installed")

        if service_id not in self.service_clients:
            raise ValueError(f"Service not connected: {service_id}")

        connection = self.service_connections[service_id]
        if connection.service_type != ServiceType.NEO4J:
            raise ValueError(f"Service is not Neo4j: {service_id}")

        connection.last_activity = datetime.now(timezone.utc)

        config = self.service_configs[service_id]
        driver = self.service_clients[service_id]
        parameters = parameters or {}
        results: List[Dict[str, Any]] = []

        async with driver.session(database=config.database) as session:
            result = await session.run(query, parameters)
            async for record in result:
                results.append(record.data())

        return results

    async def consul_put_kv(self, service_id: str, key: str, value: Any) -> bool:
        """
        Put key-value pair in Consul

        Args:
            service_id: Service ID
            key: Key
            value: Value

        Returns:
            Success status
        """
        if service_id not in self.service_clients:
            raise ValueError(f"Service not connected: {service_id}")

        connection = self.service_connections[service_id]
        if connection.service_type != ServiceType.CONSUL:
            raise ValueError(f"Service is not Consul: {service_id}")

        connection.last_activity = datetime.now(timezone.utc)

        client = self.service_clients[service_id]
        content = value if isinstance(value, bytes) else str(value).encode()
        response = await client.put(f"/v1/kv/{key}", content=content)

        return response.status_code == 200 and response.text.strip() == "true"

    async def consul_get_kv(self, service_id: str, key: str) -> Optional[Any]:
        """
        Get key-value pair from Consul

        Args:
            service_id: Service ID
            key: Key

        Returns:
            Value or None
        """
        if service_id not in self.service_clients:
            raise ValueError(f"Service not connected: {service_id}")

        connection = self.service_connections[service_id]
        if connection.service_type != ServiceType.CONSUL:
            raise ValueError(f"Service is not Consul: {service_id}")

        connection.last_activity = datetime.now(timezone.utc)

        client = self.service_clients[service_id]
        response = await client.get(f"/v1/kv/{key}")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        if not data or "Value" not in data[0]:
            return None

        return base64.b64decode(data[0]["Value"]).decode()

    async def consul_register_service(
        self,
        service_id: str,
        service_name: str,
        service_address: str,
        service_port: int,
        check_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Register service in Consul

        Args:
            service_id: Service ID
            service_name: Service name
            service_address: Service address
            service_port: Service port
            check_config: Health check configuration

        Returns:
            Success status
        """
        if service_id not in self.service_clients:
            raise ValueError(f"Service not connected: {service_id}")

        connection = self.service_connections[service_id]
        if connection.service_type != ServiceType.CONSUL:
            raise ValueError(f"Service is not Consul: {service_id}")

        connection.last_activity = datetime.now(timezone.utc)

        client = self.service_clients[service_id]
        payload: Dict[str, Any] = {
            "ID": f"{service_name}-{service_address}-{service_port}",
            "Name": service_name,
            "Address": service_address,
            "Port": service_port,
        }
        if check_config:
            payload["Check"] = check_config

        response = await client.put("/v1/agent/service/register", json=payload)
        return response.status_code == 200

    async def health_check(self, service_id: str) -> Dict[str, Any]:
        """
        Perform health check on service

        Args:
            service_id: Service ID

        Returns:
            Health check result
        """
        if service_id not in self.service_connections:
            return {"service_id": service_id, "status": "unknown", "error": "Service not found"}

        connection = self.service_connections[service_id]

        try:
            return {
                "service_id": service_id,
                "status": connection.status.value,
                "last_activity": (
                    connection.last_activity.isoformat() if connection.last_activity else None
                ),
                "healthy": connection.status == ServiceStatus.CONNECTED,
            }

        except Exception as e:
            return {"service_id": service_id, "status": "error", "error": str(e), "healthy": False}

    async def start_health_check_loop(self) -> None:
        """Start health check loop"""
        if not self.health_check_enabled:
            return

        async def health_check_loop():
            while True:
                try:
                    for service_id in self.service_connections.keys():
                        await self.health_check(service_id)

                    await asyncio.sleep(self.health_check_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health check loop error: {e}")
                    await asyncio.sleep(self.health_check_interval)

        asyncio.create_task(health_check_loop())
        logger.info("Health check loop started")

    def get_service_status(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get service status

        Args:
            service_id: Service ID

        Returns:
            Service status dictionary
        """
        if service_id not in self.service_connections:
            return None

        connection = self.service_connections[service_id]

        return {
            "service_id": connection.service_id,
            "service_type": connection.service_type.value,
            "status": connection.status.value,
            "connected_at": (
                connection.connected_at.isoformat() if connection.connected_at else None
            ),
            "last_activity": (
                connection.last_activity.isoformat() if connection.last_activity else None
            ),
            "error_message": connection.error_message,
        }

    def list_services(self) -> List[Dict[str, Any]]:
        """List all connected services"""
        return [
            status
            for service_id in self.service_connections.keys()
            if (status := self.get_service_status(service_id)) is not None
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "connected_services": len(
                [
                    c
                    for c in self.service_connections.values()
                    if c.status == ServiceStatus.CONNECTED
                ]
            ),
            "health_check_enabled": self.health_check_enabled,
        }


def get_third_party_service_integrator(
    config: Optional[Dict[str, Any]] = None,
) -> ThirdPartyServiceIntegrator:
    """
    Factory function to get third-party service integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        ThirdPartyServiceIntegrator: Integrator instance
    """
    return ThirdPartyServiceIntegrator(config)
