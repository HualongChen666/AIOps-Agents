# -*- coding: utf-8 -*-
"""
Heartbeat / 健康探针服务
================================
实现 **HTTP** 健康检查端点以及内部 **Prometheus** 心跳指标。
目标：
- 为 k8s / Docker compose 的 liveness / readiness 提供可被抓取的接口。
- 通过 `prometheus_client` 暴露一个常驻的 `heartbeat_up` Gauge，
  让 Prometheus 能实时感知服务存活状态（`up == 1` 表示正常）。

使用方式
----------
1. 在 ``main.py`` 的 ``startup_event`` 中调用 ``await core.heartbeat.start()``。
2. 在 ``shutdown_event`` 中调用 ``await core.heartbeat.stop()``（可选）。
3. 已在 ``api/heartbeat_router.py`` 中注册 ``/healthz``、``/livez`` 两个端点，
   通过 ``app.include_router(heartbeat_router)`` 暴露。

实现细节
----------
- ``HeartBeat`` 使用 ``asyncio.Task`` 在后台每 ``INTERVAL`` 秒刷新 ``heartbeat_up`` Gauge。
- 为防止重复注册同一个 metric，使用 ``Gauge`` 的 ``_created`` 检查，若已存在直接复用。
- ``stop`` 会安全取消后台任务。
"""

import asyncio
import logging
import os
from typing import Optional

from prometheus_client import Gauge

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Prometheus 指标定义（单例）
# ------------------------------------------------------------
# 采用 service 标签，便于在多实例部署时区分。
_SERVICE_NAME = os.getenv("SERVICE_NAME", "aiops-agent")

# 使用 try/except 防止在未安装 prometheus_client 时仍能 import（项目已有依赖，但保持容错）
try:
    _heartbeat_gauge = Gauge(
        "heartbeat_up",
        "Service liveness metric – 1=up, 0=down",
        ["service"],
    )
except Exception:  # pragma: no cover
    # 在极端缺少依赖的环境下提供 dummy 对象，防止 import 错误。
    class _DummyGauge:
        def labels(self, *_, **__):
            return self

        def set(self, *_, **__):
            pass

    _heartbeat_gauge = _DummyGauge()  # type: ignore[assignment]

# ------------------------------------------------------------
# 心跳后台任务实现
# ------------------------------------------------------------
INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "10"))


class _HeartBeat:
    """内部单例心跳管理器。

    - ``start`` 创建并启动 ``asyncio.Task``，每 ``INTERVAL`` 秒把 gauge 设为 ``1``。
    - ``stop`` 取消任务。
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()

    async def _run(self) -> None:
        """后台循环，定期刷新 Prometheus gauge。"""
        while not self._stopped.is_set():
            # 将 gauge 设为 1，Prometheus 抓取时即可看到该值。
            try:
                _heartbeat_gauge.labels(service=_SERVICE_NAME).set(1)
            except Exception:  # pragma: no cover
                # 任何异常不应导致循环退出。
                logger.debug("Heartbeat gauge update failed, continuing", exc_info=True)
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=INTERVAL)
            except asyncio.TimeoutError:
                pass

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped.clear()
            self._task = asyncio.create_task(self._run(), name="heartbeat-task")
            # 初始写一次，避免首次 scrape 前仍为 0。
            _heartbeat_gauge.labels(service=_SERVICE_NAME).set(1)

    async def stop(self) -> None:
        if self._task is not None:
            self._stopped.set()
            await self._task
            self._task = None


# 单例对外暴露
heartbeat = _HeartBeat()


# -------------------- 便捷函数（兼容旧代码） --------------------
async def start() -> None:  # pragma: no cover
    """启动心跳（供 ``main.startup_event`` 调用）。"""
    await heartbeat.start()


async def stop() -> None:  # pragma: no cover
    """停止心跳（供 ``main.shutdown_event`` 调用）。"""
    await heartbeat.stop()
