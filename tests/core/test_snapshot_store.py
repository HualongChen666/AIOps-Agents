# -*- coding: utf-8 -*-
"""Tests for snapshot capture, encryption, persistence and lifecycle."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet

from core import crypto as crypto_module
from core import snapshot_store as snapshot_store_module


@pytest.fixture(autouse=True)
def _isolate_crypto(monkeypatch):
    """Provide a stable encryption key for every snapshot test."""
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_KEY", key)
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "true")
    # Reset the lazy Fernet cache so the new key is used.
    crypto_module._fernet = None
    yield
    crypto_module._fernet = None


@pytest.fixture
def fake_state():
    """Minimal HealState-like object."""
    state = SimpleNamespace(
        alert={"id": "alert-123", "platform": "linux", "host": "k8s-control"},
        runbook={"script_key": "restart_service"},
        snapshot={},
        rollback_info={},
        snapshot_id=None,
    )
    return state


@pytest.fixture
def fake_session_factory():
    """Return an AsyncSessionLocal-like factory that records added objects."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock(return_value=None)

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            return False

    return _Ctx, session


@pytest.mark.asyncio
async def test_classify_operation_type():
    """Operation types are classified from commands and script_key."""
    assert (
        snapshot_store_module.classify_operation_type(["kubectl rollout restart deployment/nginx"])
        == "pod_restart"
    )
    assert (
        snapshot_store_module.classify_operation_type(
            ["kubectl scale deployment nginx --replicas=3"]
        )
        == "scale"
    )
    assert (
        snapshot_store_module.classify_operation_type(["kubectl apply -f configmap.yaml"])
        == "config_mod"
    )
    assert (
        snapshot_store_module.classify_operation_type(["kubectl get networkpolicy -n default"])
        == "network_policy"
    )
    assert (
        snapshot_store_module.classify_operation_type(
            ["systemctl restart nginx"], "restart_service"
        )
        == "service_restart"
    )
    assert (
        snapshot_store_module.classify_operation_type(["Stop-Process -Id 1234"], "kill_high_cpu")
        == "process_kill"
    )
    assert snapshot_store_module.classify_operation_type(["echo hello"]) == "generic"


@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip():
    """Snapshot data is encrypted at rest and decryptable."""
    plaintext = json.dumps({"secret": "password123", "host": "prod-01"})
    encrypted = crypto_module.encrypt_snapshot(plaintext)

    # Encrypted payload must not contain the plaintext secret.
    assert plaintext not in encrypted
    assert not encrypted.startswith(crypto_module._PLAINTEXT_PREFIX)

    decrypted = crypto_module.decrypt_snapshot(encrypted)
    assert decrypted == plaintext


@pytest.mark.asyncio
async def test_save_snapshot_persists_encrypted(fake_state, fake_session_factory, monkeypatch):
    """save_snapshot writes an encrypted Snapshot to the database."""
    ctx, session = fake_session_factory
    monkeypatch.setattr(snapshot_store_module, "AsyncSessionLocal", ctx().__class__())
    # Re-patch because the fixture returns an instance, we need a callable factory.
    snapshot_store_module.AsyncSessionLocal = ctx

    snapshot_id = await snapshot_store_module.save_snapshot(
        state=fake_state,
        commands=["systemctl restart nginx"],
        rollback_plan=["systemctl start nginx"],
        pre_metrics={"cpu": [80.0, 85.0]},
    )

    assert snapshot_id is not None
    assert fake_state.snapshot_id == snapshot_id
    assert fake_state.snapshot["operation_type"] == "service_restart"

    added = session.add.call_args[0][0]
    assert added.operation_type == "service_restart"
    assert added.status == "pending"
    assert added.expires_at > datetime.now(timezone.utc)
    assert added.expires_at <= datetime.now(timezone.utc) + timedelta(days=8)

    # pre_state and rollback_plan must be encrypted JSON.
    decrypted_pre = json.loads(crypto_module.decrypt_snapshot(added.pre_state))
    decrypted_plan = json.loads(crypto_module.decrypt_snapshot(added.rollback_plan))
    assert decrypted_pre["operation_type"] == "service_restart"
    assert decrypted_pre["metrics"] == {"cpu": [80.0, 85.0]}
    assert decrypted_plan["commands"] == ["systemctl start nginx"]


@pytest.mark.asyncio
async def test_update_snapshot_status(fake_session_factory, monkeypatch):
    """update_snapshot_status mutates the stored Snapshot."""
    ctx, session = fake_session_factory
    snapshot_obj = MagicMock()
    session.get = AsyncMock(return_value=snapshot_obj)
    snapshot_store_module.AsyncSessionLocal = ctx

    await snapshot_store_module.update_snapshot_status(
        "snap-123", "success", post_state={"ok": True}
    )

    assert snapshot_obj.status == "success"
    assert snapshot_obj.completed_at is not None
    assert snapshot_obj.post_state is not None
    decrypted = json.loads(crypto_module.decrypt_snapshot(snapshot_obj.post_state))
    assert decrypted == {"ok": True}


@pytest.mark.asyncio
async def test_cleanup_expired_snapshots(fake_session_factory, monkeypatch):
    """cleanup_expired_snapshots deletes rows whose expires_at is in the past."""
    ctx, session = fake_session_factory
    monkeypatch.setattr(snapshot_store_module, "AsyncSessionLocal", ctx)

    result_mock = MagicMock()
    result_mock.rowcount = 3
    session.execute = AsyncMock(return_value=result_mock)

    count = await snapshot_store_module.cleanup_expired_snapshots()
    assert count == 3
    assert session.execute.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_build_pre_state_for_k8s_pod_restart(monkeypatch):
    """Pre-state for pod restart includes JSON/YAML and related HPA/ReplicaSet."""
    captured = []

    async def _fake_capture(resource_type, resource_name, namespace, platform, host):
        captured.append((resource_type, resource_name, namespace))
        return {"resource_type": resource_type, "resource_name": resource_name, "json": "{}"}

    monkeypatch.setattr(snapshot_store_module, "_capture_k8s_resource_state", _fake_capture)

    pre_state = await snapshot_store_module.build_pre_state(
        operation_type="pod_restart",
        alert={"id": "a1"},
        commands=["kubectl rollout restart deployment/nginx -n default"],
        platform="linux",
    )

    assert pre_state["operation_type"] == "pod_restart"
    assert captured == [("deployment", "nginx", "default")]
    assert pre_state["resources"][0]["resource_name"] == "nginx"


@pytest.mark.asyncio
async def test_extract_k8s_resource():
    """Resource extraction supports common kubectl command forms."""
    assert snapshot_store_module._extract_k8s_resource(
        "kubectl rollout restart deployment/nginx -n kube-system"
    ) == ("deployment", "nginx", "kube-system")
    assert snapshot_store_module._extract_k8s_resource(
        "kubectl scale deployment nginx --replicas=3 --namespace=prod"
    ) == ("deployment", "nginx", "prod")
    assert snapshot_store_module._extract_k8s_resource(
        "kubectl get configmap my-cm -n default"
    ) == ("configmap", "my-cm", "default")
    assert snapshot_store_module._extract_k8s_resource("echo hello") is None


@pytest.mark.asyncio
async def test_extract_service_name():
    """Service name extraction supports systemctl and PowerShell forms."""
    assert snapshot_store_module._extract_service_name("systemctl restart nginx") == "nginx"
    assert (
        snapshot_store_module._extract_service_name("Restart-Service -Name 'win-service'")
        == "win-service"
    )
    assert snapshot_store_module._extract_service_name("echo hello") is None
