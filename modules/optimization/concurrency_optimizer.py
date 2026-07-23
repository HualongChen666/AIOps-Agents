# -*- coding: utf-8 -*-
"""
concurrency_optimizer.py
------------------------
性能优化 - 并发优化模块。

功能：
- 线程池管理
- 异步任务调度
- 并发限制
- 资源竞争检测
- 死锁预防
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 任务状态枚举
# ----------------------------------------------------------------------
class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ----------------------------------------------------------------------
# 2️⃣ 任务定义
# ----------------------------------------------------------------------
@dataclass
class Task:
    """任务定义"""

    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "status": self.status.value,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ----------------------------------------------------------------------
# 3️⃣ 并发统计
# ----------------------------------------------------------------------
@dataclass
class ConcurrencyStatistics:
    """并发统计"""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    current_running: int = 0
    max_concurrent: int = 0
    avg_execution_time: float = 0.0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "cancelled_tasks": self.cancelled_tasks,
            "current_running": self.current_running,
            "max_concurrent": self.max_concurrent,
            "avg_execution_time": self.avg_execution_time,
            "success_rate": self.success_rate,
        }


# ----------------------------------------------------------------------
# 4️⃣ 线程池管理器
# ----------------------------------------------------------------------
class ThreadPoolManager:
    """线程池管理器"""

    def __init__(
        self,
        max_workers: int = 10,
        thread_name_prefix: str = "worker",
    ):
        """
        Parameters
        ----------
        max_workers : int
            最大工作线程数
        thread_name_prefix : str
            线程名前缀
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
        )
        self.statistics = ConcurrencyStatistics()
        self.lock = threading.Lock()

    def submit(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Task:
        """
        提交任务

        Parameters
        ----------
        task_id : str
            任务 ID
        func : Callable
            函数
        *args
            位置参数
        **kwargs
            关键字参数

        Returns
        -------
        Task
            任务对象
        """
        task = Task(id=task_id, func=func, args=args, kwargs=kwargs)

        self.executor.submit(self._run_task, task)

        return task

    def _run_task(self, task: Task) -> Any:
        """运行任务"""
        with self.lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.statistics.current_running += 1
            self.statistics.max_concurrent = max(
                self.statistics.max_concurrent,
                self.statistics.current_running,
            )

        try:
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED

            with self.lock:
                self.statistics.completed_tasks += 1

            return result
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

            with self.lock:
                self.statistics.failed_tasks += 1

            raise
        finally:
            with self.lock:
                task.completed_at = datetime.now()
                self.statistics.current_running -= 1
                self.statistics.total_tasks += 1

                # 更新平均执行时间
                if task.started_at and task.completed_at:
                    execution_time = (task.completed_at - task.started_at).total_seconds()
                    total_completed = self.statistics.completed_tasks
                    self.statistics.avg_execution_time = (
                        self.statistics.avg_execution_time * (total_completed - 1) + execution_time
                    ) / total_completed

    def submit_batch(
        self,
        tasks: List[tuple],
    ) -> List[Task]:
        """
        批量提交任务

        Parameters
        ----------
        tasks : List[tuple]
            任务列表，每个元素为 (task_id, func, args, kwargs)

        Returns
        -------
        List[Task]
            任务对象列表
        """
        submitted_tasks = []

        for task_info in tasks:
            task_id = task_info[0]
            func = task_info[1]
            args = task_info[2] if len(task_info) > 2 else ()
            kwargs = task_info[3] if len(task_info) > 3 else {}

            task = self.submit(task_id, func, *args, **kwargs)
            submitted_tasks.append(task)

        return submitted_tasks

    def wait_for_completion(self, timeout: Optional[float] = None):
        """
        等待所有任务完成

        Parameters
        ----------
        timeout : float, optional
            超时时间（秒）
        """
        self.executor.shutdown(wait=True)

    def get_statistics(self) -> ConcurrencyStatistics:
        """获取统计信息"""
        return self.statistics

    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self.executor.shutdown(wait=wait)


# ----------------------------------------------------------------------
# 5️⃣ 异步任务调度器
# ----------------------------------------------------------------------
class AsyncTaskScheduler:
    """异步任务调度器"""

    def __init__(
        self,
        max_concurrent: int = 10,
    ):
        """
        Parameters
        ----------
        max_concurrent : int
            最大并发数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.statistics = ConcurrencyStatistics()
        self.lock = asyncio.Lock()

    async def submit(
        self,
        task_id: str,
        coro: Awaitable,
    ) -> Task:
        """
        提交异步任务

        Parameters
        ----------
        task_id : str
            任务 ID
        coro : Awaitable
            协程对象

        Returns
        -------
        Task
            任务对象
        """
        task = Task(id=task_id, func=lambda: None)  # func 占位

        async with self.semaphore:
            async with self.lock:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                self.statistics.current_running += 1
                self.statistics.max_concurrent = max(
                    self.statistics.max_concurrent,
                    self.statistics.current_running,
                )

            try:
                result = await coro
                task.result = result
                task.status = TaskStatus.COMPLETED

                async with self.lock:
                    self.statistics.completed_tasks += 1

                return task
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED

                async with self.lock:
                    self.statistics.failed_tasks += 1

                raise
            finally:
                async with self.lock:
                    task.completed_at = datetime.now()
                    self.statistics.current_running -= 1
                    self.statistics.total_tasks += 1

                    if task.started_at and task.completed_at:
                        execution_time = (task.completed_at - task.started_at).total_seconds()
                        total_completed = self.statistics.completed_tasks
                        self.statistics.avg_execution_time = (
                            self.statistics.avg_execution_time * (total_completed - 1)
                            + execution_time
                        ) / total_completed

    async def submit_batch(
        self,
        tasks: List[tuple],
    ) -> List[Task]:
        """
        批量提交异步任务

        Parameters
        ----------
        tasks : List[tuple]
            任务列表，每个元素为 (task_id, coro)

        Returns
        -------
        List[Task]
            任务对象列表
        """
        submitted_tasks: List[Task] = []

        coroutines = []
        for task_info in tasks:
            task_id = task_info[0]
            coro = task_info[1]
            coroutines.append(self.submit(task_id, coro))

        await asyncio.gather(*coroutines, return_exceptions=True)

        return submitted_tasks

    def get_statistics(self) -> ConcurrencyStatistics:
        """获取统计信息"""
        return self.statistics


# ----------------------------------------------------------------------
# 6️⃣ 并发限制器
# ----------------------------------------------------------------------
class ConcurrencyLimiter:
    """并发限制器"""

    def __init__(self, max_concurrent: int):
        """
        Parameters
        ----------
        max_concurrent : int
            最大并发数
        """
        self.max_concurrent = max_concurrent
        self.current_count = 0
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        获取并发许可

        Parameters
        ----------
        timeout : float, optional
            超时时间（秒）

        Returns
        -------
        bool
            是否成功获取
        """
        with self.condition:
            start_time = time.time()

            while self.current_count >= self.max_concurrent:
                if timeout is not None:
                    remaining = timeout - (time.time() - start_time)
                    if remaining <= 0:
                        return False
                    self.condition.wait(remaining)
                else:
                    self.condition.wait()

            self.current_count += 1
            return True

    def release(self):
        """释放并发许可"""
        with self.condition:
            self.current_count -= 1
            self.condition.notify()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# ----------------------------------------------------------------------
# 7️⃣ 资源竞争检测器
# ----------------------------------------------------------------------
class ResourceContentionDetector:
    """资源竞争检测器"""

    def __init__(self):
        self.lock_acquisitions: Dict[str, List[datetime]] = {}
        self.lock_holders: Dict[str, str] = {}
        self.contention_events: List[Dict[str, Any]] = []

    def record_lock_acquire(
        self,
        lock_id: str,
        thread_id: str,
    ):
        """
        记录锁获取

        Parameters
        ----------
        lock_id : str
            锁 ID
        thread_id : str
            线程 ID
        """
        if lock_id not in self.lock_acquisitions:
            self.lock_acquisitions[lock_id] = []

        self.lock_acquisitions[lock_id].append(datetime.now())
        self.lock_holders[lock_id] = thread_id

    def record_lock_release(
        self,
        lock_id: str,
        thread_id: str,
    ):
        """
        记录锁释放

        Parameters
        ----------
        lock_id : str
            锁 ID
        thread_id : str
            线程 ID
        """
        if lock_id in self.lock_holders and self.lock_holders[lock_id] == thread_id:
            del self.lock_holders[lock_id]

    def detect_contention(self) -> List[Dict[str, Any]]:
        """
        检测资源竞争

        Returns
        -------
        List[Dict[str, Any]]
            竞争事件列表
        """
        contention_events = []

        for lock_id, acquisitions in self.lock_acquisitions.items():
            if len(acquisitions) > 10:  # 阈值
                contention_events.append(
                    {
                        "lock_id": lock_id,
                        "acquisition_count": len(acquisitions),
                        "severity": "high" if len(acquisitions) > 50 else "medium",
                    }
                )

        return contention_events

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_locks": len(self.lock_acquisitions),
            "contention_events": len(self.contention_events),
            "current_holders": len(self.lock_holders),
        }


# ----------------------------------------------------------------------
# 8️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_thread_pool_manager(
    max_workers: int = 10,
) -> ThreadPoolManager:
    """创建线程池管理器"""
    return ThreadPoolManager(max_workers=max_workers)


def create_async_task_scheduler(
    max_concurrent: int = 10,
) -> AsyncTaskScheduler:
    """创建异步任务调度器"""
    return AsyncTaskScheduler(max_concurrent=max_concurrent)


def create_concurrency_limiter(
    max_concurrent: int,
) -> ConcurrencyLimiter:
    """创建并发限制器"""
    return ConcurrencyLimiter(max_concurrent)


def create_resource_contention_detector() -> ResourceContentionDetector:
    """创建资源竞争检测器"""
    return ResourceContentionDetector()


# ----------------------------------------------------------------------
# 9️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试线程池管理器
    logger.info("Testing thread pool manager")

    pool = create_thread_pool_manager(max_workers=5)

    def sample_task(x: int) -> int:
        time.sleep(0.1)
        return x * 2

    # 提交任务
    tasks = pool.submit_batch([(f"task-{i}", sample_task, (i,), {}) for i in range(10)])

    # 等待完成
    pool.wait_for_completion()

    # 获取统计
    stats = pool.get_statistics()
    logger.info(f"Thread pool statistics: {stats.to_dict()}")

    # 测试并发限制器
    logger.info("Testing concurrency limiter")

    limiter = create_concurrency_limiter(max_concurrent=3)

    def limited_task(task_id: int):
        with limiter:
            logger.info(f"Task {task_id} started")
            time.sleep(0.2)
            logger.info(f"Task {task_id} completed")

    threads = []
    for i in range(5):
        t = threading.Thread(target=limited_task, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    logger.info("Test passed!")
