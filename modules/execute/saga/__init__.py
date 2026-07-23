# -*- coding: utf-8 -*-
"""
Saga Pattern Module
全链路事务补偿模块（Saga Pattern）

功能:
- 分布式事务协调
- 补偿事务管理
- 最终一致性保证
"""

from .coordinator import SagaCoordinator, SagaInstance, SagaStep
from .participants import CompensationAction, Participant

__all__ = [
    "SagaCoordinator",
    "SagaInstance",
    "SagaStep",
    "Participant",
    "CompensationAction",
]
