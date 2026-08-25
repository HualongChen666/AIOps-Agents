# -*- coding: utf-8 -*-
"""Secret manager for managing secrets with encryption and versioning."""

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .access_control import AccessControl
    from .config import Config
    from .encryption_service import EncryptionService
except ImportError:
    from access_control import AccessControl
    from config import Config
    from encryption_service import EncryptionService
    from config import Config
    from encryption_service import EncryptionService
from loguru import logger


class SecretVersion:
    """Represents a version of a secret."""

    def __init__(
        self,
        version: int,
        encrypted_value: str,
        encryption_algorithm: str,
        key_id: str,
        created_at: int = None,
        created_by: str = None,
    ):
        """Initialize secret version.

        Args:
            version: Version number
            encrypted_value: Encrypted secret value
            encryption_algorithm: Encryption algorithm used
            key_id: Key identifier used for encryption
            created_at: Creation timestamp
            created_by: Who created this version
        """
        self.version = version
        self.encrypted_value = encrypted_value
        self.encryption_algorithm = encryption_algorithm
        self.key_id = key_id
        self.created_at = created_at or int(datetime.now().timestamp() * 1000)
        self.created_by = created_by

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "encrypted_value": self.encrypted_value,
            "encryption_algorithm": self.encryption_algorithm,
            "key_id": self.key_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SecretVersion":
        """Create from dictionary."""
        return cls(
            version=data["version"],
            encrypted_value=data["encrypted_value"],
            encryption_algorithm=data["encryption_algorithm"],
            key_id=data["key_id"],
            created_at=data.get("created_at"),
            created_by=data.get("created_by"),
        )


class SecretMetadata:
    """Metadata for a secret."""

    def __init__(
        self,
        secret_id: str,
        name: str,
        description: str = "",
        created_by: str = "",
        tags: Dict[str, str] = None,
    ):
        """Initialize secret metadata.

        Args:
            secret_id: Unique secret identifier
            name: Secret name
            description: Secret description
            created_by: Who created the secret
            tags: Optional tags
        """
        self.secret_id = secret_id
        self.name = name
        self.description = description
        self.created_by = created_by
        self.tags = tags or {}
        self.created_at = int(datetime.now().timestamp() * 1000)
        self.updated_at = int(datetime.now().timestamp() * 1000)
        self.current_version = 1
        self.status = "active"  # active, disabled, expired
        self.rotation_scheduled_at: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "secret_id": self.secret_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_version": self.current_version,
            "status": self.status,
            "rotation_scheduled_at": self.rotation_scheduled_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SecretMetadata":
        """Create from dictionary."""
        metadata = cls(
            secret_id=data["secret_id"],
            name=data["name"],
            description=data.get("description", ""),
            created_by=data.get("created_by", ""),
            tags=data.get("tags", {}),
        )
        metadata.created_at = data.get("created_at", metadata.created_at)
        metadata.updated_at = data.get("updated_at", metadata.updated_at)
        metadata.current_version = data.get("current_version", 1)
        metadata.status = data.get("status", "active")
        metadata.rotation_scheduled_at = data.get("rotation_scheduled_at")
        return metadata


class Secret:
    """Complete secret with metadata and versions."""

    def __init__(self, metadata: SecretMetadata, versions: List[SecretVersion] = None):
        """Initialize secret.

        Args:
            metadata: Secret metadata
            versions: List of secret versions
        """
        self.metadata = metadata
        self.versions = versions or []

    def to_dict(self, include_value: bool = False) -> Dict:
        """Convert to dictionary.

        Args:
            include_value: Whether to include encrypted values
        """
        return {
            "metadata": self.metadata.to_dict(),
            "versions": [v.to_dict() for v in self.versions] if include_value else [],
            "version_count": len(self.versions),
        }

    def get_current_version(self) -> Optional[SecretVersion]:
        """Get current version."""
        if not self.versions:
            return None
        return self.versions[-1]

    def get_version(self, version: int) -> Optional[SecretVersion]:
        """Get specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None


class SecretManager:
    """Main secret manager."""

    def __init__(
        self,
        storage_path: str = None,
        encryption_service: EncryptionService = None,
        access_control: AccessControl = None,
    ):
        """Initialize secret manager.

        Args:
            storage_path: Path to store secrets
            encryption_service: Encryption service instance
            access_control: Access control instance
        """
        self.storage_path = Path(storage_path or Config.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.encryption_service = encryption_service or EncryptionService()
        self.access_control = access_control or AccessControl(str(self.storage_path))

        self._secrets: Dict[str, Secret] = {}
        self._load_secrets()

        # Integrate with key_management_service
        self._integrate_with_key_management()

        logger.info("Secret manager initialized")

    def _integrate_with_key_management(self):
        """Integrate with core key_management_service."""
        try:
            # Import the core key management service
            import sys
            core_path = Path(__file__).parent.parent.parent.parent / "core"
            if str(core_path) not in sys.path:
                sys.path.insert(0, str(core_path))

            from core.key_management_service import get_key_service

            # Initialize key service with file backend
            self.key_service = get_key_service(
                backend_type=Config.KEY_MANAGEMENT_SERVICE_BACKEND,
                file_path=str(self.storage_path / "service_keys.json")
            )
            logger.info("Integrated with key_management_service")

        except Exception as e:
            logger.warning(f"Could not integrate with key_management_service: {e}")
            self.key_service = None

    def _load_secrets(self):
        """Load secrets from storage."""
        try:
            secrets_file = self.storage_path / "secrets.json"
            if secrets_file.exists():
                with open(secrets_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for secret_id, secret_data in data.items():
                        metadata = SecretMetadata.from_dict(secret_data["metadata"])
                        versions = [
                            SecretVersion.from_dict(v)
                            for v in secret_data.get("versions", [])
                        ]
                        self._secrets[secret_id] = Secret(metadata, versions)
                logger.info(f"Loaded {len(self._secrets)} secrets")
            else:
                logger.info("No existing secrets found")
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
            self._secrets = {}

    def _save_secrets(self) -> bool:
        """Save secrets to storage."""
        try:
            secrets_file = self.storage_path / "secrets.json"
            data = {
                secret_id: secret.to_dict(include_value=True)
                for secret_id, secret in self._secrets.items()
            }

            with open(secrets_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Set file permissions
            try:
                import stat
                os.chmod(secrets_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass

            logger.debug(f"Saved {len(self._secrets)} secrets")
            return True
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
            return False

    def create_secret(
        self,
        name: str,
        value: str,
        description: str = "",
        created_by: str = "",
        tags: Dict[str, str] = None,
        principal: str = "",
    ) -> Secret:
        """Create a new secret.

        Args:
            name: Secret name
            value: Secret value (will be encrypted)
            description: Secret description
            created_by: Who created the secret
            tags: Optional tags
            principal: Principal creating the secret

        Returns:
            Created secret
        """
        try:
            # Check access control
            if principal and not self.access_control.check_permission(
                name, principal, "write"
            ):
                raise PermissionError(f"Principal {principal} does not have write permission")

            # Generate secret ID
            secret_id = str(uuid.uuid4())

            # Create metadata
            metadata = SecretMetadata(
                secret_id=secret_id,
                name=name,
                description=description,
                created_by=created_by or principal,
                tags=tags,
            )

            # Encrypt value
            encrypted_data = self.encryption_service.encrypt_secret(value)

            # Create first version
            version = SecretVersion(
                version=1,
                encrypted_value=encrypted_data["encrypted_value"],
                encryption_algorithm=encrypted_data["encryption_algorithm"],
                key_id=encrypted_data["key_id"],
                created_by=created_by or principal,
            )

            # Create secret
            secret = Secret(metadata, [version])
            self._secrets[secret_id] = secret

            # Save
            self._save_secrets()

            # Store in key_management_service if available
            if self.key_service:
                self.key_service.set_key(name, value)

            # Grant creator full access
            if principal:
                self.access_control.grant_access(
                    secret_id=secret_id,
                    principal=principal,
                    principal_type="user",
                    permissions=["read", "write", "delete", "rotate"],
                    granted_by=principal,
                )

            logger.info(f"Created secret: {name} ({secret_id})")
            return secret

        except Exception as e:
            logger.error(f"Failed to create secret: {e}")
            raise

    def get_secret(
        self,
        secret_id: str,
        include_value: bool = False,
        version: int = 0,
        principal: str = "",
    ) -> Optional[Dict]:
        """Get a secret.

        Args:
            secret_id: Secret identifier
            include_value: Whether to include decrypted value
            version: Version to get (0 for latest)
            principal: Principal requesting the secret

        Returns:
            Secret data
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            secret = self._secrets[secret_id]

            # Check access control
            if principal and not self.access_control.check_permission(
                secret_id, principal, "read"
            ):
                raise PermissionError(f"Principal {principal} does not have read permission")

            # Get version
            if version == 0:
                secret_version = secret.get_current_version()
            else:
                secret_version = secret.get_version(version)

            if not secret_version:
                raise ValueError(f"Version {version} not found")

            result = {
                "metadata": secret.metadata.to_dict(),
                "version": secret_version.version,
                "created_at": secret_version.created_at,
            }

            # Decrypt value if requested
            if include_value:
                encrypted_data = {
                    "encrypted_value": secret_version.encrypted_value,
                    "key_id": secret_version.key_id,
                }
                result["value"] = self.encryption_service.decrypt_secret(encrypted_data)

            return result

        except Exception as e:
            logger.error(f"Failed to get secret: {e}")
            raise

    def get_secret_by_name(
        self,
        name: str,
        include_value: bool = False,
        principal: str = "",
    ) -> Optional[Dict]:
        """Get a secret by name.

        Args:
            name: Secret name
            include_value: Whether to include decrypted value
            principal: Principal requesting the secret

        Returns:
            Secret data
        """
        for secret in self._secrets.values():
            if secret.metadata.name == name:
                return self.get_secret(secret.metadata.secret_id, include_value, 0, principal)
        return None

    def update_secret(
        self,
        secret_id: str,
        value: str = None,
        description: str = None,
        tags: Dict[str, str] = None,
        updated_by: str = "",
        principal: str = "",
    ) -> Secret:
        """Update a secret.

        Args:
            secret_id: Secret identifier
            value: New value (will create new version)
            description: New description
            tags: New tags
            updated_by: Who updated the secret
            principal: Principal updating the secret

        Returns:
            Updated secret
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            secret = self._secrets[secret_id]

            # Check access control
            if principal and not self.access_control.check_permission(
                secret_id, principal, "write"
            ):
                raise PermissionError(f"Principal {principal} does not have write permission")

            # Update metadata
            if description is not None:
                secret.metadata.description = description
            if tags is not None:
                secret.metadata.tags = tags
            secret.metadata.updated_at = int(datetime.now().timestamp() * 1000)

            # Create new version if value changed
            if value is not None:
                encrypted_data = self.encryption_service.encrypt_secret(value)

                new_version = SecretVersion(
                    version=secret.metadata.current_version + 1,
                    encrypted_value=encrypted_data["encrypted_value"],
                    encryption_algorithm=encrypted_data["encryption_algorithm"],
                    key_id=encrypted_data["key_id"],
                    created_by=updated_by or principal,
                )

                secret.versions.append(new_version)
                secret.metadata.current_version = new_version.version

                # Limit versions
                if len(secret.versions) > Config.MAX_VERSIONS:
                    secret.versions = secret.versions[-Config.MAX_VERSIONS:]

                # Update in key_management_service
                if self.key_service:
                    self.key_service.set_key(secret.metadata.name, value)

            # Save
            self._save_secrets()

            logger.info(f"Updated secret: {secret_id}")
            return secret

        except Exception as e:
            logger.error(f"Failed to update secret: {e}")
            raise

    def delete_secret(
        self, secret_id: str, permanent: bool = False, principal: str = ""
    ) -> bool:
        """Delete a secret.

        Args:
            secret_id: Secret identifier
            permanent: If True, permanently delete; if False, soft delete
            principal: Principal deleting the secret

        Returns:
            True if successful
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            # Check access control
            if principal and not self.access_control.check_permission(
                secret_id, principal, "delete"
            ):
                raise PermissionError(f"Principal {principal} does not have delete permission")

            if permanent:
                # Permanently delete
                secret = self._secrets[secret_id]
                name = secret.metadata.name

                del self._secrets[secret_id]

                # Delete from key_management_service
                if self.key_service:
                    self.key_service.delete_key(name)

                # Delete access permissions
                self.access_control.delete_secret_permissions(secret_id)

                logger.info(f"Permanently deleted secret: {secret_id}")
            else:
                # Soft delete
                self._secrets[secret_id].metadata.status = "disabled"
                logger.info(f"Soft deleted secret: {secret_id}")

            self._save_secrets()
            return True

        except Exception as e:
            logger.error(f"Failed to delete secret: {e}")
            raise

    def list_secrets(
        self,
        filter_status: str = "active",
        filter_tag: str = None,
        limit: int = 100,
        offset: int = 0,
        principal: str = "",
    ) -> List[Dict]:
        """List secrets.

        Args:
            filter_status: Filter by status
            filter_tag: Filter by tag
            limit: Maximum number of results
            offset: Offset for pagination
            principal: Principal requesting the list

        Returns:
            List of secret metadata
        """
        results = []

        for secret in self._secrets.values():
            # Filter by status
            if filter_status != "all" and secret.metadata.status != filter_status:
                continue

            # Filter by tag
            if filter_tag and filter_tag not in secret.metadata.tags.values():
                continue

            # Check access control
            if principal and not self.access_control.check_permission(
                secret.metadata.secret_id, principal, "read"
            ):
                continue

            results.append(secret.metadata.to_dict())

        # Pagination
        total = len(results)
        results = results[offset:offset + limit]

        return results

    def rotate_secret(
        self,
        secret_id: str,
        new_value: str,
        rotated_by: str = "",
        old_value_retention_hours: int = None,
        principal: str = "",
    ) -> Secret:
        """Rotate a secret to a new value.

        Args:
            secret_id: Secret identifier
            new_value: New secret value
            rotated_by: Who rotated the secret
            old_value_retention_hours: How long to keep old value
            principal: Principal rotating the secret

        Returns:
            Updated secret
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            # Check access control
            if principal and not self.access_control.check_permission(
                secret_id, principal, "rotate"
            ):
                raise PermissionError(f"Principal {principal} does not have rotate permission")

            retention = old_value_retention_hours or Config.OLD_VALUE_RETENTION_HOURS

            # Use key_management_service rotate if available
            if self.key_service:
                secret = self._secrets[secret_id]
                self.key_service.rotate_key(
                    secret.metadata.name,
                    new_value,
                    old_value_retention=retention * 3600
                )

            # Update secret with new value
            return self.update_secret(
                secret_id=secret_id,
                value=new_value,
                updated_by=rotated_by or principal,
                principal=principal,
            )

        except Exception as e:
            logger.error(f"Failed to rotate secret: {e}")
            raise

    def get_secret_versions(self, secret_id: str, principal: str = "") -> List[Dict]:
        """Get all versions of a secret.

        Args:
            secret_id: Secret identifier
            principal: Principal requesting the versions

        Returns:
            List of version information
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            # Check access control
            if principal and not self.access_control.check_permission(
                secret_id, principal, "read"
            ):
                raise PermissionError(f"Principal {principal} does not have read permission")

            secret = self._secrets[secret_id]

            return [
                {
                    "version": v.version,
                    "encryption_algorithm": v.encryption_algorithm,
                    "key_id": v.key_id,
                    "created_at": v.created_at,
                    "created_by": v.created_by,
                }
                for v in secret.versions
            ]

        except Exception as e:
            logger.error(f"Failed to get secret versions: {e}")
            raise

    def revert_secret_version(
        self,
        secret_id: str,
        target_version: int,
        reverted_by: str = "",
        principal: str = "",
    ) -> Secret:
        """Revert a secret to a specific version.

        Args:
            secret_id: Secret identifier
            target_version: Version to revert to
            reverted_by: Who reverted the secret
            principal: Principal reverting the secret

        Returns:
            Updated secret
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            secret = self._secrets[secret_id]

            # Check access control
            if principal and not self.access_control.check_permission(
                secret_id, principal, "write"
            ):
                raise PermissionError(f"Principal {principal} does not have write permission")

            # Find target version
            target = secret.get_version(target_version)
            if not target:
                raise ValueError(f"Version {target_version} not found")

            # Decrypt old value
            encrypted_data = {
                "encrypted_value": target.encrypted_value,
                "key_id": target.key_id,
            }
            old_value = self.encryption_service.decrypt_secret(encrypted_data)

            # Create new version with old value
            return self.update_secret(
                secret_id=secret_id,
                value=old_value,
                updated_by=reverted_by or principal,
                principal=principal,
            )

        except Exception as e:
            logger.error(f"Failed to revert secret version: {e}")
            raise

    def schedule_rotation(self, secret_id: str, days: int = None) -> bool:
        """Schedule automatic rotation for a secret.

        Args:
            secret_id: Secret identifier
            days: Days until rotation (default from config)

        Returns:
            True if successful
        """
        try:
            if secret_id not in self._secrets:
                raise ValueError(f"Secret not found: {secret_id}")

            interval_days = days or Config.DEFAULT_ROTATION_INTERVAL_DAYS
            rotation_time = datetime.now() + timedelta(days=interval_days)

            self._secrets[secret_id].metadata.rotation_scheduled_at = int(
                rotation_time.timestamp() * 1000
            )

            self._save_secrets()

            logger.info(f"Scheduled rotation for {secret_id} in {interval_days} days")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule rotation: {e}")
            raise

    def get_rotation_schedule(self) -> List[Dict]:
        """Get all secrets scheduled for rotation.

        Returns:
            List of scheduled rotations
        """
        results = []
        current_time = int(datetime.now().timestamp() * 1000)

        for secret in self._secrets.values():
            if secret.metadata.rotation_scheduled_at:
                results.append({
                    "secret_id": secret.metadata.secret_id,
                    "name": secret.metadata.name,
                    "scheduled_at": secret.metadata.rotation_scheduled_at,
                    "is_due": secret.metadata.rotation_scheduled_at <= current_time,
                })

        return results

    def cleanup_old_versions(self) -> int:
        """Clean up old versions beyond MAX_VERSIONS.

        Returns:
            Number of versions cleaned up
        """
        cleaned = 0

        for secret in self._secrets.values():
            if len(secret.versions) > Config.MAX_VERSIONS:
                old_count = len(secret.versions)
                secret.versions = secret.versions[-Config.MAX_VERSIONS:]
                cleaned += old_count - len(secret.versions)

        if cleaned > 0:
            self._save_secrets()
            logger.info(f"Cleaned up {cleaned} old secret versions")

        return cleaned
