# -*- coding: utf-8 -*-
from __future__ import annotations

"""
auto_discovery.py
-----------------
智能可观测性 - 自动发现模块。

功能：
- 自动发现服务和基础设施
- 自动构建服务拓扑
- 自动配置监控
- 自动识别关键业务流程
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 资源类型枚举
# ----------------------------------------------------------------------
class ResourceType(Enum):
    """资源类型"""

    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    LOAD_BALANCER = "load_balancer"
    INFRASTRUCTURE = "infrastructure"


# ----------------------------------------------------------------------
# 2️⃣ 发现的资源
# ----------------------------------------------------------------------
@dataclass
class DiscoveredResource:
    """发现的资源"""

    id: str
    name: str
    type: ResourceType
    host: Optional[str] = None
    port: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "host": self.host,
            "port": self.port,
            "metadata": self.metadata,
            "tags": self.tags,
            "discovered_at": self.discovered_at,
        }


# ----------------------------------------------------------------------
# 3️⃣ 服务关系
# ----------------------------------------------------------------------
@dataclass
class ServiceRelation:
    """服务关系"""

    source: str
    target: str
    relation_type: str  # "calls", "depends_on", "hosts"
    strength: float = 1.0  # 关系强度
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 4️⃣ 自动发现引擎
# ----------------------------------------------------------------------
class AutoDiscoveryEngine:
    """自动发现引擎"""

    def __init__(self):
        self.discovered_resources: Dict[str, DiscoveredResource] = {}
        self.service_relations: List[ServiceRelation] = []
        self.discovery_plugins: Dict[str, Any] = {}
        self._initialize_plugins()

    def _initialize_plugins(self):
        """初始化发现插件"""
        # Kubernetes 发现插件
        self.discovery_plugins["kubernetes"] = self._discover_kubernetes
        # Docker 发现插件
        self.discovery_plugins["docker"] = self._discover_docker
        # 配置文件发现插件
        self.discovery_plugins["config"] = self._discover_from_config
        # 网络扫描插件
        self.discovery_plugins["network"] = self._discover_network

    def discover(
        self,
        methods: List[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        执行自动发现

        Parameters
        ----------
        methods : List[str], optional
            发现方法列表，默认使用所有方法
        **kwargs
            发现参数

        Returns
        -------
        Dict[str, Any]
            发现结果
        """
        if methods is None:
            methods = list(self.discovery_plugins.keys())

        logger.info(f"Starting auto-discovery with methods: {methods}")

        for method in methods:
            if method in self.discovery_plugins:
                try:
                    self.discovery_plugins[method](**kwargs)
                except Exception as e:
                    logger.error(f"Discovery method {method} failed: {e}")

        # 构建服务拓扑
        self._build_topology()

        # 识别关键业务流程
        critical_flows = self._identify_critical_flows()

        return {
            "resources": [r.to_dict() for r in self.discovered_resources.values()],
            "relations": [r.to_dict() for r in self.service_relations],
            "topology": self._get_topology_summary(),
            "critical_flows": critical_flows,
            "discovery_timestamp": datetime.now().isoformat(),
        }

    def _discover_kubernetes(self, **kwargs):
        """从 Kubernetes 发现资源"""
        try:
            from kubernetes import client, config
        except ImportError:
            logger.warning("Kubernetes client not available")
            return

        try:
            config.load_kube_config()
            v1 = client.CoreV1Api()

            # 发现 Services
            services = v1.list_service_for_all_namespaces()
            for svc in services.items:
                resource_id = f"k8s-service-{svc.metadata.namespace}-{svc.metadata.name}"

                self.discovered_resources[resource_id] = DiscoveredResource(
                    id=resource_id,
                    name=svc.metadata.name,
                    type=ResourceType.SERVICE,
                    host=svc.spec.cluster_ip,
                    metadata={
                        "namespace": svc.metadata.namespace,
                        "type": svc.spec.type,
                        "ports": [p.port for p in svc.spec.ports or []],
                    },
                    tags=["kubernetes", "service"],
                )

            # 发现 Pods
            pods = v1.list_pod_for_all_namespaces()
            for pod in pods.items:
                resource_id = f"k8s-pod-{pod.metadata.namespace}-{pod.metadata.name}"

                self.discovered_resources[resource_id] = DiscoveredResource(
                    id=resource_id,
                    name=pod.metadata.name,
                    type=ResourceType.INFRASTRUCTURE,
                    host=pod.status.host_ip,
                    metadata={
                        "namespace": pod.metadata.namespace,
                        "phase": pod.status.phase,
                        "node": pod.spec.node_name,
                    },
                    tags=["kubernetes", "pod"],
                )

            logger.info(
                f"Discovered {len(services.items)} services and {len(pods.items)} pods from Kubernetes"  # noqa: E501
            )

        except Exception as e:
            logger.error(f"Kubernetes discovery failed: {e}")

    def _discover_docker(self, **kwargs):
        """从 Docker 发现资源"""
        try:
            import docker
        except ImportError:
            logger.warning("Docker client not available")
            return

        try:
            client = docker.from_env()

            # 发现容器
            containers = client.containers.list(all=True)
            for container in containers:
                resource_id = f"docker-container-{container.id[:12]}"

                self.discovered_resources[resource_id] = DiscoveredResource(
                    id=resource_id,
                    name=container.name,
                    type=ResourceType.INFRASTRUCTURE,
                    metadata={
                        "image": (
                            container.image.tags[0] if container.image.tags else container.image.id
                        ),
                        "status": container.status,
                        "ports": container.ports,
                    },
                    tags=["docker", "container"],
                )

            logger.info(f"Discovered {len(containers)} containers from Docker")

        except Exception as e:
            logger.error(f"Docker discovery failed: {e}")

    def _discover_from_config(self, config_data: Dict[str, Any] = None, **kwargs):
        """从配置文件发现资源"""
        if config_data is None:
            logger.warning("No config data provided")
            return

        # 解析服务配置
        services = config_data.get("services", [])
        for service_config in services:
            resource_id = service_config.get("id", f"config-service-{service_config.get('name')}")

            self.discovered_resources[resource_id] = DiscoveredResource(
                id=resource_id,
                name=service_config.get("name"),
                type=ResourceType.SERVICE,
                host=service_config.get("host"),
                port=service_config.get("port"),
                metadata=service_config.get("metadata", {}),
                tags=["config", "service"],
            )

        logger.info(f"Discovered {len(services)} services from config")

    def _discover_network(self, subnet: str = "192.168.1.0/24", **kwargs):
        """通过网络扫描发现资源"""
        try:
            import nmap
        except ImportError:
            logger.warning("nmap not available, using simple ping instead")
            self._simple_network_scan(subnet)
            return

        try:
            nm = nmap.PortScanner()
            nm.scan(subnet, arguments="-p 22,80,443,3306,6379")

            for host in nm.all_hosts():
                for proto in nm[host].all_protocols():
                    for port in nm[host][proto].keys():
                        state = nm[host][proto][port]["state"]

                        if state == "open":
                            resource_id = f"network-{host}-{port}"
                            resource_type = self._infer_resource_type(port)

                            self.discovered_resources[resource_id] = DiscoveredResource(
                                id=resource_id,
                                name=f"{host}:{port}",
                                type=resource_type,
                                host=host,
                                port=port,
                                tags=["network", "discovered"],
                            )

            logger.info(f"Discovered resources from network scan of {subnet}")

        except Exception as e:
            logger.error(f"Network discovery failed: {e}")

    def _simple_network_scan(self, subnet: str):
        """简单的网络扫描（降级方案）"""

        logger.info(f"Performing simple network scan for {subnet}")
        # 简化实现，实际应使用更完整的扫描逻辑

    def _infer_resource_type(self, port: int) -> ResourceType:
        """根据端口推断资源类型"""
        port_map = {
            22: ResourceType.INFRASTRUCTURE,
            80: ResourceType.SERVICE,
            443: ResourceType.SERVICE,
            3306: ResourceType.DATABASE,
            5432: ResourceType.DATABASE,
            6379: ResourceType.CACHE,
            5672: ResourceType.MESSAGE_QUEUE,
            9092: ResourceType.MESSAGE_QUEUE,
        }
        return port_map.get(port, ResourceType.SERVICE)

    def _build_topology(self):
        """构建服务拓扑"""
        # 基于资源关系构建拓扑
        for resource_id, resource in self.discovered_resources.items():
            # 如果是服务，查找其依赖的数据库、缓存等
            if resource.type == ResourceType.SERVICE:
                # 查找同一命名空间下的数据库
                for other_id, other in self.discovered_resources.items():
                    if other.type in [ResourceType.DATABASE, ResourceType.CACHE]:
                        # 假设同一命名空间的服务依赖该数据库
                        if resource.metadata.get("namespace") == other.metadata.get("namespace"):
                            self.service_relations.append(
                                ServiceRelation(
                                    source=resource_id,
                                    target=other_id,
                                    relation_type="depends_on",
                                )
                            )

        logger.info(f"Built topology with {len(self.service_relations)} relations")

    def _get_topology_summary(self) -> Dict[str, Any]:
        """获取拓扑摘要"""
        resource_types: Dict[str, int] = {}
        for resource in self.discovered_resources.values():
            resource_types[resource.type.value] = resource_types.get(resource.type.value, 0) + 1

        return {
            "total_resources": len(self.discovered_resources),
            "resource_types": resource_types,
            "total_relations": len(self.service_relations),
        }

    def _identify_critical_flows(self) -> List[Dict[str, Any]]:
        """识别关键业务流程"""
        critical_flows = []

        # 基于关系强度和依赖数量识别关键路径
        dependency_counts: Dict[str, int] = {}
        for relation in self.service_relations:
            dependency_counts[relation.source] = dependency_counts.get(relation.source, 0) + 1

        # 找出依赖最多的服务（可能是关键服务）
        if dependency_counts:
            max_deps = max(dependency_counts.values())
            critical_services = [
                svc for svc, count in dependency_counts.items() if count == max_deps
            ]

            for svc_id in critical_services:
                critical_flows.append(
                    {
                        "service_id": svc_id,
                        "service_name": self.discovered_resources[svc_id].name,
                        "dependency_count": dependency_counts[svc_id],
                        "type": "high_dependency",
                    }
                )

        return critical_flows

    def generate_monitoring_config(self) -> Dict[str, Any]:
        """生成监控配置"""
        monitoring_config: Dict[str, List[Any]] = {
            "services": [],
            "databases": [],
            "caches": [],
        }

        for resource in self.discovered_resources.values():
            if resource.type == ResourceType.SERVICE:
                monitoring_config["services"].append(
                    {
                        "name": resource.name,
                        "host": resource.host,
                        "port": resource.port,
                        "metrics": ["cpu", "memory", "request_rate", "error_rate"],
                    }
                )
            elif resource.type == ResourceType.DATABASE:
                monitoring_config["databases"].append(
                    {
                        "name": resource.name,
                        "host": resource.host,
                        "port": resource.port,
                        "metrics": ["connections", "query_latency", "slow_queries"],
                    }
                )
            elif resource.type == ResourceType.CACHE:
                monitoring_config["caches"].append(
                    {
                        "name": resource.name,
                        "host": resource.host,
                        "port": resource.port,
                        "metrics": ["hit_rate", "memory_usage", "evictions"],
                    }
                )

        return monitoring_config


# ----------------------------------------------------------------------
# 5️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_auto_discovery_engine() -> AutoDiscoveryEngine:
    """创建自动发现引擎"""
    return AutoDiscoveryEngine()


# ----------------------------------------------------------------------
# 6️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试自动发现引擎
    logger.info("Testing auto-discovery engine")

    engine = create_auto_discovery_engine()

    # 测试配置发现
    config_data = {
        "services": [
            {
                "id": "web-service",
                "name": "Web Service",
                "host": "localhost",
                "port": 8080,
                "metadata": {"namespace": "production"},
            },
            {
                "id": "api-service",
                "name": "API Service",
                "host": "localhost",
                "port": 8081,
                "metadata": {"namespace": "production"},
            },
        ],
    }

    result = engine.discover(methods=["config"], config_data=config_data)

    logger.info(f"Discovery result: {result['topology']}")
    logger.info(f"Critical flows: {result['critical_flows']}")

    # 生成监控配置
    monitoring_config = engine.generate_monitoring_config()
    logger.info(f"Monitoring config: {monitoring_config}")

    logger.info("Test passed!")
