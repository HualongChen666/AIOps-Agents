# -*- coding: utf-8 -*-
"""Kafka流处理适配器

实现Kafka消息队列的集成，支持实时数据流处理
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer: Any = None  # type: ignore
    KafkaConsumer: Any = None  # type: ignore
    KafkaError = Exception


_logger = logging.getLogger(__name__)


class KafkaTopic(str, Enum):
    """Kafka主题枚举"""

    METRICS = "metrics-topic"
    LOGS = "logs-topic"
    TRACES = "traces-topic"
    ALERTS = "alerts-topic"
    REPAIR = "repair-topic"


@dataclass
class KafkaMessage:
    """Kafka消息数据类"""

    topic: str
    key: str
    value: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    headers: Dict[str, str] = field(default_factory=dict)


class KafkaStreamProcessor:
    """Kafka流处理器"""

    def __init__(self):
        """初始化Kafka流处理器"""
        self._initialized = True
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.cached_messages: List[KafkaMessage] = []
        self.producer: Any = None
        self.consumer: Any = None

    def send_message(
        self, topic: str, key: str, value: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """发送Kafka消息（优先真实 KafkaProducer，否则缓存到 cached_messages）。"""
        message = KafkaMessage(
            topic=topic,
            key=key,
            value=value,
            headers=headers or {},
        )

        if KAFKA_AVAILABLE and self.producer:
            try:
                self.producer.send(topic, key=key.encode(), value=json.dumps(value).encode())
                self._send_success(message)
                return True
            except Exception as e:
                self._send_error(message, e)
                return False

        # 离线模式：缓存到内存
        self.cached_messages.append(message)
        _logger.info(f"Message cached locally for topic {topic}: {key}")
        return True

    def _send_success(self, message: KafkaMessage):
        """消息发送成功回调"""
        _logger.debug(f"Successfully sent message to {message.topic}: {message.key}")

    def _send_error(self, message: KafkaMessage, error):
        """消息发送错误回调"""
        _logger.error(f"Failed to send message to {message.topic}: {message.key}, error: {error}")

    def register_handler(self, topic: str, handler: Callable):
        """注册消息处理器"""
        if topic not in self.message_handlers:
            self.message_handlers[topic] = []
        self.message_handlers[topic].append(handler)
        _logger.info(f"Registered handler for topic: {topic}")

    def consume_messages(self, topic: str, group_id: str, auto_commit: bool = True):
        """消费Kafka消息（优先真实 KafkaConsumer，否则从缓存读取）。"""
        _logger.info(f"Consuming messages from topic {topic} with group {group_id}")

        if KAFKA_AVAILABLE and self.consumer:
            try:
                self.consumer.subscribe([topic])
                for _ in range(100):
                    raw = self.consumer.poll(timeout_ms=100)
                    for t, records in raw.items():
                        for record in records:
                            try:
                                value = (
                                    json.loads(record.value.decode("utf-8"))
                                    if isinstance(record.value, bytes)
                                    else record.value
                                )
                            except Exception as e:
                                logging.exception("Unexpected exception: %s", e)
                                value = record.value
                            yield KafkaMessage(
                                topic=t.topic,
                                key=(
                                    (record.key or "").decode("utf-8")
                                    if isinstance(record.key, bytes)
                                    else str(record.key or "")
                                ),
                                value=value,
                                headers=dict(record.headers or {}),
                            )
            except Exception as e:
                _logger.error(f"Kafka consumer error: {e}")

        # 离线模式：返回缓存中匹配 topic 的消息
        for msg in list(self.cached_messages):
            if msg.topic == topic:
                yield msg

    def get_stub_messages(self) -> List[KafkaMessage]:
        """获取本地缓存消息（用于测试或离线模式）"""
        return list(self.cached_messages)

    def clear_stub_messages(self):
        """清空本地缓存消息"""
        cleared = len(self.cached_messages)
        self.cached_messages.clear()
        _logger.info(f"Cleared {cleared} cached messages")


class BackpressureController:
    """背压控制器"""

    def __init__(self, threshold: float = 0.8, max_backoff: int = 60):
        """初始化背压控制器"""
        self.threshold = threshold
        self.max_backoff = max_backoff
        self.current_backoff = 0
        self.load_history: List[float] = []

    def check_backpressure(self, current_load: float) -> bool:
        """检查是否需要背压"""
        self.load_history.append(current_load)
        if len(self.load_history) > 100:
            self.load_history = self.load_history[-100:]

        avg_load = sum(self.load_history) / len(self.load_history)

        if avg_load > self.threshold:
            self.current_backoff = min(self.current_backoff * 2, self.max_backoff)
            _logger.warning(f"Backpressure triggered, current backoff: {self.current_backoff}s")
            return True

        self.current_backoff = max(0, self.current_backoff - 1)
        return False

    def get_backoff_delay(self) -> int:
        """获取背压延迟"""
        return self.current_backoff


class TokenBucket:
    """令牌桶算法实现"""

    def __init__(self, capacity: int, rate: float):
        """初始化令牌桶

        Args:
            capacity: 桶容量
            rate: 令牌生成速率（每秒）
        """
        self.capacity = capacity
        self.rate = rate
        self.tokens: float = float(capacity)
        self.last_update = datetime.now(timezone.utc)

    def consume(self, tokens: int = 1) -> bool:
        """消费令牌"""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_update).total_seconds()

        # 补充令牌
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_available_tokens(self) -> int:
        """获取可用令牌数"""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_update).total_seconds()
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        return int(self.tokens)


class DataQualityValidator:
    """数据质量验证器"""

    def __init__(self):
        """初始化数据质量验证器"""
        self.validators = {}
        self.validation_stats = {"total_validations": 0, "total_valid": 0, "total_invalid": 0}

    def register_validator(self, data_type: str, validator: Callable):
        """注册验证器"""
        self.validators[data_type] = validator
        _logger.info(f"Registered validator for data type: {data_type}")

    def validate(self, data: Dict[str, Any], data_type: str) -> bool:
        """验证数据质量"""
        self.validation_stats["total_validations"] += 1

        if data_type not in self.validators:
            _logger.warning(f"No validator for data type: {data_type}, skipping validation")
            self.validation_stats["total_valid"] += 1
            return True

        try:
            is_valid = bool(self.validators[data_type](data))
            if is_valid:
                self.validation_stats["total_valid"] += 1
            else:
                self.validation_stats["total_invalid"] += 1
            return is_valid
        except Exception as e:
            _logger.error(f"Validation error for data type {data_type}: {e}")
            self.validation_stats["total_invalid"] += 1
            return False

    def get_validation_stats(self) -> Dict[str, Any]:
        """获取验证统计"""
        total = self.validation_stats["total_validations"]
        if total > 0:
            valid_rate = self.validation_stats["total_valid"] / total
        else:
            valid_rate = 0.0

        return {**self.validation_stats, "valid_rate": valid_rate}


# 全局实例
kafka_processor = KafkaStreamProcessor()
backpressure_controller = BackpressureController()
token_bucket = TokenBucket(capacity=1000, rate=100)
data_quality_validator = DataQualityValidator()


def get_kafka_processor() -> KafkaStreamProcessor:
    """获取Kafka流处理器实例"""
    return kafka_processor


def get_backpressure_controller() -> BackpressureController:
    """获取背压控制器实例"""
    return backpressure_controller


def get_token_bucket() -> TokenBucket:
    """获取令牌桶实例"""
    return token_bucket


def get_data_quality_validator() -> DataQualityValidator:
    """获取数据质量验证器实例"""
    return data_quality_validator