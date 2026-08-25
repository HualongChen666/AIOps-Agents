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
        self.fallback_enabled = not CONSUL_AVAILABLE

        if self.fallback_enabled:
            _logger.info("Consul not available, using component implementation")
            self.fallback_config: Dict[str, ConfigItem] = {}
        else:
            try:
                self.consul_client = consul.Consul(host=consul_host, port=consul_port)
                # 测试连接
                self.consul_client.agent.self()
                _logger.info(f"Consul client initialized: {consul_host}:{consul_port}")
            except Exception as e:
                _logger.error(f"Failed to initialize Consul client: {e}")
                self.fallback_enabled = True
                self.fallback_config = {}

        self.change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        self.watch_threads: Dict[str, threading.Thread] = {}

    def set_config(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """设置配置"""
        try:
            if self.fallback_enabled:
                event_type = (
                    ConfigEventType.UPDATE
                    if key in self.fallback_config
                    else ConfigEventType.CREATE
                )
                if key in self.fallback_config:
                    self.fallback_config[key].value = value
                    self.fallback_config[key].version += 1
                    self.fallback_config[key].updated_at = datetime.now(timezone.utc)
                    if metadata:
                        self.fallback_config[key].metadata.update(metadata)
                else:
                    self.fallback_config[key] = ConfigItem(
                        key=key,
                        value=value,
                        metadata=metadata or {},
                    )
                self._notify_change(
                    ConfigChangeEvent(
                        key=key,
                        old_value=(
                            None
                            if event_type == ConfigEventType.CREATE
                            else self.fallback_config[key].value
                        ),
                        new_value=value,
                        event_type=event_type,
                        version=self.fallback_config[key].version,
                    )
                )
                return True

            # Consul 模式：简单 KV 存储
            if self.consul_client:
                self.consul_client.kv.put(
                    key, json.dumps({"value": value, "metadata": metadata or {}})
                )
                return True
        except Exception as e:
            _logger.error(f"Failed to set config {key}: {e}")
        return False

    def get_config(self, key: str, default: Any = None) -> Optional[Any]:
        """获取配置"""
        if self.fallback_enabled:
            item = self.fallback_config.get(key)
            return item.value if item else default

        try:
            if self.consul_client:
                _, data = self.consul_client.kv.get(key)
                if data and data["Value"]:
                    payload = json.loads(data["Value"].decode("utf-8"))
                    return payload.get("value", default)
        except Exception as e:
            _logger.error(f"Failed to get config {key}: {e}")
        return default

    def get_config_item(self, key: str) -> Optional[ConfigItem]:
        """获取完整配置项（含 version 等元数据）"""
        if self.fallback_enabled:
            return self.fallback_config.get(key)
        try:
            if self.consul_client:
                _, data = self.consul_client.kv.get(key)
                if data and data["Value"]:
                    payload = json.loads(data["Value"].decode("utf-8"))
                    return ConfigItem(
                        key=key,
                        value=payload.get("value"),
                        version=payload.get("version", 0),
                        metadata=payload.get("metadata", {}),
                    )
        except Exception as e:
            _logger.error(f"Failed to get config item {key}: {e}")
        return None

    def delete_config(self, key: str) -> bool:
        """删除配置"""
        if self.fallback_enabled:
            if key not in self.fallback_config:
                return False
            old_value = self.fallback_config.pop(key).value
            self._notify_change(
                ConfigChangeEvent(
                    key=key,
                    old_value=old_value,
                    new_value=None,
                    event_type=ConfigEventType.DELETE,
                )
            )
            return True

        try:
            if self.consul_client:
                return bool(self.consul_client.kv.delete(key))
        except Exception as e:
            _logger.error(f"Failed to delete config {key}: {e}")
        return False

    def watch_config(self, key: str, callback: Callable[[Any], None]):
        """监听配置变化"""
        if self.fallback_enabled:
            _logger.info(f"Fallback mode: Watching config {key}")
            # 在 fallback 模式下，通过手动触发来刷新
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
        if self.fallback_enabled:
            return {key: item.value for key, item in self.fallback_config.items()}

        all_configs: Dict[str, Any] = {}
        try:
            if self.consul_client:
                _, data = self.consul_client.kv.get("", recurse=True)
                if data:
                    for item in data:
                        key = item["Key"]
                        try:
                            payload = json.loads(item["Value"].decode("utf-8"))
                            all_configs[key] = payload.get("value")
                        except (json.JSONDecodeError, KeyError):
                            all_configs[key] = item["Value"].decode("utf-8")
        except Exception as e:
            _logger.error(f"Failed to get all configs: {e}")
        return all_configs

    def get_fallback_configs(self) -> Dict[str, ConfigItem]:
        """获取stub配置（用于测试）"""
        return dict(self.fallback_config)


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
        instance = {
            "service_name": service_name,
            "service_id": service_id,
            "address": address,
            "port": port,
            "tags": tags or [],
        }
        self.services.setdefault(service_name, [])
        # 去重：替换相同 service_id 的实例
        self.services[service_name] = [
            s for s in self.services[service_name] if s["service_id"] != service_id
        ]
        self.services[service_name].append(instance)
        _logger.info(f"Registered service: {service_name}/{service_id} at {address}:{port}")

    def deregister_service(self, service_id: str):
        """注销服务"""
        for service_name, instances in self.services.items():
            self.services[service_name] = [s for s in instances if s["service_id"] != service_id]
        _logger.info(f"Deregistered service instance: {service_id}")

    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """发现服务"""
        return list(self.services.get(service_name, []))


# 全局实例
CONSUL_CONFIG_CENTER = ConsulConfigCenter()
SERVICE_DISCOVERY = ServiceDiscovery(CONSUL_CONFIG_CENTER)


def get_config_center() -> ConsulConfigCenter:
    """获取配置中心实例"""
    return CONSUL_CONFIG_CENTER


def get_service_discovery() -> ServiceDiscovery:
    """获取服务发现实例"""
    return SERVICE_DISCOVERY
