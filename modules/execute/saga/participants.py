# -*- coding: utf-8 -*-
"""
Saga Participants
Saga参与者定义和补偿动作

功能:
- 参与者基类
- 补偿动作定义
- 常见参与者实现
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Participant(ABC):
    """
    Saga参与者基类

    定义参与者的执行和补偿行为。
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """
        执行业务逻辑

        参数:
            context: 执行上下文

        返回:
            执行结果
        """

    @abstractmethod
    async def compensate(self, context: Dict[str, Any]) -> None:
        """
        补偿业务逻辑

        参数:
            context: 执行上下文
        """

    def should_compensate(self, context: Dict[str, Any]) -> bool:
        """
        判断是否需要补偿

        参数:
            context: 执行上下文

        返回:
            是否需要补偿
        """
        return True


class CompensationAction:
    """
    补偿动作

    参数:
        name: 动作名称
        execute: 执行函数
        compensate: 补偿函数
        compensate_if: 补偿条件函数
    """

    def __init__(
        self,
        name: str,
        execute: Callable,
        compensate: Callable,
        compensate_if: Optional[Callable] = None,
    ):
        self.name = name
        self.execute = execute
        self.compensate = compensate
        self.compensate_if = compensate_if


class DatabaseParticipant(Participant):
    """
    数据库参与者

    执行数据库操作，补偿时回滚事务。

    参数:
        name: 参与者名称
        db_session: 数据库会话
    """

    def __init__(self, name: str, db_session: Any):
        super().__init__(name)
        self.db_session = db_session
        self._transaction: Optional[Any] = None

    async def execute(self, context: Dict[str, Any]) -> Any:
        """执行数据库操作"""
        # 开始事务
        self._transaction = await self.db_session.begin()

        # 执行具体操作（由子类实现或通过context传递）
        operation = context.get(f"{self.name}_operation")
        if operation:
            result = await operation(self.db_session, context)
            return result

        return {"status": "executed"}

    async def compensate(self, context: Dict[str, Any]) -> None:
        """回滚事务"""
        if self._transaction:
            await self._transaction.rollback()
            logger.info("Database transaction rolled back for: %s", self.name)


class APICallParticipant(Participant):
    """
    API调用参与者

    调用外部API，补偿时调用回滚API。

    参数:
        name: 参与者名称
        execute_url: 执行API URL
        compensate_url: 补偿API URL
        http_client: HTTP客户端
    """

    def __init__(
        self,
        name: str,
        execute_url: str,
        compensate_url: str,
        http_client: Any,
    ):
        super().__init__(name)
        self.execute_url = execute_url
        self.compensate_url = compensate_url
        self.http_client = http_client
        self._response_data: Optional[Dict[str, Any]] = None

    async def execute(self, context: Dict[str, Any]) -> Any:
        """调用执行API"""
        payload = context.get(f"{self.name}_payload", {})

        response = await self.http_client.post(
            self.execute_url,
            json=payload,
        )

        self._response_data = response.json()
        return self._response_data

    async def compensate(self, context: Dict[str, Any]) -> None:
        """调用补偿API"""
        if not self._response_data:
            logger.warning("No response data for compensation: %s", self.name)
            return

        payload = {
            "transaction_id": self._response_data.get("transaction_id"),
            "reason": "saga_compensation",
        }

        try:
            await self.http_client.post(
                self.compensate_url,
                json=payload,
            )
            logger.info("API compensation completed for: %s", self.name)
        except Exception as e:
            logger.error("API compensation failed for %s: %s", self.name, e)


class MessageQueueParticipant(Participant):
    """
    消息队列参与者

    发送消息到队列，补偿时发送取消消息。

    参数:
        name: 参与者名称
        queue_client: 队列客户端
        topic: 主题
        cancel_topic: 取消主题
    """

    def __init__(
        self,
        name: str,
        queue_client: Any,
        topic: str,
        cancel_topic: Optional[str] = None,
    ):
        super().__init__(name)
        self.queue_client = queue_client
        self.topic = topic
        self.cancel_topic = cancel_topic or f"{topic}_cancel"
        self._message_id: Optional[str] = None

    async def execute(self, context: Dict[str, Any]) -> Any:
        """发送消息"""
        message = context.get(f"{self.name}_message", {})

        self._message_id = await self.queue_client.publish(
            self.topic,
            message,
        )

        return {"message_id": self._message_id}

    async def compensate(self, context: Dict[str, Any]) -> None:
        """发送取消消息"""
        if not self._message_id:
            return

        cancel_message = {
            "original_message_id": self._message_id,
            "reason": "saga_compensation",
        }

        try:
            await self.queue_client.publish(
                self.cancel_topic,
                cancel_message,
            )
            logger.info("Cancel message sent for: %s", self.name)
        except Exception as e:
            logger.error("Failed to send cancel message for %s: %s", self.name, e)


class ResourceAllocationParticipant(Participant):
    """
    资源分配参与者

    分配资源，补偿时释放资源。

    参数:
        name: 参与者名称
        resource_manager: 资源管理器
    """

    def __init__(self, name: str, resource_manager: Any):
        super().__init__(name)
        self.resource_manager = resource_manager
        self._allocated_resources: List[str] = []

    async def execute(self, context: Dict[str, Any]) -> Any:
        """分配资源"""
        resource_spec = context.get(f"{self.name}_spec", {})

        allocated = await self.resource_manager.allocate(resource_spec)
        self._allocated_resources = allocated

        return {"allocated": allocated}

    async def compensate(self, context: Dict[str, Any]) -> None:
        """释放资源"""
        for resource_id in self._allocated_resources:
            try:
                await self.resource_manager.release(resource_id)
                logger.info("Resource released: %s", resource_id)
            except Exception as e:
                logger.error("Failed to release resource %s: %s", resource_id, e)


class NotificationParticipant(Participant):
    """
    通知参与者

    发送通知，补偿时发送取消通知。

    参数:
        name: 参与者名称
        notification_service: 通知服务
    """

    def __init__(self, name: str, notification_service: Any):
        super().__init__(name)
        self.notification_service = notification_service
        self._notification_id: Optional[str] = None

    async def execute(self, context: Dict[str, Any]) -> Any:
        """发送通知"""
        notification = context.get(f"{self.name}_notification", {})

        self._notification_id = await self.notification_service.send(notification)

        return {"notification_id": self._notification_id}

    async def compensate(self, context: Dict[str, Any]) -> None:
        """发送取消通知"""
        if not self._notification_id:
            return

        try:
            await self.notification_service.cancel(self._notification_id)
            logger.info("Notification cancelled: %s", self._notification_id)
        except Exception as e:
            logger.error("Failed to cancel notification %s: %s", self._notification_id, e)

    def should_compensate(self, context: Dict[str, Any]) -> bool:
        """通知通常不需要补偿"""
        return False


def create_compensation_action(
    name: str,
    execute_func: Callable,
    compensate_func: Callable,
    compensate_if_func: Optional[Callable] = None,
) -> CompensationAction:
    """
    创建补偿动作

    参数:
        name: 动作名称
        execute_func: 执行函数
        compensate_func: 补偿函数
        compensate_if_func: 补偿条件函数

    返回:
        补偿动作
    """
    return CompensationAction(
        name=name,
        execute=execute_func,
        compensate=compensate_func,
        compensate_if=compensate_if_func,
    )
