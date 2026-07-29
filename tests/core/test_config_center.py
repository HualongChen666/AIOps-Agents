# -*- coding: utf-8 -*-
"""测试配置中心适配器"""

import pytest

from core.config_center import (
    ConfigChangeEvent,
    ConfigEventType,
    ConfigItem,
    ConsulConfigCenter,
    ServiceDiscovery,
    get_config_center,
    get_service_discovery,
)


class TestConfigDataClasses:
    """测试数据类"""

    def test_config_item_defaults(self):
        item = ConfigItem(key="k", value="v")
        assert item.key == "k"
        assert item.value == "v"
        assert item.metadata == {}

    def test_config_change_event(self):
        event = ConfigChangeEvent(
            key="k",
            old_value="old",
            new_value="new",
            event_type=ConfigEventType.UPDATE,
        )
        assert event.event_type == ConfigEventType.UPDATE


class TestConsulConfigCenter:
    """测试 ConsulConfigCenter（component 模式）"""

    def test_init_uses_stub(self):
        center = ConsulConfigCenter()
        assert center.stub_enabled is True

    def test_set_and_get_config(self):
        center = ConsulConfigCenter()
        assert center.set_config("key1", "value1", {"meta": True}) is True
        assert center.get_config("key1") == "value1"
        assert center.get_config("missing", default="default") == "default"

    def test_set_config_updates_version(self):
        center = ConsulConfigCenter()
        center.set_config("k", 1)
        center.set_config("k", 2)
        item = center.stub_config["k"]
        assert item.version == 1

    def test_delete_config(self):
        center = ConsulConfigCenter()
        center.set_config("del", "x")
        assert center.delete_config("del") is True
        assert center.delete_config("del") is False
        assert center.get_config("del") is None

    def test_get_all_configs(self):
        center = ConsulConfigCenter()
        center.set_config("a", 1)
        center.set_config("b", 2)
        all_configs = center.get_all_configs()
        assert all_configs == {"a": 1, "b": 2}

    def test_change_listener(self):
        center = ConsulConfigCenter()
        events = []

        def listener(event):
            events.append(event)

        center.register_change_listener(listener)
        center.set_config("listen", "value")
        center.delete_config("listen")
        assert len(events) == 2
        assert events[0].event_type == ConfigEventType.CREATE
        assert events[-1].event_type == ConfigEventType.DELETE

    def test_change_listener_exception_handled(self, caplog):
        center = ConsulConfigCenter()

        def bad_listener(event):
            raise RuntimeError("boom")

        center.register_change_listener(bad_listener)
        center.set_config("x", 1)
        assert len(center.stub_config) == 1

    def test_get_stub_configs(self):
        center = ConsulConfigCenter()
        center.set_config("x", 1)
        assert "x" in center.get_stub_configs()

    def test_watch_config_stub(self, caplog):
        center = ConsulConfigCenter()
        # Should not raise in component mode
        center.watch_config("key", lambda v: None)


class TestServiceDiscovery:
    """测试服务发现（component 模式）"""

    def test_register_and_discover_service(self):
        center = ConsulConfigCenter()
        discovery = ServiceDiscovery(center)
        discovery.register_service("api", "api-1", "127.0.0.1", 8000, ["v1"])
        services = discovery.discover_service("api")
        assert len(services) == 1
        assert services[0]["service_id"] == "api-1"

    def test_deregister_service(self):
        center = ConsulConfigCenter()
        discovery = ServiceDiscovery(center)
        discovery.register_service("api", "api-1", "127.0.0.1", 8000)
        discovery.register_service("api", "api-2", "127.0.0.1", 8001)
        discovery.deregister_service("api-1")
        services = discovery.discover_service("api")
        assert len(services) == 1
        assert services[0]["service_id"] == "api-2"

    def test_discover_missing_service(self):
        center = ConsulConfigCenter()
        discovery = ServiceDiscovery(center)
        assert discovery.discover_service("missing") == []


class TestModuleFunctions:
    """测试模块级函数"""

    def test_get_config_center_singleton(self):
        c1 = get_config_center()
        c2 = get_config_center()
        assert c1 is c2

    def test_get_service_discovery_singleton(self):
        s1 = get_service_discovery()
        s2 = get_service_discovery()
        assert s1 is s2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
