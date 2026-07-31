# -*- coding: utf-8 -*-
# core/log_collector.py
# 日志采集引擎(Windows 事件日志 + Linux 远程日志)
#
# 🔧 严格 Review 修复(R2):
#   - R2-1 [P1]:_sanitize_keyword 增强单引号防御
#   - R2-2 [P1]:Linux 日志采集复用 linux_collector 的 host Semaphore
#   - R2-3 [P2]:_run_ps_json 超时时杀死子进程,避免僵尸
#   - R2-4 [P2]:newest 参数二次钳制
#   - R2-5 [P2]:尝试从 Linux 日志行解析时间戳
#   - R2-6 [P2]:类型注解收紧
#   - R2-7 [P2]:grep 命令链增加 head 防爆

import asyncio
import json
import logging
import re
import shutil
from typing import Any, Optional

from core.security import subprocess_runner

logger = logging.getLogger(__name__)

# ============================================================
# 常量定义
# ============================================================
# 🔧 R2-4:newest 参数硬上限(防止恶意大值导致 SSH 超时)
_NEWEST_HARD_MAX = 1000

# 🔧 R2-5:常见 syslog 时间戳前缀正则
# 例:"Jan 15 10:30:45" 或 "2025-01-15T10:30:45"
_SYSLOG_TS_PATTERN = re.compile(
    r"^("
    r"[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"  # syslog 传统格式
    r"|"
    r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}"  # ISO 8601
    r")"
)


# ============================================================
# PowerShell 命令前置头
# ============================================================
_PS_HEADER = (
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "$ErrorActionPreference = 'SilentlyContinue'; "
)


def _sanitize_keyword(keyword: str) -> str:
    """
    过滤危险字符,防止命令注入(PowerShell + Shell 通用)

    🔧 R2-1 [P1]:增强单引号防御
        - 修复前:仅过滤 ['"|`;&<>{}$()\\] 等字符,但单引号已在过滤集中
        - 加固:额外检查长度归零边界,以及强制 ASCII 可打印字符
                防御 Unicode 同形字符攻击(如 U+2018 左单引号)
    """
    if not isinstance(keyword, str):
        logger.warning(f"_sanitize_keyword: keyword 非字符串 | type={type(keyword).__name__}")
        return ""

    # 第一道:过滤危险 ASCII 字符
    sanitized = re.sub(r"['\"|`;&<>{}$()\\\n\r\t]", "", keyword)

    # 🔧 R2-1:第二道:仅保留 ASCII 可打印字符 + 中文常用字符
    # 防御 Unicode 同形字符攻击
    sanitized = re.sub(
        r"[^\x20-\x7E\u4e00-\u9fff]",
        "",
        sanitized,
    )

    # 长度截断
    sanitized = sanitized[:200].strip()

    if sanitized != keyword:
        logger.warning(
            f"keyword 包含危险/非法字符已过滤 | 原始长度={len(keyword)} | 过滤后={sanitized!r}"
        )
    return sanitized


def _clamp_newest(newest: Any, default: int = 20) -> int:
    """
    🔧 R2-4 [P2]:newest 参数二次钳制
    防御恶意大值(如 newest=999999 导致 SSH 长时间执行)
    """
    try:
        val = int(newest)
        return max(1, min(_NEWEST_HARD_MAX, val))
    except (TypeError, ValueError):
        logger.debug(f"_clamp_newest: 非法值 {newest!r},使用默认 {default}")
        return default


# ============================================================
# Windows 事件日志采集
# ============================================================
async def get_event_logs(
    log_name: str = "System",
    level: str = "Error",
    newest: int = 20,
) -> list[dict[str, Any]]:
    """通过 PowerShell 采集 Windows 事件日志"""
    # 🔧 R2-4:钳制 newest
    safe_newest = _clamp_newest(newest, default=20)

    # 🔧 防御:log_name 和 level 严格白名单(防止 PowerShell 命令注入)
    safe_log_name = re.sub(r"[^a-zA-Z]", "", log_name)[:32] or "System"
    safe_level = re.sub(r"[^a-zA-Z]", "", level)[:32] or "Error"

    ps_command = (
        _PS_HEADER + f"Get-EventLog -LogName {safe_log_name} "
        f"-EntryType {safe_level} -Newest {safe_newest} | "
        "Select-Object "
        "@{Name='TimeGenerated';"
        "Expression={$_.TimeGenerated.ToString('yyyy-MM-dd HH:mm:ss')}},"
        "EventID, Source, Message | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = await asyncio.to_thread(_run_ps_json, ps_command)
        logger.info(
            "Windows 事件日志采集成功 | "
            f"log={safe_log_name} level={safe_level} newest={safe_newest} "
            f"返回={len(result)}条"
        )
        return result
    except Exception as e:
        logger.error(f"Windows 事件日志采集失败: {e}", exc_info=True)
        return []


async def get_system_errors(newest: int = 10) -> list[dict[str, Any]]:
    """采集 Windows 系统错误事件"""
    return await get_event_logs("System", "Error", newest)


async def get_application_errors(newest: int = 10) -> list[dict[str, Any]]:
    """采集 Windows 应用程序错误事件"""
    return await get_event_logs("Application", "Error", newest)


async def search_logs(
    keyword: str,
    newest: int = 50,
) -> list[dict[str, Any]]:
    """在 Windows 系统事件日志中按关键词搜索"""
    safe_keyword = _sanitize_keyword(keyword)
    if not safe_keyword:
        logger.warning("keyword 过滤后为空,拒绝执行搜索")
        return []

    # 🔧 R2-4:钳制 newest
    safe_newest = _clamp_newest(newest, default=50)

    ps_command = (
        _PS_HEADER + f"Get-EventLog -LogName System -Newest {safe_newest} | "
        f"Where-Object {{ $_.Message -like '*{safe_keyword}*' }} | "
        "Select-Object "
        "@{Name='TimeGenerated';"
        "Expression={$_.TimeGenerated.ToString('yyyy-MM-dd HH:mm:ss')}},"
        "EventID, Source, Message | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = await asyncio.to_thread(_run_ps_json, ps_command)
        logger.info(f"Windows 日志搜索完成 | keyword='{safe_keyword}' 匹配={len(result)}条")
        return result
    except Exception as e:
        logger.error(f"Windows 日志搜索失败: {e}", exc_info=True)
        return []


def _execute_powershell_with_timeout(
    command: str,
) -> tuple[Optional[subprocess_runner.Popen], Optional[str], Optional[str]]:
    """执行PowerShell命令并处理超时

    Returns:
        (进程对象, stdout, stderr) - 失败时进程对象为None
    """
    proc = None
    try:
        powershell_path = shutil.which("powershell") or "powershell"
        proc = subprocess_runner.Popen(
            [powershell_path, "-NonInteractive", "-NoProfile", "-Command", command],
            shell=False,  # nosec B603
            stdout=subprocess_runner.PIPE,
            stderr=subprocess_runner.PIPE,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
        )

        try:
            stdout, stderr = proc.communicate(timeout=30)
            return proc, stdout, stderr
        except subprocess_runner.TimeoutExpired:
            # 超时强制 kill,避免僵尸
            logger.error("PowerShell 执行超时(>30s),强制终止子进程")
            try:
                proc.kill()
                proc.communicate(timeout=5)  # 等待清理
            except Exception as kill_err:
                logger.warning(f"PowerShell 子进程 kill 失败: {kill_err}")
            return None, None, None

    except FileNotFoundError:
        logger.error("PowerShell 未找到,请确认系统环境")
        return None, None, None
    except Exception as e:
        logger.error(f"PowerShell 启动失败: {e}", exc_info=True)
        if proc is not None:
            try:
                proc.kill()
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logger.debug("Failed to kill PowerShell process", exc_info=True)
        return None, None, None


def _parse_powershell_json_output(stdout: str) -> list[dict[str, Any]]:
    """解析PowerShell JSON输出

    Returns:
        解析后的日志条目列表
    """
    try:
        log_entries = json.loads(stdout)
        if isinstance(log_entries, dict):
            log_entries = [log_entries]
        if not isinstance(log_entries, list):
            logger.warning(f"意外的 JSON 类型: {type(log_entries)}")
            return []
        return log_entries
    except json.JSONDecodeError as e:
        logger.warning(f"日志 JSON 解析失败: {e} | 原始输出: {stdout[:300]}")
        return []


def _sanitize_log_entries(log_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """清理日志条目（时间戳转换、消息截断）

    Returns:
        清理后的日志条目
    """
    for item in log_entries:
        if not isinstance(item, dict):
            continue
        if "TimeGenerated" in item:
            item["TimeGenerated"] = str(item["TimeGenerated"])
        if "Message" in item and isinstance(item["Message"], str):
            if len(item["Message"]) > 2000:
                item["Message"] = item["Message"][:2000] + "...(已截断)"
    return log_entries


def _run_ps_json(command: str) -> list[dict[str, Any]]:
    """
    同步执行 PowerShell 命令并解析 JSON

    🔧 R2-3 [P2]:超时时杀死子进程,避免僵尸进程
    """
    # 1. 执行PowerShell命令
    proc, stdout, stderr = _execute_powershell_with_timeout(command)
    if proc is None:
        return []

    # 2. 检查输出
    stdout = (stdout or "").strip()
    if not stdout:
        if stderr and stderr.strip():
            logger.debug(f"PowerShell stderr: {stderr.strip()[:200]}")
        return []

    # 3. 解析JSON
    log_entries = _parse_powershell_json_output(stdout)
    if not log_entries:
        return []

    # 4. 清理日志条目
    return _sanitize_log_entries(log_entries)


# ============================================================
# 🔧 R2-5 [P2]:从 Linux 日志行尝试提取时间戳
# ============================================================
def _extract_timestamp_from_line(line: str) -> str:
    """
    从 syslog 行中提取时间戳(尽力而为)
    返回提取到的时间字符串,失败返回空字符串
    """
    if not line or not isinstance(line, str):
        return ""
    match = _SYSLOG_TS_PATTERN.match(line)
    return match.group(1) if match else ""


# ============================================================
# Linux 远程日志采集(SSH)
# ============================================================
async def get_linux_logs(
    host_config: dict[str, Any],
    source: str = "syslog",
    newest: int = 20,
) -> list[dict[str, Any]]:
    """
    通过 SSH 采集 Linux 系统日志

    🔧 R2-2 [P1]:复用 linux_collector 的主机维度 Semaphore
    🔧 R2-4 [P2]:newest 钳制
    🔧 R2-5 [P2]:尝试从日志行解析时间戳
    """
    if not isinstance(host_config, dict):
        logger.error("get_linux_logs: host_config 非 dict")
        return []

    host_name = host_config.get("name") or host_config.get("host", "unknown")

    # 🔧 R2-4:钳制 newest
    safe_newest = _clamp_newest(newest, default=20)

    # 各日志源对应命令(source 内部白名单,无需转义)
    source_cmds: dict[str, str] = {
        "syslog": (
            f"tail -n {safe_newest} /var/log/syslog 2>/dev/null "
            f"|| tail -n {safe_newest} /var/log/messages 2>/dev/null "
            "|| echo 'NO_SYSLOG'"
        ),
        "kern": (
            f"dmesg --level=err,crit,alert 2>/dev/null | tail -n {safe_newest} "
            f"|| dmesg 2>/dev/null | tail -n {safe_newest}"
        ),
        "auth": (
            f"tail -n {safe_newest} /var/log/auth.log 2>/dev/null "
            f"|| tail -n {safe_newest} /var/log/secure 2>/dev/null "
            "|| echo 'NO_AUTH_LOG'"
        ),
        "dmesg": f"dmesg 2>/dev/null | tail -n {safe_newest}",
        "journal": (
            f"journalctl -p err -n {safe_newest} --no-pager 2>/dev/null || echo 'NO_JOURNALD'"
        ),
    }
    cmd = source_cmds.get(source, source_cmds["syslog"])

    try:
        # 🔧 R2-2:从 linux_collector 获取主机维度 Semaphore
        from core.linux_collector import _get_host_semaphore, _ssh_execute

        semaphore = _get_host_semaphore(host_name)
        raw = await _ssh_execute(host_config, cmd, semaphore)
    except ImportError:
        # 兼容旧版 linux_collector(无 _get_host_semaphore)
        try:
            from core.linux_collector import _ssh_execute

            raw = await _ssh_execute(host_config, cmd)
        except Exception as e:
            logger.error(f"Linux 日志采集 SSH 失败 | host={host_name} | {e}")
            return []
    except Exception as e:
        logger.error(f"Linux 日志采集 SSH 失败 | host={host_name} | {e}")
        return []

    if (
        not raw
        or raw
        in (
            "TIMEOUT",
            "SSH_NOT_FOUND",
            "NO_SYSLOG",
            "NO_AUTH_LOG",
            "NO_JOURNALD",
        )
        or raw.startswith("ERROR:")
    ):
        logger.debug(
            f"Linux 日志无内容 | host={host_name} | "
            f"source={source} | raw={raw[:50] if raw else 'empty'}"
        )
        return []

    # 解析原始文本为结构化记录
    results: list[dict[str, Any]] = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 截断超长行
        if len(line) > 2000:
            line = line[:2000] + "...(已截断)"

        # 🔧 R2-5:尝试从行首提取时间戳
        timestamp = _extract_timestamp_from_line(line)

        results.append(
            {
                "TimeGenerated": timestamp,
                "Source": source,
                "Message": line,
                "Platform": "linux",
                "Host": host_name,
            }
        )

    logger.info(f"Linux 日志采集成功 | host={host_name} | source={source} | 返回={len(results)}条")
    return results


# ============================================================
# Linux 内核错误日志快捷接口
# ============================================================
async def get_linux_errors(
    host_config: dict[str, Any],
    newest: int = 10,
) -> list[dict[str, Any]]:
    """采集 Linux 内核错误日志(dmesg err 级别)"""
    return await get_linux_logs(host_config, source="kern", newest=newest)


# ============================================================
# Linux 日志关键词搜索
# ============================================================
async def search_linux_logs(
    host_config: dict[str, Any],
    keyword: str,
    newest: int = 100,
) -> list[dict[str, Any]]:
    """
    在 Linux 系统日志中按关键词搜索

    🔧 R2-1:keyword 增强过滤
    🔧 R2-2:复用主机 Semaphore
    🔧 R2-7:grep 命令链增加 head 防止内存溢出
    """
    if not isinstance(host_config, dict):
        logger.error("search_linux_logs: host_config 非 dict")
        return []

    host_name = host_config.get("name") or host_config.get("host", "unknown")

    safe_keyword = _sanitize_keyword(keyword)
    if not safe_keyword:
        logger.warning("Linux 日志搜索:keyword 过滤后为空,拒绝执行")
        return []

    # 🔧 R2-4:钳制 newest
    safe_newest = _clamp_newest(newest, default=100)

    # 🔧 R2-7:grep 搜索时增加 head -n 防爆
    # 使用 || 短路:某个文件不存在时降级到下一个
    cmd = (
        f"( grep -i '{safe_keyword}' /var/log/syslog 2>/dev/null "
        f"|| grep -i '{safe_keyword}' /var/log/messages 2>/dev/null "
        f"|| journalctl --no-pager 2>/dev/null | grep -i '{safe_keyword}' "
        f") | head -n {safe_newest}"
    )

    try:
        # 🔧 R2-2:复用 linux_collector 的主机 Semaphore
        from core.linux_collector import _get_host_semaphore, _ssh_execute

        semaphore = _get_host_semaphore(host_name)
        raw = await _ssh_execute(host_config, cmd, semaphore)
    except ImportError:
        try:
            from core.linux_collector import _ssh_execute

            raw = await _ssh_execute(host_config, cmd)
        except Exception as e:
            logger.error(f"Linux 日志搜索 SSH 失败 | host={host_name} | {e}")
            return []
    except Exception as e:
        logger.error(f"Linux 日志搜索 SSH 失败 | host={host_name} | {e}")
        return []

    if not raw or raw in ("TIMEOUT", "SSH_NOT_FOUND", "") or raw.startswith("ERROR:"):
        return []

    results: list[dict[str, Any]] = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) > 2000:
            line = line[:2000] + "...(已截断)"

        # 🔧 R2-5:提取时间戳
        timestamp = _extract_timestamp_from_line(line)

        results.append(
            {
                "TimeGenerated": timestamp,
                "Source": "search",
                "Message": line,
                "Platform": "linux",
                "Host": host_name,
                "Keyword": safe_keyword,
            }
        )

    logger.info(
        f"Linux 日志搜索完成 | host={host_name} | keyword='{safe_keyword}' | 匹配={len(results)}条"
    )
    return results
