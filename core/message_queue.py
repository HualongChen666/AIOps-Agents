# -*- coding: utf-8 -*-
"""In-memory message queue backend with optional JSON persistence.

Production deployments should replace this with RabbitMQ/Kafka by setting the
``MESSAGE_QUEUE_BACKEND`` environment variable. The default in-memory store is
kept for local development and tests.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import BASE_DIR

try:
    from core.prometheus_metrics import get_metrics_exporter
except Exception:
    get_metrics_exporter = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_PERSISTENCE_FILE: Path = BASE_DIR / "data" / "message_queue_state.json"


def _record_queue_depth(queue_name: str, depth: int) -> None:
    if callable(get_metrics_exporter):
        try:
            get_metrics_exporter().record_queue_depth(queue_name, depth)
        except Exception:
            pass


def _try_real_publish(queue_name: str, message: Dict[str, Any]) -> bool:
    """Attempt to publish to a real backend if configured (RabbitMQ/Kafka)."""
    backend = os.getenv("MESSAGE_QUEUE_BACKEND", "").lower()
    if backend == "rabbitmq":
        try:
            import pika

            params = pika.URLParameters(os.environ["RABBITMQ_URL"])
            with pika.BlockingConnection(params) as conn:
                ch = conn.channel()
                ch.queue_declare(queue=queue_name, durable=True)
                ch.basic_publish(exchange="", routing_key=queue_name,
                                 body=json.dumps(message).encode())
            return True
        except Exception as exc:
            logger.warning(f"RabbitMQ publish failed: {exc}; fallback to memory")
    elif backend == "kafka":
        try:
            from kafka import KafkaProducer

            producer = KafkaProducer(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"])
            producer.send(queue_name, value=message)
            producer.flush()
            producer.close()
            return True
        except Exception as exc:
            logger.warning(f"Kafka publish failed: {exc}; fallback to memory")
    return False


class MessageQueue:
    """In-memory message queue backend with optional real-backend publish."""

    def __init__(self, persistence_file: Optional[Path] = None):
        self._queues: Dict[str, List[Dict[str, Any]]] = {}
        self._dead_letter_queue: List[Dict[str, Any]] = []
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._transaction_states: Dict[str, Dict[str, Any]] = {}
        self._consumers_target: Dict[str, int] = {}
        self._persistence_enabled = False
        self._persistence_file = persistence_file or _PERSISTENCE_FILE
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _save(self) -> None:
        if not self._persistence_enabled:
            return
        try:
            self._persistence_file.parent.mkdir(parents=True, exist_ok=True)
            self._persistence_file.write_text(
                json.dumps(
                    {"queues": self._queues, "dlq": self._dead_letter_queue},
                    ensure_ascii=False,
                    default=str,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning(f"Failed to persist message queue state: {exc}")

    def _load(self) -> None:
        try:
            if self._persistence_file.is_file():
                payload = json.loads(self._persistence_file.read_text(encoding="utf-8"))
                self._queues = payload.get("queues", {})
                self._dead_letter_queue = payload.get("dlq", [])
        except Exception as exc:
            logger.debug(f"No previous message queue state to load: {exc}")

    def enable_persistence(self) -> bool:
        self._persistence_enabled = True
        self._save()
        return True

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------
    def publish(self, queue_name: str, message: Dict[str, Any]) -> bool:
        if _try_real_publish(queue_name, message):
            return True
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].append(
            {"message": message, "timestamp": time.time(), "status": "pending"}
        )
        _record_queue_depth(queue_name, len(self._queues[queue_name]))
        self._save()
        return True

    def publish_with_retry(
        self, queue_name: str, message: Dict[str, Any], max_retries: int = 3
    ) -> bool:
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
        if _try_real_publish(queue_name, message):
            return True
        if queue_name not in self._queues:
            self._queues[queue_name] = []

        message_data = {
            "message": message,
            "timestamp": time.time(),
            "status": "pending",
            "priority": priority,
        }
        inserted = False
        for i, msg in enumerate(self._queues[queue_name]):
            if msg.get("priority", 0) < priority:
                self._queues[queue_name].insert(i, message_data)
                inserted = True
                break
        if not inserted:
            self._queues[queue_name].append(message_data)

        _record_queue_depth(queue_name, len(self._queues[queue_name]))
        self._save()
        return True

    def publish_batch(self, queue_name: str, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        success = 0
        failed = 0
        for message in messages:
            if self.publish(queue_name, message):
                success += 1
            else:
                failed += 1
        return {"success": success, "failed": failed}

    async def consume(self, queue_name: str, handler: Callable) -> Any:
        if queue_name in self._queues and self._queues[queue_name]:
            message_data = self._queues[queue_name].pop(0)
            _record_queue_depth(queue_name, len(self._queues[queue_name]))
            try:
                result = await handler(message_data["message"])
                message_data["status"] = "processed"
                self._save()
                return result
            except Exception as e:
                message_data["status"] = "failed"
                self.send_to_dead_letter(message_data)
                raise e
        return None

    def ack_message(self, message_id: str) -> bool:
        return True

    def send_to_dead_letter(self, message_data: Dict[str, Any]) -> bool:
        self._dead_letter_queue.append(message_data)
        self._save()
        return True

    def subscribe_with_filter(self, queue_name: str, filter_func: Callable) -> bool:
        self._subscriptions.setdefault(queue_name, []).append(filter_func)
        return True

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    def begin_transaction(self) -> str:
        txn_id = f"txn_{int(time.time() * 1000)}"
        self._transaction_states[txn_id] = {"status": "active", "operations": []}
        return txn_id

    def commit_transaction(self, txn_id: str) -> bool:
        if txn_id in self._transaction_states:
            self._transaction_states[txn_id]["status"] = "committed"
            self._save()
            return True
        return False

    def rollback_transaction(self, txn_id: str) -> bool:
        if txn_id in self._transaction_states:
            self._transaction_states[txn_id]["status"] = "rolled_back"
            # naive rollback: replay recorded operations is not implemented; this is best-effort
            return True
        return False

    # ------------------------------------------------------------------
    # Monitoring / scaling
    # ------------------------------------------------------------------
    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        q = self._queues.get(queue_name, [])
        consumers = len(self._subscriptions.get(queue_name, []))
        return {
            "queue_length": len(q),
            "consumers": consumers,
            "message_rate": round(len(q) / max(time.time() - q[-1]["timestamp"], 1.0), 4) if q else 0.0,
        }

    def scale_consumers(self, queue_name: str, target_count: int) -> bool:
        self._consumers_target[queue_name] = target_count
        return True

    def get_cluster_status(self) -> Dict[str, Any]:
        total_messages = sum(len(q) for q in self._queues.values())
        return {
            "nodes": 1,
            "status": "healthy",
            "queues": len(self._queues),
            "total_messages": total_messages,
            "dead_letter_count": len(self._dead_letter_queue),
        }

    def join_cluster(self, cluster_name: str) -> bool:
        logger.info(f"Joined logical cluster: {cluster_name}")
        return True

    def enable_replication(self) -> bool:
        return True

    def get_replication_status(self) -> Dict[str, Any]:
        return {"replicas": 0, "lag_ms": 0, "mode": "memory" if not os.getenv(
            "MESSAGE_QUEUE_BACKEND") else "configured"}

    # ------------------------------------------------------------------
    # Backup / restore / cleanup
    # ------------------------------------------------------------------
    def create_backup(self, queue_name: str) -> Dict[str, Any]:
        backup = {
            "queue": queue_name,
            "messages": self._queues.get(queue_name, []),
            "timestamp": time.time(),
        }
        backup_path = self._persistence_file.parent / f"backup_{queue_name}_{int(time.time())}.json"
        try:
            backup_path.write_text(json.dumps(backup, ensure_ascii=False,
                                   default=str), encoding="utf-8")
            return {"backup_file": str(backup_path), "size_mb": len(str(backup)) / 1024 / 1024}
        except Exception as exc:
            return {"backup_file": None, "error": str(exc)}

    def restore_backup(self, backup_file: str) -> bool:
        try:
            path = Path(backup_file)
            payload = json.loads(path.read_text(encoding="utf-8"))
            queue_name = payload.get("queue")
            if queue_name:
                self._queues[queue_name] = payload.get("messages", [])
                self._save()
                return True
            return False
        except Exception as exc:
            logger.error(f"Restore failed: {exc}")
            return False

    def cleanup_old_messages(self, queue_name: str, older_than_hours: int = 24) -> Dict[str, int]:
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        if queue_name in self._queues:
            original_length = len(self._queues[queue_name])
            self._queues[queue_name] = [
                msg for msg in self._queues[queue_name] if msg["timestamp"] > cutoff_time
            ]
            cleaned = original_length - len(self._queues[queue_name])
            _record_queue_depth(queue_name, len(self._queues[queue_name]))
            self._save()
            return {"cleaned": cleaned}
        _record_queue_depth(queue_name, 0)
        return {"cleaned": 0}
