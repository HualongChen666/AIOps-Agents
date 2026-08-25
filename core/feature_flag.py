# -*- coding: utf-8 -*-
"""
Feature Flag System for AIOps Platform
Provides dynamic feature toggling with support for user targeting, percentage rollouts, and A/B testing  # noqa: E501
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FlagType(Enum):
    """Feature flag type enumeration"""

    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    MULTIVARIATE = "multivariate"


class FlagStatus(Enum):
    """Feature flag status enumeration"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    ARCHIVED = "archived"


@dataclass
class FlagRule:
    """Represents a feature flag rule"""

    name: str
    conditions: Dict[str, Any]
    enabled: bool = True

    def matches(self, context: Dict[str, Any]) -> bool:
        """
        Check if rule matches context

        Args:
            context: Evaluation context

        Returns:
            True if matches
        """
        for key, condition in self.conditions.items():
            if key not in context:
                return False

            value = context[key]

            if isinstance(condition, dict):
                if "equals" in condition and value != condition["equals"]:
                    return False
                elif "in" in condition and value not in condition["in"]:
                    return False
                elif "contains" in condition and condition["contains"] not in str(value):
                    return False
                elif "gt" in condition and not (value > condition["gt"]):
                    return False
                elif "lt" in condition and not (value < condition["lt"]):
                    return False
            elif value != condition:
                return False

        return True


@dataclass
class FeatureFlag:
    """Represents a feature flag"""

    key: str
    name: str
    description: str
    flag_type: FlagType
    status: FlagStatus
    fallback_value: Any
    rules: List[FlagRule]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "flag_type": self.flag_type.value,
            "status": self.status.value,
            "fallback_value": self.fallback_value,
            "rules": [
                {"name": rule.name, "conditions": rule.conditions, "enabled": rule.enabled}
                for rule in self.rules
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class FeatureFlagManager:
    """
    Feature Flag Manager

    Manages feature flags with support for:
    - Boolean flags
    - Percentage rollouts
    - Multivariate flags (A/B testing)
    - User targeting
    - Rule-based evaluation
    """

    def __init__(self, storage=None):
        """
        Initialize Feature Flag Manager

        Args:
            storage: Optional storage backend for persistence
        """
        self.storage = storage
        self._flags: Dict[str, FeatureFlag] = {}
        self._is_initialized = False

        logger.info("Feature Flag Manager initialized")

    def initialize(self) -> bool:
        """
        Initialize feature flag manager

        Returns:
            True if initialization successful
        """
        try:
            if self.storage:
                self._load_flags_from_storage()

            self._is_initialized = True
            logger.info("Feature Flag Manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize feature flag manager: {e}")
            return False

    def _load_flags_from_storage(self) -> None:
        """Load flags from storage"""
        if self.storage:
            try:
                flags_data = self.storage.load("feature_flags", {})
                for key, flag_dict in flags_data.items():
                    self._flags[key] = FeatureFlag(
                        key=flag_dict["key"],
                        name=flag_dict["name"],
                        description=flag_dict["description"],
                        flag_type=FlagType(flag_dict["flag_type"]),
                        status=FlagStatus(flag_dict["status"]),
                        fallback_value=flag_dict["fallback_value"],
                        rules=[
                            FlagRule(
                                name=rule["name"],
                                conditions=rule["conditions"],
                                enabled=rule["enabled"],
                            )
                            for rule in flag_dict["rules"]
                        ],
                        created_at=datetime.fromisoformat(flag_dict["created_at"]),
                        updated_at=datetime.fromisoformat(flag_dict["updated_at"]),
                        metadata=flag_dict["metadata"],
                    )

                logger.info(f"Loaded {len(self._flags)} feature flags from storage")
            except Exception as e:
                logger.error(f"Failed to load flags from storage: {e}")

    def _save_flag_to_storage(self, flag: FeatureFlag) -> None:
        """Save flag to storage"""
        if self.storage:
            try:
                flags_data = {key: flag_obj.to_dict() for key, flag_obj in self._flags.items()}
                self.storage.save("feature_flags", flags_data)
                logger.debug(f"Saved feature flag {flag.key} to storage")
            except Exception as e:
                logger.error(f"Failed to save flag to storage: {e}")

    def create_flag(
        self,
        key: str,
        name: str,
        description: str,
        flag_type: FlagType,
        fallback_value: Any = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[FeatureFlag]:
        """
        Create a new feature flag

        Args:
            key: Flag key (unique identifier)
            name: Flag name
            description: Flag description
            flag_type: Flag type
            fallback_value: Default value
            metadata: Optional metadata

        Returns:
            FeatureFlag or None if failed
        """
        if key in self._flags:
            logger.error(f"Flag already exists: {key}")
            return None

        flag = FeatureFlag(
            key=key,
            name=name,
            description=description,
            flag_type=flag_type,
            status=FlagStatus.ENABLED,
            fallback_value=fallback_value,
            rules=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {},
        )

        self._flags[key] = flag

        if self.storage:
            self._save_flag_to_storage(flag)

        logger.info(f"Created feature flag: {key}")
        return flag

    def update_flag(
        self,
        key: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[FlagStatus] = None,
        fallback_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing feature flag

        Args:
            key: Flag key
            name: New name
            description: New description
            status: New status
            fallback_value: New default value
            metadata: New metadata

        Returns:
            True if successful
        """
        if key not in self._flags:
            logger.error(f"Flag not found: {key}")
            return False

        flag = self._flags[key]

        if name is not None:
            flag.name = name
        if description is not None:
            flag.description = description
        if status is not None:
            flag.status = status
        if fallback_value is not None:
            flag.fallback_value = fallback_value
        if metadata is not None:
            flag.metadata = metadata

        flag.updated_at = datetime.now()

        if self.storage:
            self._save_flag_to_storage(flag)

        logger.info(f"Updated feature flag: {key}")
        return True

    def delete_flag(self, key: str) -> bool:
        """
        Delete a feature flag

        Args:
            key: Flag key

        Returns:
            True if successful
        """
        if key not in self._flags:
            logger.error(f"Flag not found: {key}")
            return False

        del self._flags[key]
        logger.info(f"Deleted feature flag: {key}")
        return True

    def add_rule(self, key: str, rule: FlagRule) -> bool:
        """
        Add a rule to a feature flag

        Args:
            key: Flag key
            rule: Rule to add

        Returns:
            True if successful
        """
        if key not in self._flags:
            logger.error(f"Flag not found: {key}")
            return False

        self._flags[key].rules.append(rule)
        self._flags[key].updated_at = datetime.now()

        if self.storage:
            self._save_flag_to_storage(self._flags[key])

        logger.info(f"Added rule to flag: {key}")
        return True

    def remove_rule(self, key: str, rule_name: str) -> bool:
        """
        Remove a rule from a feature flag

        Args:
            key: Flag key
            rule_name: Rule name to remove

        Returns:
            True if successful
        """
        if key not in self._flags:
            logger.error(f"Flag not found: {key}")
            return False

        flag = self._flags[key]
        flag.rules = [rule for rule in flag.rules if rule.name != rule_name]
        flag.updated_at = datetime.now()

        if self.storage:
            self._save_flag_to_storage(flag)

        logger.info(f"Removed rule from flag: {key}")
        return True

    def evaluate(
        self, key: str, context: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None
    ) -> Any:
        """
        Evaluate a feature flag

        Args:
            key: Flag key
            context: Evaluation context (attributes, environment, etc.)
            user_id: User ID for percentage rollouts

        Returns:
            Flag value
        """
        if key not in self._flags:
            logger.warning(f"Flag not found: {key}, returning default False")
            return False

        flag = self._flags[key]

        if flag.status == FlagStatus.DISABLED:
            return False

        if flag.status == FlagStatus.ARCHIVED:
            return False

        # Check rules in order
        for rule in flag.rules:
            if not rule.enabled:
                continue

            if context and rule.matches(context):
                return True

        # Handle percentage rollouts
        if flag.flag_type == FlagType.PERCENTAGE and user_id:
            return self._evaluate_percentage(flag, user_id)

        # Handle multivariate flags
        if flag.flag_type == FlagType.MULTIVARIATE and user_id:
            return self._evaluate_multivariate(flag, user_id)

        # Return default value
        return flag.fallback_value

    def _evaluate_percentage(self, flag: FeatureFlag, user_id: str) -> bool:
        """
        Evaluate percentage rollout

        Args:
            flag: Feature flag
            user_id: User ID

        Returns:
            True if user is in rollout percentage
        """
        percentage = flag.fallback_value if isinstance(flag.fallback_value, (int, float)) else 0

        # Hash user ID to get consistent assignment
        hash_value = int(hashlib.sha256(f"{flag.key}:{user_id}".encode()).hexdigest(), 16)
        hash_percentage = (hash_value % 100) / 100.0

        return hash_percentage < percentage

    def _evaluate_multivariate(self, flag: FeatureFlag, user_id: str) -> Any:
        """
        Evaluate multivariate flag (A/B testing)

        Args:
            flag: Feature flag
            user_id: User ID

        Returns:
            Variant value
        """
        variants = flag.metadata.get("variants", [])
        if not variants:
            return flag.fallback_value

        # Hash user ID to get consistent variant assignment
        hash_value = int(hashlib.sha256(f"{flag.key}:{user_id}".encode()).hexdigest(), 16)
        hash_percentage = (hash_value % 100) / 100.0

        # Calculate cumulative percentages
        cumulative = 0.0
        for variant in variants:
            cumulative += variant.get("percentage", 0)
            if hash_percentage < cumulative:
                return variant.get("value", flag.fallback_value)

        return flag.fallback_value

    def get_flag(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get feature flag details

        Args:
            key: Flag key

        Returns:
            Flag dictionary or None
        """
        if key in self._flags:
            return self._flags[key].to_dict()
        return None

    def list_flags(self, status: Optional[FlagStatus] = None) -> List[Dict[str, Any]]:
        """
        List all feature flags

        Args:
            status: Optional status filter

        Returns:
            List of flag dictionaries
        """
        flags = list(self._flags.values())

        if status:
            flags = [flag for flag in flags if flag.status == status]

        return [flag.to_dict() for flag in flags]

    def is_enabled(
        self, key: str, context: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None
    ) -> bool:
        """
        Check if a boolean flag is enabled

        Args:
            key: Flag key
            context: Evaluation context
            user_id: User ID

        Returns:
            True if enabled
        """
        return bool(self.evaluate(key, context, user_id))

    def get_variant(self, key: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get variant for multivariate flag

        Args:
            key: Flag key
            user_id: User ID
            context: Evaluation context

        Returns:
            Variant value
        """
        return self.evaluate(key, context, user_id)


def create_feature_flag_manager(storage=None) -> Optional[FeatureFlagManager]:
    """
    Factory function to create Feature Flag Manager

    Args:
        storage: Optional storage backend

    Returns:
        FeatureFlagManager instance or None if failed
    """
    try:
        manager = FeatureFlagManager(storage)
        if manager.initialize():
            return manager
        return None
    except Exception as e:
        logger.error(f"Failed to create feature flag manager: {e}")
        return None
