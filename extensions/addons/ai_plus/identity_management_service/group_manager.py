# -*- coding: utf-8 -*-
"""Group Manager - User group management backed by the persistent auth store."""

import json
import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth_db import Group, GroupMembership, SessionLocal, User

logger = logging.getLogger(__name__)


class UserGroup:
    """User group value object (serialisable view of a persisted ``Group``)."""

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
    """User group management operations persisted in ``core.auth_db``."""

    def _serialize(self, db: Session, group: Group) -> Dict[str, Any]:
        memberships = (
            db.query(GroupMembership).filter(GroupMembership.group_id == group.id).all()
        )
        attributes = {}
        if group.attributes:
            try:
                attributes = json.loads(group.attributes)
            except (TypeError, ValueError):
                attributes = {}
        view = UserGroup(
            id=group.id,
            name=group.name,
            description=group.description or "",
            user_ids=[m.user_id for m in memberships],
            attributes=attributes,
            created_at=group.created_at,
        )
        return view.to_dict()

    async def create_group(
        self,
        name: str,
        description: str = "",
        usernames: Optional[List[str]] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user group."""
        db = SessionLocal()
        try:
            existing = db.query(Group).filter(Group.name == name).first()
            if existing is not None:
                logger.error(f"Group already exists: {name}")
                return None

            group = Group(
                name=name,
                description=description,
                attributes=json.dumps(attributes) if attributes else None,
            )
            db.add(group)
            db.flush()

            if usernames:
                for username in usernames:
                    user = db.query(User).filter(User.username == username).first()
                    if user:
                        db.add(GroupMembership(group_id=group.id, user_id=user.id))

            db.commit()
            db.refresh(group)
            logger.info(f"✅ Group created: {name} (id={group.id})")
            return self._serialize(db, group)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating group {name}: {e}", exc_info=True)
            return None
        finally:
            db.close()

    async def update_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        usernames: Optional[List[str]] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a user group."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group is None:
                logger.error(f"Group not found: {group_id}")
                return None

            if name is not None:
                group.name = name
            if description is not None:
                group.description = description
            if attributes is not None:
                group.attributes = json.dumps(attributes)

            if usernames is not None:
                db.query(GroupMembership).filter(
                    GroupMembership.group_id == group_id
                ).delete()
                for username in usernames:
                    user = db.query(User).filter(User.username == username).first()
                    if user:
                        db.add(GroupMembership(group_id=group_id, user_id=user.id))

            db.commit()
            db.refresh(group)
            logger.info(f"✅ Group updated: {group.name} (id={group_id})")
            return self._serialize(db, group)
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating group {group_id}: {e}", exc_info=True)
            return None
        finally:
            db.close()

    async def delete_group(self, group_id: int) -> bool:
        """Delete a user group and its memberships."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group is None:
                logger.error(f"Group not found: {group_id}")
                return False

            group_name = group.name
            db.query(GroupMembership).filter(
                GroupMembership.group_id == group_id
            ).delete()
            db.delete(group)
            db.commit()
            logger.info(f"✅ Group deleted: {group_name} (id={group_id})")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting group {group_id}: {e}", exc_info=True)
            return False
        finally:
            db.close()

    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get a group by ID."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group is None:
                return None
            return self._serialize(db, group)
        except Exception as e:
            logger.error(f"Error getting group {group_id}: {e}", exc_info=True)
            return None
        finally:
            db.close()

    async def get_group_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a group by its (unique) name."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.name == name).first()
            if group is None:
                return None
            return self._serialize(db, group)
        except Exception as e:
            logger.error(f"Error getting group by name {name}: {e}", exc_info=True)
            return None
        finally:
            db.close()

    async def list_groups(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all groups."""
        db = SessionLocal()
        try:
            groups = (
                db.query(Group)
                .order_by(Group.id)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._serialize(db, group) for group in groups]
        except Exception as e:
            logger.error(f"Error listing groups: {e}", exc_info=True)
            return []
        finally:
            db.close()

    async def add_user_to_group(self, username: str, group_id: int) -> bool:
        """Add a user to a group (persisted)."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group is None:
                logger.error(f"Group not found: {group_id}")
                return False

            user = db.query(User).filter(User.username == username).first()
            if user is None:
                logger.error(f"User not found: {username}")
                return False

            existing = (
                db.query(GroupMembership)
                .filter(
                    GroupMembership.group_id == group_id,
                    GroupMembership.user_id == user.id,
                )
                .first()
            )
            if existing is None:
                db.add(GroupMembership(group_id=group_id, user_id=user.id))
                db.commit()
                logger.info(f"✅ User {username} added to group {group_id}")
            else:
                logger.info(f"User {username} already in group {group_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding user {username} to group {group_id}: {e}", exc_info=True)
            return False
        finally:
            db.close()

    async def remove_user_from_group(self, username: str, group_id: int) -> bool:
        """Remove a user from a group (persisted)."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group is None:
                logger.error(f"Group not found: {group_id}")
                return False

            user = db.query(User).filter(User.username == username).first()
            if user is None:
                logger.error(f"User not found: {username}")
                return False

            deleted = (
                db.query(GroupMembership)
                .filter(
                    GroupMembership.group_id == group_id,
                    GroupMembership.user_id == user.id,
                )
                .delete()
            )
            db.commit()
            if deleted:
                logger.info(f"✅ User {username} removed from group {group_id}")
            else:
                logger.info(f"User {username} not in group {group_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(
                f"Error removing user {username} from group {group_id}: {e}", exc_info=True
            )
            return False
        finally:
            db.close()

    async def get_user_groups(self, username: str) -> List[Dict[str, Any]]:
        """Get all groups for a user."""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user is None:
                return []

            memberships = (
                db.query(GroupMembership)
                .filter(GroupMembership.user_id == user.id)
                .all()
            )
            result = []
            for membership in memberships:
                group = db.query(Group).filter(Group.id == membership.group_id).first()
                if group is not None:
                    result.append(self._serialize(db, group))
            return result
        except Exception as e:
            logger.error(f"Error getting groups for user {username}: {e}", exc_info=True)
            return []
        finally:
            db.close()

    async def get_group_users(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all users in a group."""
        db = SessionLocal()
        try:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group is None:
                return []

            memberships = (
                db.query(GroupMembership)
                .filter(GroupMembership.group_id == group_id)
                .all()
            )
            users = []
            for membership in memberships:
                user = db.query(User).filter(User.id == membership.user_id).first()
                if user:
                    users.append(
                        {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.full_name,
                            "role": user.role,
                        }
                    )
            return users
        except Exception as e:
            logger.error(f"Error getting users for group {group_id}: {e}", exc_info=True)
            return []
        finally:
            db.close()


# Global group manager instance
group_manager = GroupManager()
