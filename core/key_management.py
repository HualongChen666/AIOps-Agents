# -*- coding: utf-8 -*-
"""
密钥管理服务
提供安全的密钥加密存储和轮换功能
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes as crypto_hashes

from sqlalchemy.orm import Session

from core.models import SecurityKey, DataEncryptionKey

logger = logging.getLogger(__name__)


class KeyEncryptionService:
    """密钥加密服务"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化密钥加密服务
        
        Args:
            master_key: 主加密密钥，如果未提供则从环境变量获取
        """
        self.master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY", self._generate_master_key())
        self._ensure_key_length()
    
    def _generate_master_key(self) -> str:
        """生成主密钥（仅用于开发环境）"""
        logger.warning("Using auto-generated master key. Set ENCRYPTION_MASTER_KEY in production!")
        return secrets.token_urlsafe(32)
    
    def _ensure_key_length(self):
        """确保密钥长度为32字节（AES-256）"""
        if len(self.master_key) < 32:
            self.master_key = self.master_key.ljust(32, '0')[:32]
        elif len(self.master_key) > 32:
            self.master_key = self.master_key[:32]
    
    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """
        加密明文
        
        Args:
            plaintext: 要加密的明文字符串
        
        Returns:
            (加密后的密文hex字符串, IV hex字符串)
        """
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.master_key.encode()),
            modes.CFB(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt
        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
        
        return ciphertext.hex(), iv.hex()
    
    def decrypt(self, ciphertext_hex: str, iv_hex: str) -> str:
        """
        解密密文
        
        Args:
            ciphertext_hex: 加密后的密文hex字符串
            iv_hex: IV hex字符串
        
        Returns:
            解密后的明文字符串
        """
        # Convert hex to bytes
        ciphertext = bytes.fromhex(ciphertext_hex)
        iv = bytes.fromhex(iv_hex)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.master_key.encode()),
            modes.CFB(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext.decode()
    
    def generate_key(self, key_type: str = "api_key", key_size: int = 32) -> str:
        """
        生成随机密钥
        
        Args:
            key_type: 密钥类型
            key_size: 密钥大小（字节）
        
        Returns:
            生成的密钥字符串
        """
        if key_type == "api_key":
            return secrets.token_urlsafe(32)
        elif key_type == "secret_key":
            return secrets.token_hex(32)
        elif key_type == "jwt":
            return secrets.token_urlsafe(32)
        else:
            return secrets.token_urlsafe(key_size)


class KeyRotationService:
    """密钥轮换服务"""
    
    def __init__(self, db: Session, encryption_service: KeyEncryptionService):
        """
        初始化密钥轮换服务
        
        Args:
            db: 数据库会话
            encryption_service: 加密服务实例
        """
        self.db = db
        self.encryption_service = encryption_service
    
    def rotate_key(self, key_id: str) -> Optional[SecurityKey]:
        """
        轮换密钥
        
        Args:
            key_id: 要轮换的密钥ID
        
        Returns:
            更新后的密钥对象
        """
        # Get existing key
        key = self.db.query(SecurityKey).filter(SecurityKey.id == key_id).first()
        if not key:
            logger.error(f"Key not found for rotation: {key_id}")
            return None
        
        # Generate new key value
        new_key_value = self.encryption_service.generate_key(key.key_type, key.key_size // 8)
        
        # Encrypt new key
        encrypted_value, encrypted_iv = self.encryption_service.encrypt(new_key_value)
        
        # Update key
        key.encrypted_key_value = encrypted_value
        key.encrypted_key_iv = encrypted_iv
        key.last_rotated_at = datetime.now()
        
        # Update expiration if auto-renew is enabled
        if key.auto_renew and key.expires_at:
            key.expires_at = datetime.now() + timedelta(days=365)
        
        self.db.commit()
        self.db.refresh(key)
        
        logger.info(f"Key rotated successfully: {key_id}")
        return key
    
    def rotate_data_encryption_key(self, key_id: str) -> Optional[DataEncryptionKey]:
        """
        轮换数据加密密钥
        
        Args:
            key_id: 要轮换的密钥ID
        
        Returns:
            更新后的密钥对象
        """
        # Get existing key
        key = self.db.query(DataEncryptionKey).filter(DataEncryptionKey.id == key_id).first()
        if not key:
            logger.error(f"Data encryption key not found for rotation: {key_id}")
            return None
        
        # Generate new key value
        new_key_value = secrets.token_hex(key.key_size // 8)
        
        # Encrypt new key
        encrypted_value, encrypted_iv = self.encryption_service.encrypt(new_key_value)
        
        # Update key
        key.key_encrypted = encrypted_value
        key.key_iv = encrypted_iv
        key.last_rotated_at = datetime.now()
        
        # Calculate next rotation date
        if key.rotation_enabled and key.rotation_interval_days:
            key.next_rotation_at = datetime.now() + timedelta(days=key.rotation_interval_days)
        
        self.db.commit()
        self.db.refresh(key)
        
        logger.info(f"Data encryption key rotated successfully: {key_id}")
        return key
    
    def check_rotation_needed(self, key_id: str) -> bool:
        """
        检查密钥是否需要轮换
        
        Args:
            key_id: 密钥ID
        
        Returns:
            是否需要轮换
        """
        key = self.db.query(SecurityKey).filter(SecurityKey.id == key_id).first()
        if not key:
            return False
        
        # Check if auto-renew is enabled and key is near expiration
        if key.auto_renew and key.expires_at:
            days_until_expiry = (key.expires_at - datetime.now()).days
            if days_until_expiry <= 30:  # Rotate if expiring within 30 days
                return True
        
        # Check if key hasn't been rotated in 90 days
        if key.last_rotated_at:
            days_since_rotation = (datetime.now() - key.last_rotated_at).days
            if days_since_rotation >= 90:
                return True
        
        return False
    
    def rotate_all_expired_keys(self) -> int:
        """
        轮换所有过期或即将过期的密钥
        
        Returns:
            轮换的密钥数量
        """
        # Find keys that need rotation
        keys_to_rotate = self.db.query(SecurityKey).filter(
            SecurityKey.auto_renew == True,
            SecurityKey.expires_at < datetime.now() + timedelta(days=30)
        ).all()
        
        rotated_count = 0
        for key in keys_to_rotate:
            if self.rotate_key(key.id):
                rotated_count += 1
        
        logger.info(f"Rotated {rotated_count} keys")
        return rotated_count


class KeyManagementService:
    """密钥管理服务（整合加密和轮换功能）"""
    
    def __init__(self, db: Session):
        """
        初始化密钥管理服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.encryption_service = KeyEncryptionService()
        self.rotation_service = KeyRotationService(db, self.encryption_service)
    
    def create_key(
        self,
        name: str,
        key_type: str,
        algorithm: str = "RSA",
        key_size: int = 2048,
        usage: Optional[list] = None,
        auto_renew: bool = False,
    ) -> SecurityKey:
        """
        创建新的密钥
        
        Args:
            name: 密钥名称
            key_type: 密钥类型
            algorithm: 算法
            key_size: 密钥大小
            usage: 使用场景
            auto_renew: 是否自动续期
        
        Returns:
            创建的密钥对象
        """
        # Generate key value
        key_value = self.encryption_service.generate_key(key_type, key_size // 8)
        
        # Encrypt key
        encrypted_value, encrypted_iv = self.encryption_service.encrypt(key_value)
        
        # Create key record
        key = SecurityKey(
            id=str(secrets.token_urlsafe(16)),
            name=name,
            key_type=key_type,
            algorithm=algorithm,
            key_size=key_size,
            encrypted_key_value=encrypted_value,
            encrypted_key_iv=encrypted_iv,
            status="active",
            auto_renew=auto_renew,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365),
            last_rotated_at=datetime.now(),
            usage=usage or [],
        )
        
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        
        logger.info(f"Created key: {name}")
        return key
    
    def get_key_value(self, key_id: str) -> Optional[str]:
        """
        获取密钥的明文值（用于内部使用）
        
        Args:
            key_id: 密钥ID
        
        Returns:
            密钥明文值
        """
        key = self.db.query(SecurityKey).filter(SecurityKey.id == key_id).first()
        if not key:
            return None
        
        # Decrypt key
        try:
            return self.encryption_service.decrypt(
                key.encrypted_key_value,
                key.encrypted_key_iv
            )
        except Exception as e:
            logger.error(f"Failed to decrypt key {key_id}: {e}")
            return None
    
    def revoke_key(self, key_id: str) -> bool:
        """
        撤销密钥
        
        Args:
            key_id: 密钥ID
        
        Returns:
            是否成功
        """
        key = self.db.query(SecurityKey).filter(SecurityKey.id == key_id).first()
        if not key:
            return False
        
        key.status = "revoked"
        self.db.commit()
        
        logger.info(f"Revoked key: {key_id}")
        return True
    
    def get_rotation_service(self) -> KeyRotationService:
        """获取密钥轮换服务"""
        return self.rotation_service


def get_key_management_service(db: Session) -> KeyManagementService:
    """获取密钥管理服务实例"""
    return KeyManagementService(db)
