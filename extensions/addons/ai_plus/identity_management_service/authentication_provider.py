# -*- coding: utf-8 -*-
"""Authentication Provider - SSO and authentication integration."""

import logging
import sys
import os
from typing import Any, Dict, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from core.auth_service import create_access_token, decode_token, verify_password
from identity_manager import IdentityManager

logger = logging.getLogger(__name__)


class AuthenticationProvider:
    """Authentication provider with SSO support."""

    def __init__(self, identity_manager: Optional[IdentityManager] = None):
        self.identity_manager = identity_manager or IdentityManager()
        self._sso_providers: Dict[str, Dict[str, Any]] = {}

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user with username and password."""
        try:
            user = await self.identity_manager.get_user(username)
            if not user:
                logger.warning(f"Authentication failed: user not found: {username}")
                return None
            
            if user.get("disabled"):
                logger.warning(f"Authentication failed: user disabled: {username}")
                return None
            
            # Verify password (need to get the hashed password from database)
            from core.user_service import UserService
            user_service = UserService()
            db_user = await user_service.get_user_by_username(username)
            if not db_user:
                return None
            
            if not verify_password(password, db_user.hashed_password):
                logger.warning(f"Authentication failed: invalid password: {username}")
                return None
            
            # Check MFA if enabled
            if user.get("mfa_enabled"):
                logger.info(f"MFA required for user: {username}")
                return {"username": username, "mfa_required": True}
            
            # Generate access token
            token_data = {
                "sub": username,
                "role": user.get("role", "user"),
            }
            token = create_access_token(token_data)
            
            logger.info(f"✅ Authentication successful: {username}")
            return {
                "username": username,
                "token": token,
                "role": user.get("role"),
                "mfa_required": False,
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}", exc_info=True)
            return None

    async def authenticate_with_mfa(
        self, username: str, mfa_code: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user with MFA code."""
        try:
            # Verify MFA code
            verified = await self.identity_manager.verify_mfa(username, mfa_code)
            if not verified:
                logger.warning(f"MFA verification failed: {username}")
                return None
            
            # Get user
            user = await self.identity_manager.get_user(username)
            if not user:
                return None
            
            # Generate access token
            token_data = {
                "sub": username,
                "role": user.get("role", "user"),
            }
            token = create_access_token(token_data)
            
            logger.info(f"✅ MFA authentication successful: {username}")
            return {
                "username": username,
                "token": token,
                "role": user.get("role"),
            }
            
        except Exception as e:
            logger.error(f"Error during MFA authentication for {username}: {e}", exc_info=True)
            return None

    async def authenticate_with_sso(
        self, provider: str, sso_token: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user via SSO."""
        try:
            if provider not in self._sso_providers:
                logger.error(f"SSO provider not configured: {provider}")
                return None
            
            # Use identity manager's SSO login
            user = await self.identity_manager.sso_login(provider, sso_token)
            if not user:
                logger.error(f"SSO login failed for provider: {provider}")
                return None
            
            # Generate access token
            token_data = {
                "sub": user.get("username"),
                "role": user.get("role", "user"),
            }
            token = create_access_token(token_data)
            
            logger.info(f"✅ SSO authentication successful: {provider}")
            return {
                "username": user.get("username"),
                "token": token,
                "role": user.get("role"),
                "provider": provider,
            }
            
        except Exception as e:
            logger.error(f"Error during SSO authentication for {provider}: {e}", exc_info=True)
            return None

    async def register_sso_provider(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Register an SSO provider."""
        try:
            self._sso_providers[provider] = {
                "client_id": client_id,
                "client_secret": client_secret,
                "metadata": metadata or {},
                "enabled": True,
            }
            
            # Also configure in identity manager
            await self.identity_manager.configure_sso(
                provider=provider,
                client_id=client_id,
                metadata=metadata,
            )
            
            logger.info(f"✅ SSO provider registered: {provider}")
            return True
        except Exception as e:
            logger.error(f"Error registering SSO provider {provider}: {e}", exc_info=True)
            return False

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token."""
        try:
            payload = decode_token(token)
            username = payload.get("sub")
            if not username:
                return None
            
            user = await self.identity_manager.get_user(username)
            if not user or user.get("disabled"):
                return None
            
            return {
                "username": username,
                "role": payload.get("role"),
                "valid": True,
            }
        except Exception as e:
            logger.error(f"Error validating token: {e}", exc_info=True)
            return None

    async def refresh_token(self, token: str) -> Optional[str]:
        """Refresh an access token."""
        try:
            payload = decode_token(token)
            username = payload.get("sub")
            if not username:
                return None
            
            user = await self.identity_manager.get_user(username)
            if not user or user.get("disabled"):
                return None
            
            # Generate new token
            token_data = {
                "sub": username,
                "role": user.get("role", "user"),
            }
            new_token = create_access_token(token_data)
            
            logger.info(f"✅ Token refreshed for user: {username}")
            return new_token
        except Exception as e:
            logger.error(f"Error refreshing token: {e}", exc_info=True)
            return None

    async def logout(self, token: str) -> bool:
        """Logout a user (invalidate token)."""
        try:
            # In a real implementation, this would add the token to a blacklist
            # For now, we'll just log the logout
            payload = decode_token(token)
            username = payload.get("sub")
            logger.info(f"User logged out: {username}")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}", exc_info=True)
            return False

    def get_sso_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured SSO providers."""
        return self._sso_providers.copy()


# Global authentication provider instance
authentication_provider = AuthenticationProvider()
