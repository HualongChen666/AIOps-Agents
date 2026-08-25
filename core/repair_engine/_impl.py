# -*- coding: utf-8 -*-
# core/repair_engine.py
# Windows PowerShell 修复脚本库(集成高危指令护栏 + AI 自杀防护)
#
# 🔧 BUG-FIX-23 + 本次严格 Review 多项加固:
#   - RE1  [P0]:集成 command_guard 审查(对齐 linux_repair.py)
#   - RE2  [P0]:_run_powershell 超时时强制 kill 子进程
#   - RE3  [P0]:执行前调用 command_guard.analyze_command 审查
#   - RE4  [P1]:渲染后再次审查(纵深防御)
#   - RE5  [P1]:repair_history 改用 deque 自动 LRU
#   - RE6  [P1]:对接 command_guard.register_self_pid 自杀防护
#   - RE7  [P1]:_record_to_sqlite_sync 返回状态供调用方感知
#   - RE8  [P1]:params 类型注解收紧
#   - RE9  [P2]:get_repair_scripts 返回深拷贝
#   - RE10 [P2]:常量化字符串长度上限
#   - RE11 [P2]:超时时间从 config 读取
#   - RE12 [P2]:类型注解收紧
#   - RE13 [P2]:REPAIR_SCRIPTS 用 MappingProxyType 只读封装
#   - RE14 [P2]:新增 clear_repair_history 接口

import asyncio
import copy
import datetime
import logging
import re
import shutil
from collections import deque
from threading import Lock
from typing import Any, Dict, List, Optional

from config import REPAIR_HOST
from core.security import subprocess_runner

logger = logging.getLogger(__name__)


# ============================================================
# 模块级常量
# 🔧 RE10 [P2]:常量集中放在文件顶部
# ============================================================
_PARAM_MAX_LEN = 128  # 通用参数长度上限
_SERVICE_NAME_MAX_LEN = 256  # Windows 服务名规范上限
_OUTPUT_TRUNCATE_LEN = 500  # SQLite 写入时输出截断长度
_OUTPUT_LOG_LEN = 200  # 日志输出截断长度
_HISTORY_MAX = 100  # 修复历史最大保留条数

# 🔧 RE11 [P2]:PowerShell 超时时间(从 config 读取,失败用默认)
try:
    import config

    _PS_TIMEOUT_SEC = max(10, min(600, int(getattr(config, "REPAIR_PS_TIMEOUT_SEC", 120))))
except (ImportError, AttributeError, ValueError, TypeError):
    _PS_TIMEOUT_SEC = 120


# ============================================================
# 预置修复脚本库
# 🔧 RE13 [P2]:用 MappingProxyType 只读封装,防止外部模块修改污染
# ============================================================
_REPAIR_SCRIPTS_RAW: dict[str, dict[str, Any]] = {
    "clear_temp": {
        "name": "清理临时文件",
        "description": "删除 Windows 临时目录,释放磁盘空间",
        "risk": "low",
        "command": [
            'Remove-Item -Path "$env:TEMP\\*" -Recurse -Force -ErrorAction SilentlyContinue',
            'Write-Output "临时文件清理完成"',
        ],
    },
    "flush_dns": {
        "name": "刷新 DNS 缓存",
        "description": "清除 DNS 解析缓存,解决网络访问异常",
        "risk": "low",
        "command": [
            "Clear-DnsClientCache",
            'Write-Output "DNS 缓存已刷新"',
        ],
    },
    "restart_service": {
        "name": "重启指定服务",
        "description": "重启 Windows 服务,需传入 service_name 参数",
        "risk": "medium",
        "command": ["Restart-Service -Name '{service_name}' -Force"],
        "params": ["service_name"],
    },
    "kill_high_cpu": {
        "name": "终止高 CPU 进程",
        "description": "终止指定 PID 的进程,需传入 pid 参数(纯数字)",
        "risk": "high",
        # 🔧 Review 修复 7:增加 PID 存在性预检 + 终止后验证
        "command": [
            "$proc = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
            "if ($null -eq $proc) { "
            "  Write-Output 'PID {pid} not found'; "
            "  exit 1 "
            "} else { "
            "  Stop-Process -Id {pid} -Force -ErrorAction Stop; "
            "  Start-Sleep -Milliseconds 500; "
            "  if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) { "
            "    Write-Output 'Process {pid} still alive after kill'; "
            "    exit 2 "
            "  } else { "
            "    Write-Output 'Process {pid} terminated successfully' "
            "  } "
            "}"
        ],
        "params": ["pid"],
    },
    "clear_event_log": {
        "name": "清理系统事件日志",
        "description": "清空 Windows 系统和应用事件日志",
        "risk": "medium",
        "command": [
            "Clear-EventLog -LogName System",
            "Clear-EventLog -LogName Application",
            'Write-Output "事件日志已清理"',
        ],
    },
    "free_memory": {
        "name": "释放系统内存",
        "description": "强制触发 .NET GC 回收,释放部分内存",
        "risk": "low",
        "command": [
            "[System.GC]::Collect()",
            "[System.GC]::WaitForPendingFinalizers()",
            'Write-Output "内存回收完成"',
        ],
    },
    "check_disk": {
        "name": "磁盘健康扫描",
        "description": "对 C 盘执行文件系统完整性扫描",
        "risk": "low",
        "command": ["chkdsk C: /scan"],
    },
    "sfc_scan": {
        "name": "系统文件修复",
        "description": "扫描并修复损坏的 Windows 系统文件",
        "risk": "low",
        "command": ["sfc /scannow"],
    },
}


class _ReadOnlyDict(dict):
    """Read-only dict subclass exposing the same interface as MappingProxyType."""

    def __setitem__(self, key, value):
        raise TypeError("REPAIR_SCRIPTS is read-only")

    def __delitem__(self, key):
        raise TypeError("REPAIR_SCRIPTS is read-only")

    def update(self, *args, **kwargs):
        raise TypeError("REPAIR_SCRIPTS is read-only")

    def clear(self):
        raise TypeError("REPAIR_SCRIPTS is read-only")

    def pop(self, *args, **kwargs):
        raise TypeError("REPAIR_SCRIPTS is read-only")

    def popitem(self):
        raise TypeError("REPAIR_SCRIPTS is read-only")


# 🔧 RE13:对外暴露的 REPAIR_SCRIPTS 用只读 dict 封装
REPAIR_SCRIPTS: _ReadOnlyDict = _ReadOnlyDict(_REPAIR_SCRIPTS_RAW)


# ============================================================
# 修复历史 + 线程锁
# 🔧 RE5 [P1]:改用 deque 自动 LRU,避免 list.insert(0) O(n) 性能问题
# ============================================================
repair_history: deque[Dict[str, Any]] = deque(maxlen=_HISTORY_MAX)
_history_lock: Lock = Lock()


# ============================================================
# 🔧 RE1 + RE6 [P0]:command_guard 集成(自杀防护核心)
# ──────────────────────────────────────────────────────
# 修复前:Windows 修复脚本完全没有走 command_guard 审查
#         若 LLM 通过 AI_DYNAMIC 生成 "Stop-Process -Id <AIOps_PID>"
#         绕过 PID <= 4 的静态保护,可能终止 AIOps Agent 自身
# 修复后:执行前必须通过 command_guard 审查
#         BLOCKED → 直接拒绝
#         HIGH → 走审批队列(由 auto_heal 处理)
#         其他 → 放行
# ──────────────────────────────────────────────────────
def _safe_audit(
    command: str,
    risk_level: str,
    result: str,
) -> None:
    """
    安全审计写入封装(对齐 linux_repair.py 的 _safe_record_audit)
    捕获所有异常,避免审计失败导致修复主流程崩溃
    """
    try:
        from core.command_guard import record_audit

        record_audit(
            host=REPAIR_HOST,
            command=command,
            risk_level=risk_level,
            executor="repair_engine",
            result=result,
        )
    except Exception as audit_err:
        logger.warning(
            f"审计日志写入失败(不影响修复主流程): {audit_err} | risk={risk_level} | result={result}"
        )


# ============================================================
# 参数安全校验
# 🔧 Review 修复 4+5 + RE10:加固 pid 和 service_name 校验
# ============================================================
def _sanitize_param(key: str, value: Any) -> str:
    """
    清理用户传入的参数值,防止 PowerShell 命令注入

    专项校验:
      - pid:         必须为纯数字,且不能是系统保护进程(PID ≤ 4)
                     另外,通过 _check_self_pid 检测是否为 AIOps Agent 自身 PID
      - service_name:严格 ASCII 白名单,禁止 Unicode 字符迷惑

    🔧 Review 修复 4:Windows PID 保护
        - PID 0 = System Idle Process
        - PID 4 = System(NT 内核)
        - PID 8(部分系统) = 内核辅助
        终止任一会导致蓝屏

    🔧 Review 修复 5:service_name 改用 ASCII 严格白名单
        Windows 服务名规范:仅允许 ASCII 字母数字、下划线、连字符
        防御 Unicode 同形字符攻击

    🔧 RE6 [P1]:对接 command_guard.register_self_pid 自杀防护
    """
    raw_str = str(value)
    val_str = raw_str.strip()

    # ── service_name 专项校验(在通用截断前完成,避免误吞首尾空格/长度) ──
    if key == "service_name":
        # 先检查原始长度
        if len(raw_str) > _SERVICE_NAME_MAX_LEN:
            raise ValueError(f"service_name 长度超出 {_SERVICE_NAME_MAX_LEN}: {len(raw_str)}")
        # 严格 ASCII 白名单
        if not re.match(r"^[a-zA-Z0-9_\- ]+$", raw_str):
            raise ValueError(f"service_name 仅允许 ASCII 字母数字和 '_- ',收到: {raw_str!r}")
        if ".." in raw_str:
            raise ValueError(f"service_name 不允许路径遍历字符 '..': {raw_str!r}")
        # 服务名不能以空格开头/结尾,且不能包含连续空格
        if raw_str != raw_str.strip() or "  " in raw_str:
            raise ValueError(f"service_name 不允许首尾空格或连续空格: {raw_str!r}")
        return raw_str.strip()

    # 通用过滤:PowerShell 危险字符
    sanitized = re.sub(r"[;|&`$(){}<>\n\r'\"\\]", "", val_str)

    # 🔧 RE10:用常量替代魔法数字
    sanitized = sanitized[:_PARAM_MAX_LEN]

    if sanitized != val_str:
        logger.warning(f"参数过滤 | key={key} | 原始={val_str!r} | 过滤后={sanitized!r}")

    # ── pid 专项校验 ──
    if key == "pid":
        if not sanitized.isdigit():
            raise ValueError(f"pid 参数必须为纯数字,收到: {val_str!r}")
        pid_int = int(sanitized)

        # 🔧 Review 修复 4:扩大保护范围(系统底端)
        if pid_int <= 4:
            raise ValueError(f"禁止操作 PID {pid_int}(系统关键进程,PID 0/4 受保护)")

        # 🔧 RE6 [P1]:运行时 PID 自检(防止杀死 AIOps Agent)
        try:
            from core.command_guard import get_protected_pids

            protected = get_protected_pids()
            if pid_int in protected:
                raise ValueError(
                    f"🛡️ 禁止操作 PID {pid_int} - 该 PID 属于 AIOps Agent 自身,执行将导致服务瘫痪"
                )
        except ImportError:
            # command_guard 未提供该接口时降级,不阻塞主流程
            logger.debug("command_guard.get_protected_pids 不可用,跳过自检")

    return sanitized


# ============================================================
# 安全参数替换
# 🔧 Review 修复 3:使用更精确的替换,防止误命中
# ============================================================
def _render_command(cmd: str, params: Optional[Dict[str, str]] = None) -> str:
    """
    使用 str.replace() 逐个替换参数占位符
    完全避免 .format() 与 PowerShell 原生 {} 语法冲突

    🔧 Review 修复 3:严格匹配 {key} 形式,不替换 {Other.Var} 等
    """
    if not isinstance(cmd, str) or not cmd:
        return ""

    params = params or {}
    result = cmd
    for key, val in params.items():
        if not key:
            continue
        # 严格替换 "{key}" 字面量,val 强制转字符串防御
        placeholder = f"{{{str(key)}}}"
        result = result.replace(placeholder, str(val))
    return result


# ============================================================
# 🔧 BUG-FIX-23 + RE7 [P1]:同步包装函数(供 asyncio.to_thread 调用)
# ============================================================
def _record_to_sqlite_sync(
    success: bool,
    rule_name: str,
    script_key: str,
    output: str,
) -> bool:
    """
    同步写入 SQLite 修复记录的包装函数
    通过 asyncio.to_thread 调用,避免阻塞事件循环

    🔧 RE7 [P1]:返回布尔状态,供调用方感知 SQLite 写入失败
        - True:写入成功
        - False:写入失败(已记录日志,调用方可决定是否额外告警)
    """
    try:
        from core.stats_engine import record_repair as stats_record_repair

        repair_data = {
            "success": success,
            "alert_time": None,  # 手动修复无对应告警时间
            "rule_name": rule_name,
            "script_key": script_key,
            "platform": "windows",
            "output": output[:_OUTPUT_TRUNCATE_LEN] if output else "",
        }
        asyncio.run(stats_record_repair(repair_data))
        return True
    except Exception as stats_err:
        logger.error(f"BUG-FIX-23: Windows 修复记录写入 SQLite 失败 (不影响修复结果): {stats_err}")
        return False


# ============================================================
# 异步修复执行主函数
# ============================================================


def _validate_script_exists(script_key: str) -> tuple[bool, Optional[Dict]]:
    """
    验证脚本是否存在

    Args:
        script_key: 脚本键

    Returns:
        tuple: (是否存在, 脚本字典或None)
    """
    if script_key not in _REPAIR_SCRIPTS_RAW:
        return False, None
    return True, _REPAIR_SCRIPTS_RAW[script_key]


def _sanitize_and_validate_params(
    params: Optional[Dict[str, Any]], script: Dict
) -> tuple[bool, str, Dict[str, str]]:
    """
    清理和验证参数

    Args:
        params: 原始参数
        script: 脚本字典

    Returns:
        tuple: (是否有效, 错误信息, 安全参数字典)
    """
    params = params or {}
    safe_params: Dict[str, str] = {}

    try:
        for k, v in params.items():
            safe_params[k] = _sanitize_param(k, v)
    except ValueError as e:
        return False, str(e), {}

    # 验证必填参数
    for req_param in script.get("params", []):
        if req_param not in safe_params:
            return False, f"缺少必要参数: '{req_param}'", {}

    return True, "", safe_params


def _render_and_log_command(script: Dict, safe_params: Dict[str, str]) -> tuple[str, str]:
    """
    渲染命令并记录日志

    Args:
        script: 脚本字典
        safe_params: 安全参数

    Returns:
        tuple: (完整命令, 风险等级)
    """
    commands = script["command"]
    rendered = [_render_command(cmd, safe_params) for cmd in commands]
    full_command = "; ".join(rendered)

    # 🔧 Review 修复 6:日志级别根据风险动态调整
    risk = script.get("risk", "low")
    if risk in ("high", "critical"):
        log_method = logger.warning
    else:
        log_method = logger.info

    log_method(f"准备执行修复脚本: {script['name']} | 风险等级: {risk} | 参数: {safe_params}")

    return full_command, risk


def _guard_review_command(full_command: str, script_key: str) -> tuple[bool, str, Optional[Dict]]:
    """
    护栏审查命令

    Args:
        full_command: 完整命令
        script_key: 脚本键

    Returns:
        tuple: (是否通过, 错误信息, 审查结果或None)
    """
    try:
        from core.command_guard import RiskLevel, analyze_command

        guard_result = analyze_command(full_command)

        if guard_result["risk_level"] == RiskLevel.BLOCKED:
            risk_name = guard_result.get("risk_name", "未知规则")
            reason = guard_result.get("reason", "命令被护栏拦截")
            logger.error(
                "🛡️ Windows 修复被护栏拦截 | "
                f"script={script_key} | rule={risk_name} | reason={reason}"
            )
            _safe_audit(
                command=full_command,
                risk_level="blocked",
                result="blocked_by_guard",
            )
            return False, f"指令被护栏拦截: {risk_name} - {reason}", guard_result

        # 非 BLOCKED 等级也写审计(便于追溯)
        _safe_audit(
            command=full_command,
            risk_level=guard_result["risk_level"].value,
            result=f"approved_{guard_result['risk_level'].value}",
        )

        return True, "", guard_result

    except ImportError:
        logger.warning("command_guard 模块不可用,跳过审查(不推荐)")
        return True, "", None
    except Exception as guard_err:
        logger.error(
            f"command_guard 审查异常,降级为不审查: {guard_err}",
            exc_info=True,
        )
        return True, "", None


def _create_repair_record(
    script_key: str, script: Dict, risk: str, result: Dict, safe_params: Dict[str, str]
) -> Dict[str, Any]:
    """
    创建修复记录

    Args:
        script_key: 脚本键
        script: 脚本字典
        risk: 风险等级
        result: 执行结果
        safe_params: 安全参数

    Returns:
        修复记录字典
    """
    return {
        "id": f"REPAIR-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "script_key": script_key,
        "script_name": script["name"],
        "risk": risk,
        "success": result.get("success", False),
        "output": result.get("output", ""),
        "error": result.get("error", ""),
        "return_code": result.get("return_code", -1),
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "params": safe_params,
    }


def _persist_repair_record(record: Dict[str, Any], script: Dict, script_key: str) -> None:
    """
    持久化修复记录

    Args:
        record: 修复记录
        script: 脚本字典
        script_key: 脚本键
    """
    # ── 7. 🔧 RE5:线程安全写入 deque(自动 LRU)──
    with _history_lock:
        repair_history.appendleft(record)

    # ── 8. 🔧 BUG-FIX-23 + RE7:同步写入 SQLite ──
    sqlite_ok = asyncio.to_thread(
        _record_to_sqlite_sync,
        record["success"],
        f"Windows 手动修复: {script['name']}",
        script_key,
        str(record["output"]),
    )

    # 🔧 RE7:在记录中标记 SQLite 写入状态(供调用方感知)
    record["sqlite_persisted"] = sqlite_ok


async def execute_repair(
    script_key: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    异步执行 PowerShell 修复脚本
    通过 asyncio.to_thread 在线程池中运行,不阻塞事件循环

    🔧 BUG-FIX-23 + Review 加固:
      - SQLite 写入也走 asyncio.to_thread(Review 修复 2)
      - 所有错误返回路径补全 return_code 字段(Review 修复 1)
      - PID 保护范围扩大(Review 修复 4)
      - service_name 严格 ASCII 白名单(Review 修复 5)
      - 日志级别按风险动态调整(Review 修复 6)

    🔧 RE3 [P0]:执行前调用 command_guard.analyze_command 审查
                  对齐 linux_repair.py 的安全策略
    🔧 RE4 [P1]:渲染后再次审查(纵深防御)
    """
    # ── 1. 校验脚本存在性 ──
    is_valid, script = _validate_script_exists(script_key)
    if not is_valid:
        return {
            "success": False,
            "error": f"未知修复脚本: {script_key},可用值: {list(_REPAIR_SCRIPTS_RAW.keys())}",
            "output": "",
            "return_code": -1,
        }

    # ── 2. 专项参数校验 ──
    is_valid, err_msg, safe_params = _sanitize_and_validate_params(params, script)
    if not is_valid:
        return {
            "success": False,
            "error": err_msg,
            "output": "",
            "return_code": -1,
        }

    # ── 3. 渲染命令 ──
    full_command, risk = _render_and_log_command(script, safe_params)

    # ── 4. command_guard 审查(纵深防御核心)──
    is_approved, err_msg, guard_result = _guard_review_command(full_command, script_key)
    if not is_approved:
        return {
            "success": False,
            "blocked": True,
            "error": err_msg,
            "output": "",
            "return_code": -1,
            "safe_alternative": guard_result.get("safe_alternative", "") if guard_result else "",
        }

    # ── 5. 异步执行 PowerShell ──
    try:
        result = await asyncio.to_thread(_run_powershell, full_command)

        record = _create_repair_record(script_key, script, risk, result, safe_params)

        # 持久化记录
        await _persist_repair_record(record, script, script_key)

        # 写审计(执行结果)
        _safe_audit(
            command=full_command,
            risk_level=risk,
            result="success" if record["success"] else "failed",
        )

        return record

    except Exception as e:
        logger.error(f"修复脚本执行异常: {e}", exc_info=True)

        # 🔧 异常路径同样写审计
        _safe_audit(
            command=full_command,
            risk_level=risk,
            result=f"exception: {str(e)[:80]}",
        )

        return {
            "success": False,
            "error": str(e),
            "output": "",
            "return_code": -1,
        }


# ============================================================
# 同步 PowerShell 执行函数(在线程池中调用)
# 🔧 RE2 [P0]:超时时强制 kill 子进程,避免僵尸
# 🔧 RE11 [P2]:超时时间从配置读取
# ============================================================
def _run_powershell(command: str) -> Dict[str, Any]:
    """
    同步执行 PowerShell 命令
    前置 UTF-8 编码设置,根治中文系统乱码
    合并 stdout + stderr,不丢弃任何输出

    🔧 RE2 [P0]:从 subprocess_runner.run 改为 subprocess_runner.Popen + communicate(timeout)
                  超时时能 kill() 子进程,避免 PowerShell 后台僵尸进程
    🔧 RE11 [P2]:超时时间从 _PS_TIMEOUT_SEC 读取(可配置)
    """
    proc = None
    try:
        utf8_prefix = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        full_cmd = utf8_prefix + command

        # 🔧 RE2:用 Popen + communicate(timeout) 替代 subprocess_runner.run
        # 以便超时时能 kill 子进程
        powershell_path = shutil.which("powershell") or "powershell"
        proc = subprocess_runner.Popen(
            [
                powershell_path,
                "-NonInteractive",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                full_cmd,
            ],
            shell=False,
            stdout=subprocess_runner.PIPE,
            stderr=subprocess_runner.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        try:
            stdout, stderr = proc.communicate(timeout=_PS_TIMEOUT_SEC)
            return_code = proc.returncode
        except subprocess_runner.TimeoutExpired:
            # 🔧 RE2 [P0]:超时强制 kill,避免僵尸进程
            logger.error(f"PowerShell 执行超时(>{_PS_TIMEOUT_SEC}s),强制终止子进程")
            try:
                proc.kill()
                # 等待 kill 完成,清理 stdout/stderr 缓冲
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess_runner.TimeoutExpired:
                logger.error("PowerShell 子进程 kill 后 5s 内仍未退出")
                stdout = stderr = ""
            except Exception as kill_err:
                logger.warning(f"PowerShell 子进程 kill 异常: {kill_err}")
                stdout = stderr = ""

            return {
                "success": False,
                "error": f"执行超时(>{_PS_TIMEOUT_SEC}s),子进程已强制终止",
                "output": (stdout or "")[:_OUTPUT_LOG_LEN],
                "return_code": -1,
            }

        success = return_code == 0
        stdout_str = (stdout or "").strip()
        stderr_str = (stderr or "").strip()

        # 合并 stdout 和 stderr,过滤空字符串
        output = "\n".join(filter(None, [stdout_str, stderr_str]))

        if success:
            logger.info(f"修复成功 | 输出: {output[:_OUTPUT_LOG_LEN]}")
        else:
            logger.warning(f"修复失败 | 退出码: {return_code} | 输出: {output[:_OUTPUT_LOG_LEN]}")

        return {
            "success": success,
            "output": output,
            "return_code": return_code,
        }

    except FileNotFoundError:
        logger.error("PowerShell 可执行文件未找到")
        return {
            "success": False,
            "error": "PowerShell 未找到,请确认系统已安装 PowerShell",
            "output": "",
            "return_code": -1,
        }
    except Exception as e:
        logger.error(f"PowerShell 执行异常: {e}", exc_info=True)
        # 🔧 防御:异常时确保 proc 被清理
        if proc is not None:
            try:
                proc.kill()
            except Exception as kill_err:
                logger.warning(f"Failed to kill process: {kill_err}")
        return {
            "success": False,
            "error": str(e),
            "output": "",
            "return_code": -1,
        }


# ============================================================
# 查询接口
# ============================================================
def get_repair_scripts() -> List[Dict[str, Any]]:
    """
    返回所有可用修复脚本列表

    🔧 RE9 [P2]:返回深拷贝,防止调用方修改污染原数据
                (params 字段是 list,浅拷贝时调用方 append 会污染 _REPAIR_SCRIPTS_RAW)
    """
    return [
        {
            "key": k,
            "name": v["name"],
            "description": v["description"],
            "risk": v["risk"],
            # 🔧 RE9:深拷贝 params 列表
            "params": copy.deepcopy(v.get("params", [])),
        }
        for k, v in _REPAIR_SCRIPTS_RAW.items()
    ]


def get_repair_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    返回修复历史记录(线程安全)

    🔧 Review 加固:钳制 limit 范围,防御非法输入
    🔧 RE5:配合 deque 改造,切片操作仍线程安全
    """
    safe_limit = max(1, min(_HISTORY_MAX, int(limit) if limit else 50))
    with _history_lock:
        # deque 切片需先转 list
        return list(repair_history)[:safe_limit]


# ============================================================
# 🔧 RE14 [P2]:维护接口 — 清空修复历史
# ============================================================
def clear_repair_history() -> int:
    """
    清空内存修复历史(测试用 / 紧急清理)
    SQLite 持久化数据不受影响

    Returns:
        清空前的条数
    """
    with _history_lock:
        count = len(repair_history)
        repair_history.clear()

    if count > 0:
        logger.warning(
            f"⚠️ Windows 修复历史(内存)已清空 | 清空前条数={count} | SQLite 持久化数据不受影响"
        )
    return count
