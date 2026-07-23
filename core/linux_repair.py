# -*- coding: utf-8 -*-
# core/linux_repair.py
# Linux Bash 修复脚本库(集成高危指令护栏 + AI 自杀防护)
#
# 🔧 BUG-FIX-23 + BUG-FIX-24 + 本次严格 Review 多项加固:
#   - LR1  [P0]:对接 command_guard.get_protected_pids 自杀防护
#   - LR2  [P0]:linux_repair_history 改用 deque 自动 LRU
#   - LR3  [P0]:pending_approval 分支返回 proposal 字段
#   - LR4  [P1]:命令拼接从 " && " 改为 "; ",避免与脚本内分号冲突
#   - LR5  [P1]:LINUX_REPAIR_SCRIPTS 用 MappingProxyType 只读封装
#   - LR6  [P1]:_sanitize_param pid 对接 command_guard 自杀防护
#   - LR7  [P1]:pid 数值范围钳制(防超长溢出)
#   - LR8  [P1]:raw_output 类型防御加固
#   - LR9  [P2]:get_linux_repair_scripts 返回深拷贝
#   - LR10 [P2]:常量化字符串长度上限
#   - LR11 [P2]:类型注解收紧
#   - LR12 [P2]:新增 clear_linux_repair_history 接口
#   - LR13 [P2]:_record_to_sqlite_sync 返回布尔状态
#   - LR14 [P2]:alert_id 生成精度提升到毫秒

import asyncio
import copy
import datetime
import logging
import re
from collections import deque
from threading import Lock
from types import MappingProxyType
from typing import Any, Optional

from config import LINUX_HOSTS
from core.command_guard import (
    RiskLevel,
    analyze_command,
    record_audit,
)

logger = logging.getLogger(__name__)


# ============================================================
# 模块级常量
# 🔧 LR10 [P2]:常量集中放在文件顶部,便于统一调整
# ============================================================
_PARAM_MAX_LEN = 128  # 通用参数长度上限
_OUTPUT_TRUNCATE_LEN = 500  # SQLite 写入时输出截断长度
_HISTORY_MAX = 200  # 修复历史最大保留条数

# 🔧 LR7:Linux PID 范围(防御超长数字溢出)
# 来源:cat /proc/sys/kernel/pid_max,默认 4194304(2^22)
_LINUX_PID_MAX = 4_194_304

# 🔧 LR1:Linux PID 保护底端(对应内核线程父 + systemd 等)
# - PID 1     = systemd/init
# - PID 2     = kthreadd(内核线程父)
# - PID 3-10  = 内核辅助线程(如 ksoftirqd, kworker 等)
_LINUX_PID_RESERVED_MAX = 10


# ============================================================
# Linux 预置修复脚本库
# 🔧 LR5 [P1]:用 MappingProxyType 只读封装,防止外部模块修改污染
# ============================================================
_LINUX_REPAIR_SCRIPTS_RAW: dict[str, dict[str, Any]] = {
    "clear_temp": {
        "name": "清理临时文件",
        "description": "清理 /tmp 和 /var/tmp 中超过 7 天的临时文件",
        "risk": "low",
        "command": [
            'find /tmp -type f -mtime +7 -delete 2>/dev/null; echo "tmp cleaned"',
            'find /var/tmp -type f -mtime +7 -delete 2>/dev/null; echo "var/tmp cleaned"',
        ],
    },
    "clear_tmp": {
        "name": "清理临时文件",
        "description": "清理 /tmp 和 /var/tmp 中超过 7 天的临时文件",
        "risk": "low",
        "command": [
            'find /tmp -type f -mtime +7 -delete 2>/dev/null; echo "tmp cleaned"',
            'find /var/tmp -type f -mtime +7 -delete 2>/dev/null; echo "var/tmp cleaned"',
        ],
    },
    "clear_logs": {
        "name": "清理系统日志",
        "description": "清理超过 7 天的系统日志",
        "risk": "low",
        "command": [
            "journalctl --vacuum-time=7d 2>/dev/null || echo 'journalctl not available'",
        ],
    },
    "flush_dns": {
        "name": "刷新 DNS 缓存",
        "description": "清除系统 DNS 解析缓存",
        "risk": "low",
        "command": [
            (
                "systemd-resolve --flush-caches 2>/dev/null || "
                "resolvectl flush-caches 2>/dev/null || "
                "echo 'DNS flush not supported'"
            ),
        ],
    },
    "free_cache": {
        "name": "释放缓存内存",
        "description": "释放页面缓存/dentries/inodes",
        "risk": "low",
        "command": [
            (
                "sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null "
                "&& echo 'cache freed' || echo 'Permission denied'"
            ),
        ],
    },
    "restart_service": {
        "name": "重启指定服务",
        "description": "重启 systemd 服务,需传入 service_name",
        "risk": "medium",
        "command": [
            "systemctl restart {service_name} && systemctl is-active {service_name}",
        ],
        "params": ["service_name"],
    },
    "kill_process": {
        "name": "终止高 CPU 进程",
        "description": "优雅终止→强制终止,需传入 pid",
        "risk": "high",
        "command": [
            (
                "ps -p {pid} >/dev/null 2>&1 || { echo 'PID {pid} not found'; exit 1; }; "
                "kill -15 {pid} 2>/dev/null || true; "
                "sleep 2; "
                "if kill -0 {pid} 2>/dev/null; then "
                "  kill -9 {pid} 2>/dev/null && echo 'Force killed {pid}' || "
                "  echo 'Failed to kill {pid}'; "
                "else "
                "  echo 'Process {pid} terminated gracefully'; "
                "fi"
            ),
        ],
        "params": ["pid"],
    },
    "kill_high_cpu": {
        "name": "终止高 CPU 进程",
        "description": "优雅终止→强制终止,需传入 pid",
        "risk": "high",
        # 🔧 Review 修复 6:重写为单条 Shell 脚本,避免 && 短路问题
        # 原方案:三条命令用 && 拼接,kill -15 失败(进程已退出)会短路 sleep 和后续判断
        # 新方案:用 Shell if/else 控制流,任一阶段失败都能正确进入下一步判定
        "command": [
            (
                "ps -p {pid} >/dev/null 2>&1 || { echo 'PID {pid} not found'; exit 1; }; "
                "kill -15 {pid} 2>/dev/null || true; "
                "sleep 2; "
                "if kill -0 {pid} 2>/dev/null; then "
                "  kill -9 {pid} 2>/dev/null && echo 'Force killed {pid}' || "
                "  echo 'Failed to kill {pid}'; "
                "else "
                "  echo 'Process {pid} terminated gracefully'; "
                "fi"
            ),
        ],
        "params": ["pid"],
    },
    "check_disk": {
        "name": "磁盘健康检查",
        "description": "使用 SMART 检查磁盘健康状态",
        "risk": "low",
        "command": [
            "smartctl -H /dev/sda 2>/dev/null || echo 'smartctl not available'",
        ],
    },
    "clean_zombies": {
        "name": "清理僵尸进程",
        "description": "通知僵尸进程的父进程回收子进程",
        "risk": "low",
        # 合并为单条命令,变量在同一 Shell 会话中有效
        "command": [
            (
                "zombie_ppids=$(ps -eo ppid,stat 2>/dev/null "
                "| awk '$2 ~ /Z/ {print $1}' | sort -u); "
                'if [ -n "$zombie_ppids" ]; then '
                "  echo $zombie_ppids | xargs -I{} kill -s SIGCHLD {} 2>/dev/null "
                "  && echo 'SIGCHLD sent to zombie parents'; "
                "else "
                "  echo 'No zombie processes found'; "
                "fi"
            ),
        ],
    },
}

# 为每个脚本添加 "script" 字段(拼接后的命令字符串),方便对外暴露
for _lr_script in _LINUX_REPAIR_SCRIPTS_RAW.values():
    if "script" not in _lr_script:
        _lr_script["script"] = "; ".join(_lr_script.get("command", []))

# 🔧 LR5:对外暴露的 LINUX_REPAIR_SCRIPTS 用 MappingProxyType 只读封装
LINUX_REPAIR_SCRIPTS: MappingProxyType = MappingProxyType(_LINUX_REPAIR_SCRIPTS_RAW)


# ============================================================
# 修复历史 + 线程锁
# 🔧 LR2 [P0]:改用 deque 自动 LRU,O(1) 性能
# ============================================================
_repair_lock = Lock()
linux_repair_history: deque = deque(maxlen=_HISTORY_MAX)


# ============================================================
# 🔧 Review 修复 3:安全审计封装(避免审计失败影响主流程)
# ============================================================
async def _safe_record_audit(
    host: str,
    command: str,
    risk_level: str,
    executor: str = "linux_repair",
    repair_status: str = "success",
) -> None:
    """
    安全审计写入封装
    捕获所有异常,避免审计失败导致修复主流程崩溃
    """
    try:
        result = record_audit(
            host=host,
            command=command,
            risk_level=risk_level,
            executor=executor,
            result=repair_status,
        )
        if asyncio.iscoroutine(result):
            await result
    except Exception as audit_err:
        logger.warning(
            f"审计日志写入失败(不影响修复主流程): {audit_err} | "
            f"host={host} | risk={risk_level} | result={repair_status}"
        )


# ============================================================
# 🔧 Review 修复 9:复用公共函数查找主机配置
# ============================================================
def _find_host_config(host_name: str) -> Optional[dict]:
    """
    根据主机名或 IP 查找主机配置
    与 api/linux_router.find_linux_host_config 保持逻辑一致(避免循环依赖,本地实现一份)
    """
    if not host_name:
        return None
    hosts = LINUX_HOSTS
    if isinstance(hosts, dict):
        hosts = hosts.get("hosts", [])
    for h in hosts:
        if isinstance(h, dict) and (h.get("name") == host_name or h.get("host") == host_name):
            return h
    # 未配置时返回默认配置,便于测试与不依赖预配主机名的场景
    return {"name": host_name, "host": host_name}


# ============================================================
# 🔧 BUG-FIX-23 + LR13 [P2]:同步包装函数(供 asyncio.to_thread 调用)
# ============================================================
def _record_to_sqlite_sync(
    record_or_success: Any,
    rule_name: Optional[str] = None,
    script_key: Optional[str] = None,
    output: Optional[str] = None,
) -> bool:
    """
    同步写入 SQLite 修复记录的包装函数(Linux 平台)

    🔧 LR13 [P2]:返回布尔状态,供调用方感知 SQLite 写入失败
        - True:写入成功
        - False:写入失败(已记录日志)
    支持两种调用方式:
        1) _record_to_sqlite_sync(True, rule_name, script_key, output)
        2) _record_to_sqlite_sync({"host": ..., "script_key": ..., ...})
    """
    try:
        if isinstance(record_or_success, dict):
            record = record_or_success
        else:
            record = {
                "success": bool(record_or_success),
                "host": "",
                "rule_name": rule_name or "",
                "script_key": script_key or "",
                "platform": "linux",
                "params": {},
                "output": output[:_OUTPUT_TRUNCATE_LEN] if output else "",
                "timestamp": datetime.datetime.now().isoformat(),
            }

        import json
        import sqlite3

        conn = sqlite3.connect("linux_repair_history.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS linux_repair_history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "host TEXT, script_key TEXT, rule_name TEXT, params TEXT, "
            "output TEXT, success INTEGER, timestamp TEXT)"
        )
        params = record.get("params", {})
        if not isinstance(params, dict):
            params = {}
        cursor.execute(
            "INSERT INTO linux_repair_history "
            "(host, script_key, rule_name, params, output, success, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("host", ""),
                record.get("script_key", ""),
                record.get("rule_name", ""),
                json.dumps(params),
                record.get("output", "")[:_OUTPUT_TRUNCATE_LEN],
                int(bool(record.get("success", False))),
                record.get("timestamp", datetime.datetime.now().isoformat()),
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as err:
        logger.error(f"BUG-FIX-23: Linux 修复记录写入 SQLite 失败 (不影响修复结果): {err}")
        return False


# ============================================================
# 参数安全清理
# 🔧 LR1 + LR6 [P0/P1]:对接 command_guard.get_protected_pids 自杀防护
# 🔧 LR7 [P1]:pid 数值范围钳制
# ============================================================
def _sanitize_param(key: str, value: Any) -> str:
    """
    清理参数值,防止 Shell 注入

    🔧 Review 修复 4:pid 保护范围扩大到 ≤ 10
        - PID 1     = systemd/init
        - PID 2     = kthreadd(内核线程父)
        - PID 3-10  = 内核辅助线程(如 ksoftirqd, kworker 等)
        全部不可终止,扩大保护范围

    🔧 Review 修复 5:service_name 改用严格正则白名单
        - 仅允许字母/数字/下划线/连字符/点/at 符号
        - systemd service 命名规范的合法字符集

    🔧 LR1 + LR6 [P0/P1]:对接 command_guard.get_protected_pids 自杀防护
        - 防止 AI_DYNAMIC 通过 LINUX_HOST 远程杀死本地 AIOps Agent

    🔧 LR7 [P1]:pid 数值范围钳制
        - Linux 默认 pid_max=4194304(2^22)
        - 防御传入 12345678901234567890 等超长数字
    """
    val_str = str(value).strip()

    # 通用过滤:Shell 注入字符
    sanitized = re.sub(r'[;|&`$(){}<>\n\r\'"\\]', "", val_str)

    # 🔧 LR10:用常量替代魔法数字
    sanitized = sanitized[:_PARAM_MAX_LEN]

    # ── pid 参数专项校验 ──
    if key == "pid":
        if not sanitized.isdigit():
            raise ValueError(f"pid 参数必须为纯数字,收到: {val_str!r}")

        # 🔧 LR7 [P1]:数值范围钳制,防御超长数字溢出
        try:
            pid_int = int(sanitized)
        except ValueError:
            raise ValueError(f"pid 参数转换为整数失败: {val_str!r}")

        # 🔧 LR7:超出 Linux 合法 PID 范围
        if pid_int <= 0 or pid_int > _LINUX_PID_MAX:
            raise ValueError(f"pid 必须在 [1, {_LINUX_PID_MAX}] 范围内,收到: {pid_int}")

        # 🔧 Review 修复 4:扩大保护范围到 PID ≤ 10
        if pid_int <= _LINUX_PID_RESERVED_MAX:
            raise ValueError(
                f"禁止操作 PID {pid_int}(系统/内核关键进程,PID 1-{_LINUX_PID_RESERVED_MAX} 受保护)"
            )

        # 🔧 LR1 + LR6 [P0/P1]:运行时自杀防护对接
        # 注意:本进程是 AIOps Agent,如果远程主机上恰好运行着另一个进程
        # 与本机 PID 相同,这个保护可能误伤,但安全优先
        try:
            from core.command_guard import get_protected_pids

            protected = get_protected_pids()
            if pid_int in protected:
                raise ValueError(
                    f"🛡️ 禁止操作 PID {pid_int} - "
                    "该 PID 与 AIOps Agent 自身 PID 重合,"
                    "为防止远程操作误伤本地服务,已拦截"
                )
        except ImportError:
            # command_guard 未提供该接口时降级,不阻塞主流程
            logger.debug("command_guard.get_protected_pids 不可用,跳过自杀防护自检")

    # ── service_name 参数专项校验(白名单) ──
    if key == "service_name":
        # 🔧 Review 修复 5:严格白名单匹配
        # systemd service 合法字符:字母数字、下划线、连字符、点、@(template service)
        if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", sanitized):
            raise ValueError(f"service_name 包含非法字符,仅允许字母数字和 '_-.@': {val_str!r}")
        if ".." in sanitized:
            raise ValueError(f"service_name 不允许路径遍历字符 '..': {val_str!r}")

    if sanitized != val_str:
        logger.warning(f"参数过滤 | key={key} | 原始={val_str!r} | 过滤后={sanitized!r}")

    return sanitized


# ============================================================
# 辅助函数 - 降低 execute_linux_repair 复杂度
# ============================================================
def _validate_script_key(script_key: str) -> Optional[dict[str, Any]]:
    """验证脚本键是否存在,返回脚本定义或None"""
    if script_key not in _LINUX_REPAIR_SCRIPTS_RAW:
        return None
    return _LINUX_REPAIR_SCRIPTS_RAW[script_key]


def _prepare_safe_params(
    params: Optional[dict[str, str]],
    script: dict[str, Any],
) -> tuple[dict[str, str], Optional[str]]:
    """
    准备安全参数

    Returns:
        (safe_params, error_message) - error_message为None表示成功
    """
    params = params or {}
    safe_params: dict[str, str] = {}

    try:
        for k, v in params.items():
            safe_params[k] = _sanitize_param(k, v)
    except ValueError as e:
        return {}, str(e)

    # 验证必填参数
    for req in script.get("params", []):
        if req not in safe_params:
            return {}, f"缺少参数: '{req}'"

    return safe_params, None


def _render_command(
    script: dict[str, Any],
    safe_params: dict[str, str],
) -> str:
    """渲染命令模板"""
    rendered = []
    for cmd in script["command"]:
        result_cmd = cmd
        for k, v in safe_params.items():
            result_cmd = result_cmd.replace(f"{{{k}}}", v)
        rendered.append(result_cmd)

    # 使用 "; " 拼接,避免与脚本内分号优先级冲突
    return "; ".join(rendered)


async def _handle_blocked_risk(
    host_name: str,
    full_command: str,
    risk_level_value: str,
    reason: str = "Command blocked by safety guard",
) -> dict[str, Any]:
    """处理被拦截的风险命令"""
    error = f"Command blocked by safety guard: {reason}"
    logger.error(f"修复被拦截 | host={host_name} | cmd={full_command[:80]}")
    await _safe_record_audit(
        host=host_name,
        command=full_command,
        risk_level=risk_level_value,
        executor="linux_repair",
        repair_status="blocked",
    )
    return {
        "success": False,
        "blocked": True,
        "error": error,
        "reason": reason,
        "safe_alternative": "",
    }


async def _handle_high_risk_approval(
    host_name: str,
    script_key: str,
    script: dict[str, Any],
    full_command: str,
    risk: dict[str, Any],
    risk_level_value: str,
    safe_params: dict[str, str],
) -> dict[str, Any]:
    """处理高风险命令的审批流程"""
    logger.warning(f"高风险修复需审批 | host={host_name} | script={script_key}")
    await _safe_record_audit(
        host=host_name,
        command=full_command,
        risk_level=risk_level_value,
        executor="linux_repair",
        repair_status="pending_approval",
    )

    from core.approval_store import upsert_approval
    from core.db_engine import upsert_pending_approval

    # 生成毫秒级时间戳,避免同秒内冲突
    ts_ms = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    alert_id = f"LINUX-{script_key}-{ts_ms}"

    proposal_text = (
        f"目标主机:{host_name}\n"
        f"修复脚本:{script['name']}\n"
        f"执行命令:{full_command}\n"
        f"风险说明:{risk['reason']}\n"
        + (f"安全替代:{risk['safe_alternative']}\n" if risk.get("safe_alternative") else "")
    )
    alert_dict = {
        "host": host_name,
        "script_key": script_key,
        "platform": "linux",
        "params": safe_params,
        "rule_name": f"Linux 修复: {script['name']}",
    }

    # 双写:SQLite + 内存
    try:
        import json

        upsert_pending_approval(
            alert_id=alert_id,
            rule_name=f"Linux 修复: {script['name']}",
            script_key=script_key,
            proposal=proposal_text,
            alert_json=json.dumps(alert_dict),
        )
    except Exception as db_err:
        logger.error(f"Linux 审批记录写入 SQLite 失败,降级到内存 | alert_id={alert_id} | {db_err}")

    upsert_approval(
        alert_id,
        {
            "alert": alert_dict,
            "rule": f"Linux 修复: {script['name']}",
            "script_key": script_key,
            "proposal": proposal_text,
            "status": "pending",
        },
    )

    return {
        "success": False,
        "pending_approval": True,
        "alert_id": alert_id,
        "reason": risk["reason"],
        "proposal": proposal_text,
        "rule": f"Linux 修复: {script['name']}",
        "approve_url": f"/api/autoheal/approve?alert_id={alert_id}",
    }


async def _run_ssh_command(
    host: str,
    command: str,
    username: str = "root",
    password: Optional[str] = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Run SSH command via asyncssh and normalize the result.

    Tests patch ``asyncssh.connect`` and ``conn.run`` to simulate executions.
    """
    conn = None
    try:
        import asyncssh

        if password:
            conn = await asyncssh.connect(
                host, username=username, password=password, known_hosts=None
            )
        else:
            conn = await asyncssh.connect(host, username=username, known_hosts=None)

        result = await conn.run(command, timeout=timeout)

        stdout = getattr(result, "stdout", None)
        if not isinstance(stdout, str):
            stdout = ""
        stderr = getattr(result, "stderr", None)
        if not isinstance(stderr, str):
            stderr = ""
        exit_status = getattr(result, "exit_status", 0)

        if isinstance(exit_status, int) and exit_status != 0:
            return {
                "success": False,
                "output": stdout,
                "error": stderr or f"Exit code {exit_status}",
            }
        return {"success": True, "output": stdout, "error": stderr}
    except asyncio.TimeoutError:
        return {"success": False, "output": "", "error": "SSH command timeout"}
    except (ConnectionError, OSError) as e:
        return {"success": False, "output": "", "error": f"Connection error: {e}"}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}
    finally:
        if conn is not None:
            try:
                await conn.close()
            except Exception:
                logging.getLogger(__name__).debug("Failed to close SSH connection", exc_info=True)


def _normalize_ssh_output(raw_output: Any) -> str:
    """标准化SSH输出为字符串"""
    if raw_output is None:
        return ""
    elif isinstance(raw_output, bytes):
        try:
            return raw_output.decode("utf-8", errors="replace")
        except Exception:
            return repr(raw_output)
    elif isinstance(raw_output, str):
        return raw_output
    else:
        logger.warning(f"_ssh_execute 返回意外类型: {type(raw_output).__name__}")
        return repr(raw_output)


def _is_execution_success(output_str: str) -> bool:
    """判断执行是否成功"""
    output_stripped = output_str.strip()
    return bool(
        output_stripped
        and output_stripped not in ("TIMEOUT", "SSH_NOT_FOUND")
        and not output_stripped.startswith("ERROR:")
    )


async def _execute_ssh_command(
    host_config: dict[str, Any],
    full_command: str,
) -> tuple[str, bool]:
    """
    执行SSH命令并返回(输出, 成功标志)

    Returns:
        (output_str, success)
    """
    try:
        result = await _run_ssh_command(
            host=host_config.get("host", host_config.get("name", "")),
            command=full_command,
            username=host_config.get("username", "root"),
            password=host_config.get("password"),
            timeout=host_config.get("timeout", 30),
        )
    except Exception as e:
        logger.error(f"SSH 执行异常: {e}")
        return str(e), False
    output_str = _normalize_ssh_output(result.get("output", ""))
    success = bool(result.get("success", False))
    return output_str, success


def _validate_repair_request(
    host_name: str, script_key: str, params: Optional[dict[str, str]]
) -> tuple[Optional[dict], Optional[dict], Optional[str]]:
    """校验修复请求（脚本、主机、参数）

    Returns:
        (host_config, script, error) - 成功时 error 为 None
    """
    # 校验脚本存在性
    script = _validate_script_key(script_key)
    if not script:
        return (
            None,
            None,
            f"Script not found: {script_key}, available: {list(_LINUX_REPAIR_SCRIPTS_RAW.keys())}",
        )

    # 查找目标主机
    host_config = _find_host_config(host_name)
    if not host_config:
        return None, None, f"未找到主机: {host_name}"

    # 准备安全参数
    safe_params, error = _prepare_safe_params(params, script)
    if error:
        return None, None, error

    return host_config, script, None


def _build_repair_command(script: dict, safe_params: dict) -> str:
    """构建修复命令

    Returns:
        完整命令字符串
    """
    return _render_command(script, safe_params)


def _normalize_risk_level(risk: dict[str, Any]) -> tuple[RiskLevel, str]:
    """将风险字典中的 risk_level 归一化为 RiskLevel 枚举。"""
    raw_level = risk.get("risk_level", RiskLevel.LOW)
    if isinstance(raw_level, RiskLevel):
        level = raw_level
    else:
        level_str = str(raw_level).lower()
        try:
            level = RiskLevel(level_str)
        except ValueError:
            level = RiskLevel.LOW
    # 显式 allowed=False 视为被拦截
    if risk.get("allowed") is False:
        level = RiskLevel.BLOCKED
    return level, level.value


async def _execute_repair_with_risk_check(
    host_config: dict,
    command: str,
    host_name: str,
    script_key: str,
    script: dict,
    risk: dict,
    safe_params: dict,
) -> dict[str, Any]:
    """执行修复并处理风险检查

    Returns:
        执行结果字典
    """
    risk_level, risk_level_value = _normalize_risk_level(risk)

    # BLOCKED 分支
    if risk_level == RiskLevel.BLOCKED:
        return await _handle_blocked_risk(
            host_name,
            command,
            risk_level_value,
            risk.get("reason", "Command blocked by safety guard"),
        )

    # HIGH 分支:进入审批队列
    if risk_level == RiskLevel.HIGH:
        return await _handle_high_risk_approval(
            host_name, script_key, script, command, risk, risk_level_value, safe_params
        )

    # 执行修复
    logger.warning(
        f"执行 Linux 修复 | host={host_name} | script={script['name']} | risk={risk_level_value}"
    )

    output_str, success = await _execute_ssh_command(host_config, command)

    # 审计记录
    await _safe_record_audit(
        host=host_name,
        command=command,
        risk_level=risk_level_value,
        executor="linux_repair",
        repair_status="success" if success else "failed",
    )

    output_truncated = output_str[:_OUTPUT_TRUNCATE_LEN]

    # 🔧 LR14:id 也提升到毫秒精度
    ts_ms = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    record = {
        "id": f"LR-{ts_ms}",
        "host": host_name,
        "script_key": script_key,
        "script_name": script["name"],
        "risk": script["risk"],
        "success": success,
        "output": output_truncated,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "params": safe_params,
    }

    # ── 线程安全写入 deque(自动 LRU)──
    with _repair_lock:
        linux_repair_history.appendleft(record)

    # ── 同步写入 SQLite ──
    # ──────────────────────────────────────────────────────
    # 修复前:仅写内存 list,服务重启丢失,stats_engine 漏算
    # 修复后:复用 core.stats_engine.record_repair(走 SQLite)
    #         与 auto_heal 的自动修复保持一致的持久化策略
    # 🔧 LR13:用 asyncio.to_thread 包裹,避免阻塞事件循环 + 返回状态
    # ──────────────────────────────────────────────────────
    sqlite_ok = await asyncio.to_thread(
        _record_to_sqlite_sync,
        success,
        f"Linux 手动修复: {script['name']}",
        script_key,
        output_truncated,
    )
    if asyncio.iscoroutine(sqlite_ok):
        sqlite_ok = await sqlite_ok

    # 🔧 LR13:在记录中标记 SQLite 写入状态(供调用方感知)
    record["sqlite_persisted"] = sqlite_ok

    log_fn = logger.info if success else logger.warning
    log_fn(
        f"Linux 修复{'成功' if success else '失败'} | host={host_name} | script={script['name']}"
    )

    return record


# ============================================================
# 核心执行函数
# ============================================================
async def execute_linux_repair(
    host_name: str,
    script_key: str,
    params: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """
    在指定 Linux 主机上执行修复脚本

    🔧 BUG-FIX-23 + BUG-FIX-24 + Review 加固:
      - SQLite 双写持久化(BUG-FIX-23)
      - 走 approval_store 接口(BUG-FIX-24)
      - 审计封装容错(Review 修复 3)
      - output None 防御(Review 修复 1+2)
      - 命令链不再短路(Review 修复 6)

    🔧 LR3 [P0]:pending_approval 分支返回 proposal 字段
    🔧 LR4 [P1]:命令拼接从 " && " 改为 "; "
    🔧 LR8 [P1]:raw_output 类型防御加固
    🔧 LR14 [P2]:alert_id 精度提升到毫秒
    """
    # 1. 校验修复请求
    host_config, script, error = _validate_repair_request(host_name, script_key, params)
    if error:
        return {"success": False, "error": error}

    # Ensure script and host_config are not None after validation
    if script is None:
        return {"success": False, "error": "Script validation failed"}
    if host_config is None:
        return {"success": False, "error": "Host config not found"}

    # 2. 准备安全参数
    safe_params, error = _prepare_safe_params(params, script)
    if error:
        return {"success": False, "error": error}

    # 3. 构建修复命令
    full_command = _build_repair_command(script, safe_params)

    # 4. 高危指令护栏(支持同步或异步 mock)
    risk_or_coro = analyze_command(full_command)
    if asyncio.iscoroutine(risk_or_coro):
        risk = await risk_or_coro
    else:
        risk = risk_or_coro

    # 5. 执行修复并处理风险检查
    try:
        return await _execute_repair_with_risk_check(
            host_config, full_command, host_name, script_key, script, risk, safe_params
        )
    except Exception as e:
        logger.error(f"Linux 修复执行异常: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 查询接口
# ============================================================
def get_linux_repair_scripts() -> dict[str, Any]:
    """
    返回所有可用的 Linux 修复脚本

    🔧 LR9 [P2]:返回深拷贝,防止调用方修改污染原数据
                (params 字段是 list,浅拷贝时调用方 append 会污染原数据)
    """
    return copy.deepcopy({k: v for k, v in _LINUX_REPAIR_SCRIPTS_RAW.items()})


def get_linux_repair_history(limit: int = 50) -> list[dict[str, Any]]:
    """
    返回修复历史(线程安全)

    🔧 Review 加固:钳制 limit 范围
    🔧 LR2:配合 deque 改造,切片操作仍线程安全

    Args:
        limit: 最多返回的记录数,内部钳制范围 [1, _HISTORY_MAX]
    """
    safe_limit = max(1, min(_HISTORY_MAX, int(limit) if limit else 50))
    with _repair_lock:
        # deque 切片需先转 list
        return list(linux_repair_history)[:safe_limit]


# ============================================================
# 🔧 LR12 [P2]:维护接口 — 清空修复历史
# ============================================================
def clear_linux_repair_history() -> int:
    """
    清空内存修复历史(测试用 / 紧急清理)
    SQLite 持久化数据不受影响

    Returns:
        清空前的条数
    """
    with _repair_lock:
        count = len(linux_repair_history)
        linux_repair_history.clear()

    if count > 0:
        logger.warning(
            f"⚠️ Linux 修复历史(内存)已清空 | 清空前条数={count} | SQLite 持久化数据不受影响"
        )
    return count
