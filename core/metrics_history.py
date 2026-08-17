# -*- coding: utf-8 -*-
# core/metrics_history.py
#
# Refactored to support timestamped, per-metric, per-service metric samples
# while keeping the legacy push(cpu, memory, net_in, timestamp) API intact.

from __future__ import annotations

import datetime
import logging
import statistics
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque

logger = logging.getLogger(__name__)

# ============================================================
# 配置导入
# ============================================================
try:
    from config import HISTORY_MAX_POINTS  # type: ignore
except (ImportError, AttributeError):
    HISTORY_MAX_POINTS = 60  # 默认保留 60 个数据点(约 2 分钟)
    logger.info(f"config.py 中未找到 HISTORY_MAX_POINTS,使用默认值: {HISTORY_MAX_POINTS}")

try:
    if not isinstance(HISTORY_MAX_POINTS, int) or HISTORY_MAX_POINTS < 1:
        HISTORY_MAX_POINTS = 60
        logger.warning(f"HISTORY_MAX_POINTS 非法,使用默认值: {HISTORY_MAX_POINTS}")
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    HISTORY_MAX_POINTS = 60
    logger.warning(f"HISTORY_MAX_POINTS 非法,使用默认值: {HISTORY_MAX_POINTS}")


# ============================================================
# 模块级常量
# ============================================================
_SIGMA_MIN = 0.1
_SIGMA_MAX = 10.0

_VALID_METRICS = frozenset(["cpu", "memory", "net_in"])


@dataclass(frozen=True, slots=True)
class MetricPoint:
    """单个带时间戳的指标采样点"""

    metric: str
    value: float
    service: str
    timestamp: datetime.datetime


class MetricsHistory:
    """
    线程安全的指标历史缓冲区

    设计原则:
    - 使用 threading.Lock 保证多线程读写安全
    - 保留 legacy 四列数据(cpu / memory / net_in / timestamps),与 to_dict() 兼容
    - 新增 _samples 环形队列,按 MetricPoint 存储,支持 metric + service 维度的查询
    """

    def __init__(self, maxlen: int = HISTORY_MAX_POINTS):
        if not isinstance(maxlen, int) or maxlen < 1:
            logger.warning(f"MetricsHistory 收到非法 maxlen={maxlen!r},已使用默认 60")
            maxlen = 60

        self._lock = Lock()
        self._maxlen = maxlen

        # Legacy 兼容列
        self.cpu: Deque[float] = deque(maxlen=maxlen)
        self.memory: Deque[float] = deque(maxlen=maxlen)
        self.net_in: Deque[float] = deque(maxlen=maxlen)
        self.timestamps: Deque[str] = deque(maxlen=maxlen)

        # 新增:通用按点存储的 ring buffer
        self._samples: Deque[MetricPoint] = deque(maxlen=maxlen)

        logger.debug(f"MetricsHistory 初始化完成,容量: {maxlen} 个数据点")

    # ----------------------------------------------------------
    # 时间戳归一化辅助
    # ----------------------------------------------------------
    def _coerce_timestamp(
        self,
        timestamp: datetime.datetime | str | None,
    ) -> datetime.datetime:
        """把传入的 str / datetime / None 统一转换为 datetime.datetime"""
        if isinstance(timestamp, datetime.datetime):
            return timestamp

        if timestamp is None:
            return datetime.datetime.utcnow()

        if isinstance(timestamp, str):
            ts_str = timestamp.strip()
            if not ts_str:
                return datetime.datetime.utcnow()
            try:
                t = datetime.datetime.strptime(ts_str, "%H:%M:%S").time()
                return datetime.datetime.combine(datetime.date.today(), t)
            except ValueError:
                try:
                    return datetime.datetime.fromisoformat(ts_str)
                except ValueError:
                    logger.warning(
                        "MetricsHistory 无法解析 timestamp 字符串,使用 UTC 当前时间 | "
                        f"value={timestamp!r}"
                    )
                    return datetime.datetime.utcnow()

        logger.warning(
            "MetricsHistory timestamp 类型非法,使用 UTC 当前时间 | "
            f"type={type(timestamp).__name__} value={timestamp!r}"
        )
        return datetime.datetime.utcnow()

    # ----------------------------------------------------------
    # 写入方法
    # ----------------------------------------------------------
    def push(
        self,
        cpu: float,
        memory: float,
        net_in: float,
        timestamp: str,
    ) -> None:
        """
        将新的指标数据压入环形队列 (legacy API)

        - 继续返回 to_dict() 所需的 cpu / memory / net_in / timestamps 四列
        - 内部同时为 cpu、memory、net_in 各写入一个 service="global" 的 MetricPoint
        """
        try:
            cpu_val = round(float(cpu if cpu is not None else 0.0), 1)
            memory_val = round(float(memory if memory is not None else 0.0), 1)
            net_in_val = round(float(net_in if net_in is not None else 0.0), 3)
        except (TypeError, ValueError) as e:
            logger.warning(
                f"MetricsHistory.push() 数值转换失败,本次跳过: {e} "
                f"| cpu={cpu!r}, memory={memory!r}, net_in={net_in!r}"
            )
            return

        ts_dt = self._coerce_timestamp(timestamp)
        ts_str = ts_dt.strftime("%H:%M:%S")

        with self._lock:
            self.cpu.append(cpu_val)
            self.memory.append(memory_val)
            self.net_in.append(net_in_val)
            self.timestamps.append(ts_str)

            self._samples.append(MetricPoint("cpu", cpu_val, "global", ts_dt))
            self._samples.append(MetricPoint("memory", memory_val, "global", ts_dt))
            self._samples.append(MetricPoint("net_in", net_in_val, "global", ts_dt))

    def push_metric(
        self,
        metric: str,
        value: float,
        service: str = "default",
        timestamp: datetime.datetime | str | None = None,
    ) -> None:
        """写入单个 MetricPoint,支持任意 metric / service"""
        if not isinstance(metric, str):
            logger.warning(
                "MetricsHistory.push_metric() metric 必须是字符串,本次跳过 | " f"metric={metric!r}"
            )
            return

        try:
            value_val = float(value if value is not None else 0.0)
        except (TypeError, ValueError) as e:
            logger.warning(
                f"MetricsHistory.push_metric() 数值转换失败,本次跳过: {e} "
                f"| metric={metric!r}, value={value!r}"
            )
            return

        if not isinstance(service, str):
            logger.warning(
                "MetricsHistory.push_metric() service 必须是字符串,使用 'default' | "
                f"service={service!r}"
            )
            service = "default"

        ts_dt = self._coerce_timestamp(timestamp)

        with self._lock:
            self._samples.append(MetricPoint(metric, value_val, service, ts_dt))

    # ----------------------------------------------------------
    # 读取方法
    # ----------------------------------------------------------
    def to_dict(self) -> dict[str, list]:
        """
        以字典快照形式返回全部历史数据 (legacy 格式)
        """
        with self._lock:
            return {
                "cpu": list(self.cpu),
                "memory": list(self.memory),
                "net_in": list(self.net_in),
                "timestamps": list(self.timestamps),
            }

    def query(
        self,
        metric: str,
        service: str = "default",
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
    ) -> list[MetricPoint]:
        """
        按 metric + service + 可选时间窗口查询采样点

        - start / end 均为闭区间(>= start, <= end)
        - 若同时提供 start / end 且 start > end,返回空列表
        """
        if start is not None and end is not None and start > end:
            return []

        with self._lock:
            samples = list(self._samples)

        results: list[MetricPoint] = []
        for point in samples:
            if point.metric != metric or point.service != service:
                continue
            if start is not None and point.timestamp < start:
                continue
            if end is not None and point.timestamp > end:
                continue
            results.append(point)

        return results

    def get_latest(
        self,
        metric: str,
        service: str = "default",
    ) -> float | None:
        """返回指定 metric + service 的最新一个 value,不存在则返回 None"""
        with self._lock:
            samples = list(self._samples)

        for point in reversed(samples):
            if point.metric == metric and point.service == service:
                return point.value
        return None

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    @property
    def size(self) -> int:
        """线程安全地返回当前 legacy 缓冲区的数据点数量"""
        with self._lock:
            return len(self.cpu)

    @property
    def sample_count(self) -> int:
        """线程安全地返回当前 MetricPoint 总数"""
        with self._lock:
            return len(self._samples)

    def clear(self) -> None:
        """线程安全地清空所有历史数据"""
        with self._lock:
            self.cpu.clear()
            self.memory.clear()
            self.net_in.clear()
            self.timestamps.clear()
            self._samples.clear()
        logger.info("MetricsHistory 历史数据已全部清空")

    # ----------------------------------------------------------
    # 动态阈值计算 (M-5)
    # ----------------------------------------------------------
    def get_dynamic_threshold(
        self,
        metric: str,
        static_threshold: float,
        min_samples: int = 30,
        sigma: float = 2.0,
        flat_boost: float = 5.0,
        service: str = "global",
    ) -> tuple[float, dict]:
        """
        基于历史数据计算动态阈值

        算法:dynamic = max(mean + sigma * std, static_threshold)

        三层兜底:
          1. 数据点 < min_samples → 返回固定阈值
          2. 标准差 < 1(数据过于平稳)→ 阈值 = mean + flat_boost
          3. 动态阈值 < 静态下限 → 取 max(动态, 静态)

        Args:
            metric:           指标名 'cpu' | 'memory' | 'net_in'
            static_threshold: 固定阈值(作为下限保护)
            min_samples:      最少样本数
            sigma:            标准差倍数(z-score)
            flat_boost:       平稳数据加成
            service:          查询的服务名,legacy push 使用 'global'(默认)

        Returns:
            (threshold, debug_info)
        """
        try:
            safe_sigma = float(sigma)
            if safe_sigma < _SIGMA_MIN or safe_sigma > _SIGMA_MAX:
                logger.warning(
                    "M-5 sigma 超出范围,已钳制 | "
                    f"原值={sigma} 钳制后={max(_SIGMA_MIN, min(_SIGMA_MAX, safe_sigma))}"
                )
                safe_sigma = max(_SIGMA_MIN, min(_SIGMA_MAX, safe_sigma))
        except (TypeError, ValueError):
            logger.warning(f"M-5 sigma 类型非法 ({sigma!r}),使用默认 2.0")
            safe_sigma = 2.0

        try:
            safe_static = float(static_threshold)
        except (TypeError, ValueError):
            logger.warning(f"M-5 static_threshold 非法 ({static_threshold!r}),使用 0.0")
            safe_static = 0.0

        if metric not in _VALID_METRICS:
            return safe_static, {
                "source": "static_unknown_metric",
                "metric": str(metric),
                "samples": 0,
                "static": safe_static,
                "valid_metrics": sorted(_VALID_METRICS),
            }

        points = self.query(metric, service=service)
        series = [p.value for p in points]
        sample_count = len(series)

        if sample_count < min_samples:
            return safe_static, {
                "source": "static_cold_start",
                "samples": sample_count,
                "min_needed": min_samples,
                "static": safe_static,
            }

        try:
            mean = statistics.mean(series)
            std = statistics.stdev(series) if sample_count >= 2 else 0.0
        except statistics.StatisticsError as e:
            logger.warning(f"M-5 统计计算异常 ({metric}): {e}")
            return safe_static, {
                "source": "static_stats_error",
                "samples": sample_count,
                "error": str(e)[:100],
            }

        if std < 1.0:
            raw_dynamic = mean + flat_boost
            source = "dynamic_flat"
        else:
            raw_dynamic = mean + safe_sigma * std
            source = "dynamic_normal"

        threshold = max(raw_dynamic, safe_static)
        if threshold == safe_static and raw_dynamic < safe_static:
            source = "static_floor_protected"

        max_cap = 10000.0 if metric == "net_in" else 100.0
        threshold = max(0.0, min(max_cap, threshold))

        return round(threshold, 1), {
            "source": source,
            "samples": sample_count,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "raw_dynamic": round(raw_dynamic, 2),
            "static": safe_static,
            "sigma": safe_sigma,
        }

    def __repr__(self) -> str:
        """便于调试的字符串表示"""
        return f"MetricsHistory(maxlen={self._maxlen}, size={self.size})"


# ============================================================
# 全局单例
# ============================================================
metrics_history = MetricsHistory()
