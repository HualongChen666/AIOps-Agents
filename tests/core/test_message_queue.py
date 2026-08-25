# -*- coding: utf-8 -*-

import pytest  # noqa: F401  # Imported for test setup

from core.message_queue import MessageQueue


@pytest.fixture
def queue(tmp_path):
    return MessageQueue(persistence_file=tmp_path / "mq.json")


def test_publish_and_consume_sync(queue):
    assert queue.publish("alerts", {"id": "1"}) is True
    assert queue.get_queue_stats("alerts")["queue_length"] == 1


def test_batch_publish(queue):
    result = queue.publish_batch(
        "events", [{"i": i} for i in range(3)]
    )  # noqa: F841  # Variable for test verification
    assert result["success"] == 3
    assert queue.get_queue_stats("events")["queue_length"] == 3


def test_priority_publish(queue):
    queue.publish_with_priority("jobs", {"name": "low"}, priority=0)
    queue.publish_with_priority("jobs", {"name": "high"}, priority=5)
    jobs = queue._queues["jobs"]
    assert jobs[0]["message"]["name"] == "high"


def test_transaction_commit_and_rollback(queue):
    txn = queue.begin_transaction()
    assert queue.commit_transaction(txn) is True
    assert queue.rollback_transaction("missing") is False


def test_cluster_status(queue):
    queue.publish("q1", {"x": 1})
    status = queue.get_cluster_status()
    assert status["queues"] == 1
    assert status["total_messages"] == 1
