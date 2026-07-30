# -*- coding: utf-8 -*-
"""Kubernetes 修复模块（基于 kubectl）

实现思路：
- 只读修复脚本库 ``REPAIR_SCRIPTS``（只读 MappingProxyType），示例脚本包括
  ``restart_deployment``、``delete_pod``、``scale_deployment``。
- 参数安全化：
  - 长度上限 128，过滤危险字符（`&;|` 等），禁止空格、单引号等。
  - 对于 ``deployment``、``pod``、``namespace`` 等进行正则校验，
    确保只包含字母数字、短横线、下划线。
- 命令渲染：在模板中使用 ``{key}`` 替换，最终生成完整的 ``kubectl`` 命令。
- 护栏审查：使用 ``core.command_guard.analyze_command`` 检查是否属于 ``BLOCKED``
  （自杀/高危），若阻断写审计记录并返回 ``blocked=True``。
- 审计写入：调用 ``core.command_guard.record_audit``，异常不影响业务。
- 修复执行：使用 ``subprocess.run(['bash','-c', full_cmd], ...)`` 执行，捕获 stdout、stderr、返回码，
  统一返回结构。支持 ``async``（通过 ``asyncio.to_thread``）以及同步包装供 FastAPI 使用。
- 结果写入 statistics、Loki、PID 防护（与 collector 类似），并记录历史（deque + Lock）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess  # nosec B404
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List

from config import (  # noqa: F401
    K8S_HOST_COOLDOWN_SEC,
    K8S_HOST_MAX_FAILURES,
    K8S_HOSTS,
)
from core.command_guard import RiskLevel, analyze_command, record_audit, register_self_pid
from core.loki_sink import push_to_loki
from core.stats_engine import record_repair

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 修复脚本库（只读）
# ---------------------------------------------------------------------------
_REPAIR_SCRIPTS_RAW = {
    "restart_deployment": {
        "script_name": "restart_deployment",
        "description": "使用 kubectl 重启 Deployment（滚动重启）",
        "parameters": {
            "namespace": {"type": "string", "required": True},
            "deployment": {"type": "string", "required": True},
        },
        "command": "kubectl rollout restart deployment {deployment} -n {namespace}",
    },
    "delete_pod": {
        "script_name": "delete_pod",
        "description": "删除指定 Pod（Kubernetes 会依据 Replicaset 自动重建）",
        "parameters": {
            "namespace": {"type": "string", "required": True},
            "pod": {"type": "string", "required": True},
        },
        "command": "kubectl delete pod {pod} -n {namespace}",
    },
    "scale_deployment": {
        "script_name": "scale_deployment",
        "description": "水平扩容/缩容 Deployment",
        "parameters": {
            "namespace": {"type": "string", "required": True},
            "deployment": {"type": "string", "required": True},
            "replicas": {"type": "int", "required": True},
        },
        "command": "kubectl scale deployment {deployment} --replicas={replicas} -n {namespace}",
    },
}

# 只读映射，防止外部篡改
REPAIR_SCRIPTS = json.loads(json.dumps(_REPAIR_SCRIPTS_RAW))

# ---------------------------------------------------------------------------
# 参数安全化
# ---------------------------------------------------------------------------
_PARAM_MAX_LEN = 128
_DANGER_CHARS = set("&;|`$<>\"'\\")


def _sanitize_param(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        raise ValueError("Parameter must be a string or number")
    if len(value) > _PARAM_MAX_LEN:
        raise ValueError(f"Parameter exceeds max length {_PARAM_MAX_LEN}")
    if any(ch in _DANGER_CHARS for ch in value):
        raise ValueError("Parameter contains dangerous characters")
    # Kubernetes 资源名校验（只允许字母数字、短横线、下划线）
    import re

    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("Parameter contains invalid characters for K8s resource")
    return value


# ---------------------------------------------------------------------------
# 有状态 Pod 检查
# ---------------------------------------------------------------------------
def _inspect_pod_state(namespace: str, pod: str) -> Dict[str, Any]:
    """查询 Pod 的 owner kind 与 PVC 挂载情况，失败时返回 error 字段。"""
    try:
        kubectl_path = shutil.which("kubectl")
        if kubectl_path is None:
            return {"error": "kubectl executable not found in PATH"}
        proc = subprocess.run(
            [kubectl_path, "get", "pod", pod, "-n", namespace, "-o", "json"],
            shell=False,  # nosec B603
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {"error": proc.stderr.strip()[:200]}
        data = json.loads(proc.stdout)
        owner_kind = ""
        for ref in data.get("metadata", {}).get("ownerReferences", []) or []:
            if ref.get("controller"):
                owner_kind = ref.get("kind", "")
                break
        has_pvc = False
        for vol in data.get("spec", {}).get("volumes", []) or []:
            if vol.get("persistentVolumeClaim"):
                has_pvc = True
                break
        return {"owner_kind": owner_kind, "has_pvc": has_pvc}
    except Exception as e:  # pragma: no cover
        return {"error": str(e)[:200]}


# ---------------------------------------------------------------------------
# 命令渲染
# ---------------------------------------------------------------------------
def _render_command(tmpl: str, params: Dict[str, Any]) -> str:
    rendered = tmpl
    for key, raw_val in params.items():
        safe_val = _sanitize_param(raw_val)
        rendered = rendered.replace(f"{{{key}}}", safe_val)
    return rendered


# ---------------------------------------------------------------------------
# 修复执行（异步）
# ---------------------------------------------------------------------------
async def execute_repair(
    host_cfg: Dict[str, Any], script_key: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    host = host_cfg.get("host", "unknown")
    script = REPAIR_SCRIPTS.get(script_key)
    if not script:
        raise ValueError(f"Unknown repair script: {script_key}")

    # 参数渲染
    full_cmd = _render_command(script["command"], params)

    # 删除 Pod 前检查是否为 StatefulSet 或挂载 PVC
    if script_key == "delete_pod":
        namespace = params.get("namespace")
        pod = params.get("pod")
        if namespace and pod:
            inspection = await asyncio.to_thread(_inspect_pod_state, namespace, pod)
            if "error" not in inspection:
                owner_kind = inspection.get("owner_kind", "")
                has_pvc = inspection.get("has_pvc", False)
                if owner_kind == "StatefulSet" or has_pvc:
                    reason = f"Refusing to delete pod {pod}: owner={owner_kind}, has_pvc={has_pvc}"
                    record_audit(host, script_key, full_cmd, "blocked", reason)
                    return {
                        "host": host,
                        "script": script_key,
                        "blocked": True,
                        "output": "",
                        "error": reason,
                        "return_code": -1,
                    }
            else:
                _logger.warning(
                    "Could not inspect pod state for %s/%s: %s",
                    namespace,
                    pod,
                    inspection["error"],
                )

    # 护栏审查
    risk = analyze_command(full_cmd)
    if risk == RiskLevel.BLOCKED:
        record_audit(host, script_key, full_cmd, "blocked", "K8s repair blocked by guard")
        return {
            "host": host,
            "script": script_key,
            "blocked": True,
            "output": "",
            "error": "Blocked by command guard",
            "return_code": -1,
        }

    # 执行命令（使用 bash）
    start_ts = time.time()
    proc = await asyncio.to_thread(
        subprocess.run,
        ["bash", "-c", full_cmd],
        capture_output=True,
        text=True,
        timeout=180,
    )
    duration = time.time() - start_ts
    success = proc.returncode == 0
    output = proc.stdout.strip()
    error = proc.stderr.strip()

    # 记录审计
    try:
        record_audit(
            host, script_key, full_cmd, "success" if success else "failed", error or output
        )
    except Exception as e:
        _logger.error("Audit write failed for K8s repair %s on %s: %s", script_key, host, e)

    # 统计写入 & Loki 推送
    result_record = {
        "host": host,
        "script": script_key,
        "result": success,
        "output": output,
        "error": error,
        "return_code": proc.returncode,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "duration_sec": duration,
    }
    try:
        await record_repair(result_record)
    except Exception as e:
        _logger.debug("Stats record failed for K8s repair %s on %s: %s", script_key, host, e)
    try:
        push_to_loki(result_record)
    except Exception as e:
        _logger.debug("Loki push failed for K8s repair %s on %s: %s", script_key, host, e)
    # PID 防护（记录一次成功/失败）
    register_self_pid()

    # 记录历史
    record_history(result_record)
    return result_record


# ---------------------------------------------------------------------------
# 同步包装（供 FastAPI 同步路由）
# ---------------------------------------------------------------------------
def execute_repair_sync(
    host_cfg: Dict[str, Any], script_key: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    # 🔧 性能优化: 添加上下文检测，避免在异步上下文中使用 asyncio.run
    try:
        asyncio.get_running_loop()
        import warnings

        warnings.warn(
            "execute_repair_sync called from async context, use execute_repair instead",
            RuntimeWarning,
        )
    except RuntimeError:
        pass  # 不在异步上下文中，可以安全使用
    return asyncio.run(execute_repair(host_cfg, script_key, params))


# ---------------------------------------------------------------------------
# 批量修复入口
# ---------------------------------------------------------------------------
async def repair_all_k8s(script_key: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    tasks = []
    for host_cfg in K8S_HOSTS:
        tasks.append(execute_repair(host_cfg, script_key, params))
    return await asyncio.gather(*tasks, return_exceptions=False)


# ---------------------------------------------------------------------------
# 历史查询（可选）
# ---------------------------------------------------------------------------
_repair_lock = Lock()
_repair_history: deque[Dict[str, Any]] = deque(maxlen=100)


def record_history(entry: Dict[str, Any]):
    with _repair_lock:
        _repair_history.appendleft(entry)


def get_k8s_repair_history(limit: int = 20) -> List[Dict[str, Any]]:
    with _repair_lock:
        return list(_repair_history)[:limit]
