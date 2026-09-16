# -*- coding: utf-8 -*-
"""
中危台账批次 19 回归测试 · core/ 部分（2026-09-16）
====================================================

覆盖条目：
- F438 core/service_mesh_repository.py  Gateway 配置真实落库（create/get/list/update/delete）
- F255 core/kafka_stream_processor.py   真实按需创建 producer/consumer（非恒 None）
- F256 core/key_management.py            主密钥经 SHA-256 派生（不再 pad/截断）
"""

import importlib
import os
from unittest import mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.key_management import KeyEncryptionService
from core.models import MeshGateway
from core.service_mesh_repository import ServiceMeshRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


# ---------------------------------------------------------------------------
# F438 — gateway configs are really persisted
# ---------------------------------------------------------------------------
def test_gateway_config_round_trip(db_session):
    repo = ServiceMeshRepository(db_session)
    created = repo.create_gateway_config(
        name="gw-ingress",
        gateway_type="ingress",
        selector={"istio": "ingressgateway"},
        servers=[{"port": {"number": 80, "protocol": "HTTP"}}],
        config_metadata={"tier": "prod"},
    )
    assert created["id"]
    assert created["name"] == "gw-ingress"

    # 真实读回（此前恒返回 {"name": "sample-gateway"} 的占位）
    fetched = repo.get_gateway_config(created["id"])
    assert fetched is not None
    assert fetched["name"] == "gw-ingress"
    assert fetched["gateway_type"] == "ingress"
    assert fetched["servers"][0]["port"]["number"] == 80
    assert fetched["config_metadata"] == {"tier": "prod"}

    # 列表真实返回（此前恒 []）
    assert any(g["id"] == created["id"] for g in repo.list_gateway_configs())
    assert [g["id"] for g in repo.list_gateway_configs(gateway_type="egress")] == []

    # 更新 / 删除真实作用于存储
    updated = repo.update_gateway_config(created["id"], name="gw-renamed", enabled=False)
    assert updated["name"] == "gw-renamed"
    assert updated["enabled"] is False

    assert repo.delete_gateway_config(created["id"]) is True
    assert repo.get_gateway_config(created["id"]) is None
    assert repo.delete_gateway_config(created["id"]) is False


def test_gateway_model_registered():
    assert MeshGateway.__tablename__ == "mesh_gateways"


# ---------------------------------------------------------------------------
# F255 — kafka producer/consumer are really created on demand
# ---------------------------------------------------------------------------
class _FakeProducer:
    instances = []

    def __init__(self, *args, **kwargs):
        self.sent = []
        self.flushed = 0
        _FakeProducer.instances.append(self)

    def send(self, topic, key=None, value=None):
        self.sent.append((topic, key, value))

    def flush(self):
        self.flushed += 1


class _FakeConsumer:
    def __init__(self, *args, **kwargs):
        self.subscribed = []

    def subscribe(self, topics):
        self.subscribed = topics

    def poll(self, timeout_ms=100):
        return {}


def test_kafka_producer_created_from_env(monkeypatch):
    import core.kafka_stream_processor as mod

    monkeypatch.setattr(mod, "KAFKA_AVAILABLE", True)
    monkeypatch.setattr(mod, "KafkaProducer", _FakeProducer)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")

    proc = mod.KafkaStreamProcessor()
    assert proc.producer is None  # lazy
    assert proc.send_message("metrics-topic", "k1", {"v": 1}) is True
    assert proc.producer is not None  # 真实创建（此前恒 None）
    assert proc.producer.sent[0][0] == "metrics-topic"
    assert proc.cached_messages == []  # 真实发送，未走本地缓存


def test_kafka_consumer_created_from_env(monkeypatch):
    import core.kafka_stream_processor as mod

    monkeypatch.setattr(mod, "KAFKA_AVAILABLE", True)
    monkeypatch.setattr(mod, "KafkaConsumer", _FakeConsumer)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")

    proc = mod.KafkaStreamProcessor()
    list(proc.consume_messages("metrics-topic", "g1"))
    assert proc.consumer is not None
    assert proc.consumer.subscribed == ["metrics-topic"]
    # 同一 group 复用同一个 consumer
    consumer = proc.consumer
    list(proc.consume_messages("metrics-topic", "g1"))
    assert proc.consumer is consumer


def test_kafka_offline_when_broker_unreachable(monkeypatch):
    import core.kafka_stream_processor as mod

    class _BoomProducer:
        def __init__(self, *a, **k):
            raise RuntimeError("NoBrokersAvailable")

    monkeypatch.setattr(mod, "KAFKA_AVAILABLE", True)
    monkeypatch.setattr(mod, "KafkaProducer", _BoomProducer)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")

    proc = mod.KafkaStreamProcessor()
    assert proc.send_message("metrics-topic", "k1", {"v": 1}) is True
    assert proc.producer is None
    assert len(proc.cached_messages) == 1  # 回退本地缓存


def test_kafka_no_bootstrap_stays_offline(monkeypatch):
    import core.kafka_stream_processor as mod

    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    proc = mod.KafkaStreamProcessor()
    assert proc.send_message("t", "k", {"v": 1}) is True
    assert len(proc.cached_messages) == 1


# ---------------------------------------------------------------------------
# F256 — master key is derived (SHA-256), not padded/truncated
# ---------------------------------------------------------------------------
def test_master_key_derivation_distinguishes_lengths():
    # 旧实现：ljust('0')/截断 → 这两个不同输入会得到同一 32 字符密钥
    short = KeyEncryptionService(master_key="a")
    padded = KeyEncryptionService(master_key="a" + "0" * 31)
    assert short._key_bytes != padded._key_bytes
    assert len(short._key_bytes) == 32
    # 原始主密钥不被静默改写
    assert short.master_key == "a"
    assert padded.master_key == "a" + "0" * 31


def test_master_key_round_trip_encrypt_decrypt():
    svc = KeyEncryptionService(master_key="a-very-long-master-key-material")
    ct, iv = svc.encrypt("secret-value")
    assert svc.decrypt(ct, iv) == "secret-value"
    assert len(svc._key_bytes) == 32
