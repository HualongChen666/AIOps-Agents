# -*- coding: utf-8 -*-
"""Snapshot capture, persistence, encryption and lifecycle management."""

from __future__ import annotations

import asyncio
import json
import re
import shlex
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from config import SNAPSHOT_CONFIG
from core.crypto import decrypt_snapshot, encrypt_snapshot
from core.db_engine import AsyncSessionLocal
from core.models import Snapshot

# Minimum set of resource names used for kubectl state capture
_K8S_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.]+$|^$")
_SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.@]+$|^$")

_DEFAULT_TIMEOUT = 20.0

_OPERATION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "pod_restart",
        re.compile(
            r"kubectl.*(rollout\s+restart|restart|delete)\s+(deployment|deploy|pod|replicaset|rs)",
            re.I,
        ),
    ),
    (
        "config_mod",
        re.compile(r"kubectl.*(apply|set|patch|edit|replace).*(configmap|cm|secret)", re.I),
    ),
    ("scale", re.compile(r"kubectl\s+scale|kubectl.*--replicas|autoscale|hpa", re.I)),
    ("network_policy", re.compile(r"kubectl.*(networkpolicy|netpol|network-policy)", re.I)),
    (
        "service_restart",
        re.compile(
            r"systemctl\s+restart|service\s+\S+\s+restart|Restart-Service|net\s+start|net\s+stop|sc\s+(start|stop|restart)",  # noqa: E501
            re.I,
        ),
    ),
    ("process_kill", re.compile(r"\bkill\b|Stop-Process|taskkill|pkill|killall", re.I)),
    (
        "disk_cleanup",
        re.compile(r"rm\s|del\s|clear.*temp|cleanmgr|diskcleanup|findstr.*delete|rmdir", re.I),
    ),
    (
        "network_fix",
        re.compile(r"ifconfig|ip\s+addr|nmcli|netsh|iptables|flushdns|route\s|ping\s+-f", re.I),
    ),
]


def classify_operation_type(commands: List[str], script_key: str = "") -> str:
    """Classify a repair command chain into an operation type for targeted snapshotting."""
    combined = " ".join(commands) + f" {script_key}"
    for op_type, pattern in _OPERATION_PATTERNS:
        if pattern.search(combined):
            return op_type
    return "generic"


def _safe_name(name: str) -> Optional[str]:
    """Validate a K8s/service resource name to avoid shell injection."""
    if name and _K8S_NAME_PATTERN.match(name):
        return name
    return None


def _safe_service_name(name: str) -> Optional[str]:
    if name and _SERVICE_NAME_PATTERN.match(name):
        return name
    return None


def _parse_namespace(command: str) -> str:
    """Extract -n/--namespace value from a kubectl command; default to 'default'."""
    for flag in ("-n", "--namespace"):
        # Support -n ns, -n=ns, --namespace=ns
        idx = command.find(flag)
        if idx < 0:
            continue
        tail = command[idx + len(flag) :]
        if tail.startswith("="):
            ns = tail[1:].split(None, 1)[0].strip().strip("\"'")
        elif tail.startswith(" "):
            ns = tail.strip().split(None, 1)[0].strip().strip("\"'")
        else:
            continue
        if ns and _K8S_NAME_PATTERN.match(ns):
            return ns
    return "default"


def _extract_k8s_resource(command: str) -> Optional[Tuple[str, str, str]]:
    """Extract (resource_type, resource_name, namespace) from a kubectl command.

    Handles forms like:
        kubectl rollout restart deployment/nginx -n foo
        kubectl scale deployment nginx --replicas=3 --namespace bar
        kubectl get configmap my-cm
    """
    if "kubectl" not in command.lower():
        return None

    namespace = _parse_namespace(command)

    # Generic pattern for resource/name or resource name
    patterns = [
        # rollout restart deployment/nginx, delete deployment/nginx
        re.compile(
            r"kubectl\s+\S+\s+(?:restart|delete|get|describe|scale)\s+([a-zA-Z]+)/([a-zA-Z0-9_\-.]+)",  # noqa: E501
            re.I,
        ),
        # scale deployment nginx --replicas=...
        re.compile(r"kubectl\s+scale\s+([a-zA-Z]+)\s+([a-zA-Z0-9_\-.]+)", re.I),
        # get configmap my-cm, apply -f ... not handled
        re.compile(
            r"kubectl\s+(?:get|describe|delete|edit)\s+([a-zA-Z]+)\s+([a-zA-Z0-9_\-.]+)", re.I
        ),
    ]

    for pat in patterns:
        m = pat.search(command)
        if m:
            resource_type = m.group(1).lower()
            resource_name = m.group(2)
            if _safe_name(resource_name):
                return resource_type, resource_name, namespace
    return None


def _extract_service_name(command: str) -> Optional[str]:
    """Extract service name from systemctl/service/restart-Service commands."""
    patterns = [
        re.compile(r"systemctl\s+(?:restart|start|stop|status)\s+([a-zA-Z0-9_\-.@]+)", re.I),
        re.compile(r"Restart-Service\s+-Name\s+['\"]?([a-zA-Z0-9_\-.@]+)['\"]?", re.I),
        re.compile(r"Restart-Service\s+['\"]?([a-zA-Z0-9_\-.@]+)['\"]?", re.I),
    ]
    for pat in patterns:
        m = pat.search(command)
        if m:
            name = m.group(1)
            if _safe_service_name(name):
                return name
    return None


def _extract_pid_or_name(command: str) -> Optional[str]:
    """Extract PID or process name from kill/taskkill commands."""
    patterns = [
        re.compile(
            r"\b(?:kill|killall|pkill)\s+(?:-\w+\s+)*(?:['\"]?)([a-zA-Z0-9_\-.@]+)(?:['\"]?)", re.I
        ),
        re.compile(r"Stop-Process\s+(?:-Id\s+['\"]?)(\d+)(?:['\"]?)", re.I),
        re.compile(r"Stop-Process\s+-Name\s+['\"]?([a-zA-Z0-9_\-.@]+)['\"]?", re.I),
        re.compile(r"taskkill\s+/PID\s+(\d+)", re.I),
        re.compile(r"taskkill\s+/IM\s+['\"]?([a-zA-Z0-9_\-.@]+)['\"]?", re.I),
    ]
    for pat in patterns:
        m = pat.search(command)
        if m:
            return m.group(1)
    return None


async def _run_shell_capture(
    cmd: str,
    platform: str,
    timeout: float = _DEFAULT_TIMEOUT,
) -> str:
    """Run a read-only shell command and capture stdout (best-effort)."""
    if not cmd:
        return ""
    try:
        if platform == "windows" and cmd.lower().startswith("powershell"):
            proc = await asyncio.create_subprocess_exec(
                "powershell",
                "-Command",
                cmd.split("-Command", 1)[1].strip(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="ignore").strip()
        err = stderr.decode("utf-8", errors="ignore").strip()
        if proc.returncode != 0 and not out:
            return f"# command failed (rc={proc.returncode}): {err[:500]}"
        return out
    except asyncio.TimeoutError:
        return "# timeout capturing state"
    except Exception as exc:
        return f"# error capturing state: {exc}"


async def _capture_k8s_resource_state(
    resource_type: str,
    resource_name: str,
    namespace: str,
    platform: str,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture JSON/YAML state of a K8s resource before a mutating operation."""
    state: Dict[str, Any] = {
        "resource_type": resource_type,
        "resource_name": resource_name,
        "namespace": namespace,
    }

    async def _kubectl(args: str) -> str:
        host_arg = f" --server={shlex.quote(host)}" if host else ""
        return await _run_shell_capture(
            f"kubectl{host_arg} {args}",
            platform=platform,
            timeout=_DEFAULT_TIMEOUT,
        )

    state["json"] = await _kubectl(f"get {resource_type} {resource_name} -n {namespace} -o json")
    state["yaml"] = await _kubectl(f"get {resource_type} {resource_name} -n {namespace} -o yaml")

    # For deployments, also capture related HPA/ReplicaSet state
    if resource_type in ("deployment", "deploy"):
        state["hpa"] = await _kubectl(f"get hpa -n {namespace} -o json")
        state["replicasets"] = await _kubectl(
            f"get replicaset -n {namespace} -l app={shlex.quote(resource_name)} -o json"
        )

    return state


async def _capture_network_policy_state(
    resource_name: Optional[str],
    namespace: str,
    platform: str,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture NetworkPolicy state before a network policy change."""
    host_arg = f" --server={shlex.quote(host)}" if host else ""
    result: Dict[str, Any] = {"namespace": namespace}
    if resource_name:
        result["target"] = await _run_shell_capture(
            f"kubectl{host_arg} get networkpolicy {resource_name} -n {namespace} -o yaml",
            platform=platform,
        )
    result["all_networkpolicies"] = await _run_shell_capture(
        f"kubectl{host_arg} get networkpolicy -n {namespace} -o yaml",
        platform=platform,
    )
    result["all_services"] = await _run_shell_capture(
        f"kubectl{host_arg} get service -n {namespace} -o yaml",
        platform=platform,
    )
    return result


async def _capture_service_state(
    service_name: str,
    platform: str,
) -> Dict[str, Any]:
    """Capture service state before restart."""
    if platform == "windows":
        cmd = (
            f"powershell -Command \"Get-Service -Name '{service_name}' | "
            f'Select-Object Name,Status,StartType | Format-List"'
        )
        return {
            "service_name": service_name,
            "status": await _run_shell_capture(cmd, platform=platform),
        }

    cmd = f"systemctl show {service_name} --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID --no-pager"  # noqa: E501
    status = await _run_shell_capture(cmd, platform=platform)
    cmd_list = f"systemctl cat {service_name} 2>/dev/null || echo '# unit file not readable'"
    unit_file = await _run_shell_capture(cmd_list, platform=platform)
    return {"service_name": service_name, "status": status, "unit_file": unit_file}


async def _capture_process_state(
    identifier: str,
    platform: str,
) -> Dict[str, Any]:
    """Capture process state before termination."""
    if platform == "windows":
        if identifier.isdigit():
            cmd = f'tasklist /FI "PID eq {identifier}" /FO LIST'
        else:
            cmd = f'tasklist /FI "IMAGENAME eq {identifier}" /FO LIST'
        return {"identifier": identifier, "info": await _run_shell_capture(cmd, platform=platform)}

    if identifier.isdigit():
        cmd = f"ps -p {identifier} -o pid,ppid,cmd,pcpu,pmem"
    else:
        cmd = f"ps aux | grep -E '[{identifier[0]}]{identifier[1:]}' || true"
    return {"identifier": identifier, "info": await _run_shell_capture(cmd, platform=platform)}


async def build_pre_state(
    operation_type: str,
    alert: Dict[str, Any],
    commands: List[str],
    platform: str,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a structured pre-operation state snapshot for a given operation type."""
    pre_state: Dict[str, Any] = {
        "operation_type": operation_type,
        "platform": platform,
        "host": host,
        "alert_id": alert.get("id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commands": commands,
    }

    captured: List[Dict[str, Any]] = []

    if operation_type in ("pod_restart", "scale", "config_mod"):
        seen = set()
        for cmd in commands:
            parsed = _extract_k8s_resource(cmd)
            if not parsed:
                continue
            resource_type, resource_name, namespace = parsed
            key = (resource_type, resource_name, namespace)
            if key in seen:
                continue
            seen.add(key)
            captured.append(
                await _capture_k8s_resource_state(
                    resource_type, resource_name, namespace, platform, host
                )
            )

    elif operation_type == "network_policy":
        np_namespace = "default"
        np_resource_name: Optional[str] = None
        for cmd in commands:
            np_namespace = _parse_namespace(cmd)
            parsed = _extract_k8s_resource(cmd)
            if parsed:
                np_resource_name = parsed[1]
        captured.append(
            await _capture_network_policy_state(np_resource_name, np_namespace, platform, host)
        )

    elif operation_type == "service_restart":
        for cmd in commands:
            service_name = _extract_service_name(cmd)
            if service_name:
                captured.append(await _capture_service_state(service_name, platform))

    elif operation_type == "process_kill":
        for cmd in commands:
            ident = _extract_pid_or_name(cmd)
            if ident:
                captured.append(await _capture_process_state(ident, platform))

    if not captured:
        captured.append({"note": "No structured state capture available for this operation type"})

    pre_state["resources"] = captured
    return pre_state


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def save_snapshot(
    state: Any,
    commands: List[str],
    rollback_plan: List[str],
    repair_record_id: Optional[str] = None,
    pre_metrics: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Persist an encrypted pre-operation snapshot before the repair executes."""
    if not getattr(state, "alert", None) or not state.alert:
        logger.warning("[snapshot_store] Cannot save snapshot without alert")
        return None

    alert = state.alert
    alert_id = str(alert.get("id", "unknown"))
    platform = (alert.get("platform") or "windows").lower()
    host = alert.get("host") or alert.get("k8s_host") or alert.get("hostname")

    script_key = ""
    if isinstance(getattr(state, "runbook", None), dict):
        script_key = state.runbook.get("script_key", "") or ""

    operation_type = classify_operation_type(commands, script_key)
    pre_state = await build_pre_state(operation_type, alert, commands, platform, host)
    if pre_metrics:
        pre_state["metrics"] = pre_metrics

    snapshot_id = f"snap-{alert_id}-{_now().timestamp()}".replace(".", "")
    retention_days = int(SNAPSHOT_CONFIG.get("retention_days", 7))
    expires_at = _now() + timedelta(days=retention_days)

    rollback_text = json.dumps({"commands": rollback_plan}, ensure_ascii=False, default=str)
    pre_state_text = json.dumps(pre_state, ensure_ascii=False, default=str)

    try:
        snapshot = Snapshot(
            id=snapshot_id,
            alert_id=alert_id,
            repair_record_id=repair_record_id,
            operation_type=operation_type,
            pre_state=encrypt_snapshot(pre_state_text),
            rollback_plan=encrypt_snapshot(rollback_text),
            status="pending",
            retention_days=retention_days,
            expires_at=expires_at,
        )
        async with AsyncSessionLocal() as session:
            session.add(snapshot)
            await session.commit()
        logger.info(
            f"[snapshot_store] Snapshot saved | id={snapshot_id} | "
            f"operation_type={operation_type} | alert_id={alert_id}"
        )
    except Exception as exc:
        logger.error(f"[snapshot_store] Failed to save snapshot: {exc}", exc_info=True)
        return None

    # Attach to graph state for downstream nodes
    state.snapshot_id = snapshot_id
    if not isinstance(state.snapshot, dict):
        state.snapshot = {}
    state.snapshot["snapshot_id"] = snapshot_id
    state.snapshot["operation_type"] = operation_type
    state.snapshot["pre_state"] = pre_state
    state.snapshot["timestamp"] = _now().isoformat()

    state.rollback_info = {
        "snapshot_id": snapshot_id,
        "rollback_commands": rollback_plan,
        "pre_state": pre_state,
    }

    return snapshot_id


async def update_snapshot_status(
    snapshot_id: Optional[str],
    status: str,
    post_state: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Update snapshot status after repair/rollback."""
    if not snapshot_id:
        return
    try:
        async with AsyncSessionLocal() as session:
            snapshot = await session.get(Snapshot, snapshot_id)
            if snapshot:
                snapshot.status = status
                snapshot.completed_at = _now()
                if post_state is not None:
                    snapshot.post_state = encrypt_snapshot(
                        json.dumps(post_state, ensure_ascii=False, default=str)
                    )
                if error_message:
                    snapshot.error_message = error_message
                await session.commit()
    except Exception as exc:
        logger.error(f"[snapshot_store] Failed to update snapshot {snapshot_id}: {exc}")


async def get_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve and decrypt a snapshot by id."""
    try:
        async with AsyncSessionLocal() as session:
            snapshot = await session.get(Snapshot, snapshot_id)
            if not snapshot:
                return None
            return {
                "id": snapshot.id,
                "alert_id": snapshot.alert_id,
                "repair_record_id": snapshot.repair_record_id,
                "operation_type": snapshot.operation_type,
                "pre_state": (
                    json.loads(decrypt_snapshot(snapshot.pre_state)) if snapshot.pre_state else None
                ),
                "post_state": (
                    json.loads(decrypt_snapshot(snapshot.post_state))
                    if snapshot.post_state
                    else None
                ),
                "rollback_plan": (
                    json.loads(decrypt_snapshot(snapshot.rollback_plan))
                    if snapshot.rollback_plan
                    else None
                ),
                "status": snapshot.status,
                "retention_days": snapshot.retention_days,
                "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
                "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
                "completed_at": (
                    snapshot.completed_at.isoformat() if snapshot.completed_at else None
                ),
                "error_message": snapshot.error_message,
            }
    except Exception as exc:
        logger.error(f"[snapshot_store] Failed to get snapshot {snapshot_id}: {exc}")
        return None


async def cleanup_expired_snapshots() -> int:
    """Delete snapshots past their expires_at date."""
    from sqlalchemy import delete

    try:
        async with AsyncSessionLocal() as session:
            stmt = delete(Snapshot).where(Snapshot.expires_at < _now())
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount or 0
            logger.info(f"[snapshot_store] Cleaned up {count} expired snapshots")
            return count
    except Exception as exc:
        logger.error(f"[snapshot_store] Failed to cleanup expired snapshots: {exc}")
        return 0
