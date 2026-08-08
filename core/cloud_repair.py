# -*- coding: utf-8 -*-
"""Cloud platform repair executor with SDK-backed implementations."""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List

_REPAIR_HISTORY: deque[Dict[str, Any]] = deque(maxlen=1000)
_REPAIR_LOCK = Lock()


def _record(provider: str, action: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
    entry = {
        "job_id": result.get("job_id") or str(uuid.uuid4()),
        "provider": provider,
        "action": action,
        "params": params,
        "success": result.get("success", False),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": result.get("message", ""),
    }
    with _REPAIR_LOCK:
        _REPAIR_HISTORY.append(entry)


async def _aws_repair(cfg: Dict[str, Any], action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 not installed") from exc

    session = boto3.Session(
        aws_access_key_id=cfg.get("access_key"),
        aws_secret_access_key=cfg.get("secret_key"),
        region_name=cfg.get("region"),
    )
    ec2 = session.client("ec2")
    instance_id = params.get("instance_id")
    if not instance_id:
        raise ValueError("instance_id is required")

    if action == "restart_instance":
        await asyncio.to_thread(ec2.reboot_instances, InstanceIds=[instance_id])
    elif action == "start_instance":
        await asyncio.to_thread(ec2.start_instances, InstanceIds=[instance_id])
    elif action == "stop_instance":
        await asyncio.to_thread(ec2.stop_instances, InstanceIds=[instance_id])
    else:
        raise ValueError(f"Unsupported AWS action: {action}")

    return {
        "success": True,
        "provider": "aws",
        "action": action,
        "params": params,
        "job_id": str(uuid.uuid4()),
        "message": f"AWS {action} executed for {instance_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _azure_repair(cfg: Dict[str, Any], action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.compute import ComputeManagementClient
    except ImportError as exc:
        raise RuntimeError("azure-mgmt-compute or azure-identity not installed") from exc

    subscription_id = cfg.get("subscription_id")
    resource_group = params.get("resource_group_name") or params.get("resource_group")
    vm_name = params.get("vm_name") or params.get("vm")
    if not subscription_id or not resource_group or not vm_name:
        raise ValueError("subscription_id, resource_group_name and vm_name are required")

    credential = ClientSecretCredential(
        tenant_id=cfg.get("tenant_id"),
        client_id=cfg.get("client_id"),
        client_secret=cfg.get("client_secret"),
    )
    compute = ComputeManagementClient(credential, subscription_id)

    if action == "restart_vm":
        await asyncio.to_thread(compute.virtual_machines.begin_restart, resource_group, vm_name)
    elif action == "start_vm":
        await asyncio.to_thread(compute.virtual_machines.begin_start, resource_group, vm_name)
    elif action == "stop_vm":
        await asyncio.to_thread(compute.virtual_machines.begin_deallocate, resource_group, vm_name)
    else:
        raise ValueError(f"Unsupported Azure action: {action}")

    return {
        "success": True,
        "provider": "azure",
        "action": action,
        "params": params,
        "job_id": str(uuid.uuid4()),
        "message": f"Azure {action} executed for {vm_name}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _alibaba_repair(
    cfg: Dict[str, Any], action: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    raise RuntimeError("Alibaba Cloud repair SDK not installed; only metrics collection is supported")


async def execute_cloud_repair(
    provider_cfg: Dict[str, Any], action: str, **params: Any
) -> Dict[str, Any]:
    provider = str(provider_cfg.get("provider", "")).lower()
    if provider == "aws":
        result = await _aws_repair(provider_cfg, action, params)
    elif provider == "azure":
        result = await _azure_repair(provider_cfg, action, params)
    elif provider in ("alibaba", "alicloud"):
        result = await _alibaba_repair(provider_cfg, action, params)
    else:
        raise ValueError(f"Unsupported cloud provider: {provider}")

    _record(provider, action, params, result)
    return result


def get_cloud_repair_history(limit: int = 1000) -> List[Dict[str, Any]]:
    with _REPAIR_LOCK:
        return list(_REPAIR_HISTORY)[-limit:]
