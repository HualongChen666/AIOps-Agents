# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Placeholder implementation for macOS metrics collection.
# In a real environment this would use SSH, launchctl, osquery, or native macOS APIs.


async def _run_command(host: str, command: str) -> Dict[str, Any]:
    """Simulate remote command execution on a macOS host.
    Returns a dict with 'stdout' and 'stderr' for simplicity.
    """
    # This stub simply logs and returns dummy data.
    logger.debug(f"Running command on macOS host {host}: {command}")
    # Simulate network latency.
    await asyncio.sleep(0.1)
    return {"stdout": "", "stderr": ""}


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
            # Dummy metric values; replace with real commands as needed.
            cpu = 0.2  # placeholder
            mem = 0.5
            disk = 0.7
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
