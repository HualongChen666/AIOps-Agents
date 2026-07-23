# -*- coding: utf-8 -*-
# core/docker_collector.py
"""Docker 容器采集模块

负责从 Docker 主机获取容器层面的运行时指标（CPU、内存、网络、状态等），
并统一返回与 Linux/Windows 采集相同结构的字典，供后续统一处理。

实现思路：
- 使用官方 Docker SDK (`docker` 包) 与远程 Docker Daemon 交互。
- 通过 `docker.from_env` 或自定义 `docker.DockerClient` 依据 `host_cfg` 中的
  `base_url`、`tls`、`version` 等字段创建客户端。
- 对每个容器获取 `stats`（流式 JSON）一次性读取 ``stream=False``，
  只取最新一次快照，避免长时间阻塞。
- 将 Docker 原始指标映射为统一的内部字段名，保持与现有 `linux_collector`
  返回结构兼容。
🔧 重构:使用模板方法模式统一后处理流程
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List

import docker
from docker.errors import DockerException

from config import (
    DOCKER_HOST_COOLDOWN_SEC,
    DOCKER_HOST_MAX_FAILURES,
)
from core.base.collector import collect_with_post_processing

_logger = logging.getLogger(__name__)


# -------------------------------------------------------
# 辅助函数 – 创建 Docker 客户端
# -------------------------------------------------------
def _get_client(host_cfg: Dict[str, Any]) -> docker.DockerClient:
    """根据 host_cfg 创建 DockerClient。

    host_cfg 示例::
        {
            "host": "10.0.0.5",
            "port": 2376,
            "tls": false,
            "version": "auto",
        }
    """
    base_url = f"tcp://{host_cfg.get('host')}:{host_cfg.get('port', 2375)}"
    tls_cfg = host_cfg.get("tls", False)
    try:
        client = docker.DockerClient(
            base_url=base_url, tls=tls_cfg, version=host_cfg.get("version", "auto")
        )
        # 触发一次 API 调用确保连接正常
        client.ping()
        return client
    except DockerException as e:
        raise ConnectionError(f"Docker connection failed for {base_url}: {e}")


# -------------------------------------------------------
# 主采集函数（原始数据采集）
# -------------------------------------------------------
def _collect_docker_raw(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单台 Docker 主机的容器指标并返回统一结构（原始数据）。

    返回结构示例（与 linux_collector 对齐）::
        {
            "host": "10.0.0.5",
            "timestamp": "2024-10-01 12:34:56",
            "containers": [
                {
                    "id": "a1b2c3d4",
                    "name": "web_app",
                    "status": "running",
                    "cpu_percent": 2.3,
                    "mem_usage": 128000000,
                    "mem_limit": 2147483648,
                    "net_io": {"rx_bytes": 12345, "tx_bytes": 67890},
                },
                ...
            ],
        }
    """
    host = host_cfg.get("host", "unknown")
    try:
        client = _get_client(host_cfg)
    except Exception as conn_err:
        _logger.error(f"Docker 主机 {host} 连接失败: {conn_err}")
        return {}

    containers_info: List[Dict[str, Any]] = []
    try:
        for ctr in client.containers.list(all=True):
            try:
                stats = ctr.stats(stream=False)
                cpu_delta = (
                    stats["cpu_stats"]["cpu_usage"]["total_usage"]
                    - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                )
                system_cpu_delta = (
                    stats["cpu_stats"]["system_cpu_usage"]
                    - stats["precpu_stats"]["system_cpu_usage"]
                )
                cpu_percent = 0.0
                if system_cpu_delta > 0.0 and cpu_delta > 0.0:
                    cpu_percent = (
                        (cpu_delta / system_cpu_delta)
                        * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                        * 100.0
                    )

                mem_usage = stats["memory_stats"].get("usage", 0)
                mem_limit = stats["memory_stats"].get("limit", 0)
                net = stats.get("networks", {})
                rx = sum(iface.get("rx_bytes", 0) for iface in net.values())
                tx = sum(iface.get("tx_bytes", 0) for iface in net.values())

                containers_info.append(
                    {
                        "id": ctr.id[:12],
                        "name": ctr.name,
                        "status": ctr.status,
                        "cpu_percent": round(cpu_percent, 2),
                        "mem_usage": mem_usage,
                        "mem_limit": mem_limit,
                        "net_io": {"rx_bytes": rx, "tx_bytes": tx},
                    }
                )
            except Exception as inner_err:
                _logger.warning(f"采集容器 {ctr.name} 时出错: {inner_err}")
                continue
    finally:
        client.close()

    return {
        "host": host,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "containers": containers_info,
    }


# -------------------------------------------------------
# 对外统一入口（与其他 collector 保持同名）
# 🔧 重构:使用模板方法包装器
# -------------------------------------------------------
def collect_docker(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """包装函数，保持与 ``core.linux_collector.collect_linux`` 调用方式一致。
    🔧 重构:使用模板方法模式统一后处理流程
    """
    return collect_with_post_processing(
        collect_func=_collect_docker_raw,
        host_cfg=host_cfg,
        platform_name="docker",
        max_failures=DOCKER_HOST_MAX_FAILURES,
        cooldown_sec=DOCKER_HOST_COOLDOWN_SEC,
        metric_type="container",
    )
