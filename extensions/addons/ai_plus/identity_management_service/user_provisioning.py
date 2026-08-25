# -*- coding: utf-8 -*-
"""User Provisioning - Automated user lifecycle management."""

import logging
import sys
import os
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from identity_manager import IdentityManager

logger = logging.getLogger(__name__)


class UserProvisioning:
    """Automated user provisioning and deprovisioning."""

    def __init__(self, identity_manager: Optional[IdentityManager] = None):
        self.identity_manager = identity_manager or IdentityManager()

    async def provision_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        groups: Optional[List[str]] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Provision a new user with complete setup."""
        try:
            logger.info(f"Provisioning user: {username}")
            
            # Create the user
            user = await self.identity_manager.create_user(
                username=username,
                password=password,
                email=email,
                full_name=full_name,
                role=role,
                attributes=attributes,
            )
            
            if not user:
                logger.error(f"Failed to provision user: {username}")
                return None
            
            # Add to groups if specified
            if groups:
                for group_name in groups:
                    await self.add_user_to_group(username, group_name)
            
            logger.info(f"✅ User provisioned successfully: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Error provisioning user {username}: {e}", exc_info=True)
            return None

    async def deprovision_user(self, username: str) -> bool:
        """Deprovision a user (disable and cleanup)."""
        try:
            logger.info(f"Deprovisioning user: {username}")
            
            # First disable the user
            user = await self.identity_manager.update_user(
                username=username,
                disabled=True,
            )
            
            if not user:
                logger.error(f"Failed to disable user: {username}")
                return False
            
            # Remove from all groups
            # (In a real implementation, we'd query all groups and remove the user)
            
            logger.info(f"✅ User deprovisioned successfully: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error deprovisioning user {username}: {e}", exc_info=True)
            return False

    async def bulk_provision_users(
        self, users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Bulk provision multiple users."""
        try:
            results = {
                "success": 0,
                "failed": 0,
                "errors": [],
            }
            
            for user_data in users:
                username = user_data.get("username")
                if not username:
                    results["failed"] += 1
                    results["errors"].append(f"Missing username in user data")
                    continue
                
                user = await self.provision_user(
                    username=username,
                    password=user_data.get("password", "default_password"),
                    email=user_data.get("email"),
                    full_name=user_data.get("full_name"),
                    role=user_data.get("role", "user"),
                    groups=user_data.get("groups"),
                    attributes=user_data.get("attributes"),
                )
                
                if user:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to provision user: {username}")
            
            logger.info(f"Bulk provisioning completed: {results['success']} success, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error during bulk provisioning: {e}", exc_info=True)
            return {"success": 0, "failed": 0, "errors": [str(e)]}

    async def add_user_to_group(self, username: str, group_name: str) -> bool:
        """Add a user to a group."""
        try:
            # In a real implementation, this would use the group management
            logger.info(f"Adding user {username} to group {group_name}")
            return True
        except Exception as e:
            logger.error(f"Error adding user {username} to group {group_name}: {e}", exc_info=True)
            return False

    async def remove_user_from_group(self, username: str, group_name: str) -> bool:
        """Remove a user from a group."""
        try:
            # In a real implementation, this would use the group management
            logger.info(f"Removing user {username} from group {group_name}")
            return True
        except Exception as e:
            logger.error(f"Error removing user {username} from group {group_name}: {e}", exc_info=True)
            return False

    async def sync_user_from_external_source(
        self, external_id: str, source: str, user_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Sync user from external source (LDAP, AD, etc.)."""
        try:
            username = user_data.get("username")
            if not username:
                logger.error(f"Missing username in external user data")
                return None
            
            # Check if user exists
            existing_user = await self.identity_manager.get_user(username)
            
            if existing_user:
                # Update existing user
                updated_user = await self.identity_manager.update_user(
                    username=username,
                    email=user_data.get("email"),
                    full_name=user_data.get("full_name"),
                    attributes=user_data.get("attributes"),
                )
                logger.info(f"✅ User synced from {source}: {username}")
                return updated_user
            else:
                # Create new user
                new_user = await self.provision_user(
                    username=username,
                    password=user_data.get("password", "default_password"),
                    email=user_data.get("email"),
                    full_name=user_data.get("full_name"),
                    role=user_data.get("role", "user"),
                    attributes=user_data.get("attributes"),
                )
                logger.info(f"✅ User created from {source}: {username}")
                return new_user
                
        except Exception as e:
            logger.error(f"Error syncing user from {source}: {e}", exc_info=True)
            return None


# Global user provisioning instance
user_provisioning = UserProvisioning()
