# -*- coding: utf-8 -*-
"""Group Manager - User group management."""

import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth_db import SessionLocal, User

logger = logging.getLogger(__name__)


class UserGroup:
    """User group model."""

    def __init__(
        self,
        id: int,
        name: str,
        description: str = "",
        user_ids: Optional[List[int]] = None,
        attributes: Optional[Dict[str, str]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.user_ids = user_ids or []
        self.attributes = attributes or {}
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_ids": self.user_ids,
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GroupManager:
    """User group management operations."""

    def __init__(self):
        self._groups: Dict[int, UserGroup] = {}
        self._next_group_id = 1

    async def create_group(
        self,
        name: str,
        description: str = "",
        usernames: Optional[List[str]] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user group."""
        try:
            # Check if group name already exists
            for group in self._groups.values():
                if group.name == name:
                    logger.error(f"Group already exists: {name}")
                    return None
            
            # Get user IDs from usernames
            user_ids = []
            if usernames:
                db = SessionLocal()
                try:
                    for username in usernames:
                        user = db.query(User).filter(User.username == username).first()
                        if user:
                            user_ids.append(user.id)
                finally:
                    db.close()
            
            # Create group
            group = UserGroup(
                id=self._next_group_id,
                name=name,
                description=description,
                user_ids=user_ids,
                attributes=attributes,
            )
            self._groups[self._next_group_id] = group
            self._next_group_id += 1
            
            logger.info(f"✅ Group created: {name} (id={group.id})")
            return group.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating group {name}: {e}", exc_info=True)
            return None

    async def update_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        usernames: Optional[List[str]] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a user group."""
        try:
            if group_id not in self._groups:
                logger.error(f"Group not found: {group_id}")
                return None
            
            group = self._groups[group_id]
            
            # Update basic fields
            if name is not None:
                group.name = name
            if description is not None:
                group.description = description
            if attributes is not None:
                group.attributes = attributes
            
            # Update user IDs if usernames provided
            if usernames is not None:
                user_ids = []
                db = SessionLocal()
                try:
                    for username in usernames:
                        user = db.query(User).filter(User.username == username).first()
                        if user:
                            user_ids.append(user.id)
                finally:
                    db.close()
                group.user_ids = user_ids
            
            logger.info(f"✅ Group updated: {group.name} (id={group_id})")
            return group.to_dict()
            
        except Exception as e:
            logger.error(f"Error updating group {group_id}: {e}", exc_info=True)
            return None

    async def delete_group(self, group_id: int) -> bool:
        """Delete a user group."""
        try:
            if group_id not in self._groups:
                logger.error(f"Group not found: {group_id}")
                return False
            
            group_name = self._groups[group_id].name
            del self._groups[group_id]
            
            logger.info(f"✅ Group deleted: {group_name} (id={group_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting group {group_id}: {e}", exc_info=True)
            return False

    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get a group by ID."""
        try:
            if group_id not in self._groups:
                return None
            
            return self._groups[group_id].to_dict()
        except Exception as e:
            logger.error(f"Error getting group {group_id}: {e}", exc_info=True)
            return None

    async def list_groups(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all groups."""
        try:
            groups = list(self._groups.values())
            groups = groups[offset:offset + limit]
            return [group.to_dict() for group in groups]
        except Exception as e:
            logger.error(f"Error listing groups: {e}", exc_info=True)
            return []

    async def add_user_to_group(self, username: str, group_id: int) -> bool:
        """Add a user to a group."""
        try:
            if group_id not in self._groups:
                logger.error(f"Group not found: {group_id}")
                return False
            
            # Get user ID
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    logger.error(f"User not found: {username}")
                    return False
                
                # Add to group if not already present
                if user.id not in self._groups[group_id].user_ids:
                    self._groups[group_id].user_ids.append(user.id)
                    logger.info(f"✅ User {username} added to group {group_id}")
                    return True
                
                logger.info(f"User {username} already in group {group_id}")
                return True
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error adding user {username} to group {group_id}: {e}", exc_info=True)
            return False

    async def remove_user_from_group(self, username: str, group_id: int) -> bool:
        """Remove a user from a group."""
        try:
            if group_id not in self._groups:
                logger.error(f"Group not found: {group_id}")
                return False
            
            # Get user ID
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    logger.error(f"User not found: {username}")
                    return False
                
                # Remove from group if present
                if user.id in self._groups[group_id].user_ids:
                    self._groups[group_id].user_ids.remove(user.id)
                    logger.info(f"✅ User {username} removed from group {group_id}")
                    return True
                
                logger.info(f"User {username} not in group {group_id}")
                return True
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error removing user {username} from group {group_id}: {e}", exc_info=True)
            return False

    async def get_user_groups(self, username: str) -> List[Dict[str, Any]]:
        """Get all groups for a user."""
        try:
            # Get user ID
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    return []
                
                # Find groups containing this user
            finally:
                db.close()
            
            user_groups = []
            for group in self._groups.values():
                if user.id in group.user_ids:
                    user_groups.append(group.to_dict())
            
            return user_groups
        except Exception as e:
            logger.error(f"Error getting groups for user {username}: {e}", exc_info=True)
            return []

    async def get_group_users(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all users in a group."""
        try:
            if group_id not in self._groups:
                return []
            
            group = self._groups[group_id]
            if not group.user_ids:
                return []
            
            # Get user details
            db = SessionLocal()
            try:
                users = []
                for user_id in group.user_ids:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        users.append({
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.full_name,
                            "role": user.role,
                        })
                return users
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error getting users for group {group_id}: {e}", exc_info=True)
            return []


# Global group manager instance
group_manager = GroupManager()
