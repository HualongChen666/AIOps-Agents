# -*- coding: utf-8 -*-
"""
Plugin Ecosystem Manager
Enterprise-grade plugin ecosystem operations and management
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class PluginActivityType(Enum):
    """Plugin activity type"""

    INSTALL = "install"
    UPDATE = "update"
    UNINSTALL = "uninstall"
    ENABLE = "enable"
    DISABLE = "disable"
    REVIEW = "review"
    DOWNLOAD = "download"


class PluginSupportLevel(Enum):
    """Plugin support level"""

    COMMUNITY = "community"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class PluginActivity:
    """Plugin activity record"""

    activity_id: str
    plugin_id: str
    activity_type: PluginActivityType
    user_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginDeveloper:
    """Plugin developer profile"""

    developer_id: str
    name: str
    email: str
    organization: Optional[str] = None
    support_level: PluginSupportLevel = PluginSupportLevel.COMMUNITY
    plugins_developed: List[str] = field(default_factory=list)
    reputation_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginEcosystemManager:
    """
    Enterprise-grade plugin ecosystem manager
    Provides plugin operations, developer support, and ecosystem management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin ecosystem manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Plugin activities
        self.activities: Dict[str, PluginActivity] = {}

        # Developer profiles
        self.developers: Dict[str, PluginDeveloper] = {}

        # Community features
        self.community_forums: Dict[str, Dict[str, Any]] = {}
        self.developer_events: Dict[str, Dict[str, Any]] = {}

        # Incentive programs
        self.incentive_programs: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self.total_activities = 0
        self.total_developers = 0

        logger.info("Plugin ecosystem manager initialized")

    def record_activity(
        self,
        plugin_id: str,
        activity_type: PluginActivityType,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PluginActivity:
        """
        Record plugin activity

        Args:
            plugin_id: Plugin ID
            activity_type: Activity type
            user_id: User ID
            metadata: Additional metadata

        Returns:
            Activity record
        """
        activity = PluginActivity(
            activity_id=f"activity_{datetime.now(timezone.utc).timestamp()}",
            plugin_id=plugin_id,
            activity_type=activity_type,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        self.activities[activity.activity_id] = activity
        self.total_activities += 1

        logger.info(f"Recorded activity: {activity_type.value} for {plugin_id}")

        return activity

    def register_developer(
        self,
        developer_id: str,
        name: str,
        email: str,
        organization: Optional[str] = None,
        support_level: PluginSupportLevel = PluginSupportLevel.COMMUNITY,
    ) -> bool:
        """
        Register plugin developer

        Args:
            developer_id: Developer ID
            name: Developer name
            email: Developer email
            organization: Organization
            support_level: Support level

        Returns:
            True if registered, False otherwise
        """
        if developer_id in self.developers:
            logger.warning(f"Developer {developer_id} already registered")
            return False

        developer = PluginDeveloper(
            developer_id=developer_id,
            name=name,
            email=email,
            organization=organization,
            support_level=support_level,
        )

        self.developers[developer_id] = developer
        self.total_developers += 1

        logger.info(f"Registered developer: {developer_id}")

        return True

    def update_developer_reputation(self, developer_id: str, score_change: float) -> bool:
        """
        Update developer reputation score

        Args:
            developer_id: Developer ID
            score_change: Score change

        Returns:
            True if updated, False otherwise
        """
        if developer_id not in self.developers:
            logger.error(f"Developer {developer_id} not found")
            return False

        developer = self.developers[developer_id]
        developer.reputation_score += score_change

        # Ensure score stays within bounds
        developer.reputation_score = max(0.0, min(5.0, developer.reputation_score))

        logger.info(f"Updated reputation for {developer_id}: {developer.reputation_score}")

        return True

    def create_community_forum(
        self, forum_id: str, title: str, description: str, plugin_id: Optional[str] = None
    ) -> bool:
        """
        Create community forum

        Args:
            forum_id: Forum ID
            title: Forum title
            description: Forum description
            plugin_id: Related plugin ID

        Returns:
            True if created, False otherwise
        """
        if forum_id in self.community_forums:
            logger.warning(f"Forum {forum_id} already exists")
            return False

        forum: Dict[str, Any] = {
            "forum_id": forum_id,
            "title": title,
            "description": description,
            "plugin_id": plugin_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "posts": [],
            "members": [],
        }

        self.community_forums[forum_id] = forum

        logger.info(f"Created community forum: {forum_id}")

        return True

    def create_developer_event(
        self,
        event_id: str,
        title: str,
        description: str,
        event_date: datetime,
        event_type: str = "webinar",
    ) -> bool:
        """
        Create developer event

        Args:
            event_id: Event ID
            title: Event title
            description: Event description
            event_date: Event date
            event_type: Event type

        Returns:
            True if created, False otherwise
        """
        if event_id in self.developer_events:
            logger.warning(f"Event {event_id} already exists")
            return False

        event = {
            "event_id": event_id,
            "title": title,
            "description": description,
            "event_date": event_date.isoformat(),
            "event_type": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attendees": [],
        }

        self.developer_events[event_id] = event

        logger.info(f"Created developer event: {event_id}")

        return True

    def create_incentive_program(
        self, program_id: str, title: str, description: str, reward_type: str, reward_amount: float
    ) -> bool:
        """
        Create incentive program

        Args:
            program_id: Program ID
            title: Program title
            description: Program description
            reward_type: Reward type
            reward_amount: Reward amount

        Returns:
            True if created, False otherwise
        """
        if program_id in self.incentive_programs:
            logger.warning(f"Program {program_id} already exists")
            return False

        program = {
            "program_id": program_id,
            "title": title,
            "description": description,
            "reward_type": reward_type,
            "reward_amount": reward_amount,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "participants": [],
        }

        self.incentive_programs[program_id] = program

        logger.info(f"Created incentive program: {program_id}")

        return True

    def get_plugin_activities(
        self, plugin_id: str, time_range: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """
        Get plugin activities

        Args:
            plugin_id: Plugin ID
            time_range: Time range to filter

        Returns:
            List of activities
        """
        activities = []

        cutoff = (
            datetime.now(timezone.utc) - time_range
            if time_range
            else datetime.min.replace(tzinfo=timezone.utc)
        )

        for activity in self.activities.values():
            if activity.plugin_id != plugin_id:
                continue
            if activity.timestamp < cutoff:
                continue

            activities.append(
                {
                    "activity_id": activity.activity_id,
                    "activity_type": activity.activity_type.value,
                    "user_id": activity.user_id,
                    "timestamp": activity.timestamp.isoformat(),
                    "metadata": activity.metadata,
                }
            )

        return sorted(activities, key=lambda x: x["timestamp"], reverse=True)

    def get_developer_stats(self, developer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get developer statistics

        Args:
            developer_id: Developer ID

        Returns:
            Developer statistics or None
        """
        if developer_id not in self.developers:
            return None

        developer = self.developers[developer_id]

        # Calculate activity stats
        plugin_activities = [
            a for a in self.activities.values() if a.metadata.get("developer_id") == developer_id
        ]

        return {
            "developer_id": developer.developer_id,
            "name": developer.name,
            "organization": developer.organization,
            "support_level": developer.support_level.value,
            "reputation_score": developer.reputation_score,
            "plugins_developed": len(developer.plugins_developed),
            "total_activities": len(plugin_activities),
            "plugin_ids": developer.plugins_developed,
        }

    def get_ecosystem_summary(self) -> Dict[str, Any]:
        """
        Get ecosystem summary

        Returns:
            Ecosystem summary
        """
        return {
            "total_activities": self.total_activities,
            "total_developers": self.total_developers,
            "total_forums": len(self.community_forums),
            "total_events": len(self.developer_events),
            "total_programs": len(self.incentive_programs),
            "developers_by_support_level": {
                level.value: len([d for d in self.developers.values() if d.support_level == level])
                for level in PluginSupportLevel
            },
        }


# Global instance
_ecosystem_manager: Optional[PluginEcosystemManager] = None


def get_ecosystem_manager() -> PluginEcosystemManager:
    """
    Get the global plugin ecosystem manager instance

    Returns:
        PluginEcosystemManager instance
    """
    global _ecosystem_manager
    if _ecosystem_manager is None:
        _ecosystem_manager = PluginEcosystemManager()
    return _ecosystem_manager
