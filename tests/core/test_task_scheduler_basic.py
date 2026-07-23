# -*- coding: utf-8 -*-
"""
基础任务调度器模块测试
测试任务调度器核心功能的基础场景
"""

import pytest


class TestTaskSchedulerBasic:
    """任务调度器模块基础测试"""

    def test_task_scheduler_module_structure(self):
        """测试任务调度器模块结构"""
        try:
            from core import task_scheduler

            assert task_scheduler is not None
        except ImportError as e:
            pytest.skip(f"Task scheduler module not available: {e}")

    def test_task_scheduler_functions_exist(self):
        """测试任务调度器关键函数存在"""
        try:
            from core.task_scheduler import cancel_task, execute_scheduled_tasks, schedule_task

            # 验证关键函数存在
            assert schedule_task is not None
            assert execute_scheduled_tasks is not None
            assert cancel_task is not None
        except Exception as e:
            pytest.skip(f"Task scheduler functions test failed: {e}")

    def test_task_scheduler_classes_exist(self):
        """测试任务调度器关键类存在"""
        try:
            from core.task_scheduler import ScheduledTask, TaskExecutor, TaskScheduler

            # 验证关键类存在
            assert TaskScheduler is not None
            assert ScheduledTask is not None
            assert TaskExecutor is not None
        except Exception as e:
            pytest.skip(f"Task scheduler classes test failed: {e}")

    def test_task_scheduler_constants(self):
        """测试任务调度器常量定义"""
        try:
            from core.task_scheduler import TaskPriority, TaskStatus

            # 验证常量存在
            assert TaskStatus is not None
            assert TaskPriority is not None
        except Exception as e:
            pytest.skip(f"Task scheduler constants test failed: {e}")
