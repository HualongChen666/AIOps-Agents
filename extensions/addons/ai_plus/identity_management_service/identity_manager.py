# -*- coding: utf-8 -*-
"""Identity Manager - Core identity management logic."""

import asyncio
import json
import logging
import secrets
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

import jwt
import pyotp
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth_db import SessionLocal, User, UserAttribute
from core.auth_service import hash_password, verify_password
from core.user_service import UserService

logger = logging.getLogger(__name__)



class IdentityManager:
    """Core identity management operations."""

    def __init__(self):
        self.user_service = UserService()
        self._sso_configs: Dict[str, Dict[str, Any]] = {}

    async def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user with password hashing."""
        try:
            # Hash the password
            hashed_password = hash_password(password)
            
            # Create user via UserService
            user = await self.user_service.create_user(
                username=username,
                hashed_password=hashed_password,
                email=email,
                full_name=full_name,
                role=role,
                disabled=False,
            )
            
            if not user:
                logger.error(f"Failed to create user: {username}")
                return None
            
            # Store custom attributes if provided
            if attributes:
                await self._set_user_attributes(user.id, attributes)
            
            logger.info(f"✅ User created successfully: {username}")
            return self.user_service.user_to_dict(user)
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}", exc_info=True)
            return None

    async def update_user(
        self,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update user information."""
        try:
            # Update basic user info
            success = await self.user_service.update_user(
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                disabled=disabled,
            )
            
            if not success:
                logger.error(f"Failed to update user: {username}")
                return None
            
            # Update attributes if provided
            if attributes:
                user = await self.user_service.get_user_by_username(username)
                if user:
                    await self._set_user_attributes(user.id, attributes)
            
            # Get updated user
            user = await self.user_service.get_user_by_username(username)
            if user:
                logger.info(f"✅ User updated successfully: {username}")
                return self.user_service.user_to_dict(user)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating user {username}: {e}", exc_info=True)
            return None

    async def delete_user(self, username: str) -> bool:
        """Delete a user."""
        try:
            success = await self.user_service.delete_user(username)
            if success:
                logger.info(f"✅ User deleted successfully: {username}")
            return success
        except Exception as e:
            logger.error(f"Error deleting user {username}: {e}", exc_info=True)
            return False

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            user = await self.user_service.get_user_by_username(username)
            if user:
                # Load custom attributes
                attributes = await self._get_user_attributes(user.id)
                user_dict = self.user_service.user_to_dict(user)
                user_dict["attributes"] = attributes
                return user_dict
            return None
        except Exception as e:
            logger.error(f"Error getting user {username}: {e}", exc_info=True)
            return None

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List users with optional filtering."""
        try:
            users = await self.user_service.list_users(limit=limit, offset=offset)
            
            # Apply filters
            filtered_users = []
            for user in users:
                if role and user.role != role:
                    continue
                if disabled is not None and user.disabled != disabled:
                    continue
                filtered_users.append(user)
            
            # Convert to dict and load attributes
            result = []
            for user in filtered_users:
                attributes = await self._get_user_attributes(user.id)
                user_dict = self.user_service.user_to_dict(user)
                user_dict["attributes"] = attributes
                result.append(user_dict)
            
            return result
        except Exception as e:
            logger.error(f"Error listing users: {e}", exc_info=True)
            return []

    async def set_user_attribute(
        self, username: str, key: str, value: str
    ) -> bool:
        """Set a custom user attribute."""
        try:
            user = await self.user_service.get_user_by_username(username)
            if not user:
                logger.error(f"User not found: {username}")
                return False
            
            await self._set_user_attribute(user.id, key, value)
            logger.info(f"✅ Attribute set for user {username}: {key}={value}")
            return True
        except Exception as e:
            logger.error(f"Error setting attribute for user {username}: {e}", exc_info=True)
            return False

    async def delete_user_attribute(self, username: str, key: str) -> bool:
        """Delete a custom user attribute."""
        try:
            user = await self.user_service.get_user_by_username(username)
            if not user:
                logger.error(f"User not found: {username}")
                return False
            
            await self._delete_user_attribute(user.id, key)
            logger.info(f"✅ Attribute deleted for user {username}: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting attribute for user {username}: {e}", exc_info=True)
            return False

    async def enable_mfa(self, username: str) -> Optional[Dict[str, Any]]:
        """Enable multi-factor authentication for a user."""
        try:
            user = await self.user_service.get_user_by_username(username)
            if not user:
                logger.error(f"User not found: {username}")
                return None
            
            # Generate TOTP secret
            secret = pyotp.random_base32()
            
            # Generate recovery codes
            recovery_codes = [pyotp.random_base32()[:8] for _ in range(10)]
            
            # Store in database
            success = await self.user_service.enable_mfa(username, secret, recovery_codes)
            
            if success:
                logger.info(f"✅ MFA enabled for user: {username}")
                return {
                    "secret": secret,
                    "recovery_codes": recovery_codes,
                    "enabled": True,
                }
            
            return None
        except Exception as e:
            logger.error(f"Error enabling MFA for user {username}: {e}", exc_info=True)
            return None

    async def disable_mfa(self, username: str) -> bool:
        """Disable multi-factor authentication for a user."""
        try:
            success = await self.user_service.disable_mfa(username)
            if success:
                logger.info(f"✅ MFA disabled for user: {username}")
            return success
        except Exception as e:
            logger.error(f"Error disabling MFA for user {username}: {e}", exc_info=True)
            return False

    async def verify_mfa(self, username: str, code: str) -> bool:
        """Verify MFA code for a user."""
        try:
            user = await self.user_service.get_user_by_username(username)
            if not user or not user.mfa_enabled:
                logger.error(f"MFA not enabled for user: {username}")
                return False
            
            # Check if code is a recovery code
            if user.recovery_codes:
                recovery_codes = json.loads(user.recovery_codes) if isinstance(user.recovery_codes, str) else user.recovery_codes
                if code in recovery_codes:
                    # Consume the recovery code: persist the remaining set through the
                    # user service so it survives (each code is single-use).
                    recovery_codes.remove(code)
                    await self.user_service.enable_mfa(
                        username, user.mfa_secret, recovery_codes
                    )
                    logger.info(f"✅ MFA verified using recovery code for user: {username}")
                    return True
            
            # Verify TOTP code
            if user.mfa_secret:
                totp = pyotp.TOTP(user.mfa_secret)
                if totp.verify(code):
                    logger.info(f"✅ MFA verified using TOTP for user: {username}")
                    return True
            
            logger.warning(f"Invalid MFA code for user: {username}")
            return False
        except Exception as e:
            logger.error(f"Error verifying MFA for user {username}: {e}", exc_info=True)
            return False

    async def configure_sso(
        self,
        provider: str,
        client_id: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Configure SSO provider."""
        try:
            config = {
                "provider": provider,
                "client_id": client_id,
                "metadata": metadata or {},
                "enabled": True,
            }
            self._sso_configs[provider] = config
            logger.info(f"✅ SSO configured for provider: {provider}")
            return config
        except Exception as e:
            logger.error(f"Error configuring SSO for provider {provider}: {e}", exc_info=True)
            return {}

    async def sso_login(
        self, provider: str, token: str
    ) -> Optional[Dict[str, Any]]:
        """Perform SSO login by validating the provider-issued OIDC/JWT token.

        The token signature is verified against the provider's JWKS endpoint
        (``metadata.jwks_uri``) and the standard ``iss``/``aud``/``exp`` claims are
        enforced.  A locally provisioned user is mapped/created from the token
        subject.  If the provider is not configured with a ``jwks_uri`` the login
        fails closed rather than trusting an unverified token.
        """
        try:
            if provider not in self._sso_configs:
                logger.error(f"SSO provider not configured: {provider}")
                return None

            config = self._sso_configs[provider]
            metadata = config.get("metadata") or {}
            jwks_uri = metadata.get("jwks_uri")
            issuer = metadata.get("issuer")
            audience = metadata.get("audience") or config.get("client_id")

            if not jwks_uri:
                logger.error(
                    "SSO provider %s has no jwks_uri configured; refusing to trust "
                    "an unverified token",
                    provider,
                )
                return None

            claims = await asyncio.to_thread(
                self._verify_sso_token, jwks_uri, token, issuer, audience
            )

            username = (
                claims.get("preferred_username")
                or claims.get("email")
                or claims.get("sub")
            )
            if not username:
                logger.error("SSO token for provider %s has no subject claim", provider)
                return None

            user = await self.user_service.get_user_by_username(username)
            if not user:
                # SSO users authenticate through the IdP only: provision with a
                # random, unknown local secret so password login cannot be used.
                user = await self.user_service.create_user(
                    username=username,
                    hashed_password=hash_password(secrets.token_urlsafe(32)),
                    email=claims.get("email"),
                    full_name=claims.get("name") or username,
                    role=claims.get("role", "user"),
                )

            if user:
                logger.info(f"✅ SSO login successful for user: {username}")
                return self.user_service.user_to_dict(user)

            return None
        except Exception as e:
            logger.error(f"Error during SSO login for provider {provider}: {e}", exc_info=True)
            return None

    @staticmethod
    def _verify_sso_token(
        jwks_uri: str,
        token: str,
        issuer: Optional[str],
        audience: Optional[str],
    ) -> Dict[str, Any]:
        """Verify a JWT against a JWKS endpoint, returning the decoded claims."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise ValueError(f"Malformed SSO token: {exc}") from exc
        alg = header.get("alg", "")
        # Only accept asymmetric signature algorithms to prevent algorithm
        # confusion / "none" attacks.
        allowed = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256", "PS384", "PS512"}
        if alg not in allowed:
            raise ValueError(f"Unsupported SSO token algorithm: {alg}")

        jwk_client = jwt.PyJWKClient(jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        decode_kwargs: Dict[str, Any] = {"algorithms": [alg], "options": {"require": ["exp"]}}
        if audience:
            decode_kwargs["audience"] = audience
        if issuer:
            decode_kwargs["issuer"] = issuer
        return jwt.decode(token, signing_key.key, **decode_kwargs)

    async def _set_user_attributes(self, user_id: int, attributes: Dict[str, str]) -> None:
        """Set multiple user attributes."""
        for key, value in attributes.items():
            await self._set_user_attribute(user_id, key, value)

    async def _set_user_attribute(self, user_id: int, key: str, value: str) -> None:
        """Persist a single user attribute (upsert)."""
        db = SessionLocal()
        try:
            row = (
                db.query(UserAttribute)
                .filter(UserAttribute.user_id == user_id, UserAttribute.key == key)
                .first()
            )
            if row is None:
                row = UserAttribute(user_id=user_id, key=key, value=str(value))
                db.add(row)
            else:
                row.value = str(value)
            db.commit()
        finally:
            db.close()

    async def _get_user_attributes(self, user_id: int) -> Dict[str, str]:
        """Load all user attributes for a user."""
        db = SessionLocal()
        try:
            rows = (
                db.query(UserAttribute)
                .filter(UserAttribute.user_id == user_id)
                .all()
            )
            return {row.key: row.value for row in rows}
        finally:
            db.close()

    async def _delete_user_attribute(self, user_id: int, key: str) -> None:
        """Delete a user attribute."""
        db = SessionLocal()
        try:
            db.query(UserAttribute).filter(
                UserAttribute.user_id == user_id, UserAttribute.key == key
            ).delete()
            db.commit()
        finally:
            db.close()


# Global identity manager instance
identity_manager = IdentityManager()
