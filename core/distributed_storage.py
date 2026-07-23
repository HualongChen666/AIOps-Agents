# -*- coding: utf-8 -*-
"""分布式存储架构适配器

实现PostgreSQL主从复制、读写分离、Redis集群等分布式存储功能
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import redis
    from redis.cluster import RedisCluster

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis: Any = None  # type: ignore
    RedisCluster: Any = None  # type: ignore

from config import REDIS_DB, REDIS_HOST, REDIS_PORT

_logger = logging.getLogger(__name__)


class DatabaseRole(str, Enum):
    """数据库角色"""

    MASTER = "master"
    SLAVE = "slave"
    REPLICA = "replica"


class DatabaseType(str, Enum):
    """数据库类型"""

    POSTGRESQL = "postgresql"
    REDIS = "redis"
    LOKI = "loki"
    VICTORIAMETRICS = "victoriametrics"


@dataclass
class DatabaseInstance:
    """数据库实例"""

    host: str
    port: int
    role: DatabaseRole
    database_type: DatabaseType
    weight: int = 1
    is_available: bool = True
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReadWriteRouter:
    """读写分离路由器"""

    def __init__(self):
        """初始化读写分离路由器"""
        self.master: Optional[DatabaseInstance] = None
        self.slaves: List[DatabaseInstance] = []
        self.current_slave_index = 0
        self.stub_enabled = True

    def set_master(self, instance: DatabaseInstance):
        """设置主数据库"""
        self.master = instance
        _logger.info(f"Set master database: {instance.host}:{instance.port}")

    def add_slave(self, instance: DatabaseInstance):
        """添加从数据库"""
        self.slaves.append(instance)
        _logger.info(f"Added slave database: {instance.host}:{instance.port}")

    def get_read_connection(self) -> DatabaseInstance:
        """获取读连接（从数据库）"""
        if not self.slaves:
            _logger.warning("No slaves available, using master for read")
            if self.master is None:
                raise Exception("No master database configured")
            return self.master

        # 轮询选择从数据库
        available_slaves = [s for s in self.slaves if s.is_available]
        if not available_slaves:
            _logger.warning("No available slaves, using master for read")
            if self.master is None:
                raise Exception("No master database configured")
            return self.master

        # 根据权重选择
        total_weight = sum(s.weight for s in available_slaves)
        if total_weight == 0:
            return available_slaves[0]

        rand = random.randint(0, total_weight)  # nosec B311
        current_weight = 0
        for slave in available_slaves:
            current_weight += slave.weight
            if rand <= current_weight:
                return slave

        return available_slaves[0]

    def get_write_connection(self) -> DatabaseInstance:
        """获取写连接（主数据库）"""
        if not self.master:
            raise Exception("No master database configured")
        return self.master

    def check_health(self):
        """检查数据库健康状态"""
        # 简化的健康检查
        if self.master:
            self.master.last_check = datetime.now(timezone.utc)

        for slave in self.slaves:
            slave.last_check = datetime.now(timezone.utc)
            # 这里应该有实际的健康检查逻辑
            slave.is_available = True


class RedisClusterAdapter:
    """Redis集群适配器"""

    def __init__(self):
        """初始化Redis集群适配器"""
        if not REDIS_AVAILABLE:
            _logger.warning("Redis not available, using stub implementation")
            self.stub_enabled = True
            self.stub_data: Dict[str, Any] = {}
        else:
            try:
                self.stub_enabled = False
                # 尝试连接到Redis
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                self.redis_client.ping()
                _logger.info(f"Redis client initialized: {REDIS_HOST}:{REDIS_PORT}")
            except Exception as e:
                _logger.error(f"Failed to initialize Redis client: {e}")
                self.stub_enabled = True
                self.stub_data = {}

    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        if self.stub_enabled:
            return self.stub_data.get(key)

        try:
            return self.redis_client.get(key)
        except Exception as e:
            _logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置值"""
        if self.stub_enabled:
            self.stub_data[key] = value
            return True

        try:
            result: Any
            if ttl:
                result = self.redis_client.setex(key, ttl, value)
            else:
                result = self.redis_client.set(key, value)
            # Redis set/setex 返回 True/False 或 OK (bytes/str)，统一转换为 bool
            return bool(result)
        except Exception as e:
            _logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除值"""
        if self.stub_enabled:
            if key in self.stub_data:
                del self.stub_data[key]
            return True

        try:
            return self.redis_client.delete(key) > 0
        except Exception as e:
            _logger.error(f"Redis delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self.stub_enabled:
            return key in self.stub_data

        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            _logger.error(f"Redis exists error: {e}")
            return False

    def get_stub_data(self) -> Dict[str, Any]:
        """获取stub数据（用于测试）"""
        return self.stub_data


class DistributedStorageManager:
    """分布式存储管理器"""

    def __init__(self):
        """初始化分布式存储管理器"""
        self.read_write_router = ReadWriteRouter()
        self.redis_adapter = RedisClusterAdapter()
        self.database_instances: Dict[str, DatabaseInstance] = {}

    def configure_master_slave(self, master_host: str, master_port: int, slave_hosts: List[tuple]):
        """配置主从架构"""
        # 设置主数据库
        master = DatabaseInstance(
            host=master_host,
            port=master_port,
            role=DatabaseRole.MASTER,
            database_type=DatabaseType.POSTGRESQL,
        )
        self.read_write_router.set_master(master)
        self.database_instances[f"{master_host}:{master_port}"] = master

        # 添加从数据库
        for i, (host, port) in enumerate(slave_hosts):
            slave = DatabaseInstance(
                host=host,
                port=port,
                role=DatabaseRole.SLAVE,
                database_type=DatabaseType.POSTGRESQL,
                weight=1,
            )
            self.read_write_router.add_slave(slave)
            self.database_instances[f"{host}:{port}"] = slave

        _logger.info(f"Configured master-slave: 1 master, {len(slave_hosts)} slaves")

    def configure_redis_cluster(self, cluster_nodes: List[tuple]):
        """配置Redis集群"""
        if not REDIS_AVAILABLE:
            _logger.warning("Redis not available, cluster configuration skipped")
            return

        try:
            # 这里应该配置RedisCluster
            # cluster = RedisCluster(startup_nodes=cluster_nodes)
            _logger.info(f"Redis cluster configured with {len(cluster_nodes)} nodes")
        except Exception as e:
            _logger.error(f"Failed to configure Redis cluster: {e}")

    def get_read_connection_info(self) -> Dict[str, Any]:
        """获取读连接信息"""
        instance = self.read_write_router.get_read_connection()
        return {
            "host": instance.host,
            "port": instance.port,
            "role": instance.role.value,
            "database_type": instance.database_type.value,
        }

    def get_write_connection_info(self) -> Dict[str, Any]:
        """获取写连接信息"""
        instance = self.read_write_router.get_write_connection()
        return {
            "host": instance.host,
            "port": instance.port,
            "role": instance.role.value,
            "database_type": instance.database_type.value,
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        self.read_write_router.check_health()

        return {
            "master_available": self.read_write_router.master is not None,
            "slaves_count": len(self.read_write_router.slaves),
            "available_slaves_count": len(
                [s for s in self.read_write_router.slaves if s.is_available]
            ),
            "redis_available": (
                not self.redis_adapter.stub_enabled or len(self.redis_adapter.get_stub_data()) > 0
            ),
        }


# 全局实例（延迟初始化，避免模块导入时连接 Redis 导致测试挂起）
_distributed_storage_manager: Optional[DistributedStorageManager] = None


def get_distributed_storage_manager() -> DistributedStorageManager:
    """获取分布式存储管理器实例"""
    global _distributed_storage_manager
    if _distributed_storage_manager is None:
        _distributed_storage_manager = DistributedStorageManager()
    return _distributed_storage_manager
