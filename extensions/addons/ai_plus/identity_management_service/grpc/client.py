# -*- coding: utf-8 -*-
"""gRPC client for Identity Management Service."""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

SERVICE_NAME = "identity_management_service"
DEFAULT_BASE_URL = "http://localhost:8000"


class IdentityManagementClient:
    """HTTP client for Identity Management Service (using REST API)."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _call(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Make an HTTP call to the service."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, params=data)
                elif method == "POST":
                    response = await client.post(url, json=data)
                elif method == "PUT":
                    response = await client.put(url, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, params=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
            raise

    async def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        attributes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a new user."""
        data = {
            "username": username,
            "password": password,
            "email": email,
            "full_name": full_name,
            "role": role,
            "attributes": attributes,
        }
        return await self._call("POST", "/users", data)

    async def update_user(
        self,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Update user information."""
        data = {
            "email": email,
            "full_name": full_name,
            "role": role,
            "disabled": disabled,
            "attributes": attributes,
        }
        return await self._call("PUT", f"/users/{username}", data)

    async def delete_user(self, username: str) -> Dict[str, Any]:
        """Delete a user."""
        return await self._call("DELETE", f"/users/{username}")

    async def get_user(self, username: str) -> Dict[str, Any]:
        """Get user by username."""
        return await self._call("GET", f"/users/{username}")

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List users with optional filtering."""
        params = {
            "limit": limit,
            "offset": offset,
            "role": role,
            "disabled": disabled,
        }
        return await self._call("GET", "/users", params)

    async def set_user_attribute(
        self, username: str, key: str, value: str
    ) -> Dict[str, Any]:
        """Set a user attribute."""
        data = {"key": key, "value": value}
        return await self._call("POST", f"/users/{username}/attributes", data)

    async def delete_user_attribute(self, username: str, key: str) -> Dict[str, Any]:
        """Delete a user attribute."""
        return await self._call("DELETE", f"/users/{username}/attributes/{key}")

    async def enable_mfa(self, username: str) -> Dict[str, Any]:
        """Enable MFA for a user."""
        return await self._call("POST", f"/users/{username}/mfa/enable")

    async def disable_mfa(self, username: str) -> Dict[str, Any]:
        """Disable MFA for a user."""
        return await self._call("POST", f"/users/{username}/mfa/disable")

    async def verify_mfa(self, username: str, code: str) -> Dict[str, Any]:
        """Verify MFA code for a user."""
        data = {"code": code}
        return await self._call("POST", f"/users/{username}/mfa/verify", data)

    async def create_user_group(
        self,
        name: str,
        description: str = "",
        usernames: Optional[list] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a user group."""
        data = {
            "name": name,
            "description": description,
            "usernames": usernames,
            "attributes": attributes,
        }
        return await self._call("POST", "/groups", data)

    async def update_user_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        usernames: Optional[list] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Update a user group."""
        data = {
            "name": name,
            "description": description,
            "usernames": usernames,
            "attributes": attributes,
        }
        return await self._call("PUT", f"/groups/{group_id}", data)

    async def delete_user_group(self, group_id: int) -> Dict[str, Any]:
        """Delete a user group."""
        return await self._call("DELETE", f"/groups/{group_id}")

    async def get_user_group(self, group_id: int) -> Dict[str, Any]:
        """Get a group by ID."""
        return await self._call("GET", f"/groups/{group_id}")

    async def list_user_groups(
        self, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """List all groups."""
        params = {"limit": limit, "offset": offset}
        return await self._call("GET", "/groups", params)

    async def add_user_to_group(
        self, username: str, group_id: int
    ) -> Dict[str, Any]:
        """Add a user to a group."""
        data = {"username": username, "group_id": group_id}
        return await self._call("POST", "/groups/members", data)

    async def remove_user_from_group(
        self, username: str, group_id: int
    ) -> Dict[str, Any]:
        """Remove a user from a group."""
        data = {"username": username, "group_id": group_id}
        return await self._call("DELETE", "/groups/members", data)

    async def configure_sso(
        self,
        provider: str,
        client_id: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Configure SSO provider."""
        data = {
            "provider": provider,
            "client_id": client_id,
            "metadata": metadata,
        }
        return await self._call("POST", "/sso/configure", data)

    async def sso_login(self, provider: str, token: str) -> Dict[str, Any]:
        """Perform SSO login."""
        data = {"provider": provider, "token": token}
        return await self._call("POST", "/sso/login", data)

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return await self._call("GET", "/health")


# Convenience function to create a client
def create_client(base_url: str = DEFAULT_BASE_URL) -> IdentityManagementClient:
    """Create an Identity Management Service client."""
    return IdentityManagementClient(base_url=base_url)
