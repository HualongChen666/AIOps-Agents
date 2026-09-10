# -*- coding: utf-8 -*-
"""End-to-end test for the HTTPS certificate endpoint with a real SQLite DB.

Verifies the endpoint now issues a genuine, parseable X.509 certificate and
seals a real private key (regression guard for the old PLACEHOLDER body).
"""

from __future__ import annotations

import pytest
from cryptography import x509
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.security_advanced_router import router
from core.certificate_manager import unseal_private_key
from core.database import get_db
from core.models import HttpsCertificate


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "e2e-test-secret")


@pytest.fixture
def client(env):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    HttpsCertificate.__table__.create(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    app.state.testing_session = TestingSession
    return TestClient(app)


def _stored_certificate(client) -> HttpsCertificate:
    db = client.app.state.testing_session()
    try:
        return db.query(HttpsCertificate).order_by(HttpsCertificate.created_at.desc()).first()
    finally:
        db.close()


def test_create_certificate_issues_real_x509(client):
    resp = client.post(
        "/api/v1/security/https/certificates",
        json={"domain": "example.com", "algorithm": "RSA"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["domain"] == "example.com"
    assert data["issuer"]

    row = _stored_certificate(client)
    assert row is not None
    assert "PLACEHOLDER" not in row.certificate_pem

    cert = x509.load_pem_x509_certificate(row.certificate_pem.encode())
    cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
    assert cn == "example.com"
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "example.com" in [n.value for n in san]

    # the private key must be a real, sealed PKCS#8 key (not a placeholder blob)
    key_pem = unseal_private_key(row.private_key_encrypted, row.private_key_iv)
    assert b"BEGIN PRIVATE KEY" in key_pem
    assert b"placeholder_private_key" not in key_pem


def test_create_certificate_rejects_unsupported_algorithm(client):
    resp = client.post(
        "/api/v1/security/https/certificates",
        json={"domain": "example.com", "algorithm": "3DES"},
    )
    assert resp.status_code == 400, resp.text
