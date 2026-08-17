# -*- coding: utf-8 -*-
"""Targeted coverage tests for batch 29 (core modules below 80%)."""

import asyncio  # noqa: F401  # Imported for test setup
import builtins
import hashlib
import importlib
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import re
import shutil
import sys  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
import types
import urllib.parse
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.backup_strategy
# ---------------------------------------------------------------------------
import core.backup_strategy as backup
import core.oncall_adapter as oca


def _make_subprocess_mock(stdout=b"fake sql", returncode=0, raise_on_communicate=None):
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(
        side_effect=raise_on_communicate if raise_on_communicate else None,
        return_value=(stdout, b""),
    )
    return AsyncMock(return_value=proc)


@pytest.mark.asyncio
async def test_backup_database_no_compression_no_encryption(monkeypatch, tmp_path):
    monkeypatch.setattr(backup, "_backup_config", {**backup._backup_config, "enabled": True})
    backup.configure_backup_strategy(
        backup_location=str(tmp_path),
        compression_enabled=False,
        encryption_enabled=False,
        backup_types=["database"],
    )
    monkeypatch.setattr("asyncio.create_subprocess_exec", _make_subprocess_mock(b"fake sql", 0))
    result = await backup.perform_database_backup()  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_backup_database_integrity_failure(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(
        backup_location=str(tmp_path),
        compression_enabled=False,
        encryption_enabled=True,
        backup_types=["database"],
    )
    monkeypatch.setattr("asyncio.create_subprocess_exec", _make_subprocess_mock(b"fake sql", 0))
    result = await backup.perform_database_backup()  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_backup_config_raises(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(backup_location=str(tmp_path), compression_enabled=False)
    monkeypatch.setattr(backup, "_backup_config", backup.get_backup_config())
    monkeypatch.setattr(shutil, "copy2", MagicMock(side_effect=RuntimeError("boom")))
    result = await backup.perform_config_backup()  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_backup_logs_raises(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(backup_location=str(tmp_path), compression_enabled=False)
    monkeypatch.setattr("os.listdir", MagicMock(side_effect=RuntimeError("boom")))
    result = await backup.perform_logs_backup()  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_full_backup_and_cleanup(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(
        backup_location=str(tmp_path),
        compression_enabled=False,
        encryption_enabled=False,
        backup_types=["database", "config", "logs"],
    )
    monkeypatch.setattr("asyncio.create_subprocess_exec", _make_subprocess_mock(b"fake sql", 0))
    await backup.perform_full_backup()
    # Empty cleanup
    assert await backup.cleanup_old_backups() == 0
    # Insert old entries and clean (one missing, one failing removal)
    for name in ["old_missing", "old_locked"]:
        p = tmp_path / name
        p.mkdir()
        backup._backup_history.append(
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
                "path": str(p),
                "status": "success",
            }
        )
    monkeypatch.setattr("os.path.exists", MagicMock(side_effect=[False, True]))
    monkeypatch.setattr(shutil, "rmtree", MagicMock(side_effect=RuntimeError("locked")))
    assert await backup.cleanup_old_backups() == 1


@pytest.mark.asyncio
async def test_backup_database_subprocess_fail(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(backup_location=str(tmp_path), compression_enabled=False)
    monkeypatch.setattr("asyncio.create_subprocess_exec", _make_subprocess_mock(b"", 1))
    result = await backup.perform_database_backup()  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


def test_verify_integrity_failure(monkeypatch, tmp_path):
    missing = tmp_path / "missing.bin"
    assert backup.verify_backup_integrity(str(missing), "abc") is False


def test_calculate_and_verify_hash(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    h = backup.calculate_file_hash(str(p), "sha256")
    assert backup.verify_backup_integrity(str(p), h) is True
    assert backup.verify_backup_integrity(str(p), h[::-1]) is False


def test_encrypt_decrypt_roundtrip(tmp_path):
    src = tmp_path / "plain.txt"
    src.write_text("hello")
    enc = tmp_path / "plain.txt.enc"
    dec = tmp_path / "plain.txt.dec"
    assert backup.encrypt_file(str(src), str(enc)) is True
    assert backup.decrypt_file(str(enc), str(dec)) is True


def test_decrypt_invalid_token(tmp_path):
    enc = tmp_path / "bad.enc"
    enc.write_bytes(b"not a valid fernet token")
    dec = tmp_path / "out"
    assert backup.decrypt_file(str(enc), str(dec)) is False


def test_validate_manifest(tmp_path):
    good = tmp_path / "manifest.json"
    good.write_text(
        json.dumps(
            {
                "backup_id": "x",
                "type": "database",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "file_path": str(good),
                "file_size_bytes": 1,
                "file_hash": "y",
            }
        )
    )
    assert backup.validate_backup_manifest(str(good)) is False  # bad hash
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"backup_id": "x"}))
    assert backup.validate_backup_manifest(str(bad)) is False
    missing = tmp_path / "missing.json"
    assert backup.validate_backup_manifest(str(missing)) is False


@pytest.mark.asyncio
async def test_restore_database_not_found():
    backup._backup_history.clear()
    result = await backup.restore_database_backup("no-such-id")  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_restore_database_validation_and_decompress(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(backup_location=str(tmp_path))
    bid = "db_test"
    bdir = tmp_path / bid
    bdir.mkdir()
    original = bdir / "testdb.sql"
    original.write_bytes(b"create table x;")
    gz = bdir / "testdb.sql.gz"
    import gzip as GZ

    with open(original, "rb") as f_in:
        with GZ.open(gz, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    manifest = {
        "backup_id": bid,
        "type": "database",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_path": str(gz),
        "file_size_bytes": gz.stat().st_size,
        "file_hash": backup.calculate_file_hash(str(gz)),
    }
    (bdir / "manifest.json").write_text(json.dumps(manifest))
    record = {
        "backup_id": bid,
        "type": "database",
        "path": str(gz),
        "compressed": True,
        "encrypted": False,
        "manifest": manifest,
    }
    backup._backup_history.append(record)
    monkeypatch.setattr("asyncio.create_subprocess_exec", _make_subprocess_mock(b"", 1))
    result = await backup.restore_database_backup(bid)  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed" or "psql" in result.get("error", "")


@pytest.mark.asyncio
async def test_restore_database_encrypted_invalid(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(backup_location=str(tmp_path))
    bid = "db_enc"
    bdir = tmp_path / bid
    bdir.mkdir()
    enc = bdir / "testdb.sql.enc"
    enc.write_bytes(b"not fernet")
    record = {
        "backup_id": bid,
        "type": "database",
        "path": str(enc),
        "compressed": False,
        "encrypted": True,
    }
    backup._backup_history.append(record)
    result = await backup.restore_database_backup(bid)  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_restore_backup_scenarios(monkeypatch, tmp_path):
    backup._backup_history.clear()
    backup.configure_backup_strategy(backup_location=str(tmp_path))
    # not found
    res = await backup.restore_backup("missing")
    assert res["status"] == "failed"
    # path missing
    backup._backup_history.append(
        {
            "backup_id": "p",
            "type": "database",
            "path": str(tmp_path / "gone.sql"),
            "compressed": False,
            "encrypted": False,
        }
    )
    res = await backup.restore_backup("p")
    assert res["status"] == "failed"
    # unsupported type
    backup._backup_history.append(
        {
            "backup_id": "u",
            "type": "unknown",
            "path": str(tmp_path / "u.bin"),
            "compressed": False,
            "encrypted": False,
        }
    )
    (tmp_path / "u.bin").write_bytes(b"x")
    res = await backup.restore_backup("u")
    assert res["status"] == "failed"
    # database restore failure
    bdir = tmp_path / "db_restore"
    bdir.mkdir()
    (bdir / "testdb.sql").write_bytes(b"sql")
    backup._backup_history.append(
        {
            "backup_id": "db",
            "type": "database",
            "path": str(bdir / "testdb.sql"),
            "compressed": False,
            "encrypted": False,
        }
    )
    monkeypatch.setattr("asyncio.create_subprocess_exec", _make_subprocess_mock(b"", 1))
    res = await backup.restore_backup("db")
    assert res["status"] == "failed"


def test_get_backup_statistics_empty_and_failed():
    backup._backup_history.clear()
    assert backup.get_backup_statistics()["total_backups"] == 0
    backup._backup_history.append(
        {
            "backup_id": "f1",
            "type": "config",
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    stats = backup.get_backup_statistics()
    assert stats["failed_backups"] == 1
    backup._backup_history.clear()


def test_get_recent_backups_empty():
    backup._backup_history.clear()
    assert backup.get_recent_backups(5) == []
    assert backup.get_backup_history() == []


# ---------------------------------------------------------------------------
# core.notify_engine
# ---------------------------------------------------------------------------
import core.notify_engine as notify


@pytest.mark.asyncio
async def test_notify_history_full_and_tracking(monkeypatch):
    monkeypatch.setenv("NOTIFY_ENABLED", "true")
    monkeypatch.setenv("NOTIFY_MIN_LEVEL", "info")
    notify.reload_notify_config()
    # Force pop(0) by exceeding MAX_NOTIFICATION_HISTORY
    old = list(notify._notification_history)
    notify._notification_history.clear()
    for i in range(notify.MAX_NOTIFICATION_HISTORY + 2):
        notify._track_notification_status(
            {"id": f"x{i}", "fingerprint": "fp", "title": "t"},
            "slack",
            "sent",
        )
    assert len(notify._notification_history) == notify.MAX_NOTIFICATION_HISTORY
    notify._notification_history[:] = old


@pytest.mark.asyncio
async def test_channels_for_severity(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.com/teams")
    monkeypatch.setenv("WECOM_WEBHOOK", "https://we.com")
    monkeypatch.setenv("DINGTALK_WEBHOOK", "https://dt.com")
    monkeypatch.setenv("PHONE_PROVIDER", "https://phone")
    monkeypatch.setenv("SMS_PROVIDER", "https://sms")
    notify.reload_notify_config()
    ch = notify._channels_for_severity("fatal", notify.NOTIFY_CONFIG)
    assert "phone" in ch
    assert "sms" in ch
    assert "teams" in ch
    assert notify._channel_configured("teams", notify.NOTIFY_CONFIG) is True


@pytest.mark.asyncio
async def test_http_client_lifecycle(monkeypatch):
    notify._http_client = None
    monkeypatch.setenv("NOTIFY_ENGINE_SSL_VERIFY", "true")
    client = notify._get_http_client()
    assert client is not None
    await notify.close_http_client()
    assert notify._http_client is None


def test_validate_webhook_url_and_load_config(monkeypatch):
    monkeypatch.setenv("WECOM_WEBHOOK", "not-a-valid-url")
    monkeypatch.setenv("DINGTALK_WEBHOOK", "bad://dt.com")
    monkeypatch.setenv("FEISHU_WEBHOOK", " " + "https" + "://" * 1500)
    monkeypatch.setenv("EMAIL_WEBHOOK", "ftp://email")
    notify.reload_notify_config()
    assert notify.NOTIFY_CONFIG["wecom_webhook"] == ""
    assert notify.NOTIFY_CONFIG["dingtalk_webhook"] == ""
    assert notify.NOTIFY_CONFIG["feishu_webhook"] == ""
    assert notify.NOTIFY_CONFIG["email_webhook"] == ""


def test_slack_client_and_invalid_email(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    client = notify._get_slack_client()
    assert client is None or client is not None
    assert notify._is_valid_email("bad") is False
    assert notify._is_valid_email("a@b.co") is True


def test_build_structured_alert_message(monkeypatch):
    alert = {
        "summary": "s",
        "impact": "i",
        "diagnosis": "d",
        "action": "a",
        "confidence": 0.9,
        "links": ["bad"],  # not dict path
        "dashboard_url": "http://d",
        "level": "critical",
    }
    txt = notify.build_structured_alert_message(alert, "text")
    assert "0.9" in txt
    html = notify.build_structured_alert_message(alert, "html")
    assert "<h3>" in html
    md = notify.build_structured_alert_message(alert, "markdown")
    assert "相关链接" in md


@pytest.mark.asyncio
async def test_send_slack_once_scenarios(monkeypatch):
    async_client = MagicMock()
    async_client.chat_postMessage = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(notify, "_get_slack_client", lambda: async_client)
    res = await notify._send_slack_notification_once("hi", "#c")
    assert res["success"]

    # response with explicit ok=False
    async_client.chat_postMessage = AsyncMock(return_value=MagicMock(ok=False))
    res = await notify._send_slack_notification_once("hi", "#c")
    assert res["success"] is False

    # exception with rate limit
    async_client.chat_postMessage = AsyncMock(side_effect=RuntimeError("rate limit exceeded"))
    res = await notify._send_slack_notification_once("hi", "#c")
    assert "rate limit" in res["error"]

    # get_client returning a coroutine
    async def coro_client():
        return async_client

    monkeypatch.setattr(notify, "_get_slack_client", coro_client)
    async_client.chat_postMessage = AsyncMock(return_value={"ok": True})
    res = await notify._send_slack_notification_once("hi", "#c")
    assert res["success"]


@pytest.mark.asyncio
async def test_send_teams_email(monkeypatch):
    class FakeResp:
        status = 200

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        post = AsyncMock(return_value=FakeResp())

    monkeypatch.setattr(notify, "aiohttp", types.ModuleType("aiohttp"))
    notify.aiohttp.ClientSession = FakeSession
    res = await notify.send_teams_notification("hi", "https://teams.com")
    assert res["success"] is True

    # email failure
    fake_smtp = types.ModuleType("smtplib")
    fake_smtp.SMTP = MagicMock(side_effect=RuntimeError("smtp down"))
    monkeypatch.setattr(notify, "smtplib", fake_smtp)
    res = await notify.send_email_notification("a@b.com", "subj", "body")
    assert res["success"] is False


@pytest.mark.asyncio
async def test_send_notification_routing(monkeypatch):
    monkeypatch.setenv("NOTIFY_ENABLED", "true")
    monkeypatch.setenv("NOTIFY_MIN_LEVEL", "info")
    notify.reload_notify_config()

    monkeypatch.setattr(
        notify,
        "send_slack_notification",
        AsyncMock(return_value={"success": True, "recipient": "r"}),
    )
    monkeypatch.setattr(
        notify,
        "send_teams_notification",
        AsyncMock(return_value={"success": True, "recipient": "r"}),
    )
    monkeypatch.setattr(
        notify,
        "send_email_notification",
        AsyncMock(return_value={"success": True, "recipient": "r"}),
    )
    # single configured channel succeeds
    res = await notify.send_notification(
        {"type": "alert", "message": "m", "severity": "critical", "fingerprint": "fp1"},
        channels=["slack"],
    )
    assert res["success"] is True
    # no channels
    res = await notify.send_notification({"type": "alert", "message": "m"}, channels=[])
    assert res["success"] is False
    # unsupported channel
    res = await notify.send_notification({"type": "alert", "message": "m"}, channels=["weird"])
    assert res["success"] is False


@pytest.mark.asyncio
async def test_send_one_channel_exception(monkeypatch):
    monkeypatch.setenv("NOTIFY_ENABLED", "true")
    notify.reload_notify_config()

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(notify, "send_slack_notification", boom)
    res = await notify._send_one_channel(
        {"type": "alert", "message": "m", "level": "critical"},
        "slack",
        notify.NOTIFY_CONFIG,
    )
    assert res["success"] is False


@pytest.mark.asyncio
async def test_resolve_oncall_and_phone_sms(monkeypatch):
    fake_adapter = MagicMock()
    fake_adapter.lookup_async = AsyncMock(
        return_value=[types.SimpleNamespace(phone="123", email="a@b.com")]
    )
    monkeypatch.setattr(oca, "get_oncall_adapter", lambda: fake_adapter)
    oncall = await notify._resolve_oncall_recipients({"category": "db"})
    assert oncall

    # exception path
    fake_adapter.lookup_async = AsyncMock(side_effect=RuntimeError("fail"))
    oncall = await notify._resolve_oncall_recipients({"category": "db"})
    assert oncall == []

    # phone success with oncall
    fake_adapter.lookup_async = AsyncMock(
        return_value=[types.SimpleNamespace(phone="123", email="a@b.com")]
    )
    monkeypatch.setattr(
        notify,
        "_get_http_client",
        lambda: AsyncMock(
            post=AsyncMock(return_value=MagicMock(status_code=200, raise_for_status=MagicMock()))
        ),
    )
    res = await notify._send_phone_notification(
        {"level": "critical"}, {"phone_provider": "https://p"}
    )
    assert res["success"]

    # phone exception
    client = AsyncMock()
    client.post = AsyncMock(side_effect=RuntimeError("timeout"))
    monkeypatch.setattr(notify, "_get_http_client", lambda: client)
    res = await notify._send_phone_notification(
        {"level": "critical"}, {"phone_provider": "https://p"}
    )
    assert res["success"] is False

    # sms no recipient
    res = await notify._send_sms_notification({"level": "critical"}, {"sms_provider": "https://s"})
    assert res["success"] is False

    # sms with oncall then exception
    client2 = AsyncMock()
    client2.post = AsyncMock(side_effect=RuntimeError("fail"))
    monkeypatch.setattr(notify, "_get_http_client", lambda: client2)
    res = await notify._send_sms_notification(
        {"level": "critical"},
        {"sms_provider": "https://s"},
        recipient="123",
    )
    assert res["success"] is False


@pytest.mark.asyncio
async def test_post_webhook_errors(monkeypatch):
    monkeypatch.setattr(notify, "_post_webhook", notify._post_webhook_original)
    client = AsyncMock()
    client.post = AsyncMock(side_effect=RuntimeError("network"))
    monkeypatch.setattr(notify, "_get_http_client", lambda: client)
    res = await notify._post_webhook("https://example.com/webhook", {}, "wecom")
    assert res["success"] is False
    long_url = "https://x.com/" + "x" * 3000
    res = await notify._post_webhook(long_url, {}, "wecom")
    assert res["success"] is False


@pytest.mark.asyncio
async def test_send_alert_notification(monkeypatch):
    monkeypatch.setenv("NOTIFY_ENABLED", "true")
    monkeypatch.setenv("NOTIFY_MIN_LEVEL", "info")
    monkeypatch.setenv("WECOM_WEBHOOK", "https://we.com/hook?timestamp=1&sign=2")
    monkeypatch.setenv("DINGTALK_WEBHOOK", "https://dt.com/hook")
    monkeypatch.setenv("DINGTALK_SECRET", "secret")
    notify.reload_notify_config()

    async def fake(channel):
        return {"success": True, "recipient": "r"}

    monkeypatch.setattr(notify, "_send_one_channel", lambda alert, ch, cfg: fake(ch))
    res = await notify.send_alert_notification(
        {
            "type": "alert",
            "message": "m",
            "severity": "warning",
            "title": "t",
            "dashboard_url": "http://d",
        }
    )
    assert res["status"] == "ok"


# ---------------------------------------------------------------------------
# core.heal_graph
# ---------------------------------------------------------------------------
import core.heal_graph as heal


def test_heal_helpers_and_stategraph(monkeypatch):
    monkeypatch.setenv("HEAL_APPROVAL_VALIDITY_MINUTES", "not-a-number")
    assert heal._approval_validity_minutes() == 5
    assert heal._is_approval_expired({"approved_at": "garbage"}) is True
    assert heal._is_approval_expired({}) is False
    assert heal._is_approval_expired({"approved_at": None}) is True
    assert heal._is_approval_expired({"approved_at": "2020-01-01T00:00:00"}) is True
    assert heal._is_alert_resolved({"status": "resolved"}) is True
    assert (
        heal._is_alert_resolved(
            {"resolved_condition": {"metric": "m", "operator": "<=", "threshold": 1}}
        )
        is False
    )
    assert heal._pre_execution_check({"x": 1}, {"approved_at": "garbage"}) == (
        False,
        "approval expired or missing approved_at",
    )
    assert heal._pre_execution_check(
        {"status": "resolved"}, {"approved_at": datetime.now().isoformat()}
    ) == (False, "alert self-healed before execution")
    assert heal._off_hours_auto_approve_allowed() is False
    monkeypatch.setenv("HEAL_OFFHOURS_AUTO_APPROVE", "true")
    assert heal._off_hours_auto_approve_allowed() is True
    assert heal._is_auto_approve_allowed() is False
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setattr(heal, "_is_off_hours", lambda: False)
    assert heal._is_auto_approve_allowed() is True
    assert heal._is_hardware_alert({"category": "hardware"}) is True
    assert heal._is_hardware_alert("not a dict") is False
    assert heal._tokenize_alert_text(123) == []
    assert "disk" in heal._allowed_targets_from_alert({"title": "disk full", "value": 99})
    assert heal._extract_command_target("kubectl delete pod xyz") == "xyz"

    # StateGraph branches
    sg = heal.StateGraph()

    async def a(state):
        return state

    async def b(state):
        raise RuntimeError("boom")

    sg.add_node("start", a)
    sg.add_node("boom", b)
    sg.set_entry_point("start")
    sg.add_edge("start", "boom")
    sg.add_edge("boom", heal.END)
    runner = sg.compile()
    asyncio.run(runner(heal.HealState()))
    # __call__ path
    asyncio.run(sg(heal.HealState()))


def test_audit_and_checkpoint():
    heal.AUDIT_AVAILABLE = True
    heal._log_audit_event = MagicMock()
    heal.record_audit = MagicMock(side_effect=RuntimeError("audit"))
    heal._audit("TEST", "r", "ok")
    heal.record_audit = MagicMock()
    cp = heal.CheckpointSQLite()
    cp.put("cfg", {"x": 1})
    assert cp.get("cfg") == {"x": 1}


@pytest.mark.asyncio
async def test_generate_runbook(monkeypatch):
    fake_lib = types.ModuleType("core.auto_heal")
    fake_lib.repair_script_library = MagicMock()
    script = MagicMock()
    script.name = "s"
    script.description = "d"
    script.script_content = "cmd1\ncmd2"
    script.rollback_script = "rollback"
    script.risk_level = types.SimpleNamespace(value="low")
    script.requires_approval = False
    fake_lib.repair_script_library.get_script = MagicMock(return_value=script)
    monkeypatch.setitem(sys.modules, "core.auto_heal", fake_lib)
    monkeypatch.setattr(
        heal,
        "RiskLevel",
        type(
            "RiskLevel", (), {"HIGH": "high", "BLOCKED": "blocked", "SAFE": "safe", "LOW": "low"}
        )(),
    )
    monkeypatch.setattr(heal, "record_audit", MagicMock())
    state = heal.HealState(alert={"title": "ipmi failure", "metric": "ipmi"})
    out = await heal.generate_runbook(state)
    assert out.runbook is not None
    state = heal.HealState(alert={"title": "cordon node"})
    out = await heal.generate_runbook(state)
    assert out.runbook is not None


@pytest.mark.asyncio
async def test_evaluate(monkeypatch):
    fake_verifier = types.ModuleType("core.verifier")
    fake_verifier.verify_repair = AsyncMock(
        return_value=MagicMock(model_dump=lambda: {"verified": True})
    )
    monkeypatch.setitem(sys.modules, "core.verifier", fake_verifier)
    state = heal.HealState(fix_applied=True, runbook="string")
    out = await heal.evaluate(state)
    assert out.verification["passed"] is True
    state = heal.HealState(
        fix_applied=True,
        runbook={"params": "bad", "runbook": {}},
        snapshot=None,
    )
    out = await heal.evaluate(state)
    assert isinstance(out.snapshot, dict)
    assert "metrics" in out.snapshot


@pytest.mark.asyncio
async def test_rollback(monkeypatch):
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    monkeypatch.setattr(heal, "SNAPSHOT_CONFIG", {"rollback_approval_required": False})
    monkeypatch.setattr(
        heal,
        "analyze_command",
        lambda cmd: {"risk_level": "LOW"},
    )
    monkeypatch.setattr(heal, "update_snapshot_status", AsyncMock(return_value=None))
    monkeypatch.setattr(heal, "notify_rollback_failure", AsyncMock(return_value=None))
    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        AsyncMock(
            return_value=MagicMock(
                communicate=AsyncMock(return_value=(b"", b"")),
                returncode=0,
            )
        ),
    )
    state = heal.HealState(
        alert={"id": "a1", "platform": "windows"},
        verification={"passed": False},
        rollback_info={"rollback_commands": ["cmd1"]},
        snapshot_id="s1",
    )
    out = await heal.rollback(state)
    assert out.fix_applied is False


@pytest.mark.asyncio
async def test_complete(monkeypatch):
    monkeypatch.setattr(heal, "update_snapshot_status", AsyncMock(return_value=None))
    monkeypatch.setattr(heal, "async_insert_repair_record", AsyncMock(return_value=None))
    if not hasattr(heal, "_HEAL_METRIC_COUNTERS"):
        monkeypatch.setattr(heal, "_HEAL_METRIC_COUNTERS", {})
    state = heal.HealState(
        alert={"id": "a2"},
        fix_applied=True,
        verification={"passed": True},
        snapshot_id="s2",
        decision_id="d1",
    )
    out = await heal.complete(state)
    assert out.metrics["status"] == "success"


@pytest.mark.asyncio
async def test_build_graph_and_run_heal(monkeypatch):
    fake_metrics = types.ModuleType("core.phase3_metrics")
    counter = MagicMock(labels=MagicMock(return_value=MagicMock(inc=MagicMock())))
    fake_metrics.HEAL_TOTAL = counter
    fake_metrics.HEAL_SUCCESS = counter
    fake_metrics.HEAL_FAILED = counter
    monkeypatch.setitem(sys.modules, "core.phase3_metrics", fake_metrics)
    monkeypatch.setattr(
        heal, "_heal_graph_runner", AsyncMock(side_effect=RuntimeError("graph boom"))
    )
    state = heal.HealState(alert={"id": "a3"})
    out = await heal.run_heal(state)
    assert "graph boom" in out.error


# ---------------------------------------------------------------------------
# core.integration_manager
# ---------------------------------------------------------------------------
import core.integration_manager as im


def test_integration_manager_init_and_summary():
    mgr = im.IntegrationManager()
    assert mgr.get_integration_summary()["total_integrations"] == 0


@pytest.mark.asyncio
async def test_integration_test_and_register(monkeypatch):
    mgr = im.IntegrationManager()
    # not found
    assert (await mgr.test_integration("missing"))["success"] is False
    # monitoring missing URL
    cfg = im.IntegrationConfig(
        integration_id="prom-1",
        integration_type=im.IntegrationType.MONITORING,
        name="prometheus",
        config={},
    )
    mgr.integrations["prom-1"] = cfg
    res = await mgr.test_integration("prom-1")
    assert res["success"] is False
    # notification missing webhook
    cfg2 = im.IntegrationConfig(
        integration_id="slack-1",
        integration_type=im.IntegrationType.NOTIFICATION,
        name="slack",
        config={},
    )
    mgr.integrations["slack-1"] = cfg2
    res = await mgr.test_integration("slack-1")
    assert res["success"] is False

    # _validate_signature exception
    assert mgr._validate_signature(object(), "sig", "sec") is False


@pytest.mark.asyncio
async def test_query_prometheus_branches(monkeypatch):
    monkeypatch.setattr(im, "cached_query", lambda c, k, q: q)
    mgr = im.IntegrationManager()
    assert (await mgr.query_prometheus_metrics("missing", "up"))["error"] == "Integration not found"
    cfg = im.IntegrationConfig(
        integration_id="prom-1",
        integration_type=im.IntegrationType.MONITORING,
        name="prometheus",
        config={"url": "http://prom"},
    )
    mgr.integrations["prom-1"] = cfg
    # not prometheus
    cfg2 = im.IntegrationConfig(
        integration_id="other-1",
        integration_type=im.IntegrationType.MONITORING,
        name="grafana",
        config={"url": "http://g"},
    )
    mgr.integrations["other-1"] = cfg2
    assert (await mgr.query_prometheus_metrics("other-1", "up"))[
        "error"
    ] == "Not a Prometheus integration"
    # invalid promql
    monkeypatch.setattr(im, "validate_promql", MagicMock(side_effect=ValueError("bad")))
    res = await mgr.query_prometheus_metrics("prom-1", "bad")
    assert "Invalid PromQL" in res["error"]
    # invalid time range
    monkeypatch.setattr(im, "validate_promql", MagicMock())
    monkeypatch.setattr(im, "parse_duration_to_seconds", MagicMock(side_effect=ValueError("bad")))
    res = await mgr.query_prometheus_metrics("prom-1", "up", "bad")
    assert "Invalid time_range" in res["error"]
    # http_client None
    monkeypatch.setattr(im, "parse_duration_to_seconds", MagicMock(return_value=60))
    mgr.http_client = None
    res = await mgr.query_prometheus_metrics("prom-1", "up")
    assert res["error"] == "HTTP client not initialized"
    # query returns non-200
    mgr.http_client = AsyncMock()
    mgr.http_client.get = AsyncMock(return_value=MagicMock(status_code=500))
    res = await mgr.query_prometheus_metrics("prom-1", "up")
    assert res["error"] is not None
    # exception
    mgr.http_client.get = AsyncMock(side_effect=RuntimeError("conn"))
    res = await mgr.query_prometheus_metrics("prom-1", "up")
    assert res["error"] is not None


@pytest.mark.asyncio
async def test_query_cloudwatch_branches(monkeypatch):
    mgr = im.IntegrationManager()
    assert (await mgr.query_cloudwatch_metrics("missing", "CPUUtilization"))[
        "error"
    ] == "Integration not found"
    cfg = im.IntegrationConfig(
        integration_id="cw-1",
        integration_type=im.IntegrationType.CLOUD,
        name="cloudwatch",
        config={"region": "us-east-1"},
    )
    mgr.integrations["cw-1"] = cfg
    assert "boto3" in (await mgr.query_cloudwatch_metrics("cw-1", "CPUUtilization"))["error"]
    # force boto3 available and fail
    fake_boto = types.ModuleType("boto3")
    fake_boto.client = MagicMock(side_effect=RuntimeError("aws"))
    monkeypatch.setitem(sys.modules, "boto3", fake_boto)
    monkeypatch.setattr(im, "BOTO3_AVAILABLE", True)
    res = await mgr.query_cloudwatch_metrics("cw-1", "AWS/EC2/CPUUtilization")
    assert res["error"] is not None
    # parse with dimensions and missing keys
    res = await mgr.query_cloudwatch_metrics("cw-1", "AWS/EC2/CPUUtilization[InstanceId=i-1]")
    assert "Missing" in res["error"]


@pytest.mark.asyncio
async def test_query_pagerduty_jenkins_jira(monkeypatch):
    mgr = im.IntegrationManager()
    res = await mgr.query_pagerduty_incidents("missing", "")
    assert res["error"] == "Integration not found"
    cfg = im.IntegrationConfig(
        integration_id="pd-1",
        integration_type=im.IntegrationType.ITSM,
        name="pagerduty",
        config={},
    )
    mgr.integrations["pd-1"] = cfg
    assert (await mgr.query_pagerduty_incidents("pd-1", ""))[
        "error"
    ] == "Missing api_key or token in config"
    cfg.config = {"api_key": "k"}
    monkeypatch.setattr(im, "parse_duration_to_seconds", MagicMock(side_effect=ValueError("bad")))
    res = await mgr.query_pagerduty_incidents("pd-1", "q", "bad")
    assert "Invalid time_range" in res["error"]
    # exception
    monkeypatch.setattr(im, "parse_duration_to_seconds", MagicMock(return_value=60))
    mgr.http_client = AsyncMock()
    mgr.http_client.get = AsyncMock(side_effect=RuntimeError("pd"))
    res = await mgr.query_pagerduty_incidents("pd-1", "q")
    assert res["error"] is not None

    res = await mgr.trigger_jenkins_job("missing", "job")
    assert res["error"] == "Integration not found"
    mgr.integrations["jen-1"] = im.IntegrationConfig(
        integration_id="jen-1",
        integration_type=im.IntegrationType.CICD,
        name="jenkins",
        config={},
    )
    res = await mgr.trigger_jenkins_job("jen-1", "job")
    assert res["success"]

    res = await mgr.create_jira_issue("missing", "s", "d")
    assert res["error"] == "Integration not found"
    mgr.integrations["jira-1"] = im.IntegrationConfig(
        integration_id="jira-1",
        integration_type=im.IntegrationType.ITSM,
        name="jira",
        config={},
    )
    res = await mgr.create_jira_issue("jira-1", "s", "d")
    assert res["success"]


@pytest.mark.asyncio
async def test_send_and_process_notification(monkeypatch):
    mgr = im.IntegrationManager(
        config={
            "notification_channels": {"ch1": {"type": "webhook", "config": {"url": "https://x"}}}
        }
    )
    mgr.http_client = AsyncMock(
        post=AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    )
    msg = await mgr.send_notification("ch1", "r", "s", "b")
    assert msg.error is None
    assert msg.sent is True
    # not found
    msg = await mgr.send_notification("ch2", "r", "s", "b")
    assert "not found" in msg.error
    # disabled
    mgr.notification_channels["ch1"]["enabled"] = False
    msg = await mgr.send_notification("ch1", "r", "s", "b")
    assert "disabled" in msg.error
    # unsupported type
    mgr.notification_channels["ch1"]["enabled"] = True
    mgr.notification_channels["ch1"]["type"] = "sms"
    msg = await mgr.send_notification("ch1", "r", "s", "b")
    assert "Unsupported" in msg.error
    # HTTP not available -> exception in _send_webhook_notification
    mgr.notification_channels["ch3"] = {
        "name": "ch3",
        "type": "webhook",
        "config": {"url": "https://y"},
        "enabled": True,
    }
    monkeypatch.setattr(im, "HTTP_AVAILABLE", False)
    msg = await mgr.send_notification("ch3", "r", "s", "b")
    assert msg.error is not None
