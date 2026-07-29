# -*- coding: utf-8 -*-
# core/metrics_history.py
#
# 🔧 严格 Review 修复(R3):
#   - R3-1 [P1]:get_dynamic_threshold 非法 metric 返回标识统一
#   - R3-2 [P2]:push() timestamp 类型严格校验
#   - R3-3 [P2]:sigma 参数极端值钳制
#   - R3-4 [P2]:类型注解收紧

import datetime
import logging
import statistics
from collections import deque
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

# 防御测试环境中被 mock 为非整数（含 MagicMock(spec=int) 导致比较异常）
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
# 🔧 R3-3:sigma 钳制范围
_SIGMA_MIN = 0.1
_SIGMA_MAX = 10.0

# 合法的 metric 字段名
_VALID_METRICS = frozenset(["cpu", "memory", "net_in"])


class MetricsHistory:
    """
    线程安全的环形指标历史缓冲区

    设计原则:
    - 使用 threading.Lock 保证多线程读写安全
    - 四列数据(cpu / memory / net_in / timestamps)严格等长
    - push() 原子操作,to_dict() 快照操作,均持锁执行
    """

    def __init__(self, maxlen: int = HISTORY_MAX_POINTS):
        # 防御:maxlen 类型与范围
        if not isinstance(maxlen, int) or maxlen < 1:
            logger.warning(f"MetricsHistory 收到非法 maxlen={maxlen!r},已使用默认 60")
            maxlen = 60

        self._lock = Lock()
        self._maxlen = maxlen
        self.cpu: Deque[float] = deque(maxlen=maxlen)  # CPU 使用率序列(%)
        self.memory: Deque[float] = deque(maxlen=maxlen)  # 内存使用率序列(%)
        self.net_in: Deque[float] = deque(maxlen=maxlen)  # 网络入流量序列(MB/s)
        self.timestamps: Deque[str] = deque(maxlen=maxlen)  # 对应时间戳序列(HH:MM:SS)

        logger.debug(f"MetricsHistory 初始化完成,容量: {maxlen} 个数据点")

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
        将新的指标数据压入环形队列

        ✅ 修复1:所有数值字段先 float() 强转,再 round()
                  防止 None / 字符串类型导致 round() 抛出 TypeError

        ✅ 修复3:先在锁外计算所有值,再在锁内统一 append
                  保证四列数据长度在任意时刻严格一致

        🔧 R3-2:timestamp 类型严格校验
                  - 防御 datetime 对象误传(应转为字符串)
                  - 防御 None / 空字符串
        """
        # ✅ 修复1 + 修复3:锁外预计算
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

        # 🔧 R3-2:timestamp 严格校验
        if isinstance(timestamp, datetime.datetime):
            # 防御:datetime 对象自动转为 HH:MM:SS
            ts_val = timestamp.strftime("%H:%M:%S")
        elif isinstance(timestamp, str):
            ts_val = timestamp.strip()
            if not ts_val:
                # 空字符串时使用当前时间
                ts_val = datetime.datetime.now().strftime("%H:%M:%S")
        elif timestamp is None:
            ts_val = datetime.datetime.now().strftime("%H:%M:%S")
        else:
            # 其他类型(int/float/list 等)拒绝写入
            logger.warning(
                "MetricsHistory.push() timestamp 类型非法,本次跳过 | "
                f"type={type(timestamp).__name__} value={timestamp!r}"
            )
            return

        # 锁内统一 append,四列同时写入,原子性保证
        with self._lock:
            self.cpu.append(cpu_val)
            self.memory.append(memory_val)
            self.net_in.append(net_in_val)
            self.timestamps.append(ts_val)

    # ----------------------------------------------------------
    # 读取方法
    # ----------------------------------------------------------
    def to_dict(self) -> dict[str, list]:
        """
        以字典快照形式返回全部历史数据
        供 API 接口和 WebSocket 广播使用
        """
        with self._lock:
            return {
                "cpu": list(self.cpu),
                "memory": list(self.memory),
                "net_in": list(self.net_in),
                "timestamps": list(self.timestamps),
            }

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    @property
    def size(self) -> int:
        """线程安全地返回当前缓冲区中的数据点数量"""
        with self._lock:
            return len(self.cpu)

    def clear(self) -> None:
        """线程安全地清空所有列的历史数据"""
        with self._lock:
            self.cpu.clear()
            self.memory.clear()
            self.net_in.clear()
            self.timestamps.clear()
        logger.info("MetricsHistory 历史数据已全部清空")

    # ----------------------------------------------------------
    # 🔧 M-5:动态阈值计算
    # ----------------------------------------------------------
    def get_dynamic_threshold(
        self,
        metric: str,
        static_threshold: float,
        min_samples: int = 30,
        sigma: float = 2.0,
        flat_boost: float = 5.0,
    ) -> tuple[float, dict]:
        """
        🔧 M-5:基于历史数据计算动态阈值

        算法:dynamic = max(mean + sigma * std, static_threshold)

        三层兜底:
          1. 数据点 < min_samples → 返回固定阈值
          2. 标准差 < 1(数据过于平稳)→ 阈值 = mean + flat_boost
          3. 动态阈值 < 静态下限 → 取 max(动态, 静态)

        🔧 R3-1 [P1]:非法 metric 时统一 source 标识
        🔧 R3-3 [P2]:sigma 极端值钳制到 [0.1, 10.0]
        🔧 R3-4 [P2]:类型注解收紧

        Args:
            metric:           指标名 'cpu' | 'memory' | 'net_in'
            static_threshold: 固定阈值(作为下限保护)
            min_samples:      最少样本数
            sigma:            标准差倍数(z-score)
            flat_boost:       平稳数据加成

        Returns:
            (threshold, debug_info)
              threshold:   实际使用的阈值(已四舍五入)
              debug_info:  { source, samples, mean, std, raw_dynamic, ... }
        """
        # 🔧 R3-3:sigma 极端值钳制(防御非法传入)
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

        # static_threshold 防御
        try:
            safe_static = float(static_threshold)
        except (TypeError, ValueError):
            logger.warning(f"M-5 static_threshold 非法 ({static_threshold!r}),使用 0.0")
            safe_static = 0.0

        # 🔧 R3-1:非法 metric 统一标识
        if metric not in _VALID_METRICS:
            return safe_static, {
                "source": "static_unknown_metric",
                "metric": str(metric),
                "samples": 0,
                "static": safe_static,
                "valid_metrics": sorted(_VALID_METRICS),
            }

        # 提取对应序列(持锁,与 push 互斥)
        with self._lock:
            if metric == "cpu":
                series = list(self.cpu)
            elif metric == "memory":
                series = list(self.memory)
            else:  # net_in
                series = list(self.net_in)

        sample_count = len(series)

        # 兜底 1:数据点不足 → 固定阈值
        if sample_count < min_samples:
            return safe_static, {
                "source": "static_cold_start",
                "samples": sample_count,
                "min_needed": min_samples,
                "static": safe_static,
            }

        # 计算均值和标准差
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

        # 兜底 2:标准差过小(数据非常平稳)→ 用均值 + 加成
        if std < 1.0:
            raw_dynamic = mean + flat_boost
            source = "dynamic_flat"
        else:
            raw_dynamic = mean + safe_sigma * std
            source = "dynamic_normal"

        # 兜底 3:取动态值与静态下限的较大者(永不低于安全底线)
        threshold = max(raw_dynamic, safe_static)
        if threshold == safe_static and raw_dynamic < safe_static:
            source = "static_floor_protected"

        # 数值合理性钳制(避免极端值)
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
# 全局单例(整个应用共享同一个历史缓冲区实例)
# ============================================================
metrics_history = MetricsHistory()
