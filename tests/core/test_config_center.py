# -*- coding: utf-8 -*-
"""Tests for core/config_center.py."""

from core.config_center import (
    ConsulConfigCenter,
    ServiceDiscovery,
    get_config_center,
    get_service_discovery,
)


def test_consul_config_center_fallback():
    center = ConsulConfigCenter()
    assert center.set_config("key1", "value1") is True
    assert center.get_config("key1") == "value1"
    assert center.get_config_item("key1").value == "value1"
    assert center.get_config("missing", "default") == "default"
    assert center.get_all_configs() == {"key1": "value1"}
    assert center.delete_config("key1") is True
    assert center.delete_config("key1") is False


def test_change_listener_and_watch():
    center = ConsulConfigCenter()
    events = []
    center.register_change_listener(lambda e: events.append(e.key))
    center.set_config("k", 1)
    center.set_config("k", 2)
    center.delete_config("k")
    assert len(events) == 3
    # watch_config fallback returns without starting a thread
    center.watch_config("k", lambda v: None)


def test_service_discovery_and_getters():
    center = get_config_center()
    sd = get_service_discovery()
    sd2 = ServiceDiscovery(center)
    sd2.register_service("svc", "id1", "127.0.0.1", 8080, tags=["a"])
    sd2.register_service("svc", "id1", "127.0.0.1", 8081, tags=["b"])
    assert len(sd2.discover_service("svc")) == 1
    assert sd2.discover_service("svc")[0]["port"] == 8081
    sd2.deregister_service("id1")
    assert sd2.discover_service("svc") == []
    assert sd is not None
