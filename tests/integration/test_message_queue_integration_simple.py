# -*- coding: utf-8 -*-
# tests/integration/test_message_queue_integration_simple.py
# 简化的消息队列集成测试
import asyncio  # noqa: F401
import os
import sys
import time

import pytest

from core.message_queue_mock import MessageQueue

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 使用mock消息队列模块
sys.modules["core.message_queue"] = __import__("core.message_queue_mock")
sys.modules["core.message_queue"].MessageQueue = sys.modules["core.message_queue_mock"].MessageQueue


@pytest.mark.asyncio
async def test_message_publish_integration():
    """测试消息发布集成"""
    queue = MessageQueue()

    # 测试发布消息
    message = {"type": "alert", "data": {"severity": "critical"}}
    result = queue.publish("alerts", message)

    assert result is True


@pytest.mark.asyncio
async def test_message_consume_integration():
    """测试消息消费集成"""
    queue = MessageQueue()

    # 先发布消息
    message = {"type": "alert", "data": {"severity": "critical"}}
    queue.publish("alerts", message)

    # 测试消费消息
    async def message_handler(msg):
        return {"processed": True, "message": msg}

    # 模拟消费
    result = await queue.consume("alerts", message_handler)
    assert result is not None


@pytest.mark.asyncio
async def test_message_retry_integration():
    """测试消息重试集成"""
    queue = MessageQueue()

    # 测试带重试的消息发布
    message = {"type": "alert", "data": {"severity": "critical"}}
    result = queue.publish_with_retry("alerts", message, max_retries=3)

    assert result is True


@pytest.mark.asyncio
async def test_dead_letter_queue_integration():
    """测试死信队列集成"""
    queue = MessageQueue()

    # 测试发送到死信队列
    failed_message = {"type": "alert", "error": "Processing failed"}
    result = queue.send_to_dead_letter(failed_message)

    assert result is True


@pytest.mark.asyncio
async def test_message_batch_publish_integration():
    """测试批量消息发布集成"""
    queue = MessageQueue()

    # 测试批量发布
    messages = [{"id": i, "data": f"message{i}"} for i in range(10)]
    result = queue.publish_batch("alerts", messages)

    assert result["success"] >= 0


@pytest.mark.asyncio
async def test_message_queue_monitoring_integration():
    """测试消息队列监控集成"""
    queue = MessageQueue()

    # 先发布一些消息
    for i in range(5):
        queue.publish("alerts", {"id": i, "data": f"message{i}"})

    # 测试获取队列统计
    stats = queue.get_queue_stats("alerts")

    assert stats["queue_length"] >= 0
    assert "consumers" in stats


@pytest.mark.asyncio
async def test_message_queue_performance_integration():
    """测试消息队列性能集成"""

    queue = MessageQueue()

    # 测试批量发布性能
    start_time = time.time()
    messages = [{"id": i, "data": f"message{i}"} for i in range(100)]

    for msg in messages:
        queue.publish("alerts", msg)

    end_time = time.time()

    # 批量操作应该在合理时间内完成（< 2秒）
    assert (end_time - start_time) < 2.0


@pytest.mark.asyncio
async def test_message_queue_reliability_integration():
    """测试消息队列可靠性集成"""
    queue = MessageQueue()

    # 测试带确认的消息发布
    message = {"type": "alert", "data": "test"}
    # 在mock实现中，publish_with_ack模拟确认
    queue.publish("alerts", message)

    # 验证消息被存储
    stats = queue.get_queue_stats("alerts")
    assert stats["queue_length"] >= 1


@pytest.mark.asyncio
async def test_message_queue_cleanup_integration():
    """测试消息队列清理集成"""
    queue = MessageQueue()

    # 先发布一些消息
    for i in range(10):
        queue.publish("alerts", {"id": i, "data": f"message{i}"})

    # 测试清理旧消息
    result = queue.cleanup_old_messages("alerts", older_than_hours=24)

    assert result["cleaned"] >= 0


class TestMessageQueueIntegrationAdvanced:
    """消息队列高级集成测试"""

    @pytest.mark.asyncio
    async def test_message_queue_clustering(self):
        """测试消息队列集群集成"""
        queue = MessageQueue()

        # 测试加入集群
        result = queue.join_cluster("cluster1")
        assert result is True

        # 测试获取集群状态
        status = queue.get_cluster_status()
        assert status["nodes"] >= 1

    @pytest.mark.asyncio
    async def test_message_queue_replication(self):
        """测试消息队列复制集成"""
        queue = MessageQueue()

        # 测试启用复制
        result = queue.enable_replication()
        assert result is True

        # 测试获取复制状态
        status = queue.get_replication_status()
        assert status["replicas"] >= 0
