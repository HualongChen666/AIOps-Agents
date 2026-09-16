# -*- coding: utf-8 -*-
"""AES-256-GCM audit data encryption (task 28.5)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.audit_service.schemas import EncryptedBlob

# GCM 标准参数：96-bit nonce、128-bit authentication tag。
_NONCE_BYTES = 12
_TAG_BYTES = 16


class AESEncryption:
    """Authenticated encryption with real AES-256-GCM.

    主密钥材料经 SHA-256 派生为恒定 32 字节（256 bit）AES 密钥；每次加密使用
    随机 96-bit nonce，密文以 ``nonce || ciphertext || tag`` 形式自包含（可独立解密），
    同时把真实的 ``nonce`` / ``tag`` 一并返回，供审计存储登记。
    """

    algorithm = "AES-256-GCM"

    def __init__(self, key: str) -> None:
        # Derive a 32-byte (AES-256) key from the user key material using SHA-256.
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        self._aesgcm = AESGCM(digest)

    def encrypt(self, plaintext: str) -> Dict[str, str]:
        nonce = secrets.token_bytes(_NONCE_BYTES)
        sealed = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        tag = sealed[-_TAG_BYTES:]
        # 自包含密文：nonce || ciphertext(含 tag)，便于仅凭 ciphertext 解密。
        combined = nonce + sealed
        return {
            "ciphertext": base64.urlsafe_b64encode(combined).decode("utf-8"),
            "nonce": nonce.hex(),
            "tag": tag.hex(),
        }

    def decrypt(self, ciphertext: str) -> str:
        raw = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
        if len(raw) <= _NONCE_BYTES + _TAG_BYTES:
            raise ValueError("ciphertext too short to contain nonce and tag")
        nonce, sealed = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
        return self._aesgcm.decrypt(nonce, sealed, None).decode("utf-8")


class AuditEncryption:
    """Encrypts and decrypts audit data."""

    def __init__(self, key: str) -> None:
        self.engine = AESEncryption(key)

    def encrypt_event(self, event_id: str, plaintext: str) -> EncryptedBlob:
        encrypted = self.engine.encrypt(plaintext)
        return EncryptedBlob(
            blob_id=event_id,
            ciphertext=encrypted["ciphertext"],
            nonce=encrypted["nonce"],
            tag=encrypted["tag"],
            algorithm=self.engine.algorithm,
        )

    def decrypt_blob(self, blob: EncryptedBlob) -> str:
        return self.engine.decrypt(blob.ciphertext)
