# -*- coding: utf-8 -*-
# core/command_guard.py
# 高危指令护栏系统(Linux + Windows 双平台通用)
#
# 🔧 严格 Review 修复(CG):
#   - CG1  [P0]:_split_command_chain 改用 shlex 智能拆分(BUG-FIX-18)
#   - CG2  [P0]:AI 自杀防护增加运行时 PID 自检(配合 N+0.5)
#   - CG3  [P0]:审计 command 字段截断长度从 200 提升到 500
#   - CG4  [P1]:Stop-Process -Id 数字字面量保护
#   - CG5  [P1]:命令前缀匹配加边界检查
#   - CG6  [P1]:rewrite_to_safe 改用 shlex 解析
#   - CG7  [P1]:审计日志改用 deque 自动 LRU
#   - CG8  [P2]:正则模式补充内联 IGNORECASE flag
#   - CG9  [P2]:get_audit_log limit 范围钳制
#   - CG10 [P2]:类型注解收紧
#   - CG11 [P2]:新增 register_self_pid() 公共接口
#   - CG12 [P2]:dry_run_preview svc 长度钳制

import datetime
import logging
import os
import re
import shlex
import tempfile
from collections import deque
from enum import Enum
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 风险等级枚举
# ============================================================
class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"

    def serialize_to_json(self) -> str:
        return self.value


# ============================================================
# 🔧 CG2 + CG11 [P0]:AI 自杀防护 — 运行时 PID 注册表
# ──────────────────────────────────────────────────────
# 修复前:仅按"进程名"拦截 python/uvicorn,无法防御
#         "Stop-Process -Id 12345"(12345 恰是 AIOps PID)
# 修复后:启动时 main.py 调用 register_self_pid() 注册当前 PID
#         analyze_command 检测到命令包含此 PID 时直接 BLOCKED
# ──────────────────────────────────────────────────────
_protected_pids: set[int] = set()
_protected_pids_lock = Lock()


def register_self_pid(pid: Optional[int] = None) -> None:
    """
    🔧 CG11 [P2]:注册受保护的 PID(防止 AI 生成自杀命令)

    建议在 main.py lifespan 启动时调用:
        from core.command_guard import register_self_pid
        register_self_pid()  # 默认注册当前进程 PID

    Args:
        pid: 要保护的 PID,None 时自动获取当前进程
    """
    import os

    target_pid = pid if pid is not None else os.getpid()

    if not isinstance(target_pid, int) or target_pid <= 0:
        logger.warning(f"register_self_pid: 非法 PID {target_pid!r}")
        return

    with _protected_pids_lock:
        _protected_pids.add(target_pid)

    logger.warning(
        "🛡️ CG11: AIOps Agent 自杀防护已激活 | "
        f"受保护 PID={target_pid} | 总数={len(_protected_pids)}"
    )


def unregister_self_pid(pid: int) -> None:
    """从受保护 PID 列表中移除(测试用)"""
    with _protected_pids_lock:
        _protected_pids.discard(pid)


def get_protected_pids() -> set[int]:
    """获取当前受保护的 PID 集合(只读快照)"""
    with _protected_pids_lock:
        return set(_protected_pids)


def _check_self_pid_in_command(command: str) -> Optional[int]:
    """
    🔧 CG2:检测命令中是否包含受保护的 PID
    返回:命中的 PID(用于错误提示)/ None(未命中)
    """
    if not command or not _protected_pids:
        return None

    # 提取命令中所有连续数字串(可能的 PID)
    # 边界:前后必须是非数字字符,防止误命中(如 "10042" 不应匹配 "42")
    numbers = re.findall(r"(?<!\d)(\d{1,7})(?!\d)", command)

    with _protected_pids_lock:
        for num_str in numbers:
            try:
                num = int(num_str)
                if num in _protected_pids:
                    return num
            except ValueError:
                continue

    return None


# ============================================================
# 黑名单:Linux + Windows 双平台高危指令
# 🔧 CG8 [P2]:正则模式补充内联 (?i) flag 作为双重保险
# ============================================================
BLOCKED_PATTERNS: list[dict[str, Any]] = [
    # ══ 🔧 反自杀防线:禁止杀死 AIOps Agent 自身 ══════════
    {
        "name": "禁止杀死 Python 解释器(自杀防护)",
        "pattern": (
            r"(?i)\b(taskkill|Stop-Process|pkill|killall)\s+"
            r".*\b(python|python\.exe|python3|python3\.exe|"
            r"uvicorn|fastapi)\b"
        ),
        "level": RiskLevel.BLOCKED,
        "reason": (
            "禁止终止 Python/uvicorn 进程 — AIOps Agent 自身运行于此进程,执行此命令将导致服务完全瘫痪"
        ),
    },
    {
        "name": "禁止 PowerShell 按 $PID 杀进程(自杀防护)",
        "pattern": r"(?i)Stop-Process\s+.*-Id\s+\$PID\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止使用 $PID 变量(可能指向 AIOps Agent 自身)",
    },
    {
        "name": "禁止终止 AIOps Agent 进程",
        "pattern": (
            r"(?i)\b(taskkill|Stop-Process|kill|pkill)\s+"
            r".*(aiops|ai_ops|aiopsagent|aiops_agent|main\.py)"
        ),
        "level": RiskLevel.BLOCKED,
        "reason": "禁止以名字模式终止 AIOps Agent 进程",
    },
    # ══ Linux 高危 ════════════════════════════════════════
    # ── 文件系统毁灭性操作 ──
    {
        "name": "rm -rf 根目录",
        "pattern": r"(?i)rm\s+(-[rfR]+\s+)*" r"(/\s*$|/\*|/\.\.|/etc|/var|/usr|/boot|/home)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止删除系统根目录或关键目录",
    },
    {
        "name": "rm -rf 变量展开",
        "pattern": r"(?i)rm\s+(-[rfR]+\s+)*\$\{?\w*\}?/",
        "level": RiskLevel.HIGH,
        "reason": "变量为空时可能展开为 rm -rf /,需人工审核",
    },
    {
        "name": "格式化磁盘",
        "pattern": r"(?i)\b(mkfs|fdisk|parted)\s+/dev/",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止格式化磁盘设备",
    },
    {
        "name": "dd 覆写设备",
        "pattern": r"(?i)\bdd\s+.*if=/dev/(zero|random|urandom)" r".*of=/dev/",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止 dd 覆写磁盘设备",
    },
    {
        "name": "chmod 777 根目录",
        "pattern": r"(?i)\bchmod\s+(-R\s+)?777\s+/",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止对根目录递归设置 777 权限",
    },
    # ── 系统控制高危 ──
    {
        "name": "重启/关机",
        "pattern": r"(?i)\b(reboot|shutdown|poweroff|halt)\b|init\s+[06]",
        "level": RiskLevel.HIGH,
        "reason": "系统重启/关机操作需管理员审批",
    },
    {
        "name": "杀死 systemd/init",
        "pattern": r"(?i)\bkill\s+(-\d+\s+)?1\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止杀死 PID 1(systemd/init)",
    },
    {
        "name": "停止 SSH 服务",
        "pattern": r"(?i)\bsystemctl\s+(stop|disable)\s+sshd?\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止停止 SSH 服务(会导致远程连接丢失)",
    },
    # ── 网络高危 ──
    {
        "name": "清空防火墙规则",
        "pattern": r"(?i)\biptables\s+-F\b",
        "level": RiskLevel.HIGH,
        "reason": "清空防火墙规则可能暴露系统",
    },
    {
        "name": "删除默认路由",
        "pattern": r"(?i)\b(route\s+del\s+default|" r"ip\s+route\s+del\s+default)",
        "level": RiskLevel.HIGH,
        "reason": "删除默认路由会导致网络不可达",
    },
    {
        "name": "关闭网卡",
        "pattern": r"(?i)\b(ifconfig\s+\w+\s+down|" r"ip\s+link\s+set\s+\w+\s+down)\b",
        "level": RiskLevel.HIGH,
        "reason": "关闭网卡会导致网络中断",
    },
    # ── 数据库高危 ──
    {
        "name": "DROP DATABASE/TABLE",
        "pattern": r"(?i)\bDROP\s+(DATABASE|TABLE|INDEX)\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止直接删除数据库/表",
    },
    {
        "name": "TRUNCATE TABLE",
        "pattern": r"(?i)\bTRUNCATE\s+TABLE\b",
        "level": RiskLevel.HIGH,
        "reason": "清空表数据需管理员审批",
    },
    {
        "name": "DELETE/UPDATE 无 WHERE",
        "pattern": r"(?i)\b(DELETE\s+FROM|UPDATE)\s+\w+\s*;",
        "level": RiskLevel.HIGH,
        "reason": "DELETE/UPDATE 不带 WHERE 将影响全表",
    },
    # ── 权限高危 ──
    {
        "name": "修改 root 密码",
        "pattern": r"(?i)\bpasswd\s+root\b",
        "level": RiskLevel.HIGH,
        "reason": "修改 root 密码需管理员审批",
    },
    {
        "name": "覆写 SSH 密钥",
        "pattern": r"(?i)>\s*~?/?\.ssh/authorized_keys",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止覆写 SSH 授权密钥",
    },
    # ── 内核高危 ──
    {
        "name": "覆写磁盘设备",
        "pattern": r"(?i)>\s*/dev/sd[a-z]",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止直接写入磁盘设备",
    },
    {
        "name": "卸载关键内核模块",
        "pattern": r"(?i)\bmodprobe\s+-r\s+(ext4|xfs|nfs|iptable)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止卸载关键文件系统/网络内核模块",
    },
    # ── 编码绕过 ──
    {
        "name": "base64 编码执行",
        "pattern": r"(?i)\b(base64\s+-d|echo\s+\S+\s*\|\s*base64)" r".*\|\s*(bash|sh)\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 base64 编码绕过安全检查执行命令",
    },
    {
        "name": "Shell eval/exec 动态执行",
        "pattern": r"^(eval|exec)\s+[^(]",
        "level": RiskLevel.HIGH,
        "reason": "Shell eval/exec 动态执行命令需审核",
    },
    # ── 解释器参数代码执行绕过 ──
    {
        "name": "Shell 解释器 -c 参数执行",
        "pattern": r"(?i)\b(bash|sh|zsh|dash|ksh|csh|tcsh)\b.*\s+-c\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 shell 解释器 -c 参数执行任意命令",
    },
    {
        "name": "Python -c 参数执行",
        "pattern": r"(?i)\bpython[23]?(?:\.\d+)?\b.*\s+-c\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 python -c 执行任意 Python 代码",
    },
    {
        "name": "Node/Ruby/Perl -e 参数执行",
        "pattern": r"(?i)\b(node|nodejs|ruby|perl)\b.*\s+-e\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过脚本解释器 -e 参数执行任意代码",
    },
    {
        "name": "Windows cmd /c 执行",
        "pattern": r"(?i)\bcmd(?:\.exe)?\s+(/c|/k)\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 cmd /c 执行任意命令",
    },
    {
        "name": "PowerShell -Command 执行",
        "pattern": r"(?i)\b(powershell|pwsh)(?:\.exe)?\b.*\s+-[Cc](?:ommand)?\b",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 PowerShell -Command 执行任意代码",
    },
    # ══ Windows 高危 ════════════════════════════════════
    {
        "name": "Windows 删除系统盘根目录",
        "pattern": r"(?i)\bdel\s+.*/[fFsSpP]" r".*\s+[A-Za-z]:\\(\*|Windows|System32)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止删除 Windows 系统目录",
    },
    {
        "name": "Windows 格式化磁盘",
        "pattern": r"(?i)\bformat\s+[A-Za-z]:\s*(/[qQfF]|\s|$)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止格式化 Windows 磁盘分区",
    },
    {
        "name": "Windows Remove-Item 系统目录",
        "pattern": r"(?i)Remove-Item\s+.*" r"(C:\\Windows|C:\\System|%SystemRoot%|%WinDir%)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 PowerShell 删除系统目录",
    },
    {
        "name": "Windows 删除注册表关键键",
        "pattern": r"(?i)\breg\s+delete\s+" r"HKLM\\(SYSTEM|SOFTWARE\\Microsoft\\Windows NT)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止删除 Windows 注册表关键项",
    },
    {
        "name": "PowerShell 删除注册表",
        "pattern": r"(?i)Remove-Item\s+.*" r"HKLM:\\(SYSTEM|SOFTWARE\\Microsoft\\Windows NT)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 PowerShell 删除系统注册表项",
    },
    {
        "name": "Windows 关机/重启",
        "pattern": r"(?i)\bshutdown\s+(/[srhftp]|\s|$)",
        "level": RiskLevel.HIGH,
        "reason": "Windows 关机/重启操作需管理员审批",
    },
    {
        "name": "Windows 强制终止系统进程",
        "pattern": r"(?i)\btaskkill\s+.*/[fF].*" r"(lsass|csrss|winlogon|smss|wininit)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止强制终止 Windows 系统关键进程",
    },
    {
        "name": "PowerShell 停止系统进程",
        "pattern": r"(?i)Stop-Process\s+.*" r"(lsass|csrss|winlogon|smss|wininit)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 PowerShell 终止 Windows 系统关键进程",
    },
    {
        "name": "Windows 停止关键服务",
        "pattern": (
            r"(?i)\b(net\s+stop|sc\s+stop|Stop-Service)\s+"
            r"(wuauserv|windefend|mpssvc|eventlog|"
            r"lanmanserver|rpcss|cryptsvc)\b"
        ),
        "level": RiskLevel.HIGH,
        "reason": "停止 Windows 关键服务需管理员审批",
    },
    {
        "name": "Windows 删除系统服务",
        "pattern": r"(?i)\bsc\s+delete\s+\w+",
        "level": RiskLevel.HIGH,
        "reason": "删除 Windows 服务需管理员审批",
    },
    {
        "name": "Windows 清空防火墙规则",
        "pattern": (
            r"(?i)\b(netsh\s+advfirewall\s+reset"
            r"|netsh\s+firewall\s+reset"
            r"|Remove-NetFirewallRule\s+-All)"
        ),
        "level": RiskLevel.HIGH,
        "reason": "清空 Windows 防火墙规则可能暴露系统",
    },
    {
        "name": "Windows 禁用网卡",
        "pattern": (
            r"(?i)\b(netsh\s+interface\s+set\s+interface"
            r"\s+\S+\s+disable"
            r"|Disable-NetAdapter)"
        ),
        "level": RiskLevel.HIGH,
        "reason": "禁用 Windows 网卡会导致网络中断",
    },
    {
        "name": "Windows 修改 Administrator 密码",
        "pattern": r"(?i)\bnet\s+user\s+administrator\s+\S+",
        "level": RiskLevel.HIGH,
        "reason": "修改 Administrator 密码需管理员审批",
    },
    {
        "name": "Windows 添加/删除管理员账户",
        "pattern": (
            r"(?i)\bnet\s+(user\s+\S+\s+/add"
            r"|localgroup\s+administrators\s+\S+\s+/add"
            r"|user\s+\S+\s+/delete)"
        ),
        "level": RiskLevel.HIGH,
        "reason": "添加/删除管理员账户需管理员审批",
    },
    {
        "name": "PowerShell Base64 编码执行",
        "pattern": r"(?i)\bpowershell\s+.*" r"(-[eE][nN][cC]|-[eE]ncodedCommand)",
        "level": RiskLevel.BLOCKED,
        "reason": "禁止通过 Base64 编码绕过 PowerShell 安全检查",
    },
    {
        "name": "PowerShell 下载执行",
        "pattern": (
            r"(?i)(IEX|Invoke-Expression)\s*\("
            r".*?(Net\.WebClient|Invoke-WebRequest|iwr|curl|wget)"
        ),
        "level": RiskLevel.BLOCKED,
        "reason": "禁止 PowerShell 下载并执行远程代码",
    },
    {
        "name": "Windows 绕过执行策略",
        "pattern": r"(?i)\bpowershell\s+.*" r"-[Ee]xecution[Pp]olicy\s+[Bb]ypass",
        "level": RiskLevel.HIGH,
        "reason": "绕过 PowerShell 执行策略需审批",
    },
    # ══ K8s / 云原生高危 ═══════════════════════════════════
    {
        "name": "K8s 删除工作负载资源",
        "pattern": (
            r"(?i)\bkubectl\s+delete\s+" r"(pod|statefulset|pvc|deployment|service|namespace)\b"
        ),
        "level": RiskLevel.HIGH,
        "reason": "删除 K8s 工作负载资源需人工审批，有状态/PVC 资源另有前置拦截",
    },
    # ══ 远程代码执行 / 数据外带 ═════════════════════════════
    {
        "name": "网络下载并执行",
        "pattern": (
            r"(?i)\b(curl|wget|Invoke-WebRequest|iwr)\b[^\n]*"
            r"(?:\||;|&&|>)\s*"
            r"(?:bash|sh|powershell|pwsh|cmd\.exe|Invoke-Expression|iex)\b"
        ),
        "level": RiskLevel.BLOCKED,
        "reason": "禁止网络下载并立即执行命令（远程代码执行/数据外带）",
    },
    {
        "name": "命令替换与反引号",
        "pattern": r"(?i)\$\(.*\)|`.*`",
        "level": RiskLevel.HIGH,
        "reason": "命令替换与反引号可能隐藏危险操作或数据外带，需人工审批",
    },
]


# ============================================================
# 白名单:安全只读命令(Linux + Windows)
# ============================================================
SAFE_PREFIXES: list[str] = [
    # Linux 安全命令
    "ls ",
    "ls\t",
    "cat ",
    "head ",
    "tail ",
    "grep ",
    "find ",
    "wc ",
    "df ",
    "df\t",
    "du ",
    "free ",
    "free\t",
    "top -",
    "ps ",
    "ps\t",
    "who",
    "w\t",
    "w ",
    "uptime",
    "hostname",
    "uname ",
    "uname\t",
    "date",
    "id",
    "ip addr",
    "ip route",
    "ip link show",
    "ss ",
    "ss\t",
    "netstat ",
    "systemctl status ",
    "systemctl is-active ",
    "systemctl list-",
    "journalctl ",
    "dmesg",
    "last ",
    "last\t",
    "history",
    "mount",
    "lsblk",
    "lscpu",
    "lsmem",
    "cat /proc/",
    "cat /etc/os-release",
    "timedatectl",
    "chronyc ",
    # Windows / PowerShell 安全命令
    "get-process",
    "get-service",
    "get-eventlog",
    "get-disk",
    "get-volume",
    "get-netadapter",
    "get-netipaddress",
    "get-netroute",
    "get-childitem",
    "get-item ",
    "get-content ",
    "get-date",
    "get-host",
    "get-computerinfo",
    "get-wmiobject",
    "get-ciminstance",
    "systeminfo",
    "ipconfig",
    "netstat ",
    "tasklist",
    "sc query",
    "dir ",
    "dir\t",
    "type ",
    "whoami",
    "hostname",
    "ping ",
    "tracert ",
    "nslookup ",
]

SAFE_EXACT: set[str] = {
    # Linux
    "ls",
    "df",
    "free",
    "top",
    "ps",
    "who",
    "w",
    "uptime",
    "hostname",
    "date",
    "id",
    "mount",
    "lsblk",
    "lscpu",
    "lsmem",
    "dmesg",
    "history",
    "uname",
    # Windows
    "systeminfo",
    "ipconfig",
    "whoami",
    "tasklist",
    "hostname",
    "date /t",
    "time /t",
}


# ============================================================
# 🔧 CG7 [P1]:审计日志改用 deque 自动 LRU
# ============================================================
_AUDIT_MAX = 5000
_audit_log: deque = deque(maxlen=_AUDIT_MAX)
_audit_lock = Lock()


# ============================================================
# 🔧 CG1 [P0]:命令链智能拆分(BUG-FIX-18)
# ──────────────────────────────────────────────────────
# 修复前:re.split 无法识别引号内的分隔符
#         "echo 'a;b' && rm -rf /" 被错误拆分为 4 段
# 修复后:用 shlex.split 先 token 化,识别引号边界
#         拆分失败时降级到 re.split(保持向后兼容)
# ──────────────────────────────────────────────────────
def _split_command_chain(command: str) -> list[str]:
    """
    将命令链拆分为独立命令段,智能识别引号边界
    🔧 CG1:用 shlex 分词,防御引号绕过
    """
    if not command or not command.strip():
        return []

    # 优先策略:shlex 智能拆分
    try:
        # posix=True 处理引号转义
        # punctuation_chars 让 ; && || | 成为独立 token
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True

        tokens: list[str] = []
        try:
            tokens = list(lexer)
        except ValueError as e:
            # shlex 解析失败(如引号不闭合)→ 降级到 re.split
            logger.debug(f"CG1: shlex 解析失败,降级 re.split | {e}")
            return _split_command_chain_fallback(command)

        # 按分隔符 token 拆分
        result: list[str] = []
        current: list[str] = []
        SEPARATORS = {";", "&&", "||", "|", "&"}

        for tok in tokens:
            if tok in SEPARATORS:
                if current:
                    result.append(" ".join(current).strip())
                    current = []
            else:
                current.append(tok)

        if current:
            result.append(" ".join(current).strip())

        # 过滤空段
        return [seg for seg in result if seg]

    except Exception as e:
        logger.debug(f"CG1: shlex 异常,降级 re.split | {e}")
        return _split_command_chain_fallback(command)


def _split_command_chain_fallback(command: str) -> list[str]:
    """降级方案:原 re.split 实现(向后兼容)"""
    segments = re.split(r"\s*(?:;|&&|\|\|)\s*", command)
    result: list[str] = []
    for seg in segments:
        for p in seg.split("|"):
            stripped = p.strip()
            if stripped:
                result.append(stripped)
    return result


def _check_empty_command(command: str) -> Optional[dict[str, Any]]:
    """检查空命令

    Returns:
        空命令响应或None
    """
    if not command or not command.strip():
        return {
            "command": "",
            "risk_level": RiskLevel.SAFE,
            "risk_name": "空命令",
            "reason": "空命令无需处理",
            "action": "skip",
        }
    return None


def _check_self_termination(command: str) -> Optional[dict[str, Any]]:
    """检查自杀命令

    Returns:
        拦截响应或None
    """
    hit_pid = _check_self_pid_in_command(command)
    if hit_pid is not None:
        logger.error(f"🛡️ CG2: 拦截 AI 自杀命令 | PID={hit_pid} | cmd={command[:100]}")
        return {
            "command": command,
            "risk_level": RiskLevel.BLOCKED,
            "risk_name": "AI 自杀防护(运行时 PID 检测)",
            "reason": f"命令包含受保护的 PID {hit_pid}(AIOps Agent 自身),执行将导致服务瘫痪",
            "action": "block",
        }
    return None


def _analyze_command_chain(segments: list[str], original_command: str) -> dict[str, Any]:
    """分析命令链风险

    Returns:
        风险分析结果
    """
    worst_result = None
    worst_level = -1

    level_weight = {
        RiskLevel.SAFE: 0,
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.CRITICAL: 4,
        RiskLevel.BLOCKED: 5,
    }

    for seg in segments:
        result = _analyze_single_command(seg)
        weight = level_weight.get(result["risk_level"], 0)
        if weight > worst_level:
            worst_level = weight
            worst_result = result

    if worst_result and len(segments) > 1:
        worst_result["command"] = original_command
        worst_result["is_chained"] = True
        worst_result["chain_count"] = len(segments)

    return worst_result or {
        "command": original_command,
        "risk_level": RiskLevel.LOW,
        "risk_name": "解析异常",
        "reason": "命令解析异常,按低风险处理",
        "action": "execute",
    }


# ============================================================
# 核心分析函数
# ============================================================
def analyze_command(command: str) -> dict[str, Any]:
    """分析命令风险等级,命令链取最高风险"""
    # 1. 检查空命令
    empty_result = _check_empty_command(command)
    if empty_result:
        return empty_result

    cmd_stripped = command.strip()

    # 2. 检查自杀命令
    suicide_result = _check_self_termination(cmd_stripped)
    if suicide_result:
        return suicide_result

    # 3. 命令链拆分
    segments = _split_command_chain(cmd_stripped)
    if not segments:
        # 拆分后为空,直接按原命令分析
        segments = [cmd_stripped]

    # 4. 分析命令链风险
    return _analyze_command_chain(segments, cmd_stripped)


def _check_whitelist(cmd: str, cmd_lower: str) -> Optional[dict[str, Any]]:
    """检查白名单（精确匹配+前缀匹配）

    Returns:
        安全响应或None
    """
    cmd_stripped = cmd.strip()

    # 精确匹配白名单
    if cmd_lower in SAFE_EXACT:
        return {
            "command": cmd_stripped,
            "risk_level": RiskLevel.SAFE,
            "risk_name": "安全命令(精确匹配)",
            "reason": "只读命令,安全执行",
            "action": "execute",
        }

    # 前缀匹配(已在 _split_command_chain 拆分前提下,前缀就是首词)
    for prefix in SAFE_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            return {
                "command": cmd_stripped,
                "risk_level": RiskLevel.SAFE,
                "risk_name": "安全命令(前缀匹配)",
                "reason": "只读命令,安全执行",
                "action": "execute",
            }
    return None


def _check_blacklist(cmd: str, cmd_lower: str) -> Optional[dict[str, Any]]:
    """检查黑名单

    Returns:
        风险响应或None
    """
    cmd_stripped = cmd.strip()

    # 黑名单正则匹配
    for rule in BLOCKED_PATTERNS:
        try:
            if re.search(rule["pattern"], cmd_stripped):
                level = rule["level"]
                action_map = {
                    RiskLevel.BLOCKED: "block",
                    RiskLevel.CRITICAL: "block",
                    RiskLevel.HIGH: "approve",
                    RiskLevel.MEDIUM: "confirm",
                    RiskLevel.LOW: "execute",
                }
                result = {
                    "command": cmd_stripped,
                    "risk_level": level,
                    "risk_name": rule["name"],
                    "reason": rule["reason"],
                    "action": action_map.get(level, "block"),
                }
                alt = _get_safe_alternative(cmd_stripped)
                if alt:
                    result["safe_alternative"] = alt
                logger.warning(
                    f"高危指令检测 | level={level.value} "
                    f"| rule={rule['name']} | cmd={cmd_stripped[:80]}"
                )
                return result
        except re.error as e:
            logger.error(f"正则匹配异常: {rule['name']} | {e}")
            continue
    return None


def _build_default_risk_response(cmd: str) -> dict[str, Any]:
    """构建默认低风险响应

    Returns:
        默认响应
    """
    cmd_stripped = cmd.strip()
    return {
        "command": cmd_stripped,
        "risk_level": RiskLevel.LOW,
        "risk_name": "未匹配已知规则",
        "reason": "未在黑白名单中,按低风险处理",
        "action": "execute",
    }


def _analyze_single_command(cmd: str) -> dict[str, Any]:
    """
    分析单条命令风险

    🔧 CG5 [P1]:前缀匹配增加严格边界检查
    """
    cmd_stripped = cmd.strip()
    cmd_lower = cmd_stripped.lower()

    # 1. 检查白名单
    whitelist_result = _check_whitelist(cmd_stripped, cmd_lower)
    if whitelist_result:
        return whitelist_result

    # 2. 检查黑名单
    blacklist_result = _check_blacklist(cmd_stripped, cmd_lower)
    if blacklist_result:
        return blacklist_result

    # 3. 默认低风险
    return _build_default_risk_response(cmd_stripped)


def is_command_allowed(command: str) -> bool:
    """快速判断:BLOCKED → False,其他 → True"""
    return bool(analyze_command(command)["risk_level"] != RiskLevel.BLOCKED)


# ============================================================
# 🔧 CG6 [P1]:安全替代方案(改用 shlex 解析路径)
# ============================================================
def _get_safe_alternative(command: str) -> str:
    """
    生成安全替代方案
    🔧 CG6:涉及路径的场景用 shlex.split 解析,防御含空格的路径
    """
    cmd = command.strip().lower()

    if cmd.startswith("rm "):
        # 🔧 CG6:用 shlex 解析,正确处理含空格/引号的路径
        try:
            parts = shlex.split(command, posix=True)
        except ValueError:
            parts = command.split()

        # 提取最后一个非选项参数作为目标
        target = ""
        for p in reversed(parts[1:]):
            if not p.startswith("-"):
                target = p
                break

        if target:
            # shell 引用以处理特殊字符
            target_quoted = shlex.quote(target)
            return (
                "# 安全替代:移动到回收站\n"
                "mkdir -p /tmp/.trash && "
                f"mv {target_quoted} /tmp/.trash/"
                f"$(date +%Y%m%d%H%M%S)_$RANDOM_$(basename {target_quoted})"
            )

    if "shutdown" in cmd or "reboot" in cmd:
        return (
            "# 安全替代:延迟5分钟,给予取消窗口\n"
            "shutdown -r +5 'Scheduled reboot. Cancel: shutdown -c'"
        )
    if "iptables -f" in cmd:
        return "# 安全替代:先备份再清空\niptables-save > /tmp/fw_backup_$(date +%s) && iptables -F"
    if "drop database" in cmd or "drop table" in cmd:
        return "# 安全替代:先备份数据库\nmysqldump --all-databases > /tmp/db_bak_$(date +%s).sql"
    # Windows 替代方案
    if "format " in cmd:
        return "# 请使用磁盘管理工具(diskmgmt.msc)进行磁盘操作"
    if "reg delete" in cmd:
        return "# 安全替代:先导出备份\nreg export HKLM\\SYSTEM C:\\reg_backup.reg"
    return ""


def _parse_rm_command(command: str) -> Optional[list[str]]:
    """解析rm命令

    Returns:
        命令部分或None
    """
    cmd = command.strip()
    if not re.match(r"rm\s+", cmd):
        return None

    # 用 shlex.split 解析(替代 cmd.split())
    try:
        parts = shlex.split(cmd, posix=True)
    except ValueError as e:
        logger.warning(f"CG6: rewrite_to_safe shlex 解析失败: {e}")
        return None

    if not parts or parts[0] != "rm":
        return None

    return parts


def _extract_rm_targets(parts: list[str]) -> list[str]:
    """提取rm命令的目标路径

    Returns:
        目标路径列表
    """
    return [p for p in parts[1:] if not p.startswith("-")]


def _build_mv_to_trash_command(targets: list[str]) -> str:
    """构建移动到回收站的命令

    Returns:
        重构后的命令
    """
    trash = os.path.join(tempfile.gettempdir(), ".aiops_trash").replace(os.sep, "/")
    cmds = [f"mkdir -p {trash}"]
    for t in targets:
        # shell 引用,处理含特殊字符的路径
        t_quoted = shlex.quote(t)
        cmds.append(f"mv {t_quoted} {trash}/$(basename {t_quoted})_$(date +%Y%m%d_%H%M%S)_$RANDOM")

    return " && ".join(cmds)


# ============================================================
# 🔧 CG6 [P1]:指令改写(rm → mv 回收站,改用 shlex)
# ============================================================
def rewrite_to_safe(command: str) -> str:
    """
    将 rm 改写为 mv 到回收站
    🔧 CG6:用 shlex.split 解析,正确处理含空格的路径
    """
    cmd = command.strip()

    # 1. 解析rm命令
    parts = _parse_rm_command(cmd)
    if not parts:
        return cmd

    # 2. 提取目标路径
    targets = _extract_rm_targets(parts)
    if not targets:
        return cmd

    # 3. 构建mv命令
    rewritten = _build_mv_to_trash_command(targets)
    logger.info(f"指令改写 | rm→mv | {cmd[:60]} → {rewritten[:60]}")
    return rewritten


def _build_rm_preview(command: str) -> Optional[str]:
    """构建rm命令的预览

    Returns:
        预览命令或None
    """
    # 用 shlex 解析
    try:
        parts = shlex.split(command, posix=True)
    except ValueError:
        parts = command.split()

    targets = [p for p in parts[1:] if not p.startswith("-")]
    if targets:
        target_str = " ".join(shlex.quote(t) for t in targets)
        return (
            "echo '=== 将要删除的文件/目录 ===' && "
            f"ls -la {target_str} 2>/dev/null && "
            f"echo '共 '$(ls {target_str} 2>/dev/null | wc -l)' 项'"
        )
    return None


def _build_systemctl_preview(command: str) -> Optional[str]:
    """构建systemctl命令的预览

    Returns:
        预览命令或None
    """
    parts = command.split()
    svc = parts[-1] if len(parts) > 1 else "unknown"
    # 严格白名单 + 长度钳制(64 字符上限)
    safe_svc = re.sub(r"[^a-zA-Z0-9._-]", "", svc)[:64]
    if not safe_svc:
        safe_svc = "unknown"
    return f"echo '=== 即将重启服务: {safe_svc} ===' && systemctl status {safe_svc} --no-pager"


def _build_default_preview(command: str) -> str:
    """构建默认预览

    Returns:
        默认预览命令
    """
    safe_cmd = command.replace("'", "'\\''")
    return f"echo '=== Dry-run 预览 ===' && printf '%s\\n' '{safe_cmd}'"


# ============================================================
# 🔧 CG12 [P2]:Dry-run 预览(svc 长度钳制)
# ============================================================
def dry_run_preview(command: str) -> str:
    """生成命令的预览版本(不实际执行)"""
    cmd = command.strip()

    # 1. rm命令预览
    if cmd.startswith("rm "):
        preview = _build_rm_preview(cmd)
        if preview:
            return preview

    # 2. systemctl命令预览
    if "systemctl restart" in cmd:
        systemctl_preview = _build_systemctl_preview(cmd)
        if systemctl_preview:
            return systemctl_preview

    # 3. 默认预览
    return _build_default_preview(cmd)


# ============================================================
# 🔧 CG3 + CG7 [P0/P1]:审计日志(deque + 长度提升)
# ============================================================
def record_audit(
    host: str,
    command: str,
    risk_level: str,
    executor: str = "agent",
    result: str = "success",
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """
    记录命令执行审计日志(Who/When/Where/What/Risk/Result)
    """
    record = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "who": str(executor)[:64],
        "user_id": str(user_id) if user_id else None,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "where": str(host)[:128],
        "what": str(command)[:500],
        "risk_level": str(risk_level)[:16],
        "result": str(result)[:128],
        "trace_id": str(trace_id) if trace_id else None,
    }
    with _audit_lock:
        # 🔧 CG7:deque 自带 maxlen,自动淘汰最旧条目
        _audit_log.append(record)

    if risk_level in ("high", "blocked"):
        logger.warning(
            f"审计 | {executor}@{host} | risk={risk_level} | cmd={command[:80]} | result={result}"
        )
    else:
        logger.debug(f"审计 | {executor}@{host} | risk={risk_level} | cmd={command[:80]}")


def get_audit_log(limit: int = 50) -> list[dict[str, Any]]:
    """
    获取最近的审计日志(线程安全)
    🔧 CG9 [P2]:limit 范围钳制 [1, _AUDIT_MAX]
    """
    safe_limit = max(1, min(_AUDIT_MAX, int(limit) if limit else 50))
    with _audit_lock:
        # deque 切片需先转 list
        snapshot = list(_audit_log)
    # 倒序返回最新在前
    return list(reversed(snapshot[-safe_limit:]))


def clear_audit_log() -> int:
    """
    清空审计日志(测试/紧急维护用)
    返回清空前的条数
    """
    with _audit_lock:
        count = len(_audit_log)
        _audit_log.clear()
    if count > 0:
        logger.warning(f"⚠️ 审计日志已被清空 | 清空前条数={count}")
    return count
