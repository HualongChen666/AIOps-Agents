# -*- coding: utf-8 -*-
"""
Saga Coordinator
Saga协调器，管理分布式事务的执行和补偿

功能:
- Saga实例管理
- 步骤执行协调
- 补偿事务执行
- 状态追踪
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SagaState(Enum):
    """Saga状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class StepState(Enum):
    """步骤状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    SKIPPED = "skipped"


class SagaStep:
    """
    Saga步骤

    参数:
        name: 步骤名称
        action: 执行函数
        compensation: 补偿函数
        compensate_if: 补偿条件函数
    """

    def __init__(
        self,
        name: str,
        action: Callable,
        compensation: Optional[Callable] = None,
        compensate_if: Optional[Callable] = None,
    ):
        self.name = name
        self.action = action
        self.compensation = compensation
        self.compensate_if = compensate_if
        self.state = StepState.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[Exception] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "state": self.state.value,
            "result": str(self.result) if self.result else None,
            "error": str(self.error) if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SagaInstance:
    """
    Saga实例

    参数:
        saga_id: Saga ID
        name: Saga名称
        steps: 步骤列表
    """

    def __init__(
        self,
        saga_id: str,
        name: str,
        steps: List[SagaStep],
    ):
        self.saga_id = saga_id
        self.name = name
        self.steps = steps
        self.state = SagaState.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[Exception] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "saga_id": self.saga_id,
            "name": self.name,
            "state": self.state.value,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": str(self.error) if self.error else None,
        }


class SagaCoordinator:
    """
    Saga协调器

    管理Saga实例的执行和补偿。

    参数:
        enable_persistence: 是否启用持久化
    """

    def __init__(self, enable_persistence: bool = False):
        self.enable_persistence = enable_persistence
        self._sagas: Dict[str, SagaInstance] = {}
        self._persistence_store: Dict[str, Dict[str, Any]] = {}

        logger.info("Saga coordinator initialized (persistence=%s)", enable_persistence)

    def create_saga(
        self,
        name: str,
        steps: List[SagaStep],
        saga_id: Optional[str] = None,
    ) -> SagaInstance:
        """
        创建Saga实例

        参数:
            name: Saga名称
            steps: 步骤列表
            saga_id: Saga ID（可选，自动生成）

        返回:
            Saga实例
        """
        if saga_id is None:
            saga_id = str(uuid.uuid4())

        saga = SagaInstance(saga_id=saga_id, name=name, steps=steps)
        self._sagas[saga_id] = saga

        if self.enable_persistence:
            self._persist_saga(saga)

        logger.info("Created saga instance: %s (id=%s)", name, saga_id)
        return saga

    async def execute_saga(
        self,
        saga_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行Saga

        参数:
            saga_id: Saga ID
            context: 执行上下文

        返回:
            执行结果
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            raise ValueError(f"Saga not found: {saga_id}")

        saga.state = SagaState.RUNNING
        saga.started_at = datetime.now()
        context = context or {}

        logger.info("Executing saga: %s (id=%s)", saga.name, saga_id)

        try:
            # 执行所有步骤
            for step in saga.steps:
                step.state = StepState.RUNNING
                step.started_at = datetime.now()

                try:
                    # 执行步骤
                    result = await step.action(context)
                    step.result = result
                    step.state = StepState.COMPLETED
                    step.completed_at = datetime.now()

                    # 更新上下文
                    context[step.name] = result

                    logger.info("Step completed: %s", step.name)

                except Exception as e:
                    step.error = e
                    step.state = StepState.FAILED
                    step.completed_at = datetime.now()

                    logger.error("Step failed: %s - %s", step.name, e)

                    # 开始补偿
                    await self._compensate_saga(saga, context)
                    saga.state = SagaState.COMPENSATED
                    saga.error = e
                    saga.completed_at = datetime.now()

                    if self.enable_persistence:
                        self._persist_saga(saga)

                    return {
                        "success": False,
                        "saga_id": saga_id,
                        "error": str(e),
                        "state": saga.state.value,
                    }

            # 所有步骤成功
            saga.state = SagaState.COMPLETED
            saga.completed_at = datetime.now()

            if self.enable_persistence:
                self._persist_saga(saga)

            logger.info("Saga completed successfully: %s", saga.name)

            return {
                "success": True,
                "saga_id": saga_id,
                "state": saga.state.value,
            }

        except Exception as e:
            saga.state = SagaState.FAILED
            saga.error = e
            saga.completed_at = datetime.now()

            if self.enable_persistence:
                self._persist_saga(saga)

            logger.error("Saga execution failed: %s - %s", saga.name, e)

            return {
                "success": False,
                "saga_id": saga_id,
                "error": str(e),
                "state": saga.state.value,
            }

    async def _compensate_saga(
        self,
        saga: SagaInstance,
        context: Dict[str, Any],
    ) -> None:
        """
        补偿Saga

        参数:
            saga: Saga实例
            context: 执行上下文
        """
        saga.state = SagaState.COMPENSATING
        logger.info("Starting compensation for saga: %s", saga.name)

        # 逆序补偿已完成的步骤
        completed_steps = [step for step in saga.steps if step.state == StepState.COMPLETED]

        for step in reversed(completed_steps):
            # 检查是否需要补偿
            if step.compensate_if and not step.compensate_if(context):
                step.state = StepState.SKIPPED
                logger.info("Step compensation skipped: %s", step.name)
                continue

            if not step.compensation:
                step.state = StepState.SKIPPED
                logger.warning("No compensation for step: %s", step.name)
                continue

            step.state = StepState.COMPENSATING

            try:
                # 执行补偿
                await step.compensation(context)
                step.state = StepState.COMPENSATED
                logger.info("Step compensated: %s", step.name)

            except Exception as e:
                step.state = StepState.FAILED
                logger.error("Step compensation failed: %s - %s", step.name, e)
                # 继续补偿其他步骤

    def get_saga(self, saga_id: str) -> Optional[SagaInstance]:
        """获取Saga实例"""
        return self._sagas.get(saga_id)

    def get_all_sagas(self) -> List[SagaInstance]:
        """获取所有Saga实例"""
        return list(self._sagas.values())

    def delete_saga(self, saga_id: str) -> bool:
        """删除Saga实例"""
        if saga_id in self._sagas:
            del self._sagas[saga_id]
            if self.enable_persistence:
                self._persistence_store.pop(saga_id, None)
            return True
        return False

    def _persist_saga(self, saga: SagaInstance) -> None:
        """持久化Saga"""
        self._persistence_store[saga.saga_id] = saga.to_dict()

    def _load_saga(self, saga_id: str) -> Optional[SagaInstance]:
        """从持久化加载Saga"""
        data = self._persistence_store.get(saga_id)
        if not data:
            return None
        # 简化实现，实际应完整重建
        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._sagas)
        by_state: Dict[str, int] = {}

        for saga in self._sagas.values():
            state = saga.state.value
            by_state[state] = by_state.get(state, 0) + 1

        return {
            "total": total,
            "by_state": by_state,
        }
