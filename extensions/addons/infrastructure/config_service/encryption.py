# -*- coding: utf-8 -*-
"""AES-256 configuration encryption (task 30.5)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


class ConfigEncryption:
    """Encrypts and decrypts configuration values."""

    def __init__(self, key: str) -> None:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
