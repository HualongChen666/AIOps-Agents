# -*- coding: utf-8 -*-
"""
中危台账批次 18 回归测试（2026-09-16）
=====================================

覆盖条目：
- F096 core/causal/algorithms.py        PC 算法骨架条件独立检验 + v-structure/Meek 定向
- F158 core/enhanced_auth_integration.py require_permission 真实鉴权（fail-closed）
- F164 core/enterprise_functionality.py  ISO27001 合规结论随加密级别真实判定
- F216 core/infrastructure_repository.py health_check 对存储端点做真实连通性探测
- F338 core/plugin_marketplace.py        插件签名 verified 仅在验证通过后置真 / 真非对称签名
"""

import socket
import threading

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.causal.algorithms import PCAlgorithm
from core.database import Base
from core.enhanced_auth_integration import (
    EnhancedAuthIntegration,
    Permission,
    Role,
    User,
)
from core.enterprise_functionality import (
    ComplianceStandard,
    EnterpriseFunctionalityManager,
    EncryptionLevel,
)
from core.infrastructure_repository import InfrastructureStorageRepository
from core.plugin_marketplace import PluginMarketplace


def _run(coro):
    import asyncio

    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# F096 — PC algorithm: conditional independence + orientation
# ---------------------------------------------------------------------------
def _chain_data(n=4000, seed=7):
    rng = np.random.default_rng(seed)
    a = rng.standard_normal(n)
    c = a + 0.2 * rng.standard_normal(n)  # a -> c
    b = c + 0.2 * rng.standard_normal(n)  # c -> b
    return np.column_stack([a, b, c])


def test_pc_conditional_independence_removes_mediated_edge():
    data = _chain_data()
    pc = PCAlgorithm(alpha=0.05)
    # a(0) 与 b(1) 边际相关但给定中介 c(2) 后近似独立
    marginal = pc._test_independence(data, 0, 1, set())
    conditional = pc._test_independence(data, 0, 1, {2})
    assert marginal.independent is False
    assert conditional.independent is True
    assert isinstance(conditional.p_value, float)
    assert conditional.p_value > 0.05

    graph = pc.discover(data, ["a", "b", "c"])
    edges = {(e.from_var, e.to_var) for e in graph.edges}
    # 中介结构不应产生 a<->b 直接边
    assert ("a", "b") not in edges and ("b", "a") not in edges
    assert len(graph.edges) == 2


def test_pc_orient_v_structure():
    rng = np.random.default_rng(11)
    n = 4000
    a = rng.standard_normal(n)
    b = rng.standard_normal(n)
    k = a + b + 0.1 * rng.standard_normal(n)  # a -> k <- b (v-structure)
    data = np.column_stack([a, b, k])
    pc = PCAlgorithm(alpha=0.05)
    graph = pc.discover(data, ["a", "b", "k"])
    edges = {(e.from_var, e.to_var) for e in graph.edges}
    # v-structure 必须被定向为 a->k 与 b->k
    assert ("a", "k") in edges
    assert ("b", "k") in edges
    assert ("k", "a") not in edges and ("k", "b") not in edges


# ---------------------------------------------------------------------------
# F158 — require_permission real enforcement
# ---------------------------------------------------------------------------
def test_require_permission_denies_without_user():
    auth = EnhancedAuthIntegration(config={"jwt_secret": "test-secret"})

    @auth.require_permission(Permission.READ, "metrics")
    def endpoint(*args, **kwargs):
        return "ok"

    with pytest.raises(PermissionError):
        endpoint()


def test_require_permission_allows_with_permission():
    auth = EnhancedAuthIntegration(config={"jwt_secret": "test-secret"})
    user = User(
        user_id="u1",
        username="u1",
        email="u1@example.com",
        roles={Role.OPERATOR},
        permissions={Permission.READ},
    )

    @auth.require_permission(Permission.READ, "metrics")
    def endpoint(user=None):
        return "ok"

    assert endpoint(user=user) == "ok"


def test_require_permission_denies_insufficient_permission():
    auth = EnhancedAuthIntegration(config={"jwt_secret": "test-secret"})
    user = User(
        user_id="u2",
        username="u2",
        email="u2@example.com",
        roles={Role.VIEWER},
        permissions={Permission.READ},
    )

    @auth.require_permission(Permission.DELETE, "alerts")
    def endpoint(user=None):
        return "ok"

    with pytest.raises(PermissionError):
        endpoint(user=user)


def test_require_permission_async_wrapper():
    auth = EnhancedAuthIntegration(config={"jwt_secret": "test-secret"})
    user = User(
        user_id="u3",
        username="u3",
        email="u3@example.com",
        roles=set(),
        permissions={Permission.EXECUTE},
    )

    @auth.require_permission(Permission.EXECUTE, "repairs")
    async def endpoint(user=None):
        return "done"

    assert _run(endpoint(user=user)) == "done"
    with pytest.raises(PermissionError):
        _run(endpoint())


# ---------------------------------------------------------------------------
# F164 — ISO27001 compliance reflects real encryption state
# ---------------------------------------------------------------------------
def test_iso27001_fails_below_high_encryption():
    mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_level": "standard"}
    )
    result = _run(mgr.run_compliance_check(ComplianceStandard.ISO27001))
    assert result.passed is False
    assert any("below recommended high" in f for f in result.findings)


def test_iso27001_passes_at_high_encryption():
    mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_level": "high"}
    )
    result = _run(mgr.run_compliance_check(ComplianceStandard.ISO27001))
    assert result.passed is True


def test_iso27001_fails_when_encryption_disabled():
    mgr = EnterpriseFunctionalityManager(config={"encryption_enabled": False})
    result = _run(mgr.run_compliance_check(ComplianceStandard.ISO27001))
    assert result.passed is False
    assert any("not enabled" in f for f in result.findings)


# ---------------------------------------------------------------------------
# F216 — infrastructure storage health_check real probe
# ---------------------------------------------------------------------------
@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _closed_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_storage_health_check_unreachable(in_memory_db):
    repo = InfrastructureStorageRepository(in_memory_db)
    port = _closed_port()
    storage = repo.create_storage(
        storage_type="redis",
        endpoint=f"127.0.0.1:{port}",
        bucket_name="b",
        access_key="k",
        secret_key="s",
    )
    result = repo.health_check(storage.id)
    assert result["reachable"] is False
    assert result["status"] == "unhealthy"
    # 状态被真实持久化
    assert repo.get_storage_by_id(storage.id).health_status == "unhealthy"


def test_storage_health_check_reachable(in_memory_db):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    stop = threading.Event()

    def _accept_loop():
        server.settimeout(0.5)
        while not stop.is_set():
            try:
                conn, _ = server.accept()
                conn.close()
            except socket.timeout:
                continue
            except OSError:
                break

    thread = threading.Thread(target=_accept_loop, daemon=True)
    thread.start()
    try:
        repo = InfrastructureStorageRepository(in_memory_db)
        storage = repo.create_storage(
            storage_type="redis",
            endpoint=f"127.0.0.1:{port}",
            bucket_name="b",
            access_key="k",
            secret_key="s",
        )
        result = repo.health_check(storage.id)
        assert result["reachable"] is True
        assert result["status"] == "healthy"
        assert repo.get_storage_by_id(storage.id).health_status == "healthy"
    finally:
        stop.set()
        server.close()
        thread.join(timeout=2)


def test_storage_health_check_missing(in_memory_db):
    repo = InfrastructureStorageRepository(in_memory_db)
    assert repo.health_check("nope")["status"] == "error"


# ---------------------------------------------------------------------------
# F338 — plugin signature: verified only after verification; real asymmetric
# ---------------------------------------------------------------------------
def test_signature_not_verified_at_signing_symmetric():
    m = PluginMarketplace(config={"private_key": "secret-key", "public_key": "pk"})
    p = m.register_plugin(
        name="x", version="1.0.0", description="", author="a",
        download_url="u", package_data=b"data",
    )
    assert p.signature.verified is False
    assert p.signature.algorithm == "HMAC-SHA256"
    # 对称签名不伪造公钥
    assert p.signature.public_key == ""
    assert m.verify_plugin(p.id, b"data") is True
    assert p.signature.verified is True
    assert m.verify_plugin(p.id, b"tampered") is False


def test_signature_asymmetric_independent_verification():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    key = ed25519.Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    signer = PluginMarketplace(config={"private_key": pem})
    p = signer.register_plugin(
        name="p", version="1.0.0", description="", author="a",
        download_url="u", package_data=b"pkg",
    )
    assert p.signature.verified is False
    assert p.signature.algorithm == "Ed25519"
    assert p.signature.public_key.startswith("-----BEGIN PUBLIC KEY")

    # 独立验证方：只有公钥，无私钥
    verifier = PluginMarketplace(config={})
    verifier._plugins[p.id] = p
    assert verifier.verify_plugin(p.id, b"pkg") is True
    assert p.signature.verified is True

    # 篡改包体：校验和不匹配 → 拒绝，且不置 verified
    p.signature.verified = False
    assert verifier.verify_plugin(p.id, b"other") is False
    assert p.signature.verified is False


def test_unverified_signature_blocks_approval():
    m = PluginMarketplace(config={"private_key": "k"})
    p = m.register_plugin(
        name="q", version="1.0.0", description="", author="a",
        download_url="u", package_data=b"z",
    )
    assert m.approve_plugin(p.id) is False
    assert m.verify_plugin(p.id, b"z") is True
    assert m.approve_plugin(p.id) is True
