# -*- coding: utf-8 -*-
"""中危台账批次 20 回归测试（services/，2026-09-16）。

覆盖条目：
- SRV-027 services/alert_service/notifier.py       未配置 webhook 时如实上报未发送（success=False/channel=none）
- SRV-042 services/audit_service/encryption.py     真实 AES-256-GCM（真实 nonce/tag，可验签拒绝篡改）
- SRV-055 services/audit_service/retention.py      cleanup/archive 真实删除/归档（非纯计数）
- SRV-079 services/repair_service/executor.py      步骤按声明顺序串行执行（非并行 gather）
- SRV-069 services/plugin_service/service.py       执行耗时真实（错误路径不再恒 0）
"""

from __future__ import annotations

import asyncio
import base64
import time
from datetime import datetime, timedelta

import pytest

from services.alert_service.notifier import NotificationService
from services.alert_service.schemas import Alert, AlertSeverity
from services.audit_service import encryption as audit_encryption
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.retention import RetentionManager
from services.audit_service.schemas import AuditEvent, AuditEventStatus
from services.repair_service.executor import RunbookExecutor
from services.repair_service.schemas import RepairRunbook, RepairStep

pytestmark = pytest.mark.services


# ---------------------------------------------------------------------------
# SRV-027 — notifier honesty when no webhook is configured
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_notifier_no_webhook_reports_not_sent():
    svc = NotificationService(webhook_url="")
    alert = Alert(id="a1", title="boom", level=AlertSeverity.CRITICAL)
    result = await svc.notify(alert)
    assert result["channel"] == "none"
    assert result["success"] is False  # 未发送任何通知不能记成功
    assert result["detail"] == "no webhook configured"


@pytest.mark.asyncio
async def test_notifier_below_min_level_is_noop_success():
    svc = NotificationService(webhook_url="")
    alert = Alert(id="a2", title="info", level=AlertSeverity.INFO)
    result = await svc.notify(alert)
    assert result["channel"] == "none"
    assert result["success"] is True  # 低于阈值属正常忽略
    assert result["detail"] == "below min level"


# ---------------------------------------------------------------------------
# SRV-042 — real AES-256-GCM
# ---------------------------------------------------------------------------
def test_aes256gcm_real_nonce_and_tag_roundtrip():
    engine = audit_encryption.AESEncryption("secret-key-32")
    assert engine.algorithm == "AES-256-GCM"

    enc1 = engine.encrypt("hello world")
    enc2 = engine.encrypt("hello world")
    # 12-byte nonce / 16-byte tag，真实随机
    assert len(bytes.fromhex(enc1["nonce"])) == 12
    assert len(bytes.fromhex(enc1["tag"])) == 16
    assert enc1["nonce"] != enc2["nonce"]
    assert enc1["ciphertext"] != enc2["ciphertext"]
    assert engine.decrypt(enc1["ciphertext"]) == "hello world"


def test_aes256gcm_rejects_tampered_ciphertext():
    engine = audit_encryption.AESEncryption("k")
    enc = engine.encrypt("top secret")
    raw = bytearray(base64.urlsafe_b64decode(enc["ciphertext"].encode()))
    raw[-1] ^= 0x01  # 篡改末字节
    tampered = base64.urlsafe_b64encode(bytes(raw)).decode()
    with pytest.raises(Exception):
        engine.decrypt(tampered)


def test_audit_encryption_blob_flags_real_algorithm():
    audit = audit_encryption.AuditEncryption("another-key")
    blob = audit.encrypt_event("e1", "secret message")
    assert blob.algorithm == "AES-256-GCM"
    assert audit.decrypt_blob(blob) == "secret message"


# ---------------------------------------------------------------------------
# SRV-055 — retention really deletes / archives
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retention_archive_marks_and_cleanup_deletes():
    repo = InMemoryAuditRepository()
    rm = RetentionManager(repo)
    await rm.apply_policy("t1", ttl_days=30, archive_after_days=7, auto_archive=True)

    now = datetime.utcnow()
    old = now - timedelta(days=60)
    recent = now - timedelta(days=1)
    await repo.update_event(AuditEvent(event_id="old", action="a", resource="r", user_id="u",
                                       tenant_id="t1", timestamp=old, status=AuditEventStatus.RECORDED))
    await repo.update_event(AuditEvent(event_id="new", action="a", resource="r", user_id="u",
                                       tenant_id="t1", timestamp=recent, status=AuditEventStatus.RECORDED))

    archived = await rm.archive("t1", now=now)
    assert archived["archived"] == 1
    assert (await repo.get_event("old")).status == AuditEventStatus.ARCHIVED  # 真实落库
    assert (await repo.get_event("new")).status == AuditEventStatus.RECORDED
    # 再次归档：已归档的被跳过
    assert (await rm.archive("t1", now=now))["archived"] == 0

    deleted = await rm.cleanup("t1", now=now)
    assert deleted["deleted"] == 1
    assert await repo.get_event("old") is None  # 真实删除
    assert await repo.get_event("new") is not None


# ---------------------------------------------------------------------------
# SRV-079 — executor runs steps sequentially in declared order
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_executor_runs_steps_in_order_sequentially(monkeypatch):
    ex = RunbookExecutor(dry_run=True)
    order: list[str] = []
    active = {"max": 0, "cur": 0}

    async def fake_step(step, params):
        active["cur"] += 1
        active["max"] = max(active["max"], active["cur"])
        order.append(step.name)
        await asyncio.sleep(0.02)
        active["cur"] -= 1
        return {"success": True, "stdout": f"ran {step.name}", "stderr": ""}

    monkeypatch.setattr(ex, "_execute_step", fake_step)

    rb = RepairRunbook(
        runbook_id="rb",
        name="rb",
        steps=[
            RepairStep(name="s1", command="echo 1"),
            RepairStep(name="s2", command="echo 2"),
            RepairStep(name="s3", command="echo 3"),
        ],
    )
    result = await ex.execute("t1", rb)
    assert result.success is True
    assert result.executed_steps == 3
    assert order == ["s1", "s2", "s3"]      # 顺序被遵守
    assert active["max"] == 1               # 串行：无并发重叠
    assert "ran s1" in result.output and "ran s3" in result.output


# ---------------------------------------------------------------------------
# SRV-069 — plugin execution duration is real in the error path
# ---------------------------------------------------------------------------
def test_plugin_error_path_records_real_duration(monkeypatch):
    import services.plugin_service.service as svc_mod
    from fastapi.testclient import TestClient

    # 构造一个执行耗时可观测、但会失败的插件实例
    class BoomPlugin:
        def collect(self):
            time.sleep(0.02)
            raise RuntimeError("boom")

    monkeypatch.setattr(svc_mod, "get_plugin", lambda name: BoomPlugin())

    import os

    os.environ["PLUGIN_SERVICE_USE_IN_MEMORY"] = "true"
    from services.plugin_service.main_app import app

    with TestClient(app) as client:
        name = "durtest-plugin"
        created = client.post(
            "/plugins",
            json={
                "name": name,
                "version": "1.0.0",
                "description": "d",
                "author": "t",
                "plugin_type": "collector",
            },
        )
        assert created.status_code in (200, 201)

        resp = client.post(f"/plugins/{name}/run", json={"input_data": {}})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        # 此前恒为 0；现在应为真实耗时（>= ~20ms）
        assert body["duration_ms"] is not None
        assert body["duration_ms"] >= 10.0
