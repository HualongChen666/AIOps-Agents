# -*- coding: utf-8 -*-
"""Tests for the real X.509 certificate material generator."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

from core import certificate_manager as cm


def test_generate_rsa_self_signed_is_a_real_parseable_certificate():
    material = cm.generate_self_signed_certificate("example.com", "RSA")
    cert = x509.load_pem_x509_certificate(material["certificate_pem"].encode())

    cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
    assert cn == "example.com"
    # self-signed -> issuer == subject
    assert cert.issuer == cert.subject
    assert material["issuer"] == cert.subject.rfc4514_string()
    assert material["serial_number"] == str(cert.serial_number)
    assert material["fingerprint_sha256"] == cert.fingerprint(hashes.SHA256()).hex()

    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "example.com" in [n.value for n in san]


def test_subject_alternative_name_accepts_ip_addresses():
    material = cm.generate_self_signed_certificate("10.0.0.5", "RSA")
    cert = x509.load_pem_x509_certificate(material["certificate_pem"].encode())
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert str(san.get_values_for_type(x509.IPAddress)[0]) == "10.0.0.5"


def test_validity_window_matches_requested_days():
    material = cm.generate_self_signed_certificate("a.example.com", "RSA", validity_days=30)
    now = datetime.now(timezone.utc)
    assert timedelta(days=29) < (material["expires_at"] - now) < timedelta(days=31)
    assert material["issued_at"] <= now


def test_private_key_pem_round_trips():
    material = cm.generate_self_signed_certificate("key.example.com", "RSA")
    key = serialization.load_pem_private_key(
        material["private_key_pem"], password=None
    )
    assert key.key_size == 2048


@pytest.mark.parametrize("algorithm", ["RSA", "ECDSA", "Ed25519"])
def test_all_supported_algorithms_produce_valid_certificates(algorithm):
    material = cm.generate_self_signed_certificate("multi.example.com", algorithm)
    cert = x509.load_pem_x509_certificate(material["certificate_pem"].encode())
    assert cert.public_key() is not None


def test_seal_and_unseal_private_key_round_trip(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "unit-test-secret")
    material = cm.generate_self_signed_certificate("seal.example.com", "RSA")
    sealed = cm.seal_private_key(material["private_key_pem"])
    assert sealed["ciphertext"] != material["private_key_pem"].hex()

    restored = cm.unseal_private_key(sealed["ciphertext"], sealed["iv"])
    assert restored == material["private_key_pem"]

    # a wrong key must fail the GCM authentication
    with pytest.raises(cm.CertificateError):
        cm.unseal_private_key(sealed["ciphertext"], sealed["iv"], key=b"\x00" * 32)


def test_no_placeholder_literal_in_emitted_material():
    material = cm.generate_self_signed_certificate("real.example.com", "RSA")
    assert "PLACEHOLDER" not in material["certificate_pem"]
    assert b"placeholder_private_key" not in material["private_key_pem"]
    assert "BEGIN CERTIFICATE" in material["certificate_pem"]
    assert "BEGIN PRIVATE KEY" in material["private_key_pem"].decode()


def test_invalid_algorithm_rejected():
    with pytest.raises(cm.CertificateError):
        cm.generate_self_signed_certificate("x.example.com", "3DES")


def test_empty_domain_rejected():
    with pytest.raises(cm.CertificateError):
        cm.generate_self_signed_certificate("   ", "RSA")


def test_invalid_validity_rejected():
    with pytest.raises(cm.CertificateError):
        cm.generate_self_signed_certificate("x.example.com", "RSA", validity_days=0)


def test_seal_rejects_empty_input():
    with pytest.raises(cm.CertificateError):
        cm.seal_private_key(b"")
