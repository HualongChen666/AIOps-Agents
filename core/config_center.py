# -*- coding: utf-8 -*-
"""配置中心适配器

实现Consul配置中心集成，支持配置热更新、版本管理、服务发现等功能
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    import consul

    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False
    consul = None


_logger = logging.getLogger(__name__)


class ConfigEventType(str, Enum):
    """配置事件类型"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class ConfigChangeEvent:
    """配置变更事件"""

    key: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    event_type: ConfigEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 0


@dataclass
class ConfigItem:
    """配置项"""

    key: str
    value: Any
    version: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConsulConfigCenter:
    """Consul配置中心"""

    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        """初始化Consul配置中心"""
        self.consul_host = consul_host
        self.consul_port = consul_port
        self.stub_enabled = not CONSUL_AVAILABLE

        if self.stub_enabled:
            _logger.info("Consul not available, using stub implementation")
            self.stub_config: Dict[str, ConfigItem] = {}
        else:
            try:
                self.consul_client = consul.Consul(host=consul_host, port=consul_port)
                # 测试连接
                self.consul_client.agent.self()
                _logger.info(f"Consul client initialized: {consul_host}:{consul_port}")
            except Exception as e:
                _logger.error(f"Failed to initialize Consul client: {e}")
                self.stub_enabled = True
                self.stub_config = {}

        self.change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        self.watch_threads: Dict[str, threading.Thread] = {}

    def set_config(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """设置配置"""
        if self.stub_enabled:
            old_item = self.stub_config.get(key)
            old_value = old_item.value if old_item else None

            new_item = ConfigItem(
                key=key,
                value=value,
                version=old_item.version + 1 if old_item else 0,
                metadata=metadata or {},
            )
            self.stub_config[key] = new_item

            # 触发变更事件
            event = ConfigChangeEvent(
                key=key,
                old_value=old_value,
                new_value=value,
                event_type=ConfigEventType.UPDATE if old_item else ConfigEventType.CREATE,
                version=new_item.version,
            )
            self._notify_change(event)
            return True

        try:
            # 实际Consul设置
            value_str = json.dumps(value) if not isinstance(value, str) else value
            self.consul_client.kv.put(key, value_str)
            _logger.info(f"Config set: {key}")
            return True
        except Exception as e:
            _logger.error(f"Failed to set config {key}: {e}")
            return False

    def get_config(self, key: str, default: Any = None) -> Optional[Any]:
        """获取配置"""
        if self.stub_enabled:
            item = self.stub_config.get(key)
            return item.value if item else default

        try:
            index, data = self.consul_client.kv.get(key)
            if data is None:
                return default

            value_str = data["Value"].decode("utf-8")
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
        except Exception as e:
            _logger.error(f"Failed to get config {key}: {e}")
            return default

    def delete_config(self, key: str) -> bool:
        """删除配置"""
        if self.stub_enabled:
            old_item = self.stub_config.get(key)
            if old_item:
                old_value = old_item.value
                del self.stub_config[key]

                event = ConfigChangeEvent(
                    key=key,
                    old_value=old_value,
                    new_value=None,
                    event_type=ConfigEventType.DELETE,
                    version=old_item.version,
                )
                self._notify_change(event)
                return True
            return False

        try:
            self.consul_client.kv.delete(key)
            _logger.info(f"Config deleted: {key}")
            return True
        except Exception as e:
            _logger.error(f"Failed to delete config {key}: {e}")
            return False

    def watch_config(self, key: str, callback: Callable[[Any], None]):
        """监听配置变化"""
        if self.stub_enabled:
            _logger.info(f"Stub mode: Watching config {key}")
            # 在stub模式下，我们通过手动触发来模拟
            return

        def watch_thread():
            index = None
            while True:
                try:
                    index, data = self.consul_client.kv.get(key, index=index)
                    if data:
                        value_str = data["Value"].decode("utf-8")
                        try:
                            value = json.loads(value_str)
                        except json.JSONDecodeError:
                            value = value_str
                        callback(value)
                    time.sleep(1)
                except Exception as e:
                    _logger.error(f"Watch error for {key}: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=watch_thread, daemon=True)
        thread.start()
        self.watch_threads[key] = thread
        _logger.info(f"Started watching config: {key}")

    def register_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """注册配置变更监听器"""
        self.change_listeners.append(listener)
        _logger.info(f"Registered change listener, total listeners: {len(self.change_listeners)}")

    def _notify_change(self, event: ConfigChangeEvent):
        """通知配置变更"""
        for listener in self.change_listeners:
            try:
                listener(event)
            except Exception as e:
                _logger.error(f"Change listener error: {e}")

    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置"""
        if self.stub_enabled:
            return {key: item.value for key, item in self.stub_config.items()}

        try:
            index, data = self.consul_client.kv.get("/", recurse=True)
            configs = {}
            if data:
                for item in data:
                    key = item["Key"]
                    value_str = item["Value"].decode("utf-8")
                    try:
                        value = json.loads(value_str)
                    except json.JSONDecodeError:
                        value = value_str
                    configs[key] = value
            return configs
        except Exception as e:
            _logger.error(f"Failed to get all configs: {e}")
            return {}

    def get_stub_configs(self) -> Dict[str, ConfigItem]:
        """获取stub配置（用于测试）"""
        return self.stub_config


class ServiceDiscovery:
    """服务发现"""

    def __init__(self, config_center: ConsulConfigCenter):
        """初始化服务发现"""
        self.config_center = config_center
        self.services: Dict[str, List[Dict[str, Any]]] = {}

    def register_service(
        self,
        service_name: str,
        service_id: str,
        address: str,
        port: int,
        tags: Optional[List[str]] = None,
    ):
        """注册服务"""
        if self.config_center.stub_enabled:
            service_info = {
                "service_id": service_id,
                "address": address,
                "port": port,
                "tags": tags or [],
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }
            if service_name not in self.services:
                self.services[service_name] = []
            self.services[service_name].append(service_info)
            _logger.info(f"Service registered: {service_name}/{service_id}")
            return

        try:
            self.config_center.consul_client.agent.service.register(
                name=service_name,
                service_id=service_id,
                address=address,
                port=port,
                tags=tags or [],
            )
            _logger.info(f"Service registered: {service_name}/{service_id}")
        except Exception as e:
            _logger.error(f"Failed to register service {service_name}: {e}")

    def deregister_service(self, service_id: str):
        """注销服务"""
        if self.config_center.stub_enabled:
            for service_name, services in self.services.items():
                self.services[service_name] = [s for s in services if s["service_id"] != service_id]
            _logger.info(f"Service deregistered: {service_id}")
            return

        try:
            self.config_center.consul_client.agent.service.deregister(service_id)
            _logger.info(f"Service deregistered: {service_id}")
        except Exception as e:
            _logger.error(f"Failed to deregister service {service_id}: {e}")

    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """发现服务"""
        if self.config_center.stub_enabled:
            return self.services.get(service_name, [])

        try:
            _, services = self.config_center.consul_client.health.service(
                service_name, passing=True
            )
            return [
                {
                    "service_id": s["Service"]["ID"],
                    "address": s["Service"]["Address"],
                    "port": s["Service"]["Port"],
                    "tags": s["Service"]["Tags"],
                }
                for s in services
            ]
        except Exception as e:
            _logger.error(f"Failed to discover service {service_name}: {e}")
            return []


# 全局实例
consul_config_center = ConsulConfigCenter()
service_discovery = ServiceDiscovery(consul_config_center)


def get_config_center() -> ConsulConfigCenter:
    """获取配置中心实例"""
    return consul_config_center


def get_service_discovery() -> ServiceDiscovery:
    """获取服务发现实例"""
    return service_discovery
