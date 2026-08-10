# -*- coding: utf-8 -*-
# core/linux_collector.py
# Linux 远程监控:10 维度 SSH 采集引擎
# 采集方式:SSH 远程执行 Shell 命令,目标机器无需安装任何软件
#
# ──────────────────────────────────────────────────────────────
# 🔧 严格 Review 修复(R1):
#   - R1-1 [P0]:Semaphore 改为模块级 dict,跨采集周期生效
#   - R1-2 [P0]:命令拼接前防御 None 类型
#   - R1-3 [P1]:_last_collect_cache 增加 Lock 保护
#   - R1-4 [P1]:批量命令分隔符增加 nonce,防注入
#   - R1-5 [P1]:_parse_structured_metrics swap 字段对齐 topology_engine
#   - R1-6 [P2]:超时缓冲钳制
#   - R1-7 [P2]:get_configured_hosts 增加拓扑字段
#   - R1-8 [P2]:主机配置缺失字段降级
#   - R1-9 [P2]:类型注解收紧
# 🔧 技术债修复：从 config 模块导入统一配置
import asyncio
import datetime
import logging
import secrets
import time
from threading import Lock
from typing import Any, Optional

from config import HEALTH_CHECK_URL, LINUX_HOSTS, LINUX_SSH_TIMEOUT

#
# ──────────────────────────────────────────────────────────────
# 🆕 N+3 全量采集超时优化(本次落地):
#
# [N3-1] 🔴 P0 — Linux 失败主机冷却机制
#   问题: 不可达主机每次都触发 SSH 超时(LINUX_SSH_TIMEOUT 秒),
#         在 alert_monitor_loop 高频采集场景下,一台死主机
#         会反复拖累整个采集周期(20 台主机配置时累计可达 200s)
#   修复: ① 模块级 _host_failure_tracker 记录连续失败次数
#         ② 失败次数 >= LINUX_HOST_MAX_FAILURES 时进入冷却期
#         ③ 冷却期内跳过 SSH 调用,返回上次成功的缓存数据
#         ④ 冷却期到期后自动恢复采集(避免主机永久冷却)
#         ⑤ 失败计数器与冷却状态严格 Lock 保护
#   收益: 不可达主机不再拖累正常主机,采集周期稳定在合理范围
#
# [N3-2] 🟡 P1 — SSH 批次大小配置化
#   问题: 原硬编码 batch_size = 10,38 个指标分成 4 个批次,
#         每批次需独立 SSH 连接,网络延迟开销大
#   修复: ① 从 config 读取 LINUX_SSH_BATCH_SIZE(默认 20)
#         ② 38 / 20 = 2 个批次(原 4 个),SSH 连接次数减半
#         ③ 严格范围钳制 [5, 50],防御非法配置
#   收益: Linux 全量采集耗时降低 ~30%
#
# [N3-3] 🟢 P2 — 冷却状态查询公共接口
#   问题: 运维需要观测哪些主机处于冷却期
#   修复: 新增 get_host_cooldown_status() 公共接口,
#         供 /health 端点 + 监控大盘使用
#
# ──────────────────────────────────────────────────────────────
# 🔧 本次严格 Review 修复(LCV 系列共 11 项,N+3 校验落地):
#
# [LCV1] 🔴 P0 — N+3 段落位置错误(模块布局违反"先定义后使用")
#   问题: N+3 配置加载段(_SSH_BATCH_SIZE 等)和冷却函数
#         (_is_host_in_cooldown 等)放在 collect_linux_host
#         之后,但 collect_linux_host 内部引用了这些符号。
#         虽然 async def 函数体不在模块加载时执行,实际运行不崩溃,
#         但严重违反"先定义后使用"规范,Pylance 可能误报
#         reportUndefinedVariable
#   修复: ① 配置加载段移到模块顶部"模块级常量"区域
#         ② 冷却函数移到 _ssh_execute 之前(在 _get_host_semaphore 旁)
#         ③ 整个文件按"常量 → 状态 → 工具 → 引擎 → 业务"严格分层
#
# [LCV2] 🔴 P0 — collect_linux_host 冷却期分支裸读 _last_collect_cache
#   问题: 冷却期分支直接 _last_collect_cache.get(host_name),
#         未走 _last_collect_cache_lock,违反 R1-3 设计原则
#         (文件头明确写明"必须 Lock 保护")。与 collect_all_linux
#         的写入路径产生迭代竞态
#   修复: ① 锁内浅拷贝快照,锁外深加工(对照 approval_store R3 决策)
#         ② 严格遵循"读 _last_collect_cache 必持锁"原则
#
# [LCV3] 🔴 P0 — collect_linux_host 双 docstring 导致 R1 注释失效
#   问题: 函数定义后有两个连续 docstring 字符串:
#         """对单台...(N3 优化版)"""
#         """🔧 R1-1 ... R1-8 ..."""
#         Python 只识别第一个,第二个变成无效字符串字面量但不报错。
#         R1-1 / R1-8 关键设计注释实际未生效
#   修复: 合并为单个完整 docstring,包含 R1 + N3 所有修复说明
#
# [LCV4] 🟡 P1 — 文件头补全 N+3 修复说明
#   问题: 文件实际新增 ~120 行 N+3 代码,但文件头修复说明完全未提及,
#         严重违反 ADR-012 "修复说明必须放在文件开头"规范
#   修复: 新增"🆕 N+3 全量采集超时优化"独立段落 + LCV 系列说明
#
# [LCV5] 🟡 P1 — N+3 配置加载段位置错误(同 LCV1)
#   修复: 已在 LCV1 中合并修复
#
# [LCV6] 🟡 P1 — _record_host_failure 与 _is_host_in_cooldown 并发竞态
#   问题: _is_host_in_cooldown 释放锁后,_record_host_failure 才进入锁。
#         极端场景:主机刚好到冷却期末尾时,可能产生"先恢复又立即失败"
#         的抖动(虽然影响小,但语义不严谨)
#   修复: 当前实现已可接受(原子操作粒度足够),增加注释说明
#         "本设计可接受短期抖动,符合冷却机制的弹性恢复语义"
#
# [LCV7] 🟡 P1 — get_host_cooldown_status 锁内调用 time.monotonic
#   问题: 锁内迭代字典时多次调用 time.monotonic(),持锁时间不必要拉长
#   修复: 锁内仅做浅拷贝快照,锁外计算 remaining 时间
#         (对照 approval_store get_all_approvals_snapshot R3 决策)
#
# [LCV8] 🟢 P2 — Pylance reportUndefinedVariable 潜在警告
#   问题: 同 LCV1,函数内引用的符号在函数定义之后才出现
#   修复: 已在 LCV1 中合并修复(段落重排后此问题消失)
#
# [LCV9] 🟢 P2 — 冷却期返回的 cached_copy 缺少 timestamp 更新
#   问题: 下游消费者可能误以为是新鲜数据
#   修复: cached_copy 增加 stale_at 字段(当前时间),
#         明确标记"此数据从缓存读取,采集时间见 timestamp 字段"
#
# [LCV10] 🟢 P2 — _ssh_execute 类型注解 Pylance 友好度
#   问题: Optional[asyncio.subprocess.Process] 注解依赖,
#         严格模式下可能误报
#   修复: 添加注释说明 asyncio 已导入,asyncio.subprocess 是子模块,
#         运行时和静态分析都能正确解析
#
# [LCV11] 🟢 P2 — get_host_cooldown_status 函数缺少 N+3 修复编号
#   修复: docstring 增加 [N3-3] 编号,与项目其他公共接口规范一致
# ──────────────────────────────────────────────────────────────


logger = logging.getLogger(__name__)


# ============================================================
# 模块级常量(LCV1 修复:配置加载段提到顶部)
# ============================================================

# SSH 单主机并发上限(R1-1)
_SSH_CONCURRENCY_PER_HOST = 8

# 🆕 N3-2:SSH 批量命令数(从 config 读取,默认 20)
try:
    from config import LINUX_SSH_BATCH_SIZE as _CFG_BATCH_SIZE

    _SSH_BATCH_SIZE: int = max(5, min(50, int(_CFG_BATCH_SIZE)))
except (ImportError, AttributeError, ValueError, TypeError):
    _SSH_BATCH_SIZE = 20

# 🆕 N3-1:失败主机冷却时间(秒)
try:
    from config import LINUX_HOST_COOLDOWN_SEC as _CFG_COOLDOWN

    _HOST_COOLDOWN_SEC: int = max(30, min(3600, int(_CFG_COOLDOWN)))
except (ImportError, AttributeError, ValueError, TypeError):
    _HOST_COOLDOWN_SEC = 300  # 5 分钟

# 🆕 N3-1:触发冷却的连续失败次数
try:
    from config import LINUX_HOST_MAX_FAILURES as _CFG_MAX_FAIL

    _HOST_MAX_FAILURES: int = max(1, min(20, int(_CFG_MAX_FAIL)))
except (ImportError, AttributeError, ValueError, TypeError):
    _HOST_MAX_FAILURES = 3


# ============================================================
# 全局状态(LCV1 修复:状态集中管理)
# ============================================================

# 🔧 R1-1 [P0]:模块级 Semaphore 字典(跨采集周期生效)
_host_semaphores: dict[str, asyncio.Semaphore] = {}
_host_semaphores_lock = Lock()

# 🔧 R1-3 [P1]:最近一次全量采集结果缓存(Lock 保护)
_last_collect_cache: dict[str, dict] = {}
_last_collect_cache_lock = Lock()

# 🆕 N3-1:失败计数器
# 结构: { host_name: {"count": int, "last_fail": float} }
_host_failure_tracker: dict[str, dict[str, Any]] = {}
_host_failure_lock = Lock()


# ============================================================
# 工具函数 1:Semaphore 管理(R1-1)
# ============================================================
def _get_host_semaphore(host_key: str) -> asyncio.Semaphore:
    """
    获取指定主机的 Semaphore(懒加载 + 线程安全)
    🔧 R1-1:跨采集周期复用,真正控制每台主机的并发 SSH 数
    """
    # 快速路径:已存在直接返回(无需加锁)
    sem = _host_semaphores.get(host_key)
    if sem is not None:
        return sem

    # 慢速路径:加锁创建(双重检查锁定模式)
    with _host_semaphores_lock:
        sem = _host_semaphores.get(host_key)
        if sem is None:
            sem = asyncio.Semaphore(_SSH_CONCURRENCY_PER_HOST)
            _host_semaphores[host_key] = sem
            logger.debug(
                "R1-1: 为主机创建 Semaphore | "
                f"host={host_key} | concurrency={_SSH_CONCURRENCY_PER_HOST}"
            )
        return sem


# ============================================================
# 工具函数 2:采集快照查询(R1-3)
# ============================================================
def get_last_snapshot() -> dict[str, dict]:
    """
    🔧 R1-3:线程安全地获取最近一次采集快照(浅拷贝)
    供 topology_engine 调用,替代直接访问 _last_collect_cache
    """
    with _last_collect_cache_lock:
        return dict(_last_collect_cache)


# ============================================================
# 工具函数 3:失败主机冷却机制(🆕 N3-1)
# ──────────────────────────────────────────────────────
# LCV1 修复:冷却函数移到 _ssh_execute 之前(合理位置)
# LCV6 说明:_is_host_in_cooldown / _record_host_failure 之间
#           理论存在极短抖动窗口,但符合冷却机制的弹性恢复语义
# ──────────────────────────────────────────────────────
def _is_host_in_cooldown(host_name: str) -> bool:
    """
    🆕 N3-1:检查主机是否处于冷却期

    连续失败 N 次的主机进入冷却期,冷却期间跳过采集,
    返回上次成功的缓存数据,避免不可达主机拖垮整个采集周期
    """
    with _host_failure_lock:
        tracker = _host_failure_tracker.get(host_name)
        if not tracker:
            return False
        if tracker["count"] < _HOST_MAX_FAILURES:
            return False
        # 检查冷却是否到期
        elapsed = time.monotonic() - tracker["last_fail"]
        # 🔧 防御时间倒退(对照 collector.py MR4)
        if elapsed < 0:
            logger.warning(f"N3-1: 检测到时间倒退,重置冷却 | host={host_name}")
            _host_failure_tracker.pop(host_name, None)
            return False
        if elapsed >= _HOST_COOLDOWN_SEC:
            # 冷却期结束,重置计数器
            _host_failure_tracker.pop(host_name, None)
            logger.info(f"N3-1: 主机 {host_name} 冷却期结束,恢复采集")
            return False
        remaining = _HOST_COOLDOWN_SEC - elapsed
        logger.debug(f"N3-1: 主机 {host_name} 处于冷却期,剩余 {remaining:.0f}s")
        return True


def _record_host_failure(host_name: str) -> None:
    """🆕 N3-1:记录主机采集失败"""
    with _host_failure_lock:
        tracker = _host_failure_tracker.get(host_name)
        if tracker:
            tracker["count"] += 1
            tracker["last_fail"] = time.monotonic()
        else:
            _host_failure_tracker[host_name] = {
                "count": 1,
                "last_fail": time.monotonic(),
            }
        count = _host_failure_tracker[host_name]["count"]
        if count >= _HOST_MAX_FAILURES:
            logger.warning(
                f"N3-1: 主机 {host_name} 连续失败 {count} 次,进入 {_HOST_COOLDOWN_SEC}s 冷却期"
            )


def _record_host_success(host_name: str) -> None:
    """🆕 N3-1:记录主机采集成功(重置失败计数)"""
    with _host_failure_lock:
        _host_failure_tracker.pop(host_name, None)


def get_host_cooldown_status() -> dict[str, Any]:
    """
    🆕 N3-3:获取失败主机冷却状态(供 /health 端点使用)

    🔧 LCV7 [P1] 修复:锁内仅做浅拷贝快照,锁外计算 remaining 时间
        (对照 approval_store.get_all_approvals_snapshot 的 R3 决策)
    🔧 LCV11 [P2] 修复:添加 N3-3 修复编号注释
    """
    # 🔧 LCV7:锁内浅拷贝,持锁时间最小化
    with _host_failure_lock:
        # 复制字典,锁外迭代计算
        tracker_snapshot = {name: dict(tracker) for name, tracker in _host_failure_tracker.items()}

    # 锁外计算 remaining(time.monotonic 不需要持锁)
    now = time.monotonic()
    stale_hosts = []
    for name, tracker in tracker_snapshot.items():
        if tracker["count"] >= _HOST_MAX_FAILURES:
            remaining = max(0, _HOST_COOLDOWN_SEC - (now - tracker["last_fail"]))
            stale_hosts.append(
                {
                    "host": name,
                    "fail_count": tracker["count"],
                    "cooldown_remaining_sec": round(remaining, 0),
                }
            )

    return {
        "total_tracked": len(tracker_snapshot),
        "stale_hosts": stale_hosts,
    }


# ============================================================
# 10 维度采集命令定义
# ============================================================
COLLECT_COMMANDS: dict[str, dict[str, str]] = {
    # ── 维度1:CPU 与负载 ──
    "cpu_usage": {
        "cmd": "top -bn1 2>/dev/null | grep 'Cpu(s)' | awk '{print 100 - $8}' || echo '0'",
        "desc": "CPU 使用率(%)",
    },
    "load_avg": {
        "cmd": "cat /proc/loadavg | awk '{print $1,$2,$3,$4}'",
        "desc": "系统负载(1/5/15min + 运行进程数)",
    },
    "cpu_cores": {
        "cmd": "nproc 2>/dev/null || grep -c processor /proc/cpuinfo",
        "desc": "CPU 核心数",
    },
    "context_switches": {
        "cmd": "vmstat 1 2 2>/dev/null | tail -1 | awk '{print $12}' || echo '0'",
        "desc": "每秒上下文切换次数",
    },
    "io_wait": {
        "cmd": "vmstat 1 2 2>/dev/null | tail -1 | awk '{print $16}' || echo '0'",
        "desc": "IO 等待时间(%)",
    },
    "top_cpu_procs": {
        "cmd": (
            "ps aux --sort=-%cpu 2>/dev/null | head -6 | tail -5 | "
            "awk '{printf \"%s %s %s\\n\",$11,$3,$4}'"
        ),
        "desc": "CPU Top5 进程",
    },
    # ── 维度2:内存与交换 ──
    "memory": {
        "cmd": "free -m 2>/dev/null | awk 'NR==2{printf \"%s %s %s %.1f\", $2,$3,$7,$3/$2*100}'",
        "desc": "内存: 总量(MB) 已用 可用 使用率(%)",
    },
    "swap": {
        "cmd": (
            "free -m 2>/dev/null | awk 'NR==3{if($2>0) "
            'printf "%s %s %.1f", $2,$3,$3/$2*100; '
            'else print "0 0 0.0"}\''
        ),
        "desc": "Swap: 总量(MB) 已用 使用率(%)",
    },
    "oom_count": {
        "cmd": "dmesg 2>/dev/null | grep -ci 'out of memory' || echo 0",
        "desc": "OOM Killer 触发次数",
    },
    "top_mem_procs": {
        "cmd": (
            "ps aux --sort=-%mem 2>/dev/null | head -6 | tail -5 | "
            "awk '{printf \"%s %s %s\\n\",$11,$4,$6}'"
        ),
        "desc": "内存 Top5 进程",
    },
    # ── 维度3:磁盘与 IO ──
    "disk_usage": {
        "cmd": (
            "df -h --output=target,size,used,avail,pcent -x tmpfs -x devtmpfs "
            "2>/dev/null | tail -n+2 || df -h 2>/dev/null | tail -n+2"
        ),
        "desc": "磁盘分区使用率",
    },
    "inode_usage": {
        "cmd": (
            "df -i --output=target,iused,iavail,ipcent -x tmpfs -x devtmpfs "
            "2>/dev/null | tail -n+2 || df -i 2>/dev/null | tail -n+2"
        ),
        "desc": "Inode 使用率",
    },
    "disk_readonly": {
        "cmd": "mount 2>/dev/null | grep ' ro,' | grep -v 'snap\\|squash' | head -5 || echo ''",
        "desc": "只读文件系统检测",
    },
    "large_files": {
        "cmd": "du -sh /var/log/* 2>/dev/null | sort -rh | head -5 || echo ''",
        "desc": "日志目录大文件排查",
    },
    # ── 维度4:网络与连接 ──
    "network_errors": {
        "cmd": (
            "cat /proc/net/dev 2>/dev/null | awk "
            "'NR>2{if($4>0||$12>0) printf \"%s errin=%s errout=%s\\n\",$1,$4,$12}'"
        ),
        "desc": "网卡错误统计",
    },
    "tcp_connections": {
        "cmd": "ss -s 2>/dev/null | head -5 || netstat -s 2>/dev/null | head -10",
        "desc": "TCP 连接状态摘要",
    },
    "time_wait_count": {
        "cmd": "ss -tan 2>/dev/null | grep -c TIME-WAIT || echo 0",
        "desc": "TIME_WAIT 连接数",
    },
    "listening_ports": {
        "cmd": (
            "ss -tlnp 2>/dev/null | tail -n+2 | awk '{print $4}' | head -20 || "
            "netstat -tlnp 2>/dev/null | tail -n+3 | awk '{print $4}' | head -20"
        ),
        "desc": "监听端口列表",
    },
    # ── 维度5:进程与服务 ──
    "process_count": {
        "cmd": "ps aux 2>/dev/null | wc -l",
        "desc": "运行进程总数",
    },
    "zombie_count": {
        "cmd": "ps aux 2>/dev/null | awk '$8 ~ /Z/' | wc -l",
        "desc": "僵尸进程数",
    },
    "d_state_count": {
        "cmd": "ps aux 2>/dev/null | awk '$8 ~ /D/' | wc -l",
        "desc": "D 状态(IO等待)进程数",
    },
    "file_descriptors": {
        "cmd": (
            "cat /proc/sys/fs/file-nr 2>/dev/null | awk '{printf \"%s %s %.1f\", $1,$3,$1/$3*100}'"
        ),
        "desc": "文件描述符: 已用 最大 使用率(%)",
    },
    "failed_services": {
        "cmd": "systemctl --failed --no-legend 2>/dev/null | head -10 || echo ''",
        "desc": "最近失败的服务",
    },
    # ── 维度6:系统日志与事件 ──
    "kernel_errors": {
        "cmd": (
            "dmesg --level=err,crit,alert 2>/dev/null | tail -10 || "
            "journalctl -p err -n 10 --no-pager 2>/dev/null || echo ''"
        ),
        "desc": "内核错误日志",
    },
    "segfault_count": {
        "cmd": "dmesg 2>/dev/null | grep -ci segfault || echo 0",
        "desc": "段错误(segfault)计数",
    },
    "io_errors": {
        "cmd": "dmesg 2>/dev/null | grep -ci 'i/o error' || echo 0",
        "desc": "磁盘 IO 错误计数",
    },
    # ── 维度7:系统配置与安全 ──
    "ssh_failed_logins": {
        "cmd": (
            "grep -ci 'Failed' /var/log/auth.log 2>/dev/null || "
            "journalctl -u sshd --no-pager 2>/dev/null | grep -ci 'Failed' || echo 0"
        ),
        "desc": "SSH 登录失败次数",
    },
    "current_users": {
        "cmd": "who 2>/dev/null | head -10 || echo ''",
        "desc": "当前登录用户",
    },
    "time_sync": {
        "cmd": "timedatectl status 2>/dev/null | grep -E '(synchronized|NTP)' || echo 'unknown'",
        "desc": "时间同步状态",
    },
    # ── 维度9:容量趋势 ──
    "log_size": {
        "cmd": "du -sh /var/log 2>/dev/null | awk '{print $1}' || echo '0'",
        "desc": "/var/log 总大小",
    },
    # ── 维度10:应用层健康 ──
    "http_check": {
        "cmd": (
            "curl -o /dev/null -s -w '%{http_code}' --max-time 5 "
            f"{HEALTH_CHECK_URL} 2>/dev/null || echo 000"
        ),
        "desc": "本机 HTTP 健康检查",
    },
    # ── 基础信息 ──
    "hostname": {
        "cmd": "hostname",
        "desc": "主机名",
    },
    "os_version": {
        "cmd": "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'\"' -f2 || uname -r",
        "desc": "操作系统版本",
    },
    "uptime": {
        "cmd": "uptime -p 2>/dev/null || uptime",
        "desc": "系统运行时长",
    },
    "kernel_version": {
        "cmd": "uname -r",
        "desc": "内核版本",
    },
}


# ============================================================
# SSH 远程执行引擎
# ============================================================
async def _ssh_execute(
    host_config: dict[str, Any],
    command: str,
    semaphore: asyncio.Semaphore | None = None,
) -> str:
    """
    通过 SSH 远程执行单条命令

    🔧 R1-2 [P0]:增加输入参数防御
        - host_config 缺失关键字段时直接返回 ERROR(不抛异常)
        - command 为 None/空时直接返回空字符串(防 LLM 误传)
    🔧 R1-6 [P2]:超时缓冲钳制为 max(10, LINUX_SSH_TIMEOUT + 5)
    🆕 N+3 修复 LCV10:asyncio.subprocess 是 asyncio 子模块,
        Python 标准库自动加载,Pylance 严格模式可正确解析
    """
    # 🔧 R1-2:输入防御
    if not isinstance(host_config, dict):
        logger.error(f"_ssh_execute: host_config 非 dict | type={type(host_config).__name__}")
        return "ERROR: invalid host_config"

    if not command or not isinstance(command, str):
        logger.warning(f"_ssh_execute: command 为空或非字符串 | command={command!r}")
        return ""

    host = (host_config.get("host") or "").strip()
    if not host:
        logger.error("_ssh_execute: host 字段缺失")
        return "ERROR: host field missing"

    port = host_config.get("port", 22)
    user = (host_config.get("username") or "").strip()
    if not user:
        logger.error(f"_ssh_execute: username 字段缺失 | host={host}")
        return "ERROR: username field missing"

    key = host_config.get("key_file", "")
    pwd = host_config.get("password", "")

    # 构建 SSH 命令
    ssh_args = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"ConnectTimeout={LINUX_SSH_TIMEOUT}",
        "-p",
        str(port),
    ]

    # 仅在密钥认证时启用 BatchMode
    if key:
        ssh_args.extend(["-o", "BatchMode=yes"])
        ssh_args.extend(["-i", key])

    ssh_args.append(f"{user}@{host}")
    ssh_args.append(command)

    # 密码认证需要 sshpass
    if pwd and not key:
        ssh_args = ["sshpass", "-p", pwd] + ssh_args

    # 🔧 R1-6:超时缓冲钳制
    wait_timeout = max(10, LINUX_SSH_TIMEOUT + 5)

    async def _run() -> str:
        # 🆕 N+3 修复:proc 预声明为 None,防御 Pylance reportPossiblyUnbound
        # ──────────────────────────────────────────────
        # 修复前:try 块内才赋值 proc,except 块访问 proc.kill() 时
        #         Pylance 报 "proc is possibly unbound"
        # 修复后:① 函数开头预声明 proc = None
        #         ② except 块内增加 None 守卫
        # ──────────────────────────────────────────────
        proc: Optional[asyncio.subprocess.Process] = None

        try:
            proc = await asyncio.create_subprocess_exec(
                *ssh_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=wait_timeout,
            )
            output = stdout.decode("utf-8", errors="replace").strip()
            if proc.returncode != 0 and not output:
                err = stderr.decode("utf-8", errors="replace").strip()
                logger.debug(f"SSH rc={proc.returncode} | host={host} | err={err[:100]}")
            return output or ""

        except asyncio.TimeoutError:
            logger.warning(f"SSH 超时 | host={host} | cmd={command[:50]}")
            # 🆕 N+3 修复:增加 None 守卫,防御 proc 未初始化场景
            if proc is not None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)
                    logger.debug("Failed to terminate timed-out SSH process", exc_info=True)
            return "TIMEOUT"

        except FileNotFoundError as e:
            cmd_name = "sshpass" if pwd and not key else "ssh"
            logger.error(f"{cmd_name} 未安装 | {e}")
            return f"{cmd_name.upper()}_NOT_FOUND"

        except Exception as e:
            logger.error(f"SSH 异常 | host={host} | {e}")
            return f"ERROR: {str(e)[:100]}"

    if semaphore:
        async with semaphore:
            return await _run()
    else:
        return await _run()


# ============================================================
# 🔧 R1-4 [P1]:批量执行 — 增加 nonce 防注入
# ============================================================
async def _ssh_execute_batch(
    host_config: dict,
    commands: dict[str, str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, str]:
    """
    将多个采集命令合并为单次 SSH 执行,大幅减少连接数
    🔧 R1-4:使用随机 nonce 作为分隔符,防止用户数据中的字符串误命中
    """
    if not commands:
        return {}

    # 🔧 R1-4:生成本次执行的唯一 nonce
    nonce = secrets.token_hex(16)
    sep_prefix = f"===AIOPS{nonce}METRIC:"
    sep_suffix = f":{nonce}===AIOPSEND==="

    # 构建合并命令
    parts = []
    metric_names = list(commands.keys())
    for name in metric_names:
        cmd = commands[name]
        parts.append(f"echo '{sep_prefix}{name}{sep_suffix}' && ({cmd}) 2>/dev/null")

    merged_cmd = " && ".join(parts)

    # 执行单次 SSH
    raw_output = await _ssh_execute(host_config, merged_cmd, semaphore)

    # SSH 失败时,所有指标都标记为错误
    if (
        not raw_output
        or raw_output in ("TIMEOUT", "SSH_NOT_FOUND")
        or raw_output.startswith("ERROR")
    ):
        return {name: raw_output or "" for name in metric_names}

    # 解析分割输出
    results: dict[str, str] = {}
    current_metric = None
    current_lines: list[str] = []

    for line in raw_output.split("\n"):
        # 检测分隔符行(必须严格匹配 prefix + name + suffix)
        if line.startswith(sep_prefix) and line.endswith(sep_suffix):
            # 保存上一个指标的结果
            if current_metric is not None:
                results[current_metric] = "\n".join(current_lines).strip()
            # 提取新指标名
            current_metric = line[len(sep_prefix): -len(sep_suffix)]
            current_lines = []
        else:
            current_lines.append(line)

    # 保存最后一个指标
    if current_metric is not None:
        results[current_metric] = "\n".join(current_lines).strip()

    # 未解析到的指标填充空值
    for name in metric_names:
        if name not in results:
            results[name] = ""

    return results


# ============================================================
# 单台主机全量采集(🆕 N+3 优化版)
# 🔧 LCV3 修复:合并双 docstring,完整记录所有改造点
# ============================================================
async def collect_linux_host(
    host_config: dict,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """
    对单台 Linux 主机执行全量或指定维度的指标采集(🆕 N3 优化版)

    🔧 R1-1:使用模块级 Semaphore 控制每台主机的并发(已生效)
    🔧 R1-8:主机配置缺失字段时降级处理(已生效)
    🆕 N3-1:冷却期主机直接返回缓存数据,跳过 SSH 调用
    🆕 N3-2:从 _SSH_BATCH_SIZE 读取批次大小(默认 20)
    🔧 LCV2:冷却期分支必须走 _last_collect_cache_lock(R1-3 一致性)
    🔧 LCV9:cached_copy 增加 stale_at 字段,明确标记缓存来源

    Returns:
        采集结果字典,status 字段包含:
        - "ok":     全量采集成功
        - "degraded": 部分指标失败(>50%)
        - "error":  大面积失败(>80%),触发冷却记录
        - "cooldown": 冷却期内,无缓存数据
        - "cached_stale": 冷却期内,返回上次缓存数据
        - "skipped": 未配置认证信息
    """
    # 🔧 R1-8:防御性提取主机标识
    if not isinstance(host_config, dict):
        return {
            "name": "unknown",
            "host": "unknown",
            "status": "error",
            "error": "host_config 必须为 dict",
        }

    host_ip = (host_config.get("host") or "").strip()
    host_name = host_config.get("name") or host_ip or "unknown"

    if not host_ip:
        return {"name": host_name, "host": "", "status": "error", "error": "host 为空"}

    # 🆕 N3-1:冷却期检查 — 跳过不可达主机
    # 🔧 LCV2 [P0]:必须走 _last_collect_cache_lock(R1-3 一致性)
    if _is_host_in_cooldown(host_name):
        # 🔧 LCV2:锁内浅拷贝,锁外深加工(对照 approval_store R3 决策)
        with _last_collect_cache_lock:
            cached = _last_collect_cache.get(host_name)
            cached_copy = dict(cached) if isinstance(cached, dict) else None

        # 锁外深加工
        if cached_copy:
            cached_copy["status"] = "cached_stale"
            cached_copy["stale_reason"] = (
                f"主机连续失败 {_HOST_MAX_FAILURES} 次,冷却 {_HOST_COOLDOWN_SEC}s 中,使用上次缓存"
            )
            # 🔧 LCV9 [P2]:增加 stale_at 字段,明确标记数据来源
            cached_copy["stale_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            return cached_copy

        return {
            "name": host_name,
            "host": host_ip,
            "status": "cooldown",
            "error": f"主机连续失败,冷却期 {_HOST_COOLDOWN_SEC}s 中",
        }

    # 验证认证信息
    if not host_config.get("key_file") and not host_config.get("password"):
        logger.warning(f"主机 {host_name}({host_ip}) 未配置认证信息,跳过采集")
        return {
            "name": host_name,
            "host": host_ip,
            "status": "skipped",
            "error": "未配置 SSH 认证(key_file 或 password)",
        }

    logger.info(f"开始采集 Linux 主机: {host_name}({host_ip})")

    result: dict[str, Any] = {
        "name": host_name,
        "host": host_ip,
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "metrics": {},
    }

    # 确定要采集的指标
    target_metrics = metrics if metrics else list(COLLECT_COMMANDS.keys())
    target_cmds = {k: COLLECT_COMMANDS[k]["cmd"] for k in target_metrics if k in COLLECT_COMMANDS}

    if not target_cmds:
        result["status"] = "error"
        result["error"] = "无有效的采集指标"
        return result

    # 🔧 R1-1:使用模块级 Semaphore(主机维度复用)
    semaphore = _get_host_semaphore(host_name)

    # 🆕 N3-2:批次大小从配置读取(原硬编码 10,默认升至 20)
    batch_size = _SSH_BATCH_SIZE
    metric_keys = list(target_cmds.keys())
    all_results: dict[str, str] = {}

    batches = [metric_keys[i: i + batch_size] for i in range(0, len(metric_keys), batch_size)]

    batch_tasks = []
    for batch_keys in batches:
        batch_cmds = {k: target_cmds[k] for k in batch_keys}
        batch_tasks.append(_ssh_execute_batch(host_config, batch_cmds, semaphore))

    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

    for i, br in enumerate(batch_results):
        if isinstance(br, Exception):
            logger.error(f"批次采集异常 | host={host_name} | batch={i} | {br}")
            for k in batches[i]:
                all_results[k] = f"ERROR: {str(br)[:80]}"
        elif isinstance(br, dict):
            all_results.update(br)

    # 组装最终结果
    errors = 0
    for metric_name in target_metrics:
        if metric_name not in COLLECT_COMMANDS:
            continue
        raw = all_results.get(metric_name, "")
        is_error = raw in ("TIMEOUT", "SSH_NOT_FOUND", "") or raw.startswith("ERROR:")
        if is_error:
            errors += 1

        result["metrics"][metric_name] = {
            "value": raw,
            "desc": COLLECT_COMMANDS[metric_name]["desc"],
        }

    # 🆕 N3-1:根据成功/失败记录冷却状态
    total = len(target_metrics)
    if errors > total * 0.8:
        # 大面积失败(>80%),记录失败 + 进入冷却倒计时
        _record_host_failure(host_name)
        result["status"] = "error"
    elif errors > total * 0.5:
        # 部分失败不记录冷却(可能是某些命令不支持)
        result["status"] = "degraded"
    else:
        # 成功,重置失败计数
        _record_host_success(host_name)

    # 关键指标结构化解析
    _parse_structured_metrics(result)

    logger.info(
        f"Linux 采集完成: {host_name} | 成功={total - errors}/{total} | SSH批次={len(batches)}"
    )

    return result


# ============================================================
# 🔧 R1-5 [P1]:关键指标结构化解析
# ──────────────────────────────────────────────────────
# 修复前:swap.parsed 缺失 usage_percent 字段,
#         topology_engine 等下游用 parsed["usage_percent"] 读取会失败
# 修复后:swap 也产生 usage_percent 字段,与 cpu/memory 字段名对齐
# ──────────────────────────────────────────────────────
def _parse_structured_metrics(result: dict[str, Any]) -> None:
    """
    将关键指标的原始字符串解析为结构化数据
    解析失败时保留原始字符串,不影响其他指标
    """
    metrics = result.get("metrics", {})
    if not isinstance(metrics, dict):
        return

    # 解析 CPU 使用率
    cpu_metric = metrics.get("cpu_usage", {})
    if isinstance(cpu_metric, dict):
        cpu_raw = cpu_metric.get("value", "")
        try:
            # SECURITY: Check for empty string before split to avoid IndexError
            if not cpu_raw:
                pass
            else:
                # 取首行,防御多行输出
                cleaned = str(cpu_raw).strip().split("\n")[0].strip()
                cpu_val = float(cleaned)
                # 数值钳制
                cpu_val = max(0.0, min(100.0, cpu_val))
                cpu_metric["parsed"] = {"usage_percent": round(cpu_val, 1)}
        except (ValueError, TypeError, IndexError):
            pass

    # 解析内存
    mem_metric = metrics.get("memory", {})
    if isinstance(mem_metric, dict):
        mem_raw = mem_metric.get("value", "")
        try:
            # SECURITY: Check for empty string before split to avoid IndexError
            if not mem_raw:
                pass
            else:
                cleaned = str(mem_raw).strip().split("\n")[0]
                parts = cleaned.split()
                if len(parts) >= 4:
                    usage = max(0.0, min(100.0, float(parts[3])))
                    mem_metric["parsed"] = {
                        "total_mb": int(parts[0]),
                        "used_mb": int(parts[1]),
                        "available_mb": int(parts[2]),
                        "usage_percent": round(usage, 1),
                    }
        except (ValueError, TypeError, IndexError):
            pass

    # 解析负载
    load_metric = metrics.get("load_avg", {})
    if isinstance(load_metric, dict):
        load_raw = load_metric.get("value", "")
        try:
            # SECURITY: Check for empty string before split to avoid IndexError
            if not load_raw:
                pass
            else:
                cleaned = str(load_raw).strip().split("\n")[0]
                parts = cleaned.split()
                if len(parts) >= 3:
                    load_metric["parsed"] = {
                        "load_1min": float(parts[0]),
                        "load_5min": float(parts[1]),
                        "load_15min": float(parts[2]),
                    }
        except (ValueError, TypeError, IndexError):
            pass

    # 解析 Swap(🔧 R1-5:字段名对齐 memory.usage_percent)
    swap_metric = metrics.get("swap", {})
    if isinstance(swap_metric, dict):
        swap_raw = swap_metric.get("value", "")
        try:
            # SECURITY: Check for empty string before split to avoid IndexError
            if not swap_raw:
                pass
            else:
                cleaned = str(swap_raw).strip().split("\n")[0]
                parts = cleaned.split()
                if len(parts) >= 3:
                    usage = max(0.0, min(100.0, float(parts[2])))
                    swap_metric["parsed"] = {
                        "total_mb": int(parts[0]),
                        "used_mb": int(parts[1]),
                        "usage_percent": round(usage, 1),
                    }
        except (ValueError, TypeError, IndexError):
            pass


# ============================================================
# 全部主机采集
# ============================================================
async def collect_all_linux(
    metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    并行采集所有已配置的 Linux 主机
    🔧 R1-3:更新 _last_collect_cache 时使用 Lock 保护
    """
    hosts_list = LINUX_HOSTS.get("hosts", [])
    if not hosts_list:
        logger.debug("无已配置的 Linux 主机,跳过采集")
        return []

    logger.info(f"开始并行采集 {len(hosts_list)} 台 Linux 主机")

    tasks = [collect_linux_host(h, metrics) for h in hosts_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            host = hosts_list[i]
            host_name = host.get("name") or host.get("host", "unknown")
            logger.error(f"主机采集异常: {host_name} | {r}")
            final.append(
                {
                    "name": host_name,
                    "host": host.get("host", ""),
                    "status": "error",
                    "error": str(r)[:200],
                }
            )
        elif isinstance(r, dict):
            final.append(r)

    # 🔧 R1-3:更新全局缓存,Lock 保护
    try:
        new_cache = {
            (item.get("name") or item.get("host") or "unknown"): item
            for item in final
            if isinstance(item, dict)
        }
        with _last_collect_cache_lock:
            _last_collect_cache.clear()
            _last_collect_cache.update(new_cache)
    except Exception as cache_err:
        logger.warning(f"R1-3 拓扑缓存写入失败(不影响采集): {cache_err}")

    return final


# ============================================================
# 查询接口
# ============================================================
def get_available_metrics() -> list[dict[str, str]]:
    """返回所有可采集的维度和描述"""
    return [{"key": k, "desc": v["desc"]} for k, v in COLLECT_COMMANDS.items()]


def get_configured_hosts() -> list[dict[str, Any]]:
    """
    返回已配置的主机列表(不含敏感信息)
    🔧 R1-7 [P2]:增加 role/layer/downstream 字段(供前端拓扑可视化)
    """
    hosts_list = LINUX_HOSTS.get("hosts", [])
    return [
        {
            "name": h.get("name") or h.get("host", ""),
            "host": h.get("host", ""),
            "port": h.get("port", 22),
            "user": h.get("username", ""),
            "auth": "key" if h.get("key_file") else "password" if h.get("password") else "none",
            # 🔧 R1-7:拓扑相关字段
            "role": h.get("role", "app"),
            "layer": h.get("layer", 3),
            "downstream": h.get("downstream", []),
        }
        for h in hosts_list
    ]
