# -*- coding: utf-8 -*-
"""
Alert Engine Module
===================

Handles alert processing, correlation, and deduplication.
Supports real-time alert stream processing and intelligent alert grouping.

Key Features:
- Real-time alert processing
- Alert correlation and deduplication
- Intelligent alert grouping
- Alert severity classification

P2 Enhancement:
- Topology correlation for root cause identification
- Automatic alert routing based on rules and ML
- Alert trend prediction based on historical data
"""

# core/alert_engine.py
# 告警规则引擎(N-1 SQLite 持久化 + N-2 告警去重聚合)
#
# 🔧 BUG-FIX-15 + BUG-FIX-21 + 本次严格 Review 多项加固:
#   - AL1  [P0]:_check_ssh_brute_force 防御 auth.log 切割导致的负增量
#   - AL2  [P0]:check_and_generate_alerts 数值字段类型防御
#   - AL3  [P0]:alert_monitor_loop 普通告警接入通知引擎
#   - AL4  [P1]:_try_dedup 改 while 循环淘汰
#   - AL5  [P1]:热路径懒导入移到循环外
#   - AL6  [P1]:SSH 告警触发后清理窗口
#   - AL7  [P1]:_try_dedup 逻辑重构提高可读性
#   - AL8  [P2]:broadcast 迭代前快照
#   - AL9  [P2]:类型注解统一
#   - AL10 [P2]:SSH 暴破缓存过期清理
#   - AL11 [P2]:metrics 字段 None 防御
#   - AL12 [P2]:SSH alert id 增加随机后缀
#   - AL13 [P2]:维护接口

import asyncio
import datetime
import json
import random
import statistics
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger  # type: ignore

from config import DYNAMIC_THRESHOLD_CONFIG  # 🔧 M-5
from config import ALERT_HISTORY_MAX, ALERT_THRESHOLDS, COLLECT_INTERVAL_SEC
from core.collector import collect_all
from core.metrics_history import metrics_history
from core.stats_engine import record_alert_noise, record_ingestion

# BUSINESS_SLA does not exist in config, using default values if needed
BUSINESS_SLA = {"cpu": 90, "memory": 90, "disk": 90}  # Default SLA thresholds

# Module-level alert repository (lazy-loaded; can be patched by tests)
alert_repository: Any = None


def _get_alert_repository() -> Any:
    """Lazily load alert repository; allows test patches to override."""
    global alert_repository
    if alert_repository is None:
        from core.db_engine import alert_repository as _real_repo

        alert_repository = _real_repo
    return alert_repository


# P0-3: Import business metrics collector
try:
    pass

    BUSINESS_METRICS_AVAILABLE = True
except ImportError:
    BUSINESS_METRICS_AVAILABLE = False
    logger.warning("Business metrics collector not available")

# 🔧 N-1:导入 SQLite 持久化引擎

# 🔧 AL5 [P1]:热路径依赖移到模块顶部(避免循环内反复触发 import 锁)

# P1-1: 导入智能告警分析引擎
try:
    from core.alert_intelligence import alert_intelligence_engine

    ALERT_INTELLIGENCE_AVAILABLE = True
    logger.info("✅ 智能告警引擎已加载")
except ImportError:
    ALERT_INTELLIGENCE_AVAILABLE = False
    logger.warning("智能告警引擎不可用，使用传统处理方式")

# ============================================================
# 模块级常量
# 🔧 AL9:常量集中放在文件顶部
# ============================================================
# SSH 暴破检测参数
_SSH_WINDOW_SEC: int = 300  # 5 分钟滑动窗口
_SSH_FAIL_THRESHOLD: int = 10  # 5 分钟内失败次数阈值
_SSH_ALERT_COOLDOWN_SEC: int = 600  # 同主机告警冷却时间 10 分钟
_SSH_CACHE_EXPIRY_SEC: int = 3600  # 🔧 AL10:SSH 缓存过期时间(1 小时)
_SSH_CACHE_MAX_HOSTS: int = 500  # 🔧 AL10:SSH 缓存最大主机数

# 去重缓存参数
_DEDUP_WINDOW_SEC: int = 300  # 5 分钟去重窗口
_DEDUP_CACHE_MAX: int = 200  # 去重缓存硬上限


# ============================================================
# 全局状态
# ============================================================
# 🔧 P0-6:内存 deque 作为热缓存(供 WebSocket 广播使用)
# 主存储在 PostgreSQL 数据库，启动时从数据库恢复
alert_history: deque[Dict[str, Any]] = deque(maxlen=ALERT_HISTORY_MAX)


# 🔧 N-1 + BUG-FIX-21(高危):函数保留,但不在模块加载时自动调用
#                              由 main.py 的 lifespan 钩子在 init_db 后显式调用
async def _restore_alert_cache() -> None:
    """
    服务启动时从 SQLite 恢复最近告警到内存 deque
    🔧 BUG-FIX-21:必须在 init_db() 之后调用,否则查询会失败
    """
    try:
        repo = _get_alert_repository()

        recent = await repo.get_recent(limit=ALERT_HISTORY_MAX)
        for alert in reversed(recent):
            alert_history.appendleft(alert)
        logger.info(f"✅ 从数据库恢复了 {len(recent)} 条告警到内存缓存")
    except Exception as e:
        logger.warning(f"从数据库恢复告警缓存失败(首次运行属正常): {e}")


# WebSocket 订阅者集合
_ws_subscribers: set[Any] = set()


# ============================================================
# 🔧 M-4:SSH 暴力破解检测 — 滑动窗口
# ============================================================
# 结构: { "host_name": [(timestamp, fail_count), ...] }
_ssh_failed_window: Dict[str, List[Tuple[datetime.datetime, int]]] = {}

# 主机告警冷却时间记录
_ssh_last_alert_time: Dict[str, datetime.datetime] = {}


def _check_ssh_brute_force(
    host_name: str,
    current_fail_count: int,
) -> Optional[Dict[str, Any]]:
    """
    🔧 M-4:检测指定 Linux 主机是否触发 SSH 暴力破解告警

    🔧 AL1 [P0]:防御 auth.log 被 logrotate 切割导致的负增量
        - 修复前:logrotate 后 fail_count 骤降到 0,
                  下一次采样得 increment 为负值,告警漏报
        - 修复后:检测到负增量时清空窗口,重新建立基准
    🔧 AL6 [P1]:触发后清理窗口,避免冷却期内冗余累积
    🔧 AL12 [P2]:alert id 增加随机后缀,防御毫秒级冲突

    Args:
        host_name: Linux 主机名称
        current_fail_count: 当前 ssh_failed_logins 累计值
                           (来自 grep -c 'Failed' /var/log/auth.log)
    Returns:
        触发时返回告警字典,否则返回 None
    """
    now = datetime.datetime.now()

    # ── 1. 更新滑动窗口 ──
    if host_name not in _ssh_failed_window:
        _ssh_failed_window[host_name] = []

    window = _ssh_failed_window[host_name]
    window.append((now, current_fail_count))

    # ── 2. 清理超过 5 分钟的旧采样点 ──
    cutoff = now - timedelta(seconds=_SSH_WINDOW_SEC)
    window[:] = [(t, c) for t, c in window if t >= cutoff]

    # 数据点不足,无法判定增量
    if len(window) < 2:
        return None

    # SECURITY: Explicit check for empty window to prevent IndexError
    if not window:
        return None

    # ── 3. 计算窗口内失败次数增量 ──
    earliest_count = window[0][1]
    latest_count = window[-1][1]

    # 🔧 AL1 [P0]:防御 auth.log 被 logrotate 切割
    # 当 fail_count 从大值骤降到小值,通常意味着日志被切割
    # 此时清空窗口,以当前点作为新基准重新统计
    if latest_count < earliest_count:
        logger.info(
            "M-4 SSH 检测到 fail_count 下降(可能 auth.log 被切割) | "
            f"host={host_name} | earliest={earliest_count} → latest={latest_count} | "
            "重置滑动窗口"
        )
        # 清空窗口,仅保留当前点
        _ssh_failed_window[host_name] = [(now, current_fail_count)]
        return None

    increment = latest_count - earliest_count

    # 增量 < 阈值,不触发
    if increment < _SSH_FAIL_THRESHOLD:
        return None

    # ── 4. 冷却保护:同主机 10 分钟内不重复告警 ──
    last_alert = _ssh_last_alert_time.get(host_name)
    if last_alert:
        elapsed = (now - last_alert).total_seconds()
        if elapsed < _SSH_ALERT_COOLDOWN_SEC:
            logger.debug(
                f"M-4 SSH 告警冷却中 | host={host_name} | "
                f"剩余={_SSH_ALERT_COOLDOWN_SEC - elapsed:.0f}s"
            )
            return None

    # ── 5. 触发告警 ──
    _ssh_last_alert_time[host_name] = now
    now_str = now.strftime("%H:%M:%S")

    # 🔧 AL12 [P2]:毫秒精度 + 4 位随机后缀,杜绝同毫秒冲突
    unique_suffix = now.strftime("%H%M%S%f")[:-3] + f"-{random.randint(1000, 9999)}"  # nosec B311

    alert = {
        "id": f"SEC-SSH-{host_name}-{unique_suffix}",
        "level": "critical",
        "category": "security",  # 🔧 M-4:新增安全分类
        "alert_type": "ssh_brute_force",  # 🔧 M-4:子类型
        "title": f"🔒 SSH 暴力破解告警 ({host_name})",
        "desc": f"主机 {host_name} 在 5 分钟内 SSH 登录失败 {increment} 次(≥{_SSH_FAIL_THRESHOLD})",
        "time": "刚刚",
        "raw_time": now_str,
        "detected_at": now,
        "metric_time": now,
        "value": increment,
        "metric": "ssh_failed_logins",
        "platform": "linux",
        "host": host_name,
    }

    logger.warning(f"🚨 M-4 SSH 暴力破解告警触发 | host={host_name} | 5min 失败={increment} 次")

    # 🔧 AL6 [P1]:触发后清理窗口,避免冷却期内冗余累积
    # 仅保留触发时刻的采样点作为下一周期的基准
    _ssh_failed_window[host_name] = [(now, current_fail_count)]

    return alert


# ============================================================
# 🔧 AL10 [P2]:SSH 暴破缓存过期清理
# ============================================================
def _cleanup_ssh_brute_force_cache() -> None:
    """
    清理过期的 SSH 暴破检测缓存
    防止配置主机持续累积导致内存泄漏
    """
    now = datetime.datetime.now()

    # 1. 清理 _ssh_failed_window 中超过过期时间的主机
    expired_hosts: List[str] = []
    for host_name, window in _ssh_failed_window.items():
        if not window:
            expired_hosts.append(host_name)
            continue
        last_sample_time = window[-1][0]
        elapsed = (now - last_sample_time).total_seconds()
        if elapsed > _SSH_CACHE_EXPIRY_SEC:
            expired_hosts.append(host_name)

    for host in expired_hosts:
        _ssh_failed_window.pop(host, None)

    # 2. 清理 _ssh_last_alert_time 中超过过期时间的主机
    expired_alert_hosts = [
        h
        for h, t in _ssh_last_alert_time.items()
        if (now - t).total_seconds() > _SSH_CACHE_EXPIRY_SEC
    ]
    for host in expired_alert_hosts:
        _ssh_last_alert_time.pop(host, None)

    # 3. 硬上限保护(理论上很难触发)
    if len(_ssh_failed_window) > _SSH_CACHE_MAX_HOSTS:
        # 按最后采样时间排序,淘汰最旧的
        sorted_hosts = sorted(
            _ssh_failed_window.items(),
            key=lambda x: x[1][-1][0] if x[1] else datetime.datetime.min,
        )
        excess = len(_ssh_failed_window) - _SSH_CACHE_MAX_HOSTS
        for host, _ in sorted_hosts[:excess]:
            _ssh_failed_window.pop(host, None)
        logger.warning(
            f"AL10: SSH 暴破缓存超出上限 {_SSH_CACHE_MAX_HOSTS},已淘汰 {excess} 台最旧主机"
        )

    if expired_hosts or expired_alert_hosts:
        logger.debug(
            "AL10: SSH 暴破缓存清理 | "
            f"窗口清理={len(expired_hosts)} | "
            f"告警冷却清理={len(expired_alert_hosts)}"
        )


async def check_linux_security_alerts(
    linux_results: List[Any],
) -> List[Dict[str, Any]]:
    """
    🔧 M-4:从 Linux 采集结果中提取安全告警

    由 main.py 的 linux_collect_loop 在每次采集后调用

    🔧 BUG-FIX-15(中危):告警双写 SQLite + 内存
        - SQLite 写入失败时降级为仅内存(不阻塞通知链路)
        - 与 alert_monitor_loop 普通告警的持久化策略保持一致

    Args:
        linux_results: collect_all_linux() 返回的主机列表
    Returns:
        新产生的安全告警列表
    """
    new_security_alerts: List[Dict[str, Any]] = []

    if not linux_results or not isinstance(linux_results, list):
        return new_security_alerts

    for host_data in linux_results:
        if not isinstance(host_data, dict):
            continue
        if host_data.get("status") not in ("ok", "degraded"):
            continue

        host_name = host_data.get("name", "unknown")
        metrics = host_data.get("metrics", {})
        ssh_metric = metrics.get("ssh_failed_logins", {}) if isinstance(metrics, dict) else {}
        raw_value = ssh_metric.get("value", "0") if isinstance(ssh_metric, dict) else "0"

        # 🔧 BUG-FIX-6:增强解析容错
        try:
            cleaned = str(raw_value).strip().split("\n")[0].strip()
            if not cleaned:
                continue
            if cleaned.startswith("ERROR") or cleaned in ("TIMEOUT", "SSH_NOT_FOUND"):
                continue
            fail_count = int(cleaned)
        except (ValueError, TypeError, IndexError):
            logger.debug(f"M-4 ssh_failed_logins 解析失败 | host={host_name} | raw={raw_value!r}")
            continue

        # 检测是否触发告警
        alert = _check_ssh_brute_force(host_name, fail_count)
        # 首次采集缺少基准时,若失败次数本身已超过阈值且不在冷却期内,仍生成告警
        if alert is None and fail_count >= _SSH_FAIL_THRESHOLD:
            last_alert = _ssh_last_alert_time.get(host_name)
            now = datetime.datetime.now()
            if last_alert and (now - last_alert).total_seconds() < _SSH_ALERT_COOLDOWN_SEC:
                logger.debug(
                    f"M-4 SSH 告警冷却中(首次采集) | host={host_name} | " f"fail_count={fail_count}"
                )
            else:
                now_str = now.strftime("%H:%M:%S")
                unique_suffix = now.strftime("%H%M%S%f")[:-3] + f"-{random.randint(1000, 9999)}"  # nosec B311  # noqa: E501
                alert = {
                    "id": f"SEC-SSH-{host_name}-{unique_suffix}",
                    "level": "critical",
                    "category": "security",
                    "alert_type": "ssh_brute_force",
                    "title": f"🔒 SSH 暴力破解告警 ({host_name})",
                    "desc": (
                        f"主机 {host_name} 在 5 分钟内 SSH 登录失败 {fail_count} 次"
                        f"(≥{_SSH_FAIL_THRESHOLD})"
                    ),
                    "time": "刚刚",
                    "raw_time": now_str,
                    "detected_at": now,
                    "metric_time": now,
                    "value": fail_count,
                    "metric": "ssh_failed_logins",
                    "platform": "linux",
                    "host": host_name,
                }
                _ssh_last_alert_time[host_name] = now
        if alert is None:
            continue

        # 🔧 BUG-FIX-15:写入数据库持久化(失败降级到仅内存)
        try:
            repo = _get_alert_repository()

            await repo.save(alert)
            logger.debug(
                f"M-4 安全告警已持久化到数据库 | host={host_name} | alert_id={alert.get('id')}"
            )
        except Exception as db_err:
            logger.error(
                f"M-4 安全告警写入数据库失败(将仅保留内存): {db_err}",
                exc_info=True,
            )

        alert_history.appendleft(alert)
        new_security_alerts.append(alert)

        # ── 🔧 BUG-FIX-3+4:触发现有通知引擎(优先,统一推送渠道) ──
        try:
            from core.notify_engine import send_alert_notification

            notify_result = await send_alert_notification(alert)
            logger.info(f"✅ M-4 安全告警通知推送 | host={host_name} | result={notify_result}")
        except Exception as e:
            logger.error(f"M-4 通知引擎推送异常: {e}", exc_info=True)

        # ── 触发自动处理(M-4 安全规则会走 hardware_dispatch 通道) ──
        try:
            from core.auto_heal import try_auto_heal  # type: ignore[attr-defined]

            heal_result = await try_auto_heal(alert)
            if heal_result.get("status") == "dispatched":
                logger.info(f"✅ M-4 auto_heal 安全告警已分发 | host={host_name}")
        except Exception as e:
            logger.error(f"M-4 安全告警自动处理异常: {e}", exc_info=True)

        # ── 通过 WebSocket 立即广播 ──
        try:
            await broadcast(
                {
                    "type": "security_alert",
                    "alert": alert,
                }
            )
        except Exception as e:
            logger.warning(f"M-4 安全告警 WebSocket 广播失败: {e}")

    return new_security_alerts


# ============================================================
# 🔧 N-2:告警去重缓存
# ============================================================
# 结构: { "{metric}_{level}[_{device}]": {
#           "last_time": datetime,
#           "repeat_count": int,
#           "last_alert": dict
#        } }
_dedup_cache: dict[str, dict[str, Any]] = {}


def _dedup_key(alert: dict[str, Any]) -> str:
    """
    生成去重聚合的 key
    🔧 N-2:按 metric + level 维度聚合(与改造方案一致)
    🔧 BUG-FIX-5:磁盘告警需区分分区设备,避免 C: 和 D: 互相拦截
    """
    metric = alert.get("metric", "unknown")
    level = alert.get("level", "unknown")

    # 磁盘告警:从 id 字段提取设备标识(格式为 "DISK-C:-HH:MM:SS")
    if metric == "disk_percent":
        alert_id = alert.get("id", "")
        if alert_id.startswith("DISK-"):
            parts = alert_id.split("-")
            if len(parts) >= 3:
                device = "-".join(parts[1:-1])  # 取中间部分作为设备名
                return f"{metric}_{level}_{device}"

    return f"{metric}_{level}"


def _try_dedup(alert: dict[str, Any]) -> bool:
    """
    尝试对告警进行去重判定

    🔧 AL4 [P1]:缓存淘汰改 while 循环
    🔧 AL7 [P1]:逻辑重构,提高可读性

    Returns:
        True  = 该告警被去重拦截(不应产生新记录)
        False = 该告警应放行(首次或窗口已过期)
    """
    key = _dedup_key(alert)
    now = datetime.datetime.now()

    # ── 1. 命中缓存且窗口内:拦截 ──
    if key in _dedup_cache:
        cached = _dedup_cache[key]
        elapsed = (now - cached["last_time"]).total_seconds()

        if elapsed < _DEDUP_WINDOW_SEC:
            # 窗口内:拦截,累加 repeat_count
            cached["repeat_count"] += 1
            cached["last_alert"] = alert
            logger.debug(
                f"🔕 告警去重拦截 | key={key} | "
                f"repeat_count={cached['repeat_count']} | "
                f"窗口剩余={_DEDUP_WINDOW_SEC - elapsed:.0f}s"
            )
            return True  # 拦截

    # ── 2. 计算上一轮抑制次数(若有)──
    # 🔧 AL7:与上方 if 分离,语义更清晰
    prev_count = 0
    if key in _dedup_cache:
        prev_count = _dedup_cache[key].get("repeat_count", 0)

    # ── 3. 容量保护(while 循环淘汰)──
    # 🔧 AL4 [P1]:while 循环确保 len 严格 < MAX
    while len(_dedup_cache) >= _DEDUP_CACHE_MAX and key not in _dedup_cache:
        oldest_key = min(
            _dedup_cache,
            key=lambda k: _dedup_cache[k]["last_time"],
        )
        _dedup_cache.pop(oldest_key, None)
        logger.debug(f"🗑️ 去重缓存已满({_DEDUP_CACHE_MAX}),淘汰最旧条目: {oldest_key}")

    # ── 4. 写入缓存(首次或窗口过期后的新告警)──
    _dedup_cache[key] = {
        "last_time": now,
        "repeat_count": 0,
        "last_alert": alert,
    }

    # ── 5. 上一轮抑制信息附加到告警 ──
    if prev_count > 0:
        alert["prev_suppressed"] = prev_count
        logger.info(
            f"🔔 告警去重窗口过期,放行新告警 | key={key} | 上一窗口抑制了 {prev_count} 条重复告警"
        )

    return False  # 放行


def get_dedup_stats() -> dict[str, Any]:
    """
    获取当前去重缓存的统计信息(供调试和监控使用)
    🔧 N-2:辅助函数
    """
    now = datetime.datetime.now()
    active = 0
    total_suppressed = 0

    for key, cached in _dedup_cache.items():
        elapsed = (now - cached["last_time"]).total_seconds()
        if elapsed < _DEDUP_WINDOW_SEC:
            active += 1
        total_suppressed += cached.get("repeat_count", 0)

    return {
        "cache_size": len(_dedup_cache),
        "active_windows": active,
        "total_suppressed": total_suppressed,
        "window_sec": _DEDUP_WINDOW_SEC,
    }


# ============================================================
# 🔧 AL13 [P2]:维护接口
# ============================================================
def clear_dedup_cache() -> int:
    """清空去重缓存(测试/紧急维护用)"""
    count = len(_dedup_cache)
    _dedup_cache.clear()
    if count > 0:
        logger.warning(f"⚠️ 告警去重缓存已被清空 | 清空前条数={count}")
    return count


def clear_ssh_brute_force_cache() -> int:
    """清空 SSH 暴破检测缓存(测试/紧急维护用)"""
    count = len(_ssh_failed_window)
    _ssh_failed_window.clear()
    _ssh_last_alert_time.clear()
    if count > 0:
        logger.warning(f"⚠️ SSH 暴破检测缓存已被清空 | 清空前主机数={count}")
    return count


# ============================================================
# 告警阈值安全读取
# ============================================================
_CPU_WARN_THRESHOLD = ALERT_THRESHOLDS.get("cpu_percent", 80.0)
_MEM_WARN_THRESHOLD = ALERT_THRESHOLDS.get("memory_percent", 85.0)
_DISK_WARN_THRESHOLD = ALERT_THRESHOLDS.get("disk_percent", 90.0)


# ============================================================
# 🔧 M-5:动态阈值统一查询函数
# ============================================================
def _get_dynamic_warn_threshold(
    metric: str,
    static_value: float,
) -> float:
    """
    🔧 M-5:获取指定指标的动态告警阈值

    Args:
        metric:       'cpu' | 'memory' | 'net_in'(对应 metrics_history 字段)
        static_value: 该指标的固定阈值(作为下限)
    Returns:
        实际使用的阈值
    """
    # 全局未启用时直接返回固定阈值
    if not DYNAMIC_THRESHOLD_CONFIG.get("enabled", False):
        return static_value

    try:
        threshold, info = metrics_history.get_dynamic_threshold(
            metric=metric,
            static_threshold=static_value,
            min_samples=DYNAMIC_THRESHOLD_CONFIG.get("min_samples", 30),
            sigma=DYNAMIC_THRESHOLD_CONFIG.get("sigma", 2.0),
            flat_boost=DYNAMIC_THRESHOLD_CONFIG.get("flat_boost", 5.0),
        )

        # 仅在动态阈值与静态阈值有显著差异时打日志(避免日志刷屏)
        if abs(threshold - static_value) >= 1.0:
            logger.debug(
                f"M-5 动态阈值 | metric={metric} | "
                f"threshold={threshold} | static={static_value} | "
                f"source={info.get('source')} | "
                f"samples={info.get('samples')} | "
                f"mean={info.get('mean')} | std={info.get('std')}"
            )

        return float(threshold)

    except Exception as e:
        logger.warning(f"M-5 动态阈值计算异常({metric}),退回固定阈值: {e}")
        return float(static_value)


# ============================================================
# 告警级别判定
# 🔧 AL2 [P0]:_xxx_level 内部增加防御
# ============================================================
def _safe_float(val: Any, default: float = 0.0) -> float:
    """
    🔧 AL2 [P0]:安全数值转换
    防御 None / 字符串 / 异常类型导致的 TypeError
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def _cpu_level(val: float) -> str:
    # 🔧 M-5:动态阈值(失败时降级到 _CPU_WARN_THRESHOLD)
    warn_threshold = _get_dynamic_warn_threshold("cpu", _CPU_WARN_THRESHOLD)
    if val >= 95:
        return "critical"
    if val >= warn_threshold:
        return "warning"
    return "normal"


def _mem_level(val: float) -> str:
    # 🔧 M-5:动态阈值(失败时降级到 _MEM_WARN_THRESHOLD)
    warn_threshold = _get_dynamic_warn_threshold("memory", _MEM_WARN_THRESHOLD)
    if val >= 95:
        return "critical"
    if val >= warn_threshold:
        return "warning"
    return "normal"


def _disk_level(val: float) -> str:
    if val >= 98:
        return "critical"
    if val >= _DISK_WARN_THRESHOLD:
        return "warning"
    return "normal"


# ============================================================
# 告警检测主函数
# 🔧 AL2 [P0]:全部数值字段强制 _safe_float 转换
# 🔧 AL11 [P2]:metrics 字段 None 防御
# ============================================================
def check_and_generate_alerts(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    # compute_bis doesn't exist in priority_engine, skip for now
    # from .priority_engine import compute_bis
    """
    根据采集指标检测是否触发告警规则,返回本次新产生的告警列表

    🔧 N-2:产生的候选告警会经过 _try_dedup() 去重过滤
    🔧 AL2 [P0]:数值字段全部 _safe_float 转换,防御异常类型
    """
    if metrics is None or not isinstance(metrics, dict):
        return []

    now = datetime.datetime.now()
    now_str = now.strftime("%H:%M:%S")
    candidates = []  # 🔧 N-2:候选告警

    # 🔧 AL11 [P2]:metrics 字段 None / 非 dict 防御
    cpu_data = metrics.get("cpu") or {}
    mem_data = metrics.get("memory") or {}
    disk_list = metrics.get("disk") or []

    if not isinstance(cpu_data, dict):
        cpu_data = {}
    if not isinstance(mem_data, dict):
        mem_data = {}
    if not isinstance(disk_list, list):
        disk_list = []

    # —— CPU 告警检测 ——
    # 🔧 AL2:_safe_float 防御
    cpu_val = _safe_float(cpu_data.get("usage_percent"), 0.0)
    cpu_lv = _cpu_level(cpu_val)
    if cpu_lv != "normal":
        cpu_threshold = _get_dynamic_warn_threshold("cpu", _CPU_WARN_THRESHOLD)
        alert_dict = {
            "id": f"CPU-{now_str}",
            "level": cpu_lv,
            "title": "CPU 使用率异常飙升",
            "desc": f"当前主机 · CPU {cpu_val}% (阈值 {cpu_threshold}%)",
            "time": "刚刚",
            "raw_time": now_str,
            "detected_at": now,
            "metric_time": now,
            "value": cpu_val,
            "metric": "cpu_percent",
        }
        bis_score, priority = 0, "P3"  # compute_bis doesn't exist, use defaults
        alert_dict["bis_score"] = bis_score
        alert_dict["priority"] = priority
        candidates.append(alert_dict)

    # —— 内存告警检测 ——
    mem_val = _safe_float(mem_data.get("usage_percent"), 0.0)
    used_gb = _safe_float(mem_data.get("used_gb"), 0.0)
    total_gb = _safe_float(mem_data.get("total_gb"), 0.0)
    mem_lv = _mem_level(mem_val)
    if mem_lv != "normal":
        mem_threshold = _get_dynamic_warn_threshold("memory", _MEM_WARN_THRESHOLD)
        alert_dict = {
            "id": f"MEM-{now_str}",
            "level": mem_lv,
            "title": "内存使用率过高",
            "desc": f"已用 {used_gb} GB / 共 {total_gb} GB ({mem_val}%, 阈值 {mem_threshold}%)",
            "time": "刚刚",
            "raw_time": now_str,
            "detected_at": now,
            "metric_time": now,
            "value": mem_val,
            "metric": "memory_percent",
        }
        bis_score, priority = 0, "P3"  # compute_bis doesn't exist, use defaults
        alert_dict["bis_score"] = bis_score
        alert_dict["priority"] = priority
        candidates.append(alert_dict)

    # —— 磁盘告警检测 ——
    for disk in disk_list:
        if not isinstance(disk, dict):
            continue
        disk_val = _safe_float(disk.get("usage_percent", disk.get("percent")), 0.0)
        disk_dev = str(disk.get("device", "unknown"))
        disk_used = _safe_float(disk.get("used_gb"), 0.0)
        disk_total = _safe_float(disk.get("total_gb"), 0.0)
        disk_lv = _disk_level(disk_val)
        if disk_lv != "normal":
            candidates.append(
                {
                    "id": f"DISK-{disk_dev}-{now_str}",
                    "level": disk_lv,
                    "title": f"磁盘空间告警 ({disk_dev})",
                    "desc": f"已用 {disk_used} GB / 共 {disk_total} GB ({disk_val}%)",
                    "time": "刚刚",
                    "raw_time": now_str,
                    "detected_at": now,
                    "metric_time": now,
                    "value": disk_val,
                    "metric": "disk_percent",
                }
            )

    # 返回候选告警；去重过滤由调用方（如 alert_monitor_loop）统一进行
    return candidates


# ============================================================
# 总览大盘摘要数据
# ============================================================
async def get_summary_metrics() -> dict[str, Any]:
    """
    计算总览大盘四个指标卡片的数值
    🔧 N-1:改为从 SQLite 查询
    """
    from core.stats_engine import get_real_summary

    return await get_real_summary()


# ============================================================
# WebSocket 订阅者管理
# ============================================================
def register_ws(ws) -> None:
    _ws_subscribers.add(ws)
    logger.debug(f"WebSocket 已注册,当前连接数: {len(_ws_subscribers)}")


def unregister_ws(ws) -> None:
    _ws_subscribers.discard(ws)
    logger.debug(f"WebSocket 已注销,当前连接数: {len(_ws_subscribers)}")


async def broadcast(payload: dict) -> None:
    """
    向所有 WebSocket 订阅者广播消息

    🔧 AL8 [P2]:迭代前快照 _ws_subscribers,
                  防止迭代时其他协程修改集合导致 RuntimeError
    """
    # 🔧 AL8:快照后迭代,与原集合解耦
    subscribers_snapshot = set(_ws_subscribers)
    if not subscribers_snapshot:
        return

    dead = set()
    msg = json.dumps(payload, ensure_ascii=False, default=str)

    for ws in subscribers_snapshot:
        try:
            await ws.send_text(msg)
        except Exception as e:
            logger.warning(f"WebSocket 推送失败,标记为死连接: {e}")
            dead.add(ws)

    if dead:
        _ws_subscribers.difference_update(dead)
        logger.debug(f"清理死连接 {len(dead)} 个,剩余: {len(_ws_subscribers)}")


# ============================================================
# 后台告警监控循环
# 🔧 AL3 [P0]:普通告警接入通知引擎(对齐 SSH 安全告警链路)
# 🔧 AL5 [P1]:热路径懒导入移到循环外
# ============================================================
async def alert_monitor_loop() -> None:
    """核心后台协程:定时采集 → 告警检测 → 去重 → 持久化 → 通知 → 广播推送"""
    logger.info("✅ 告警监控引擎已启动")

    # 🔧 AL5 [P1]:热路径依赖循环外导入(避免每秒 N 次 import 锁开销)
    from core.auto_heal import try_auto_heal  # type: ignore[attr-defined]
    from core.notify_engine import send_alert_notification
    from core.stats_engine import get_real_summary

    # 🔧 AL10:SSH 缓存清理计数器(每 N 次循环清理一次)
    cleanup_counter = 0
    _CLEANUP_INTERVAL = 60  # 每 60 个循环(默认 2 秒/次,即每 2 分钟)

    while True:
        try:
            # 1. 采集指标
            metrics = await asyncio.to_thread(collect_all)

            # 2. 更新历史缓冲区(🔧 AL11:metrics 字段 None 防御)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            cpu_data_safe = metrics.get("cpu") or {}
            mem_data_safe = metrics.get("memory") or {}
            net_data_safe = metrics.get("network") or {}

            metrics_history.push(
                cpu=_safe_float(cpu_data_safe.get("usage_percent"), 0.0),
                memory=_safe_float(mem_data_safe.get("usage_percent"), 0.0),
                net_in=_safe_float(net_data_safe.get("recv_speed_mb"), 0.0),
                timestamp=ts,
            )

            # 3. 告警检测(🔧 N-2:内部已包含去重过滤)
            new_alerts = check_and_generate_alerts(metrics)

            # P1-1: 智能告警处理（聚合、降噪、关联分析）
            if ALERT_INTELLIGENCE_AVAILABLE and new_alerts:
                try:
                    original_count = len(new_alerts)
                    new_alerts = await alert_intelligence_engine.analyze_and_aggregate_alerts(
                        new_alerts
                    )
                    logger.info(
                        f"🤖 智能告警处理: {original_count} → {len(new_alerts)} "
                        f"(聚合率: {(1 - len(new_alerts) / original_count) * 100:.1f}%)"
                    )
                except Exception as ai_err:
                    logger.error(f"智能告警处理失败，使用传统方式: {ai_err}", exc_info=True)

            # P1-摄入速率
            disk_count = len(metrics.get("disk") or [])
            proc_count = len(metrics.get("top_processes") or [])
            data_points = 2 + disk_count + 1 + proc_count
            record_ingestion(data_points=data_points)

            # 🔧 N-2:P2-降噪效率统计
            raw_check_count = 2 + disk_count
            # 在监控循环内统一进行去重过滤
            new_alerts = [a for a in new_alerts if not _try_dedup(a)]
            record_alert_noise(
                raw_count=raw_check_count,
                effective_count=len(new_alerts),
            )

            # 4. 处理新告警
            for alert in new_alerts:
                # 🔧 N-1:双写 — 同时写入数据库和内存 deque
                try:
                    repo = _get_alert_repository()

                    await repo.save(alert)
                except Exception as db_err:
                    logger.error(f"告警写入数据库失败: {db_err}")

                alert_history.appendleft(alert)

                logger.warning(f"🚨 {alert['title']} | {alert['desc']}")

                # 🔧 AL3 [P0]:接入通知引擎(对齐 SSH 安全告警链路)
                # ──────────────────────────────────────────────────────
                # 修复前:alert_monitor_loop 主循环只调用 try_auto_heal,
                #         CPU/内存/磁盘等普通告警的通知引擎调用缺失,
                #         导致企微/钉钉/飞书永远收不到普通告警
                # 修复后:与 check_linux_security_alerts 中的 SSH 告警
                #         保持完全一致的通知链路
                # ──────────────────────────────────────────────────────
                try:
                    notify_result = await send_alert_notification(alert)
                    logger.info(f"✅ 告警通知推送 | id={alert.get('id')} | result={notify_result}")
                except Exception as notify_err:
                    logger.error(
                        f"告警通知推送异常: {notify_err}",
                        exc_info=True,
                    )

                # 自动修复尝试
                try:
                    heal_result = await try_auto_heal(alert)
                    if heal_result.get("healed"):
                        logger.info(f"✅ 自动修复成功: {heal_result.get('rule')}")
                except Exception as heal_err:
                    logger.error(
                        f"自动修复异常: {heal_err}",
                        exc_info=True,
                    )

            # 🔧 N-2:定期清理过期的去重缓存
            _cleanup_dedup_cache()

            # 🔧 AL10:周期性清理 SSH 暴破缓存
            cleanup_counter += 1
            if cleanup_counter >= _CLEANUP_INTERVAL:
                _cleanup_ssh_brute_force_cache()
                cleanup_counter = 0

            # 5. 广播
            disk_list = metrics.get("disk") or []
            first_disk_usage = (
                _safe_float(disk_list[0].get("usage_percent"), 0)
                if isinstance(disk_list, list)
                and len(disk_list) > 0
                and isinstance(disk_list[0], dict)
                else 0
            )

            await broadcast(
                {
                    "type": "realtime",
                    "metrics": {
                        "cpu": _safe_float(cpu_data_safe.get("usage_percent"), 0.0),
                        "memory": _safe_float(mem_data_safe.get("usage_percent"), 0.0),
                        "net_in": _safe_float(net_data_safe.get("recv_speed_mb"), 0.0),
                        "disk": first_disk_usage,
                    },
                    "history": metrics_history.to_dict(),
                    "summary": get_real_summary(),
                    "alerts": list(alert_history)[:10],
                }
            )

        except asyncio.CancelledError:
            logger.info("告警监控引擎收到停止信号,正在退出...")
            break

        except Exception as e:
            logger.error(f"告警引擎本次采集异常: {e}", exc_info=True)

        await asyncio.sleep(COLLECT_INTERVAL_SEC)

    logger.info("✅ 告警监控引擎已安全停止")


# ============================================================
# 🔧 N-2:过期去重缓存清理
# ============================================================
def _cleanup_dedup_cache() -> None:
    """
    清理超过 2 倍窗口时间的过期缓存条目
    防止长时间运行后内存泄漏(例如某个磁盘分区被卸载后 key 永远不再出现)
    """
    now = datetime.datetime.now()
    expired_keys = []

    for key, cached in _dedup_cache.items():
        elapsed = (now - cached["last_time"]).total_seconds()
        if elapsed > _DEDUP_WINDOW_SEC * 2:
            expired_keys.append(key)

    for key in expired_keys:
        removed = _dedup_cache.pop(key, None)
        if removed and removed.get("repeat_count", 0) > 0:
            logger.debug(f"🗑️ 清理过期去重缓存 | key={key} | 累计抑制={removed['repeat_count']}条")


# ============================================================
# P2 Enhancement: Alert Topology Correlation
# ============================================================
class AlertTopologyCorrelation:
    """
    P2 Enhanced alert correlation with system topology for root cause identification
    """

    def __init__(self):
        self.topology_graph: Dict[str, List[str]] = {}  # node -> dependencies
        self.alert_correlation_rules: List[Dict] = []

    def build_topology_from_alerts(self, alerts: List[Dict]) -> Dict[str, List[str]]:
        """
        Build system topology from alert patterns

        Args:
            alerts: List of alerts

        Returns:
            Topology graph
        """
        # Simple topology inference based on alert patterns
        # In production, this would use actual service discovery
        topology: dict[str, list[str]] = {}

        for alert in alerts:
            source = alert.get("source", "unknown")
            if source not in topology:
                topology[source] = []

            # Infer dependencies based on alert types
            if alert.get("type") == "cpu_high":
                if "processes" not in topology[source]:
                    topology[source].append("processes")
            elif alert.get("type") == "disk_high":
                if "storage" not in topology[source]:
                    topology[source].append("storage")

        self.topology_graph = topology
        return topology

    def correlate_alerts_with_topology(self, alert: Dict) -> List[str]:
        """
        Correlate alert with topology to identify potential root causes

        Args:
            alert: Current alert

        Returns:
            List of potential root cause nodes
        """
        source = alert.get("source", "unknown")
        root_causes = []

        if source in self.topology_graph:
            # Check if dependencies have alerts
            dependencies = self.topology_graph[source]
            for dep in dependencies:
                if dep in self.topology_graph:
                    root_causes.append(dep)

        return root_causes

    def get_impact_analysis(self, alert: Dict) -> Dict[str, Any]:
        """
        Analyze potential impact of alert based on topology

        Args:
            alert: Current alert

        Returns:
            Impact analysis
        """
        source = alert.get("source", "unknown")
        affected_services = []

        # Find services that depend on this source
        for node, deps in self.topology_graph.items():
            if source in deps:
                affected_services.append(node)

        return {
            "source": source,
            "affected_services": affected_services,
            "impact_level": len(affected_services),
        }


# ============================================================
# P2 Enhancement: Automatic Alert Routing
# ============================================================
class AlertRoutingStrategy(Enum):
    """Alert routing strategies"""

    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"
    HYBRID = "hybrid"


@dataclass
class AlertRoute:
    """Alert route configuration"""

    route_id: str
    conditions: Dict[str, Any]
    target_channel: str
    priority: int = 5
    ml_enabled: bool = False


class AutomaticAlertRouter:
    """
    P2 Enhanced automatic alert routing based on rules and ML
    """

    def __init__(self):
        self.routes: List[AlertRoute] = []
        self.routing_history: List[Dict] = []
        self.strategy = AlertRoutingStrategy.HYBRID

    def add_route(
        self,
        route_id: str,
        conditions: Dict[str, Any],
        target_channel: str,
        priority: int = 5,
        ml_enabled: bool = False,
    ) -> None:
        """
        Add alert routing rule

        Args:
            route_id: Route ID
            conditions: Routing conditions
            target_channel: Target notification channel
            priority: Route priority
            ml_enabled: Whether ML is enabled for this route
        """
        route = AlertRoute(
            route_id=route_id,
            conditions=conditions,
            target_channel=target_channel,
            priority=priority,
            ml_enabled=ml_enabled,
        )
        self.routes.append(route)
        self.routes.sort(key=lambda r: r.priority, reverse=True)

    def route_alert(self, alert: Dict) -> List[str]:
        """
        Route alert to appropriate channels based on rules and ML

        Args:
            alert: Alert to route

        Returns:
            List of target channels
        """
        target_channels = []

        # Rule-based routing
        for route in self.routes:
            if self._match_conditions(alert, route.conditions):
                target_channels.append(route.target_channel)

        # ML-based routing (placeholder for actual ML model)
        if self.strategy in [AlertRoutingStrategy.ML_BASED, AlertRoutingStrategy.HYBRID]:
            ml_channels = self._ml_route_alert(alert)
            target_channels.extend(ml_channels)

        # Record routing decision
        self.routing_history.append(
            {
                "alert_id": alert.get("id"),
                "channels": target_channels,
                "timestamp": datetime.datetime.now().isoformat(),
            }
        )

        # Keep only last 1000 routing decisions
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]

        return list(set(target_channels))  # Remove duplicates

    def _match_conditions(self, alert: Dict, conditions: Dict) -> bool:
        """
        Check if alert matches routing conditions

        Args:
            alert: Alert to check
            conditions: Conditions to match

        Returns:
            Match status
        """
        for key, value in conditions.items():
            alert_value = alert.get(key)
            if alert_value != value:
                return False
        return True

    def _ml_route_alert(self, alert: Dict) -> List[str]:
        """
        ML-based alert routing (placeholder for actual ML model)

        Args:
            alert: Alert to route

        Returns:
            List of ML-predicted channels
        """
        # Placeholder for ML model inference
        # In production, this would use a trained ML model
        severity = alert.get("severity", "info")

        if severity == "critical":
            return ["email", "sms", "webhook"]
        elif severity == "warning":
            return ["email", "webhook"]
        else:
            return ["webhook"]

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics

        Returns:
            Routing statistics
        """
        channel_counts: dict[str, int] = {}
        for routing in self.routing_history:
            for channel in routing["channels"]:
                channel_counts[channel] = channel_counts.get(channel, 0) + 1

        return {
            "total_routes": len(self.routing_history),
            "channel_distribution": channel_counts,
            "strategy": self.strategy.value,
        }


alert_engine = AutomaticAlertRouter()


# ============================================================
# P2 Enhancement: Alert Trend Prediction
# ============================================================
class TrendPredictionModel(Enum):
    """Trend prediction models"""

    LINEAR_REGRESSION = "linear_regression"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LSTM = "lstm"


@dataclass
class TrendPrediction:
    """Trend prediction result"""

    metric_name: str
    predicted_values: List[float]
    confidence_interval: List[tuple]
    trend_direction: str  # increasing, decreasing, stable
    anomaly_probability: float
    prediction_horizon_hours: int


class AlertTrendPredictor:
    """
    P2 Enhanced alert trend prediction based on historical data
    """

    def __init__(self, model: TrendPredictionModel = TrendPredictionModel.MOVING_AVERAGE):
        self.model = model
        self.historical_data: Dict[str, List[float]] = {}
        self.predictions: Dict[str, TrendPrediction] = {}

    def add_historical_data(self, metric_name: str, value: float) -> None:
        """
        Add historical data point for a metric

        Args:
            metric_name: Metric name
            value: Metric value
        """
        if metric_name not in self.historical_data:
            self.historical_data[metric_name] = []

        self.historical_data[metric_name].append(value)

        # Keep only last 1000 data points
        if len(self.historical_data[metric_name]) > 1000:
            self.historical_data[metric_name] = self.historical_data[metric_name][-1000:]

    def predict_trend(
        self, metric_name: str, prediction_horizon_hours: int = 24
    ) -> Optional[TrendPrediction]:
        """
        Predict trend for a metric

        Args:
            metric_name: Metric name
            prediction_horizon_hours: Prediction horizon in hours

        Returns:
            Trend prediction
        """
        if metric_name not in self.historical_data:
            return None

        data = self.historical_data[metric_name]
        if len(data) < 10:
            return None

        if self.model == TrendPredictionModel.MOVING_AVERAGE:
            prediction = self._moving_average_prediction(data, prediction_horizon_hours)
        elif self.model == TrendPredictionModel.LINEAR_REGRESSION:
            prediction = self._linear_regression_prediction(data, prediction_horizon_hours)
        else:
            prediction = self._moving_average_prediction(data, prediction_horizon_hours)
        self.predictions[metric_name] = prediction
        return prediction

    def _moving_average_prediction(
        self, data: List[float], prediction_horizon_hours: int
    ) -> TrendPrediction:
        """
        Moving average trend prediction

        Args:
            data: Historical data
            prediction_horizon_hours: Prediction horizon

        Returns:
            Trend prediction
        """
        window_size = min(10, len(data))
        moving_avg = sum(data[-window_size:]) / window_size

        # Simple prediction: assume current trend continues
        recent_trend = data[-1] - data[-window_size]
        predicted_values = []
        for i in range(prediction_horizon_hours):
            predicted_values.append(moving_avg + recent_trend * (i + 1))

        # Determine trend direction
        if recent_trend > 0.1:
            trend_direction = "increasing"
        elif recent_trend < -0.1:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        # Calculate anomaly probability
        std_dev = statistics.stdev(data[-window_size:]) if len(data) >= 2 else 0
        anomaly_probability = min(abs(recent_trend) / (std_dev + 0.01), 1.0)

        return TrendPrediction(
            metric_name="metric",
            predicted_values=predicted_values,
            confidence_interval=[(v - std_dev, v + std_dev) for v in predicted_values],
            trend_direction=trend_direction,
            anomaly_probability=anomaly_probability,
            prediction_horizon_hours=prediction_horizon_hours,
        )

    def _linear_regression_prediction(
        self, data: List[float], prediction_horizon_hours: int
    ) -> TrendPrediction:
        """
        Linear regression trend prediction

        Args:
            data: Historical data
            prediction_horizon_hours: Prediction horizon

        Returns:
            Trend prediction
        """
        import statistics

        n = len(data)
        x = list(range(n))
        y = data

        # Calculate linear regression
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # Predict future values
        predicted_values = []
        for i in range(prediction_horizon_hours):
            predicted_values.append(slope * (n + i) + intercept)

        # Determine trend direction
        trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"

        # Calculate confidence interval
        residuals = [y[i] - (slope * x[i] + intercept) for i in range(n)]
        std_error = statistics.stdev(residuals) if len(residuals) >= 2 else 0
        confidence_interval = [(v - std_error, v + std_error) for v in predicted_values]

        return TrendPrediction(
            metric_name="metric",
            predicted_values=predicted_values,
            confidence_interval=confidence_interval,
            trend_direction=trend_direction,
            anomaly_probability=abs(slope) / (std_error + 0.01),
            prediction_horizon_hours=prediction_horizon_hours,
        )

    def get_prediction_summary(self) -> Dict[str, Any]:
        """
        Get prediction summary

        Returns:
            Prediction summary
        """
        summary: dict[str, Any] = {
            "metrics_with_predictions": len(self.predictions),
            "predictions": {},
        }

        for metric_name, prediction in self.predictions.items():
            summary["predictions"][metric_name] = {  # type: ignore[index]
                "trend_direction": prediction.trend_direction,
                "anomaly_probability": prediction.anomaly_probability,
                "prediction_horizon_hours": prediction.prediction_horizon_hours,
            }

        return summary


# ============================================================
# P2 Enhancement: Global instances
# ============================================================
alert_topology_correlation = AlertTopologyCorrelation()
automatic_alert_router = AutomaticAlertRouter()
alert_trend_predictor = AlertTrendPredictor()

# Initialize default routing rules
automatic_alert_router.add_route(
    route_id="critical_alert",
    conditions={"severity": "critical"},
    target_channel="email",
    priority=10,
)
automatic_alert_router.add_route(
    route_id="warning_alert",
    conditions={"severity": "warning"},
    target_channel="webhook",
    priority=5,
)

# Expose the same routed instance under the historical alias used by tests/routers.
alert_engine = automatic_alert_router
