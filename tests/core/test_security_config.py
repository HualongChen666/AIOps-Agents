# -*- coding: utf-8 -*-
"""Tests for core/security_config.py."""

from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from core.security_config import SecurityConfig, setup_enterprise_security


def _make_self_signed(tmp_path):
    import os
    import stat

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    # Set restrictive permissions: 600 for private key, 644 for certificate
    try:
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
        os.chmod(cert_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 644
    except (OSError, AttributeError):
        # chmod may fail on Windows or non-Unix systems
        pass
    return str(cert_path), str(key_path)


def test_security_status():
    config = SecurityConfig()
    status = config.get_security_status()
    assert "tls_enabled" in status
    assert "mfa_enabled" in status
    assert "rate_limiting_enabled" in status


def test_enable_disable():
    config = SecurityConfig()
    config.enable_mfa()
    assert config.config["mfa_enabled"] is True
    config.disable_mfa()
    assert config.config["mfa_enabled"] is False

    config.enable_rate_limiting(max_requests=10, time_window=30)
    assert config.config["rate_limiting_enabled"] is True
    config.disable_rate_limiting()
    assert config.config["rate_limiting_enabled"] is False


def test_enable_and_validate_tls(tmp_path):
    cert_path, key_path = _make_self_signed(tmp_path)
    config = SecurityConfig()
    config.enable_tls(cert_path, key_path)
    result = config.validate_tls_certificates()  # noqa: F841  # Variable for test verification
    assert "valid" in result
    assert "reason" in result


def test_setup_enterprise_security():
    result = setup_enterprise_security()  # noqa: F841  # Variable for test verification
    assert "security_status" in result
