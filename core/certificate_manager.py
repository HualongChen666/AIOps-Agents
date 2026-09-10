# -*- coding: utf-8 -*-
"""Real X.509 certificate material for the HTTPS certificate endpoints.

This module owns the full cryptographic lifecycle used by
``api/security_advanced_router`` for HTTPS certificates:

* key-pair generation (RSA / ECDSA / Ed25519),
* self-signed X.509 issuance with proper SAN + extensions,
* PEM serialisation,
* authenticated (AES-256-GCM) sealing of the private key for at-rest storage.

It replaces the previous placeholder implementation that emitted a literal
``"PLACEHOLDER CERTIFICATE FOR <domain>"`` body and a bogus private key.
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

logger = logging.getLogger(__name__)

#: Algorithms accepted by :func:`generate_self_signed_certificate`.
SUPPORTED_ALGORITHMS = ("RSA", "ECDSA", "Ed25519")

#: Default key sizes per algorithm (bits) when the caller does not specify one.
_DEFAULT_KEY_SIZES = {"RSA": 2048, "ECDSA": 256}

#: Development-only fallback encryption key. Using this in production is
#: insecure; a warning is emitted whenever it is used.
_DEV_FALLBACK_KEY = "aiops-dev-insecure-default-key"


class CertificateError(ValueError):
    """Raised when certificate parameters are invalid."""


def _dev_warning(key_source: str) -> None:
    logger.warning(
        "[certificate_manager] Using insecure development encryption key (%s). "
        "Set ENCRYPTION_KEY (or JWT_SECRET_KEY) in production.",
        key_source,
    )


def derive_encryption_key() -> bytes:
    """Return the 32-byte AES key used to seal private keys.

    Resolution order: ``ENCRYPTION_KEY`` -> ``JWT_SECRET_KEY`` -> a
    documented development fallback. The raw key material is hashed with
    SHA-256 so that any input length yields a valid AES-256 key.
    """
    material = os.getenv("ENCRYPTION_KEY", "").strip()
    if material:
        return hashlib.sha256(material.encode("utf-8")).digest()

    material = os.getenv("JWT_SECRET_KEY", "").strip()
    if material:
        return hashlib.sha256(material.encode("utf-8")).digest()

    _dev_warning("ENCRYPTION_KEY not set")
    return hashlib.sha256(_DEV_FALLBACK_KEY.encode("utf-8")).digest()


def seal_private_key(private_key_pem: bytes, key: Optional[bytes] = None) -> Dict[str, str]:
    """Encrypt *private_key_pem* with AES-256-GCM.

    Returns a dict with the ciphertext (``ciphertext``, hex — GCM tag
    appended) and the 96-bit nonce (``iv``, hex). These map directly onto the
    ``private_key_encrypted`` / ``private_key_iv`` columns.
    """
    if not private_key_pem:
        raise CertificateError("private_key_pem must not be empty")
    aes_key = key or derive_encryption_key()
    nonce = os.urandom(12)
    ciphertext = AESGCM(aes_key).encrypt(nonce, private_key_pem, None)
    return {"ciphertext": ciphertext.hex(), "iv": nonce.hex()}


def unseal_private_key(ciphertext_hex: str, iv_hex: str, key: Optional[bytes] = None) -> bytes:
    """Decrypt a private key sealed by :func:`seal_private_key`."""
    aes_key = key or derive_encryption_key()
    try:
        return AESGCM(aes_key).decrypt(bytes.fromhex(iv_hex), bytes.fromhex(ciphertext_hex), None)
    except Exception as exc:  # noqa: BLE001 - surfaced as a domain error
        raise CertificateError(f"failed to unseal private key: {exc}") from exc


def _generate_private_key(algorithm: str, key_size: Optional[int]):
    normalized = (algorithm or "RSA").upper()
    if normalized not in {a.upper() for a in SUPPORTED_ALGORITHMS}:
        raise CertificateError(
            f"unsupported algorithm {algorithm!r}; expected one of {SUPPORTED_ALGORITHMS}"
        )
    if normalized == "RSA":
        size = key_size or _DEFAULT_KEY_SIZES["RSA"]
        if size not in (2048, 3072, 4096, 8192):
            raise CertificateError(f"invalid RSA key size: {size}")
        return rsa.generate_private_key(public_exponent=65537, key_size=size)
    if normalized == "ECDSA":
        size = key_size or _DEFAULT_KEY_SIZES["ECDSA"]
        curves = {256: ec.SECP256R1, 384: ec.SECP384R1, 521: ec.SECP521R1}
        if size not in curves:
            raise CertificateError(f"invalid ECDSA curve size: {size}")
        return ec.generate_private_key(curves[size]())
    return ed25519.Ed25519PrivateKey.generate()


def _sign_key(private_key, builder: x509.CertificateBuilder) -> x509.Certificate:
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        return builder.sign(private_key, None)
    return builder.sign(private_key, hashes.SHA256())


def generate_self_signed_certificate(
    domain: str,
    algorithm: str = "RSA",
    *,
    key_size: Optional[int] = None,
    validity_days: int = 365,
    organization: str = "AIOps",
    common_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a real self-signed X.509 certificate for *domain*.

    Returns a dict containing ``certificate_pem``, ``private_key_pem``,
    ``issuer``, ``serial_number``, ``fingerprint_sha256``, ``issued_at`` and
    ``expires_at`` (both timezone-aware datetimes).
    """
    if not domain or not domain.strip():
        raise CertificateError("domain must not be empty")
    if validity_days <= 0 or validity_days > 3650:
        raise CertificateError("validity_days must be within 1..3650")

    domain = domain.strip()
    cn = common_name or domain
    private_key = _generate_private_key(algorithm, key_size)
    public_key = private_key.public_key()

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        ]
    )

    # SAN: accept DNS names and IP addresses transparently.
    san_entries: list = []
    try:
        import ipaddress

        san_entries.append(x509.IPAddress(ipaddress.ip_address(domain)))
    except ValueError:
        san_entries.append(x509.DNSName(domain))

    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=not isinstance(private_key, ec.EllipticCurvePrivateKey),
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False,
        )
    )

    certificate = _sign_key(private_key, builder)

    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()

    logger.info("Issued self-signed certificate for %s (%s)", domain, algorithm)

    return {
        "certificate_pem": cert_pem,
        "private_key_pem": key_pem,
        "issuer": subject.rfc4514_string(),
        "serial_number": str(certificate.serial_number),
        "fingerprint_sha256": fingerprint,
        "issued_at": now,
        "expires_at": now + timedelta(days=validity_days),
    }
