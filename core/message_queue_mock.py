# -*- coding: utf-8 -*-
# core/message_queue_mock.py
# 消息队列的Mock实现
# 用于测试目的，提供基本的消息队列功能

import time
from typing import Any, Callable, Dict, List


class MessageQueue:
    """消息队列的Mock实现"""

    def __init__(self):
        self._queues: Dict[str, List[Dict[str, Any]]] = {}
        self._dead_letter_queue: List[Dict[str, Any]] = []
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._transaction_states: Dict[str, Dict[str, Any]] = {}

    def publish(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].append(
            {"message": message, "timestamp": time.time(), "status": "pending"}
        )
        return True

    def publish_with_retry(
        self, queue_name: str, message: Dict[str, Any], max_retries: int = 3
    ) -> bool:
        """带重试的消息发布"""
        retry_count = 0
        while retry_count < max_retries:
            if self.publish(queue_name, message):
                return True
            retry_count += 1
            time.sleep(0.1)
        return False

    def publish_with_priority(
        self, queue_name: str, message: Dict[str, Any], priority: int = 0
    ) -> bool:
        """带优先级的消息发布"""
        if queue_name not in self._queues:
            self._queues[queue_name] = []

        # 根据优先级插入
        message_data = {
            "message": message,
            "timestamp": time.time(),
            "status": "pending",
            "priority": priority,
        }

        # 简单的优先级插入逻辑
        inserted = False
        for i, msg in enumerate(self._queues[queue_name]):
            if msg.get("priority", 0) < priority:
                self._queues[queue_name].insert(i, message_data)
                inserted = True
                break

        if not inserted:
            self._queues[queue_name].append(message_data)

        return True

    def publish_batch(self, queue_name: str, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量发布消息"""
        success = 0
        failed = 0

        for message in messages:
            if self.publish(queue_name, message):
                success += 1
            else:
                failed += 1

        return {"success": success, "failed": failed}

    async def consume(self, queue_name: str, handler: Callable) -> Any:
        """消费消息"""
        if queue_name in self._queues and self._queues[queue_name]:
            message_data = self._queues[queue_name].pop(0)
            try:
                result = await handler(message_data["message"])
                message_data["status"] = "processed"
                return result
            except Exception as e:
                message_data["status"] = "failed"
                self.send_to_dead_letter(message_data)
                raise e
        return None

    def ack_message(self, message_id: str) -> bool:
        """确认消息"""
        # 在mock实现中，消息被消费后自动确认
        return True

    def send_to_dead_letter(self, message_data: Dict[str, Any]) -> bool:
        """发送到死信队列"""
        self._dead_letter_queue.append(message_data)
        return True

    def subscribe_with_filter(self, queue_name: str, filter_func: Callable) -> bool:
        """带过滤的订阅"""
        if queue_name not in self._subscriptions:
            self._subscriptions[queue_name] = []
        self._subscriptions[queue_name].append(filter_func)
        return True

    def enable_persistence(self) -> bool:
        """启用持久化"""
        # 在mock实现中，持久化是默认的（内存存储）
        return True

    def begin_transaction(self) -> str:
        """开始事务"""
        txn_id = f"txn_{int(time.time())}"
        self._transaction_states[txn_id] = {"status": "active", "operations": []}
        return txn_id

    def commit_transaction(self, txn_id: str) -> bool:
        """提交事务"""
        if txn_id in self._transaction_states:
            self._transaction_states[txn_id]["status"] = "committed"
            return True
        return False

    def rollback_transaction(self, txn_id: str) -> bool:
        """回滚事务"""
        if txn_id in self._transaction_states:
            self._transaction_states[txn_id]["status"] = "rolled_back"
            return True
        return False

    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """获取队列统计信息"""
        if queue_name in self._queues:
            return {
                "queue_length": len(self._queues[queue_name]),
                "consumers": len(self._subscriptions.get(queue_name, [])),
                "message_rate": 0.0,
            }
        return {"queue_length": 0, "consumers": 0, "message_rate": 0.0}

    def scale_consumers(self, queue_name: str, target_count: int) -> bool:
        """扩展消费者"""
        # 在mock实现中，只是记录目标数量
        return True

    def join_cluster(self, cluster_name: str) -> bool:
        """加入集群"""
        return True

    def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        return {"nodes": 1, "status": "healthy"}

    def enable_replication(self) -> bool:
        """启用复制"""
        return True

    def get_replication_status(self) -> Dict[str, Any]:
        """获取复制状态"""
        return {"replicas": 0, "lag_ms": 0}

    def create_backup(self, queue_name: str) -> Dict[str, Any]:
        """创建备份"""
        backup_data = {
            "backup_file": f"backup_{queue_name}_{int(time.time())}.dat",
            "size_mb": len(str(self._queues.get(queue_name, []))) / 1024 / 1024,
        }
        return backup_data

    def restore_backup(self, backup_file: str) -> bool:
        """恢复备份"""
        return True

    def cleanup_old_messages(self, queue_name: str, older_than_hours: int = 24) -> Dict[str, int]:
        """清理旧消息"""
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)

        if queue_name in self._queues:
            original_length = len(self._queues[queue_name])
            self._queues[queue_name] = [
                msg for msg in self._queues[queue_name] if msg["timestamp"] > cutoff_time
            ]
            cleaned = original_length - len(self._queues[queue_name])
            return {"cleaned": cleaned}

        return {"cleaned": 0}
