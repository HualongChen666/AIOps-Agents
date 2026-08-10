# -*- coding: utf-8 -*-
import asyncio
import logging
import platform
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


async def _run_command(host: str, command: str) -> Dict[str, Any]:
    """Run a command on a macOS host. Remote execution is not supported."""
    logger.debug(f"Running command on macOS host {host}: {command}")
    if host not in ("localhost", "127.0.0.1", "::1"):
        return {
            "stdout": "",
            "stderr": f"Remote command execution not supported for {host}",
        }
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
        }
    except Exception as e:
        logger.error(f"Failed to run command on macOS host {host}: {e}")
        return {"stdout": "", "stderr": str(e)}


async def collect_macos_metrics(hosts: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """Collect basic metrics (cpu, memory, disk) from macOS hosts.
    If `hosts` is None, collect from all hosts defined in config.
    Returns a dict keyed by host name.
    """
    from config import MAC_HOSTS  # type: ignore

    target_hosts = hosts if hosts is not None else [h["host"] for h in MAC_HOSTS]
    results: Dict[str, Dict[str, Any]] = {}
    for host in target_hosts:
        try:
            if host not in ("localhost", "127.0.0.1", "::1"):
                raise RuntimeError(
                    f"macOS metrics collection is only supported on localhost (got {host})"
                )
            if platform.system() != "Darwin":
                raise RuntimeError(
                    f"macOS metrics collection is only supported on Darwin (got {platform.system()})"
                )
            if psutil is None:
                raise RuntimeError("psutil is not installed; cannot collect macOS metrics")

            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            results[host] = {
                "cpu": cpu,
                "mem": mem,
                "disk": disk,
                "status": "ok",
            }
        except Exception as e:
            logger.error(f"Failed to collect metrics from macOS host {host}: {e}")
            results[host] = {"error": str(e)}
    return results
