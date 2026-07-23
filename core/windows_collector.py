# -*- coding: utf-8 -*-
# core/windows_collector.py
# Windows 远程采集实现 (基于 WinRM)
# 采用 pywinrm 通过 HTTPS 5986 端口执行 PowerShell 脚本
#
# SECURITY NOTE:
# - Password authentication is used for simplicity. In production, consider using
#   Windows Integrated Authentication (Kerberos/NTLM with domain join) or certificate-based auth.
# - SSL certificate validation is enabled by default. Configure WINRM_CERT_VALIDATION
#   environment variable to 'ignore' only for testing with self-signed certificates.

import asyncio
import logging
import os
import time
from typing import Any, Dict, List

from config import WIN_HOSTS

logger = logging.getLogger(__name__)

# SSL certificate validation setting
# Set to 'ignore' only for testing with self-signed certificates
WINRM_CERT_VALIDATION = os.getenv("WINRM_CERT_VALIDATION", "validate")

# 简化实现：仅示例采集 CPU、内存、磁盘 使用 PowerShell 命令


async def _execute_winrm(host_cfg: Dict[str, Any], cmd: str) -> str:
    """执行 WinRM 命令，返回输出字符串"""
    try:
        import winrm  # pywinrm
    except ImportError:
        logger.error("WinRM 库未安装,请在 requirements.txt 中添加 pywinrm", exc_info=True)
        raise

    endpoint = f"https://{host_cfg.get('ip')}:{host_cfg.get('port', 5986)}/wsman"
    auth = (
        host_cfg.get("user"),
        host_cfg.get("password"),
    )

    # SECURITY: Log warning if using plaintext password
    if auth[1]:
        logger.warning(
            f"Using plaintext password authentication for host {host_cfg.get('ip')}. "
            "Consider using Windows Integrated Authentication in production."
        )

    # SECURITY: Use certificate validation by default
    cert_validation = WINRM_CERT_VALIDATION
    if cert_validation == "ignore":
        logger.warning(
            f"SSL certificate validation DISABLED for host {host_cfg.get('ip')}. "
            "This is only safe for testing environments."
        )

    # SECURITY: Check if auth list is valid to avoid IndexError
    if not auth or len(auth) < 2:
        raise ValueError("Auth credentials must be a list of [username, password]")

    sess = winrm.Protocol(
        endpoint=endpoint,
        transport="ntlm",
        username=auth[0],
        password=auth[1],
        server_cert_validation=cert_validation,
    )
    shell_id = sess.open_shell()
    try:
        command_id = sess.run_command(shell_id, cmd)
        std_out, std_err, status_code = sess.get_command_output(shell_id, command_id)
        output: str = std_out.decode("utf-8", errors="ignore") if std_out else ""
        return output
    finally:
        sess.cleanup_command(shell_id, command_id)
        sess.close_shell(shell_id)


async def collect_windows_host(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单台 Windows 主机的指标并返回 dict"""
    ip = host_cfg.get("ip")
    name = host_cfg.get("name") or ip
    try:
        cpu = await _execute_winrm(
            host_cfg,
            r"Get-Counter '\Processor(_Total)\% Processor Time' | "
            r"Select -ExpandProperty CounterSamples | "
            r"Select -ExpandProperty CookedValue",
        )
        mem = await _execute_winrm(
            host_cfg, "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"
        )
        disk = await _execute_winrm(
            host_cfg,
            "Get-PSDrive -PSProvider 'FileSystem' | Select-Object Name, Free, Used, "
            "@{Name='PercentFree';Expression={($_.Free/($_.Free+$_.Used))*100}}",
        )
        return {
            "host": name,
            "cpu_percent": float(cpu.strip()),
            "memory_free_mb": float(mem.strip()) / 1024,
            "disk": disk,
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.error(f"Windows 主机 {name} 采集失败: {exc}", exc_info=True)
        return {"host": name, "error": str(exc)}


async def collect_all_windows() -> List[Dict[str, Any]]:
    """并发采集所有配置的 Windows 主机"""
    tasks = []
    for host in WIN_HOSTS:
        tasks.append(collect_windows_host(host))
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return results
