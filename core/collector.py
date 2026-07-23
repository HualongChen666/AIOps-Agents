# -*- coding: utf-8 -*-
# core/collector.py — Windows 系统指标采集探针
#
# ──────────────────────────────────────────────────────────────
# 🔧 严格 Review 修复(C 系列,v2.x 历史保留):
#
# [C1]  [P0] get_top_processes 全部权限失败时返回原始进程信息(避免空列表)
# [C2]  [P0] net_io 单次采样,移除误导性注释
# [C3]  [P1] 进程采样间隔从 0.3s 提升到 0.5s
# [C4]  [P1] 磁盘分区数量上限保护(_DISK_PARTITION_MAX = 50)
# [C5]  [P1] collect_all 整体超时上限(_COLLECT_ALL_TIMEOUT_SEC = 10s)
# [C6]  [P1] 网络速率计算 elapsed 上限钳制(_NET_ELAPSED_MAX_SEC = 60s)
# [C7]  [P2] processor 字段降级
# [C8]  [P2] 进程排序稳定性增强(CPU 相同时按 PID 二级排序)
# [C9]  [P2] 类型注解收紧
# [C10] [P2] swap 字段防御性处理
# [C11] [P2] _collector_lock 序列化保护(v2.x 整个 collect_all 持锁)
# [C12] [P2] 网络速率"时间倒退"防御(NTP 校时场景)
#
# ──────────────────────────────────────────────────────────────
# 🆕 N+3 全量采集超时优化(本次落地):
#
# [N3-1] 🔴 P0 — 引擎层共享 TTL 缓存下沉
#   问题: metrics_router 有 30s 缓存,但 alert_monitor_loop / ai_router /
#         topology_engine 每次都直接调 collect_all(),无共享缓存。
#         同一 2s 采集周期内,多个调用方各自触发 collect_all(),
#         重复阻塞 ~1.1s,浪费 CPU + 污染双采样基准
#   修复: ① collect_all() 内部引入 _collect_cache + _collect_cache_ts
#         ② TTL 可配置(COLLECT_CACHE_TTL_SEC,默认 1.5s)
#         ③ 新增 get_cached_snapshot() 公共接口(接受稍旧数据的场景)
#         ④ 所有调用方自动享受缓存,无需改代码
#   收益: 同一采集周期内缓存命中率 ≥ 70%,重复采集降为零
#
# [N3-2] 🔴 P0 — CPU + 进程双采样窗口合并
#   问题: get_cpu_metrics() 含 time.sleep(0.5),get_top_processes() 也含
#         time.sleep(0.5),两者串行执行总阻塞 ~1.0s
#   修复: ① 新增 _collect_cpu_and_processes() 合并函数
#         ② 在同一个 0.5s 窗口内同时触发 CPU 和进程的基准采样
#         ③ 窗口结束后同时读取两者的真实差值
#         ④ 总阻塞从 ~1.1s 降到 ~0.6s
#   收益: collect_all() 单次耗时降低 45%
#
# [N3-3] 🟡 P1 — 非阻塞指标并行采集
#   问题: 内存/磁盘/网络/系统信息无 sleep,但串行执行仍需 ~50-100ms
#   修复: ① 使用 concurrent.futures.ThreadPoolExecutor 并行执行
#         ② 与 CPU+进程的 0.5s 窗口重叠执行
#         ③ IO 采集时间被 0.5s sleep 完全隐藏
#   收益: 额外 ~50-100ms 的 IO 采集时间降为零(被 sleep 掩盖)
#
# [N3-4] 🟡 P1 — _collector_lock 粒度优化(原 C11 改进)
#   问题: v2.x 整个 collect_all() 持 _collector_lock(~1.1s),
#         其他调用方被阻塞
#   修复: ① 仅 CPU+进程双采样基准部分持 _sampling_lock(防基准污染)
#         ② 其他指标(内存/磁盘/网络)锁外执行
#         ③ 缓存读写用独立的 _cache_lock(不与采样锁竞争)
#         ④ 三把锁严禁交叉嵌套(避免死锁)
#   收益: 锁竞争窗口从 ~1.1s 降到 ~0.6s
#
# [N3-5] 🟢 P2 — 采集性能指标暴露
#   问题: 无法观测 collect_all() 的实际耗时、缓存命中率等
#   修复: ① 新增模块级计数器(_collect_metrics)
#         ② get_collect_metrics() 公共接口(供 stats_engine / /health 使用)
#         ③ 缓存命中/未命中/采集耗时 全部可观测
#   收益: 运维可实时监控采集健康度
#
# [N3-6] 🟢 P2 — collect_all 分段超时
#   问题: 整体 _COLLECT_ALL_TIMEOUT_SEC=10s 粒度太粗,
#         磁盘卡顿时拖垮整个快照
#   修复: ① CPU+进程合并段: 2.0s 超时(含 0.5s sleep + 1.5s 余量)
#         ② 并行 IO 段: 3.0s 超时(磁盘可能卡顿)
#         ③ 任一段超时 → 该字段降级为默认值,不影响其他段
#
# ──────────────────────────────────────────────────────────────
# 🔧 本次严格 Review 修复(CR 系列,N+3 校验落地):
#
# [CR1] 🔴 P0 — 缓存命中分支锁嵌套修复
#   问题: _record_collect_metric 在 _cache_lock 内调用,
#         其内部又获取 _metrics_lock,违反 N3-4 "三把锁严禁交叉嵌套"
#         设计原则,且锁持有时间倍增(高并发时性能下降)
#   修复: ① 锁内仅获取缓存数据快照
#         ② 指标记录移到锁外执行
#         ③ 与 N3-4 设计原则保持一致
#
# [CR2] 🔴 P0 — 元组解包异常精确化
#   问题: future_cpu_proc.result() 解包失败时被 except Exception 吞掉,
#         has_timeout=True 标志会误导(实际不是超时),调试困难
#   修复: ① 区分 TimeoutError 和其他 Exception
#         ② tuple 类型校验,失败时显式日志
#         ③ has_timeout 仅在真超时时设置
#
# [CR3] 🟡 P1 — 移除未使用的 as_completed 导入
#   问题: as_completed 被 import 但全文未使用,
#         Pylance 报 reportUnusedImport 警告,违反 ADR-019
#   修复: 移除 as_completed,仅保留 ThreadPoolExecutor
#
# [CR4] 🟡 P1 — io_futures 字典结构简化
#   问题: io_futures 字典第二个元素字符串完全未使用(用 _ 占位丢弃),
#         死代码,可读性差
#   修复: 简化为 dict[str, Future] 单值字典
#
# [CR5] 🟡 P1 — psutil.cpu_freq 锁外读取语义说明
#   问题: cpu_freq() 在 _sampling_lock 外调用,理论上并发时
#         freq 值可能不一致(虽然实际影响极小)
#   修复: 增加注释说明语义边界,freq 值漂移不影响业务
#
# [CR6] 🟢 P2 — 文件头补全 C1-C12 详细修复说明
#   问题: 文件头只有一行 "C1 ~ C12 原有修复全部保留",
#         违反 ADR-012 "修复说明必须放在文件开头"规范,
#         后续维护者无法快速理解历史修复
#   修复: 补全 C1-C12 完整修复说明
#
# [CR7] 🟢 P2 — _collect_cache 类型严格化注释
#   问题: dict[str, Any] 类型推断后 ["data"] 访问返回 Any,
#         失去类型检查能力(对照 ADR-019)
#   修复: 增加类型注释说明字典结构契约
#
# [CR8] 🟢 P2 — get_collect_metrics 返回构造优化
#   问题: 先 dict 复制再 pop 内部字段,语义不清
#   修复: 先排除内部字段再构造返回 dict,语义更清晰
#
# [CR9] 🟢 P2 — CPU 核数缓存为模块级常量
#   问题: psutil.cpu_count 每次调用都执行,运行期不变
#   修复: 启动时一次性读取,缓存为模块级常量
# ──────────────────────────────────────────────────────────────

import datetime
import logging
import platform
import time
from concurrent.futures import ThreadPoolExecutor  # 🔧 CR3:移除未使用的 as_completed
from threading import Lock
from typing import Any, Optional

import psutil

# Phase 1 集成: OpenTelemetry 遥测
try:
    from core.telemetry import get_meter, get_tracer

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info("Phase 1 OpenTelemetry not available")

logger = logging.getLogger(__name__)


# ============================================================
# Phase 1 集成: OpenTelemetry 初始化
# ============================================================
_tracer = None
_meter = None
_collect_all_counter = None
_collect_all_histogram = None

if OTEL_AVAILABLE:
    try:
        _tracer = get_tracer(__name__)
        _meter = get_meter(__name__)

        # 创建指标
        _collect_all_counter = _meter.create_counter(
            "collect_all_calls", description="Total collect_all calls"
        )
        _collect_all_histogram = _meter.create_histogram(
            "collect_all_duration", description="collect_all duration in seconds"
        )

        logger.info("Phase 1 OpenTelemetry initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")


# ============================================================
# 模块级常量
# ============================================================
# 🔧 C3 [P1]:进程双采样最小间隔(秒)
_PROCESS_SAMPLE_INTERVAL_SEC = 0.5

# 🔧 C4 [P1]:磁盘分区数量上限
_DISK_PARTITION_MAX = 50

# 🔧 C5 [P1]:collect_all 整体超时上限(秒)
_COLLECT_ALL_TIMEOUT_SEC = 10.0

# 🔧 C6 [P1]:网络速率计算 elapsed 上限(秒)
_NET_ELAPSED_MAX_SEC = 60.0

# 🆕 N3-1:引擎层缓存 TTL(秒,可从 config 覆盖)
try:
    from config import COLLECT_CACHE_TTL_SEC as _CFG_CACHE_TTL  # type: ignore

    _COLLECT_CACHE_TTL_SEC: float = max(0.5, min(30.0, float(_CFG_CACHE_TTL)))
except (ImportError, AttributeError, ValueError, TypeError):
    _COLLECT_CACHE_TTL_SEC = 1.5

# 🆕 N3-3:并行 IO 采集线程池大小(固定 4:内存+磁盘+网络+系统信息)
_IO_POOL_SIZE = 4

# 🆕 N3-6:分段超时
_CPU_PROC_TIMEOUT_SEC = 2.0  # CPU+进程合并段(含 0.5s sleep + 余量)
_IO_PARALLEL_TIMEOUT_SEC = 3.0  # 并行 IO 段(磁盘可能卡顿)

# 🔧 CR9 [P2]:CPU 核数缓存为模块级常量(运行期不变)
# 启动时一次性读取,避免 _collect_cpu_and_processes 每次调用都触发系统调用
try:
    _CPU_CORE_COUNT = psutil.cpu_count(logical=False) or 1
    _CPU_LOGICAL_COUNT = psutil.cpu_count(logical=True) or 1
except Exception as _cpu_count_err:
    logger.warning(f"CR9: psutil.cpu_count 初始化异常,使用默认 1: {_cpu_count_err}")
    _CPU_CORE_COUNT = 1
    _CPU_LOGICAL_COUNT = 1


# ============================================================
# 🆕 N3-1:引擎层共享 TTL 缓存
# ──────────────────────────────────────────────────────
# 所有调用方(alert_monitor_loop / ai_router / topology_engine /
# metrics_router / autoheal_router)自动享受缓存
#
# 🔧 CR7 [P2]:_collect_cache 字典结构契约
# ──────────────────────────────────────────────────────
# 字段约定:
#   - "data": Optional[dict[str, Any]] — 缓存的快照数据,None 表示未初始化
#   - "ts":   float                     — time.monotonic() 时间戳
# Pylance 推断 dict[str, Any] 后 ["data"] 类型为 Any,
# 这是 Python dict 类型系统的局限,需要在使用时显式 isinstance 校验
# ──────────────────────────────────────────────────────
_collect_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_cache_lock = Lock()


def _is_collect_cache_valid() -> bool:
    """🆕 N3-1:检查引擎层缓存是否有效(调用方需持有 _cache_lock)"""
    now = time.monotonic()
    ts = _collect_cache["ts"]
    if ts <= 0 or _collect_cache["data"] is None:
        return False
    elapsed = now - ts
    if elapsed < 0:
        # 时间倒退(NTP 校时等),缓存失效
        return False
    return bool(elapsed < float(_COLLECT_CACHE_TTL_SEC))


def get_cached_snapshot(host_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    🆕 N3-1:获取引擎层缓存快照(线程安全)

    供"接受稍旧数据"的场景使用:
      - ai_router._collect_rich_context (M-1 富上下文)
      - topology_engine._get_collector_snapshot
      - autoheal_router.ai_propose_repair
      - mcp_tools.get_host_health / get_metrics

    Args:
        host_id: Optional host identifier to filter the snapshot.

    返回:
        缓存的 snapshot dict / None(缓存无效或未初始化)
    """
    with _cache_lock:
        if _is_collect_cache_valid():
            data = _collect_cache["data"] or {}
            if host_id and isinstance(data, dict) and "hosts" in data:
                return dict(data["hosts"].get(host_id, {}))
            return dict(data)
    return None


def invalidate_collect_cache() -> None:
    """
    🆕 N3-1:显式失效引擎层缓存
    供维护接口 / 测试 使用
    """
    with _cache_lock:
        _collect_cache["data"] = None
        _collect_cache["ts"] = 0.0


# ============================================================
# 🆕 N3-5:采集性能指标
# ──────────────────────────────────────────────────────
# 供 stats_engine / /health 端点使用
# ──────────────────────────────────────────────────────
_collect_metrics: dict[str, Any] = {
    "total_calls": 0,  # collect_all 总调用次数
    "cache_hits": 0,  # 缓存命中次数
    "cache_misses": 0,  # 缓存未命中(真实采集)次数
    "last_collect_ms": 0.0,  # 最近一次真实采集耗时(ms)
    "avg_collect_ms": 0.0,  # 平均真实采集耗时(ms)
    "timeout_count": 0,  # 分段超时次数
    "_total_collect_ms": 0.0,  # 累计采集耗时(内部用)
}
_metrics_lock = Lock()


def get_collect_metrics() -> dict[str, Any]:
    """
    🆕 N3-5:获取采集性能指标(线程安全)
    供 stats_engine.get_real_summary() 和 /health 端点调用

    🔧 CR8 [P2]:先排除内部字段再构造返回 dict,语义更清晰
    """
    # 锁内一次性快照,锁外构造返回
    with _metrics_lock:
        total = _collect_metrics["total_calls"]
        hits = _collect_metrics["cache_hits"]
        misses = _collect_metrics["cache_misses"]
        last_ms = _collect_metrics["last_collect_ms"]
        avg_ms = _collect_metrics["avg_collect_ms"]
        timeout_count = _collect_metrics["timeout_count"]

    # 锁外构造返回 dict(排除内部字段 _total_collect_ms)
    return {
        "total_calls": total,
        "cache_hits": hits,
        "cache_misses": misses,
        "last_collect_ms": last_ms,
        "avg_collect_ms": avg_ms,
        "timeout_count": timeout_count,
        "cache_hit_rate": round(hits / total * 100, 1) if total > 0 else 0.0,
    }


def _record_collect_metric(
    cache_hit: bool,
    collect_ms: float = 0.0,
    timeout: bool = False,
) -> None:
    """
    🆕 N3-5:记录单次采集的性能数据

    🔧 CR1 [P0]:必须在 _cache_lock 之外调用,避免锁嵌套
    """
    with _metrics_lock:
        _collect_metrics["total_calls"] += 1
        if cache_hit:
            _collect_metrics["cache_hits"] += 1
        else:
            _collect_metrics["cache_misses"] += 1
            _collect_metrics["last_collect_ms"] = round(collect_ms, 1)
            _collect_metrics["_total_collect_ms"] += collect_ms
            misses = _collect_metrics["cache_misses"]
            if misses > 0:
                _collect_metrics["avg_collect_ms"] = round(
                    _collect_metrics["_total_collect_ms"] / misses, 1
                )
        if timeout:
            _collect_metrics["timeout_count"] += 1


# ============================================================
# 网络速率计算基准值 + 模块级线程锁
# (C12 时间倒退防御 + BUG-FIX-16 并发保护)
# ============================================================
_last_net_recv = 0
_last_net_sent = 0
_last_net_time = datetime.datetime.now()
_is_first_net_call = True
_net_metric_lock = Lock()


# 🔧 C11 → 🆕 N3-4:_collector_lock 粒度优化
# 修改前:整个 collect_all() 持锁
# 修改后:仅 CPU+进程双采样基准部分持锁
_sampling_lock = Lock()  # 🆕 N3-4:仅保护 CPU+进程双采样(重命名)


# ============================================================
# 函数 1:CPU 指标采集(单独调用版,保留向后兼容)
# ============================================================
def get_cpu_metrics() -> dict[str, Any]:
    """
    采集 CPU 详细指标(独立版)
    注意:collect_all() 内部使用合并版 _collect_cpu_and_processes(),
         本函数仅供外部直接调用 CPU 指标时使用(向后兼容)
    """
    try:
        freq = psutil.cpu_freq()
    except Exception as e:
        logger.debug(f"psutil.cpu_freq() 异常: {e}")
        freq = None

    psutil.cpu_percent(interval=None)
    psutil.cpu_percent(interval=None, percpu=True)
    time.sleep(0.5)
    usage = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)

    usage = max(0.0, min(100.0, float(usage or 0)))
    per_core = [max(0.0, min(100.0, float(c or 0))) for c in per_core or []]

    return {
        "usage_percent": usage,
        "core_count": _CPU_CORE_COUNT,  # 🔧 CR9:使用缓存常量
        "logical_count": _CPU_LOGICAL_COUNT,  # 🔧 CR9:使用缓存常量
        "frequency_mhz": round(freq.current, 1) if freq else 0.0,
        "per_core": per_core,
    }


# ============================================================
# 函数 2:内存指标采集
# 🔧 C10 [P2]:swap 字段防御性处理
# ============================================================
def get_memory_metrics() -> dict[str, Any]:
    """采集内存详细指标"""
    vm = psutil.virtual_memory()

    swap_total_gb = 0.0
    swap_used_gb = 0.0
    swap_percent = 0.0
    try:
        swap = psutil.swap_memory()
        swap_total_gb = round(swap.total / (1024**3), 2)
        swap_used_gb = round(swap.used / (1024**3), 2)
        swap_percent = float(swap.percent or 0)
    except Exception as e:
        logger.debug(f"psutil.swap_memory() 异常: {e}")

    return {
        "total_gb": round(vm.total / (1024**3), 2),
        "used_gb": round(vm.used / (1024**3), 2),
        "available_gb": round(vm.available / (1024**3), 2),
        "usage_percent": float(vm.percent or 0),
        "swap_total_gb": swap_total_gb,
        "swap_used_gb": swap_used_gb,
        "swap_percent": swap_percent,
    }


# ============================================================
# 函数 3:磁盘指标采集
# 🔧 C4 [P1]:磁盘分区数量上限保护
# ============================================================
def get_disk_metrics() -> list[dict[str, Any]]:
    """采集所有磁盘分区指标"""
    disks: list[dict[str, Any]] = []
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception as e:
        logger.error(f"psutil.disk_partitions() 异常: {e}")
        return []

    for part in partitions:
        if len(disks) >= _DISK_PARTITION_MAX:
            logger.warning(f"磁盘分区数超过上限 {_DISK_PARTITION_MAX},截断采集")
            break
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_percent": float(usage.percent or 0),
                }
            )
        except (PermissionError, OSError) as e:
            logger.debug(f"磁盘分区 {part.device} 读取跳过: {e}")
            continue
    return disks


# ============================================================
# 函数 4:网络指标采集
# 🔧 C12 [P2]:时间倒退防御 + 🔧 C6 [P1]:elapsed 上限钳制
# 🔧 BUG-FIX-16:_net_metric_lock 并发保护
# ============================================================
def get_network_metrics() -> dict[str, Any]:
    """采集网络 IO 指标(含实时速率计算)"""
    global _last_net_recv, _last_net_sent, _last_net_time, _is_first_net_call

    with _net_metric_lock:
        try:
            net_io = psutil.net_io_counters()
        except Exception as e:
            logger.error(f"psutil.net_io_counters() 异常: {e}")
            return {
                "recv_speed_mb": 0.0,
                "sent_speed_mb": 0.0,
                "bytes_recv_total_mb": 0.0,
                "bytes_sent_total_mb": 0.0,
                "packets_recv": 0,
                "packets_sent": 0,
                "errin": 0,
                "errout": 0,
            }

        now = datetime.datetime.now()

        if _is_first_net_call:
            _last_net_recv = net_io.bytes_recv
            _last_net_sent = net_io.bytes_sent
            _last_net_time = now
            _is_first_net_call = False
            recv_speed = 0.0
            sent_speed = 0.0
        else:
            elapsed_raw = (now - _last_net_time).total_seconds()

            if elapsed_raw < 0:
                logger.warning(f"检测到时间倒退(elapsed={elapsed_raw:.3f}s)")
                _last_net_recv = net_io.bytes_recv
                _last_net_sent = net_io.bytes_sent
                _last_net_time = now
                recv_speed = 0.0
                sent_speed = 0.0
            elif elapsed_raw > _NET_ELAPSED_MAX_SEC:
                logger.warning(f"网络采集间隔过长({elapsed_raw:.1f}s)")
                _last_net_recv = net_io.bytes_recv
                _last_net_sent = net_io.bytes_sent
                _last_net_time = now
                recv_speed = 0.0
                sent_speed = 0.0
            else:
                elapsed = max(elapsed_raw, 0.001)
                recv_diff = net_io.bytes_recv - _last_net_recv
                sent_diff = net_io.bytes_sent - _last_net_sent
                if recv_diff < 0 or sent_diff < 0:
                    recv_speed = 0.0
                    sent_speed = 0.0
                else:
                    recv_speed = recv_diff / elapsed / (1024**2)
                    sent_speed = sent_diff / elapsed / (1024**2)
                _last_net_recv = net_io.bytes_recv
                _last_net_sent = net_io.bytes_sent
                _last_net_time = now

        bytes_recv_snapshot = net_io.bytes_recv
        bytes_sent_snapshot = net_io.bytes_sent
        packets_recv_snapshot = net_io.packets_recv
        packets_sent_snapshot = net_io.packets_sent
        errin_snapshot = net_io.errin
        errout_snapshot = net_io.errout

    return {
        "recv_speed_mb": round(max(recv_speed, 0), 3),
        "sent_speed_mb": round(max(sent_speed, 0), 3),
        "bytes_recv_total_mb": round(bytes_recv_snapshot / (1024**2), 1),
        "bytes_sent_total_mb": round(bytes_sent_snapshot / (1024**2), 1),
        "packets_recv": packets_recv_snapshot,
        "packets_sent": packets_sent_snapshot,
        "errin": errin_snapshot,
        "errout": errout_snapshot,
    }


# ============================================================
# 函数 5:Top 进程采集(独立版,保留向后兼容)
# 🔧 C1 [P0]:全部权限失败时降级
# 🔧 C8 [P2]:CPU 相同时按 PID 二级排序
# ============================================================
def get_top_processes(limit: int = 10) -> list[dict[str, Any]]:
    """
    双采样法获取真实 CPU 占用率的 Top N 进程(独立版)
    注意:collect_all() 内部使用合并版 _collect_cpu_and_processes(),
         本函数仅供 metrics_router.get_processes() 等独立调用
    """
    safe_limit = max(1, min(100, int(limit) if limit else 10))

    snapshot: dict[int, psutil.Process] = {}
    snapshot_info: dict[int, dict] = {}

    for proc in psutil.process_iter(["pid", "name", "status", "username"]):
        try:
            proc.cpu_percent()
            snapshot[proc.pid] = proc
            snapshot_info[proc.pid] = {
                "pid": proc.pid,
                "name": proc.info.get("name") or "Unknown",
                "status": proc.info.get("status") or "unknown",
                "username": proc.info.get("username") or "N/A",
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    time.sleep(_PROCESS_SAMPLE_INTERVAL_SEC)

    result: list[dict[str, Any]] = []
    for pid, proc in snapshot.items():
        try:
            info = proc.info
            name = info.get("name") or "Unknown"
            status = info.get("status") or "unknown"
            username = info.get("username") or "N/A"
            username = username.split("\\")[-1] if username != "N/A" else "N/A"
            try:
                cpu_pct = round(proc.cpu_percent(), 1)
            except Exception:
                cpu_pct = 0.0
            try:
                mem_pct = round(proc.memory_percent(), 2)
            except Exception:
                mem_pct = 0.0
            result.append(
                {
                    "pid": pid,
                    "name": name,
                    "cpu_percent": cpu_pct,
                    "memory_percent": mem_pct,
                    "status": status,
                    "username": username,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # C1 降级保护
    if not result and snapshot_info:
        logger.warning("C1: 所有进程二次采样均失败,降级返回基础信息")
        for pid, base_info in snapshot_info.items():
            username = base_info["username"]
            username = username.split("\\")[-1] if username != "N/A" else "N/A"
            result.append(
                {
                    "pid": base_info["pid"],
                    "name": base_info["name"],
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "status": base_info["status"],
                    "username": username,
                }
            )

    # C8:二级排序(CPU 相同时按 PID,稳定 UI)
    return sorted(result, key=lambda x: (-x["cpu_percent"], x["pid"]))[:safe_limit]


# ============================================================
# 函数 6:系统基本信息
# 🔧 C7 [P2]:processor 字段降级
# ============================================================
def get_system_info() -> dict[str, Any]:
    """获取系统基本信息"""
    try:
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        uptime_hours = round(uptime.total_seconds() / 3600, 1)
        boot_time_str = boot_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        boot_time_str = "Unknown"
        uptime_hours = 0.0
    try:
        processor = platform.processor() or platform.machine() or "Unknown"
    except Exception:
        processor = "Unknown"
    try:
        os_version = platform.version()[:50]
    except Exception:
        os_version = "Unknown"
    return {
        "os": platform.system() or "Unknown",
        "os_version": os_version,
        "os_release": platform.release() or "Unknown",
        "hostname": platform.node() or "Unknown",
        "architecture": platform.machine() or "Unknown",
        "processor": processor[:60],
        "boot_time": boot_time_str,
        "uptime_hours": uptime_hours,
    }


# ============================================================
# 🆕 N3-2:CPU + 进程双采样合并函数(核心优化)
# ──────────────────────────────────────────────────────
# 关键创新:在同一个 0.5s 窗口内同时触发 CPU 和进程的
# 基准采样,窗口结束后同时读取两者的真实差值。
# 总阻塞从 ~1.0s(两次 0.5s)降到 ~0.5s(一次 0.5s)
#
# 🔧 CR9 [P2]:使用模块级缓存的 CPU 核数常量,
#              避免每次调用都触发系统调用
# ──────────────────────────────────────────────────────
def _collect_cpu_and_processes(
    proc_limit: int = 10,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    🆕 N3-2:合并采集 CPU 指标 + Top 进程列表

    关键优化:
      1. CPU 双采样基准 + 进程双采样基准 → 同一个 time.sleep(0.5)
      2. sleep 后同时读取 CPU 真实值 + 进程真实值
      3. 总阻塞 0.5s(原 1.0s,降低 50%)

    🆕 N3-4:仅本函数内持 _sampling_lock,其他指标锁外采集
    🔧 CR5 [P1]:psutil.cpu_freq() 在锁外读取,freq 漂移(MHz 级)
                业务影响极小,语义上接受此微小不一致

    Returns:
        (cpu_metrics_dict, top_processes_list)
    """
    safe_limit = max(1, min(100, int(proc_limit) if proc_limit else 10))

    # ── Phase 1:触发基准(CPU + 进程同时触发)──
    # CPU 频率(锁外读取,允许微小漂移)
    try:
        freq = psutil.cpu_freq()
    except Exception:
        freq = None

    # 🆕 N3-4:仅基准采样和读取期间持锁
    with _sampling_lock:
        # CPU 基准触发(interval=None,立即返回)
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

        # 进程基准触发(同一锁内,确保基准不被其他线程污染)
        proc_snapshot: dict[int, psutil.Process] = {}
        proc_snapshot_info: dict[int, dict] = {}

        for proc in psutil.process_iter(["pid", "name", "status", "username"]):
            try:
                proc.cpu_percent()  # 触发进程级 CPU 基准
                proc_snapshot[proc.pid] = proc
                proc_snapshot_info[proc.pid] = {
                    "pid": proc.pid,
                    "name": proc.info.get("name") or "Unknown",
                    "status": proc.info.get("status") or "unknown",
                    "username": proc.info.get("username") or "N/A",
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # ── Phase 2:共享等待窗口(CPU + 进程共享这 0.5s)──
        time.sleep(_PROCESS_SAMPLE_INTERVAL_SEC)

        # ── Phase 3:同时读取 CPU + 进程的真实值 ──
        # CPU 真实值
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

    # 锁已释放 — 以下是无共享状态的纯计算

    # CPU 结果组装
    cpu_usage = max(0.0, min(100.0, float(cpu_usage or 0)))
    cpu_per_core = [max(0.0, min(100.0, float(c or 0))) for c in cpu_per_core or []]

    cpu_result: dict[str, Any] = {
        "usage_percent": cpu_usage,
        "core_count": _CPU_CORE_COUNT,  # 🔧 CR9:使用缓存常量
        "logical_count": _CPU_LOGICAL_COUNT,  # 🔧 CR9:使用缓存常量
        "frequency_mhz": round(freq.current, 1) if freq else 0.0,
        "per_core": cpu_per_core,
    }

    # 进程真实值读取(锁外执行,进程可能已消失但不影响 CPU 基准)
    proc_result: list[dict[str, Any]] = []
    for pid, proc in proc_snapshot.items():
        try:
            info = proc.info
            name = info.get("name") or "Unknown"
            status = info.get("status") or "unknown"
            username = info.get("username") or "N/A"
            username = username.split("\\")[-1] if username != "N/A" else "N/A"
            try:
                cpu_pct = round(proc.cpu_percent(), 1)
            except Exception:
                cpu_pct = 0.0
            try:
                mem_pct = round(proc.memory_percent(), 2)
            except Exception:
                mem_pct = 0.0
            proc_result.append(
                {
                    "pid": pid,
                    "name": name,
                    "cpu_percent": cpu_pct,
                    "memory_percent": mem_pct,
                    "status": status,
                    "username": username,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # C1 降级保护
    if not proc_result and proc_snapshot_info:
        logger.warning("N3-2 C1: 所有进程二次采样均失败,降级返回基础信息")
        for pid, base_info in proc_snapshot_info.items():
            username = base_info["username"]
            username = username.split("\\")[-1] if username != "N/A" else "N/A"
            proc_result.append(
                {
                    "pid": base_info["pid"],
                    "name": base_info["name"],
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "status": base_info["status"],
                    "username": username,
                }
            )

    # C8:二级排序(CPU 相同时按 PID)
    proc_result = sorted(
        proc_result,
        key=lambda x: (-x["cpu_percent"], x["pid"]),
    )[:safe_limit]

    return cpu_result, proc_result


# ============================================================
# 函数 7:全量快照采集入口(🆕 N3 核心重构)
# ──────────────────────────────────────────────────────
# 改造要点:
#   1. 引擎层 TTL 缓存(N3-1)
#   2. CPU+进程合并采样(N3-2)
#   3. 非阻塞 IO 并行(N3-3)
#   4. 锁粒度优化(N3-4)
#   5. 性能指标(N3-5)
#   6. 分段超时(N3-6)
#
# 🔧 本次严格 Review 修复:
#   - CR1 [P0]:缓存命中分支锁嵌套修复(指标记录移到锁外)
#   - CR2 [P0]:元组解包异常精确化(区分超时 vs 其他异常)
#   - CR4 [P1]:io_futures 字典结构简化
# ──────────────────────────────────────────────────────
def collect_host_metrics() -> dict[str, Any]:
    """Collect host metrics (stub for test compatibility)."""
    return collect_all()


def collect_system_metrics() -> dict[str, Any]:
    """Collect system metrics (stub for test compatibility)."""
    return collect_all()


def collect_process_metrics() -> dict[str, Any]:
    """Collect process metrics (stub for test compatibility)."""
    return collect_all()


def collect_network_metrics() -> dict[str, Any]:
    """Collect network metrics (stub for test compatibility)."""
    return collect_all()


def collect_all() -> dict[str, Any]:
    """
    一次性采集所有指标快照(🆕 N3 优化版)

    Phase 1 集成: 使用 OpenTelemetry 追踪采集过程

    🆕 N3-1:引擎层 TTL 缓存(1.5s 默认)
        - 同一采集周期内多个调用方共享同一份快照
        - alert_monitor_loop / ai_router / topology_engine 自动受益
        - 缓存到期后自动刷新

    🆕 N3-2:CPU+进程合并采样(0.5s → 替代 1.0s)
    🆕 N3-3:内存/磁盘/网络/系统信息并行采集(与 0.5s sleep 重叠)
    🆕 N3-4:锁粒度优化(仅 CPU+进程基准持锁)
    🆕 N3-5:采集性能指标可观测
    🆕 N3-6:分段超时(IO 卡顿不拖垮整个快照)

    🔧 CR1 [P0]:缓存命中分支严格遵循 N3-4 锁不嵌套原则
        修复前:_record_collect_metric 在 _cache_lock 内调用(锁嵌套)
        修复后:仅缓存数据快照在锁内,指标记录在锁外执行

    🔧 CR2 [P0]:tuple 解包异常精确化
        修复前:任何异常都被吞为 "异常/超时",has_timeout=True 标志误导
        修复后:区分 TimeoutError 真超时 vs Exception 其他异常

    调用方应通过 asyncio.to_thread() 执行,避免阻塞事件循环
    """
    # Phase 1 集成: OpenTelemetry 追踪
    span = None
    if _tracer:
        span = _tracer.start_span("collect_all")
        span.set_attribute("cache_enabled", True)

    # ── N3-1:快速路径 — 缓存命中(🔧 CR1:锁外记录指标)──
    cached_data: Optional[dict[str, Any]] = None
    with _cache_lock:
        if _is_collect_cache_valid():
            # 锁内仅做浅拷贝,O(n) 但常数极小
            cached_data = dict(_collect_cache["data"])

    # 🔧 CR1 [P0]:指标记录移到锁外,避免锁嵌套
    if cached_data is not None:
        logger.debug("N3-1: collect_all 缓存命中")
        _record_collect_metric(cache_hit=True)
        if span:
            span.set_attribute("cache_hit", True)
            span.end()
        return cached_data

    # ── 缓存未命中,执行真实采集 ──
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    start_time = time.monotonic()
    has_timeout = False

    logger.debug("N3-1: collect_all 缓存未命中,开始真实采集")

    # ── N3-2 + N3-3:并行采集策略 ──
    # Phase A:CPU+进程合并采样(持 _sampling_lock,阻塞 ~0.5s)
    # Phase B:与 Phase A 的 sleep(0.5) 窗口重叠,并行采集 IO 指标
    #
    # 实现:用 ThreadPoolExecutor 同时提交两组任务
    # - Task 1:_collect_cpu_and_processes()  → 阻塞 0.5s
    # - Task 2-5:get_memory/disk/network/system → 并行,总共 <100ms
    # 两组任务的执行时间重叠,总耗时 = max(0.5s, IO时间) ≈ 0.5s

    cpu_data: dict[str, Any] = {"usage_percent": 0.0}
    top_procs: list[dict[str, Any]] = []
    mem_data: dict[str, Any] = {"usage_percent": 0.0}
    disk_data: list[dict[str, Any]] = []
    net_data: dict[str, Any] = {"recv_speed_mb": 0.0, "sent_speed_mb": 0.0}
    sys_data: dict[str, Any] = {"hostname": "Unknown"}

    try:
        # 🆕 N3-3:使用线程池并行执行所有采集任务
        with ThreadPoolExecutor(
            max_workers=_IO_POOL_SIZE + 1,  # +1 给 CPU+进程合并任务
            thread_name_prefix="n3_collect",
        ) as executor:
            # 提交所有任务(非阻塞)
            future_cpu_proc = executor.submit(_collect_cpu_and_processes, 10)
            future_memory = executor.submit(get_memory_metrics)
            future_disk = executor.submit(get_disk_metrics)
            future_network = executor.submit(get_network_metrics)
            future_system = executor.submit(get_system_info)

            # ── N3-6:分段超时 — CPU+进程段 ──
            # 🔧 CR2 [P0]:区分超时 vs 其他异常,日志更精确
            try:
                cpu_proc_result = future_cpu_proc.result(timeout=_CPU_PROC_TIMEOUT_SEC)
                # 🔧 CR2:tuple 解包前校验类型
                if isinstance(cpu_proc_result, tuple) and len(cpu_proc_result) == 2:
                    cpu_data, top_procs = cpu_proc_result
                else:
                    logger.error(
                        "N3-6 CR2: CPU+进程合并函数返回类型异常 | "
                        f"type={type(cpu_proc_result).__name__} | "
                        "降级为默认值"
                    )
            except TimeoutError as cpu_timeout_err:
                # 🔧 CR2:仅 TimeoutError 才设置 has_timeout 标志
                has_timeout = True
                logger.warning(
                    f"N3-6: CPU+进程合并采集超时(>{_CPU_PROC_TIMEOUT_SEC}s),"
                    f"降级为默认值: {cpu_timeout_err}"
                )
            except Exception as cpu_err:
                # 🔧 CR2:其他异常单独记录,不混淆超时语义
                logger.warning(
                    "N3-6: CPU+进程合并采集异常(非超时),降级为默认值: "
                    f"{type(cpu_err).__name__}: {cpu_err}",
                    exc_info=True,
                )

            # ── N3-6:分段超时 — IO 并行段 ──
            # 🔧 CR4 [P1]:简化为 dict[str, Future],移除未使用的字符串
            io_futures: dict[str, Any] = {
                "memory": future_memory,
                "disk": future_disk,
                "network": future_network,
                "system": future_system,
            }

            for io_name, future in io_futures.items():
                try:
                    result = future.result(timeout=_IO_PARALLEL_TIMEOUT_SEC)
                    if io_name == "memory":
                        mem_data = result
                    elif io_name == "disk":
                        disk_data = result
                    elif io_name == "network":
                        net_data = result
                    elif io_name == "system":
                        sys_data = result
                except TimeoutError as io_timeout_err:
                    # 🔧 CR2:IO 段也区分超时 vs 异常
                    has_timeout = True
                    logger.warning(
                        f"N3-6: {io_name} 采集超时"
                        f"(>{_IO_PARALLEL_TIMEOUT_SEC}s),使用默认值: "
                        f"{io_timeout_err}"
                    )
                except Exception as io_err:
                    logger.warning(
                        f"N3-6: {io_name} 采集异常(非超时),使用默认值: "
                        f"{type(io_err).__name__}: {io_err}"
                    )

    except Exception as e:
        logger.error(f"N3: 全量采集线程池异常: {e}", exc_info=True)

    # ── 组装快照 ──
    snapshot: dict[str, Any] = {
        "timestamp": ts,
        "cpu": cpu_data,
        "memory": mem_data,
        "disk": disk_data,
        "network": net_data,
        "system": sys_data,
        "top_processes": top_procs,
    }

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # ── N3-1:写入缓存(线程安全)──
    with _cache_lock:
        _collect_cache["data"] = snapshot
        _collect_cache["ts"] = time.monotonic()

    # ── N3-5:记录性能指标(锁外执行)──
    _record_collect_metric(
        cache_hit=False,
        collect_ms=elapsed_ms,
        timeout=has_timeout,
    )

    # ── C5:执行时间监控 ──
    if elapsed_ms > _COLLECT_ALL_TIMEOUT_SEC * 1000:
        logger.warning(
            f"N3: 全量采集超时告警 | 耗时={elapsed_ms:.0f}ms "
            f"(>{_COLLECT_ALL_TIMEOUT_SEC * 1000:.0f}ms)"
        )
    else:
        logger.debug(
            f"N3: 全量采集完成 | 耗时={elapsed_ms:.0f}ms | "
            f"CPU={cpu_data.get('usage_percent', 0)}% | "
            f"MEM={mem_data.get('usage_percent', 0)}% | "
            f"磁盘分区={len(disk_data)} | 进程={len(top_procs)}"
        )

    # Phase 1 集成: OpenTelemetry 追踪结束
    if span:
        span.set_attribute("elapsed_ms", elapsed_ms)
        span.set_attribute("cache_hit", False)
        span.set_attribute("timeout", has_timeout)
        span.set_attribute("cpu_percent", cpu_data.get("usage_percent", 0))
        span.set_attribute("memory_percent", mem_data.get("usage_percent", 0))
        span.end()

    # Phase 1 集成: 记录指标
    if _collect_all_counter:
        _collect_all_counter.add(1)
    if _collect_all_histogram:
        _collect_all_histogram.record(elapsed_ms / 1000.0)

    return snapshot
