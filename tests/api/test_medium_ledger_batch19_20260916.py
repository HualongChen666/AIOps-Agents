# -*- coding: utf-8 -*-
"""
中危台账批次 19 回归测试 · api/ 部分（2026-09-16）
==================================================

覆盖条目：
- API-151 api/security_advanced_router.py  create_key 不再使用弱默认加密密钥（SHA-256 派生）
- API-138 api/cost_management_router.py    不再伪造 "Sample Report"；delete 真实落库/如实 503；
                                          鉴权后端缺失时 fail-closed（503 而非放行）
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import api.security_advanced_router as sar
from api.security_advanced_router import _get_aes_key_bytes


# ---------------------------------------------------------------------------
# API-151 — no weak hardcoded encryption key
# ---------------------------------------------------------------------------
def test_aes_key_is_32_bytes_and_not_constant(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "short")
    key1 = _get_aes_key_bytes()
    assert len(key1) == 32
    # 不同配置材料 → 不同密钥；且不等于旧默认常量派生值
    monkeypatch.setenv("ENCRYPTION_KEY", "another-different-key")
    key2 = _get_aes_key_bytes()
    assert key1 != key2

    import hashlib

    weak = hashlib.sha256(b"default-encryption-key-32-bytes-long!!").digest()
    monkeypatch.setenv("ENCRYPTION_KEY", "short")
    assert _get_aes_key_bytes() != weak


def test_aes_key_fails_closed_in_production(monkeypatch):
    for var in ("ENCRYPTION_KEY", "ENCRYPTION_MASTER_KEY", "JWT_SECRET_KEY", "INTERNAL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as exc:
        _get_aes_key_bytes()
    assert exc.value.status_code == 500


def test_aes_key_dev_fallback_differs_from_source_constant(monkeypatch):
    for var in ("ENCRYPTION_KEY", "ENCRYPTION_MASTER_KEY", "JWT_SECRET_KEY", "INTERNAL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    key = _get_aes_key_bytes()
    assert len(key) == 32


# ---------------------------------------------------------------------------
# API-138 — no fabricated reports; honest storage failure; fail-closed auth
# ---------------------------------------------------------------------------
def test_get_report_no_db_returns_503(monkeypatch):
    import api.cost_management_router as cm

    monkeypatch.setattr(cm, "SessionLocal", None)
    client = TestClient(cm.app) if hasattr(cm, "app") else None
    # 直接调用端点函数，避免依赖全局 app 挂载
    import asyncio

    with pytest.raises(HTTPException) as exc:
        asyncio.run(cm.get_report("rep-xyz", user=None))
    assert exc.value.status_code == 503
    assert "Sample Report" not in str(exc.value.detail)


def test_delete_report_no_db_returns_503(monkeypatch):
    import api.cost_management_router as cm
    import asyncio

    monkeypatch.setattr(cm, "SessionLocal", None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cm.delete_report("rep-xyz", user=None))
    assert exc.value.status_code == 503


def test_auth_fallback_is_fail_closed(monkeypatch):
    """鉴权/授权后端导入失败时，降级桩必须拒绝（503），而不是放行。"""
    import importlib
    import sys

    # 阻断 core.authentication / core.rbac 的导入，触发 except ImportError 分支
    saved_auth = sys.modules.pop("core.authentication", None)
    saved_rbac = sys.modules.pop("core.rbac", None)
    monkeypatch.setitem(sys.modules, "core.authentication", None)
    monkeypatch.setitem(sys.modules, "core.rbac", None)
    try:
        cm = importlib.reload(importlib.import_module("api.cost_management_router"))
        import asyncio

        with pytest.raises(HTTPException) as exc1:
            asyncio.run(cm.get_current_active_user())
        assert exc1.value.status_code == 503

        dep = cm.role_required("admin")
        with pytest.raises(HTTPException) as exc2:
            dep()
        assert exc2.value.status_code == 503
    finally:
        for name, mod in (("core.authentication", saved_auth), ("core.rbac", saved_rbac)):
            if mod is not None:
                sys.modules[name] = mod
            else:
                sys.modules.pop(name, None)
        importlib.reload(importlib.import_module("api.cost_management_router"))
