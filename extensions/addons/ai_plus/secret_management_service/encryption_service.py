# -*- coding: utf-8 -*-
"""Encryption service for secret management."""

import base64
import hashlib
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from .config import Config
except ImportError:
    from config import Config
from loguru import logger


class EncryptionBackend(ABC):
    """Encryption backend abstract base class."""

    @abstractmethod
    def encrypt(self, plaintext: str, key_id: str = "default") -> Tuple[str, str]:
        """Encrypt plaintext and return (ciphertext, key_id)."""

    @abstractmethod
    def decrypt(self, ciphertext: str, key_id: str = "default") -> str:
        """Decrypt ciphertext."""

    @abstractmethod
    def generate_key(self, key_id: str) -> str:
        """Generate a new encryption key."""

    @abstractmethod
    def rotate_key(self, key_id: str) -> str:
        """Rotate an encryption key."""


class AESGCMBackend(EncryptionBackend):
    """AES-256-GCM encryption backend."""

    def __init__(self, key_path: str = None):
        """Initialize the encryption backend.

        Args:
            key_path: Path to store encryption keys
        """
        self.key_path = Path(key_path or Config.ENCRYPTION_KEY_PATH)
        self.key_path.mkdir(parents=True, exist_ok=True)
        self._keys: Dict[str, bytes] = {}
        self._load_keys()

    def _load_keys(self):
        """Load encryption keys from storage."""
        try:
            keys_file = self.key_path / "encryption_keys.json"
            if keys_file.exists():
                with open(keys_file, "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    for key_id, key_b64 in keys_data.items():
                        self._keys[key_id] = base64.b64decode(key_b64)
                logger.info(f"Loaded {len(self._keys)} encryption keys")
            else:
                logger.info("No existing encryption keys found")
                # Generate default key
                self.generate_key("default")
        except Exception as e:
            logger.error(f"Failed to load encryption keys: {e}")
            self._keys = {}
            self.generate_key("default")

    def _save_keys(self) -> bool:
        """Save encryption keys to storage."""
        try:
            keys_file = self.key_path / "encryption_keys.json"
            keys_data = {
                key_id: base64.b64encode(key_bytes).decode("utf-8")
                for key_id, key_bytes in self._keys.items()
            }
            with open(keys_file, "w", encoding="utf-8") as f:
                json.dump(keys_data, f, indent=2)

            # Set file permissions
            try:
                import stat
                os.chmod(keys_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass

            logger.debug(f"Saved {len(self._keys)} encryption keys")
            return True
        except Exception as e:
            logger.error(f"Failed to save encryption keys: {e}")
            return False

    def _get_or_create_key(self, key_id: str) -> bytes:
        """Get or create an encryption key."""
        if key_id not in self._keys:
            self.generate_key(key_id)
        return self._keys[key_id]

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive a key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def encrypt(self, plaintext: str, key_id: str = "default") -> Tuple[str, str]:
        """Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: Text to encrypt
            key_id: Key identifier to use for encryption

        Returns:
            Tuple of (encrypted_data_b64, key_id)
        """
        try:
            key = self._get_or_create_key(key_id)
            aesgcm = AESGCM(key)

            # Generate random nonce (96 bits for GCM)
            nonce = os.urandom(12)

            # Encrypt
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

            # Combine nonce and ciphertext
            combined = nonce + ciphertext

            # Encode as base64
            encrypted_b64 = base64.b64encode(combined).decode("utf-8")

            logger.debug(f"Encrypted data using key: {key_id}")
            return encrypted_b64, key_id

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str, key_id: str = "default") -> str:
        """Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphertext: Base64-encoded encrypted data
            key_id: Key identifier to use for decryption

        Returns:
            Decrypted plaintext
        """
        try:
            if key_id not in self._keys:
                raise ValueError(f"Key {key_id} not found")

            key = self._keys[key_id]
            aesgcm = AESGCM(key)

            # Decode base64
            combined = base64.b64decode(ciphertext)

            # Extract nonce (first 12 bytes) and ciphertext
            nonce = combined[:12]
            ciphertext_bytes = combined[12:]

            # Decrypt
            plaintext = aesgcm.decrypt(nonce, ciphertext_bytes, None)

            logger.debug(f"Decrypted data using key: {key_id}")
            return plaintext.decode("utf-8")

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def generate_key(self, key_id: str) -> str:
        """Generate a new AES-256 key.

        Args:
            key_id: Identifier for the new key

        Returns:
            Key ID
        """
        try:
            # Generate 256-bit (32 byte) key
            key = os.urandom(32)
            self._keys[key_id] = key
            self._save_keys()
            logger.info(f"Generated new encryption key: {key_id}")
            return key_id
        except Exception as e:
            logger.error(f"Failed to generate key: {e}")
            raise

    def rotate_key(self, key_id: str) -> str:
        """Rotate an encryption key.

        Args:
            key_id: Key identifier to rotate

        Returns:
            New key ID
        """
        try:
            # Generate new key with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_key_id = f"{key_id}_{timestamp}"

            self.generate_key(new_key_id)

            # Keep old key for backward compatibility
            logger.info(f"Rotated key {key_id} to {new_key_id}")

            return new_key_id

        except Exception as e:
            logger.error(f"Failed to rotate key: {e}")
            raise

    def list_keys(self) -> list:
        """List all available key IDs."""
        return list(self._keys.keys())

    def delete_key(self, key_id: str) -> bool:
        """Delete an encryption key.

        Args:
            key_id: Key identifier to delete

        Returns:
            True if successful
        """
        if key_id == "default":
            logger.warning("Cannot delete default key")
            return False

        if key_id in self._keys:
            del self._keys[key_id]
            self._save_keys()
            logger.info(f"Deleted encryption key: {key_id}")
            return True
        return False


class EncryptionService:
    """Main encryption service."""

    def __init__(self, backend: EncryptionBackend = None):
        """Initialize the encryption service.

        Args:
            backend: Encryption backend to use
        """
        self.backend = backend or AESGCMBackend()
        self.algorithm = Config.ENCRYPTION_ALGORITHM
        logger.info(f"Encryption service initialized with {self.algorithm}")

    def encrypt_secret(self, plaintext: str, key_id: str = "default") -> Dict[str, str]:
        """Encrypt a secret value.

        Args:
            plaintext: Secret value to encrypt
            key_id: Key identifier to use

        Returns:
            Dictionary with encrypted value and metadata
        """
        encrypted_b64, actual_key_id = self.backend.encrypt(plaintext, key_id)

        return {
            "encrypted_value": encrypted_b64,
            "encryption_algorithm": self.algorithm,
            "key_id": actual_key_id,
        }

    def decrypt_secret(self, encrypted_data: Dict[str, str]) -> str:
        """Decrypt a secret value.

        Args:
            encrypted_data: Dictionary with encrypted value and metadata

        Returns:
            Decrypted plaintext
        """
        ciphertext = encrypted_data.get("encrypted_value")
        key_id = encrypted_data.get("key_id", "default")

        if not ciphertext:
            raise ValueError("No encrypted value provided")

        return self.backend.decrypt(ciphertext, key_id)

    def generate_encryption_key(self, key_id: str) -> str:
        """Generate a new encryption key.

        Args:
            key_id: Key identifier

        Returns:
            Key ID
        """
        return self.backend.generate_key(key_id)

    def rotate_encryption_key(self, key_id: str) -> str:
        """Rotate an encryption key.

        Args:
            key_id: Key identifier to rotate

        Returns:
            New key ID
        """
        return self.backend.rotate_key(key_id)

    def reencrypt_secret(
        self, encrypted_data: Dict[str, str], new_key_id: str
    ) -> Dict[str, str]:
        """Re-encrypt a secret with a new key.

        Args:
            encrypted_data: Current encrypted data
            new_key_id: New key identifier to use

        Returns:
            New encrypted data
        """
        # Decrypt with old key
        plaintext = self.decrypt_secret(encrypted_data)

        # Encrypt with new key
        return self.encrypt_secret(plaintext, new_key_id)
