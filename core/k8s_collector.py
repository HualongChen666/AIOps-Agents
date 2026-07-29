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
import time
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
from core.observability_query import DEFAULT_MAX_LLM_ITEMS, sanitize_error_for_llm

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内部缓存 & 锁
# ---------------------------------------------------------------------------
_collect_lock = Lock()
_collect_history: deque[Dict[str, Any]] = deque(maxlen=50)

# 按主机维护失败次数与冷却截止时间（秒，time.monotonic 时间戳）
_host_status_lock = Lock()
_host_status: Dict[str, Dict[str, Any]] = {}


def _load_api(host_cfg: Dict[str, Any]):
    """根据主机配置加载 Kubernetes API 客户端。

    host_cfg 必须包含 ``kubeconfig``（本地文件路径）或 ``context``（已在默认 kubeconfig 中定义的上下文）。
    若加载失败会抛 ``ConnectionError``，上层负责捕获并记录日志。
    生产环境建议配置 ``read_only=True`` 以只读账号运行采集。
    """
    read_only = host_cfg.get("read_only", True)
    if not read_only:
        _logger.warning(
            "K8s collector for %s is not using read_only credentials; "
            "set read_only=True to enforce least privilege.",
            host_cfg.get("host", "unknown"),
        )

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


def _collect_pods(
    api: client.CoreV1Api, max_pods: int = DEFAULT_MAX_LLM_ITEMS
) -> List[Dict[str, Any]]:
    """采集 Pod 列表并提取基础信息。返回 ``list``，每项为 ``dict``。

    Args:
        api: Kubernetes CoreV1Api 客户端。
        max_pods: 单次采集最大 Pod 数量（分页第一页），避免大集群返回量爆炸。
    """
    pods_info: List[Dict[str, Any]] = []
    try:
        pod_list = api.list_pod_for_all_namespaces(
            watch=False,
            limit=max_pods,
            timeout_seconds=30,
        )
        truncated = len(getattr(pod_list, "items", [])) >= max_pods
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
        if truncated:
            _logger.warning("K8s pod collection truncated at %s pods", max_pods)
            pods_info.append({"_truncated": True, "limit": max_pods})
    except ApiException as e:
        _logger.error("K8s Pod collection ApiException: %s", e)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        _logger.exception("Unexpected error during K8s pod collection")
    return pods_info


def _collect_k8s_raw(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单个 K8s 集群的指标并返回 ``snapshot``（原始数据）。"""
    host = host_cfg.get("host", "unknown")
    snapshot: Dict[str, Any] = {
        "host": host,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "_data_completeness": "partial",
    }
    try:
        api = _load_api(host_cfg)
        pods = _collect_pods(api, max_pods=host_cfg.get("max_pods", DEFAULT_MAX_LLM_ITEMS))
        snapshot["pods"] = pods
        snapshot["_data_completeness"] = "complete"
    except Exception as e:
        _logger.error("K8s collection failed for host %s: %s", host, e)
        snapshot["_data_completeness"] = "failed"
        snapshot["pods"] = []
    return snapshot


def _is_in_cooldown(host: str, max_failures: int, cooldown_sec: int) -> bool:
    """根据失败次数和冷却时间判断主机是否处于冷却期。"""
    if max_failures <= 0 or cooldown_sec <= 0:
        return False
    with _host_status_lock:
        status = _host_status.get(host)
        if not status:
            return False
        if status["failures"] >= max_failures and time.monotonic() < status["cooldown_until"]:
            _logger.warning("K8s host %s is in cooldown until %s", host, status["cooldown_until"])
            return True
    return False


def _record_failure(host: str, cooldown_sec: int, max_failures: int) -> None:
    """记录一次 K8s 采集失败，达到阈值后进入冷却期。"""
    with _host_status_lock:
        status = _host_status.setdefault(host, {"failures": 0, "cooldown_until": 0.0})
        status["failures"] += 1
        if status["failures"] >= max_failures:
            status["cooldown_until"] = time.monotonic() + cooldown_sec
            _logger.warning(
                "K8s host %s reached %s failures; entering %ss cooldown",
                host,
                max_failures,
                cooldown_sec,
            )


def _record_success(host: str) -> None:
    """重置失败计数。"""
    with _host_status_lock:
        status = _host_status.get(host)
        if status:
            status["failures"] = 0
            status["cooldown_until"] = 0.0


def collect_k8s(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单个 K8s 集群的指标并返回 ``snapshot``。
    🔧 重构:使用模板方法模式统一后处理流程
    """
    host = host_cfg.get("host", "unknown")
    if _is_in_cooldown(host, K8S_HOST_MAX_FAILURES, K8S_HOST_COOLDOWN_SEC):
        return {
            "host": host,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "pods": [],
            "_data_completeness": "cooldown",
            "_cooldown": True,
        }

    snapshot = collect_with_post_processing(
        collect_func=_collect_k8s_raw,
        host_cfg=host_cfg,
        platform_name="kubernetes",
        max_failures=K8S_HOST_MAX_FAILURES,
        cooldown_sec=K8S_HOST_COOLDOWN_SEC,
        metric_type="pod",
    )

    if snapshot.get("_cooldown"):
        # cooldown was already handled, don't count it as a failure
        pass
    elif snapshot.get("_data_completeness") in ("failed", "timeout"):
        _record_failure(host, K8S_HOST_COOLDOWN_SEC, K8S_HOST_MAX_FAILURES)
    else:
        _record_success(host)

    # 记录到历史（保留原有逻辑）
    with _collect_lock:
        _collect_history.appendleft(snapshot)

    return snapshot


def collect_all_k8s(max_workers: int = 4, timeout: float = 30.0) -> List[Dict[str, Any]]:
    """遍历 ``K8S_HOSTS`` 并并发（线程池）采集，返回所有 ``snapshot`` 列表。

    Args:
        max_workers: 最大并发采集线程数。
        timeout: 每个集群采集的最大等待时间（秒）。
    """
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as FutureTimeoutError

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(collect_k8s, host_cfg): host_cfg for host_cfg in K8S_HOSTS}
        for future in futures:
            host = futures[future].get("host", "unknown")
            try:
                results.append(future.result(timeout=timeout))
            except FutureTimeoutError:
                _logger.error("K8s collection for host %s timed out after %ss", host, timeout)
                results.append(
                    {
                        "host": host,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "pods": [],
                        "_data_completeness": "timeout",
                        "_timeout": True,
                    }
                )
            except Exception as e:
                _logger.error("K8s collection for host %s failed: %s", host, e)
                results.append(
                    {
                        "host": host,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "pods": [],
                        "_data_completeness": "failed",
                        "_error": sanitize_error_for_llm(e),
                    }
                )
    return results


def get_k8s_collect_history(limit: int = 20) -> List[Dict[str, Any]]:
    """返回最近 ``limit`` 条采集历史（从最新到最旧）。"""
    with _collect_lock:
        return list(_collect_history)[:limit]