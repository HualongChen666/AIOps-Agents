# -*- coding: utf-8 -*-
"""Kubernetes 集群采集模块

实现方式：
- 通过官方 ``kubernetes`` Python SDK 读取集群 **Pod** 基础信息。
- 支持多集群：在 ``config.py`` 中通过 ``K8S_HOSTS`` 配置每个集群的 ``kubeconfig`` 路径或 ``context``。
- 采集结果统一为 ``snapshot``，结构与 ``linux_collector``、``docker_collector`` 保持一致，便于后续统一上报、存储、Loki、OTel。

注意事项：
- 该实现仅采集 **Pod** 级别的基本状态（名称、命名空间、所在节点、运行相位、重启次数）。
- 若需更细粒度（CPU/Memory）请在集群部署 ``metrics-server`` 并在此基础上扩展 ``CustomObjectsApi`` 查询。
🔧 重构:使用模板方法模式统一后处理流程
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List

from kubernetes import client, config  # pip install kubernetes
from kubernetes.client import ApiException

from config import (
    K8S_HOST_COOLDOWN_SEC,
    K8S_HOST_MAX_FAILURES,
    K8S_HOSTS,
)
from core.base.collector import collect_with_post_processing

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内部缓存 & 锁
# ---------------------------------------------------------------------------
_collect_lock = Lock()
_collect_history: deque[Dict[str, Any]] = deque(maxlen=50)


def _load_api(host_cfg: Dict[str, Any]):
    """根据主机配置加载 Kubernetes API 客户端。

    host_cfg 必须包含 ``kubeconfig``（本地文件路径）或 ``context``（已在默认 kubeconfig 中定义的上下文）。
    若加载失败会抛 ``ConnectionError``，上层负责捕获并记录日志。
    """
    try:
        if "kubeconfig" in host_cfg:
            cfg_path = host_cfg["kubeconfig"]
            config.load_kube_config(config_file=cfg_path)
        elif "context" in host_cfg:
            config.load_kube_config(context=host_cfg["context"])
        else:
            # 默认加载本机 ~/.kube/config
            config.load_kube_config()
        return client.CoreV1Api()
    except Exception as e:
        raise ConnectionError(f"K8s API load failed for {host_cfg}: {e}") from e


def _collect_pods(api: client.CoreV1Api) -> List[Dict[str, Any]]:
    """采集 Pod 列表并提取基础信息。返回 ``list``，每项为 ``dict``。"""
    pods_info: List[Dict[str, Any]] = []
    try:
        pod_list = api.list_pod_for_all_namespaces(watch=False)
        for pod in pod_list.items:
            # 统计容器重启次数（所有容器累计）
            restart_cnt = sum(
                cs.restart_count for cs in getattr(pod.status, "container_statuses", []) or []
            )
            pods_info.append(
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "node": pod.spec.node_name,
                    "phase": pod.status.phase,
                    "restart_count": restart_cnt,
                }
            )
    except ApiException as e:
        _logger.error("K8s Pod collection ApiException: %s", e)
    except Exception:
        _logger.exception("Unexpected error during K8s pod collection")
    return pods_info


def _collect_k8s_raw(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单个 K8s 集群的指标并返回 ``snapshot``（原始数据）。"""
    host = host_cfg.get("host", "unknown")
    snapshot: Dict[str, Any] = {
        "host": host,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }
    try:
        api = _load_api(host_cfg)
        pods = _collect_pods(api)
        snapshot["pods"] = pods
    except Exception as e:
        _logger.error("K8s collection failed for host %s: %s", host, e)
        return {}
    return snapshot


def collect_k8s(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单个 K8s 集群的指标并返回 ``snapshot``。
    🔧 重构:使用模板方法模式统一后处理流程
    """
    snapshot = collect_with_post_processing(
        collect_func=_collect_k8s_raw,
        host_cfg=host_cfg,
        platform_name="kubernetes",
        max_failures=K8S_HOST_MAX_FAILURES,
        cooldown_sec=K8S_HOST_COOLDOWN_SEC,
        metric_type="pod",
    )

    # 记录到历史（保留原有逻辑）
    with _collect_lock:
        _collect_history.appendleft(snapshot)

    return snapshot


def collect_all_k8s() -> List[Dict[str, Any]]:
    """遍历 ``K8S_HOSTS`` 并并行（同步）采集，返回所有 ``snapshot`` 列表。"""
    results: List[Dict[str, Any]] = []
    for host_cfg in K8S_HOSTS:
        results.append(collect_k8s(host_cfg))
    return results


def get_k8s_collect_history(limit: int = 20) -> List[Dict[str, Any]]:
    """返回最近 ``limit`` 条采集历史（从最新到最旧）。"""
    with _collect_lock:
        return list(_collect_history)[:limit]
