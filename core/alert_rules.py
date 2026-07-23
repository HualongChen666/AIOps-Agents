# -*- coding: utf-8 -*-
"""Alert rules management for AIOps Agent.

This module provides alert rule configuration, evaluation, and management
for enterprise-grade monitoring and alerting.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

import config

# Alert rule storage
_alert_rules: Dict[str, Dict[str, Any]] = config.DEFAULT_ALERT_RULES.copy()


def load_alert_rules(rules: Dict[str, Dict[str, Any]]) -> None:
    """Load alert rules from configuration.

    Args:
        rules: Dictionary of alert rules
    """
    global _alert_rules
    _alert_rules = rules.copy()
    logger.info(f"Loaded {len(_alert_rules)} alert rules")


def get_alert_rule(rule_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific alert rule.

    Args:
        rule_name: Name of the alert rule

    Returns:
        Alert rule configuration, or None if not found
    """
    return _alert_rules.get(rule_name)


def get_all_alert_rules() -> Dict[str, Dict[str, Any]]:
    """Get all alert rules.

    Returns:
        Dictionary of all alert rules
    """
    return _alert_rules.copy()


def add_alert_rule(rule_name: str, rule_config: Dict[str, Any]) -> None:
    """Add or update an alert rule.

    Args:
        rule_name: Name of the alert rule
        rule_config: Configuration for the alert rule
    """
    _alert_rules[rule_name] = rule_config
    logger.info(f"Added/updated alert rule: {rule_name}")


def remove_alert_rule(rule_name: str) -> bool:
    """Remove an alert rule.

    Args:
        rule_name: Name of the alert rule to remove

    Returns:
        True if rule was removed, False if not found
    """
    if rule_name in _alert_rules:
        del _alert_rules[rule_name]
        logger.info(f"Removed alert rule: {rule_name}")
        return True
    return False


def evaluate_alert_rule(
    rule_name: str, current_value: float, metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Evaluate an alert rule against current metrics.

    Args:
        rule_name: Name of the alert rule to evaluate
        current_value: Current metric value
        metadata: Optional additional metadata

    Returns:
        Alert dictionary if rule triggered, None otherwise
    """
    rule = get_alert_rule(rule_name)
    if not rule:
        logger.warning(f"Alert rule not found: {rule_name}")
        return None

    if not rule.get("enabled", True):
        return None

    threshold = rule.get("threshold", 0)
    severity = rule.get("severity", "warning")

    # Check if threshold is exceeded
    if current_value >= threshold:
        return {
            "rule_name": rule_name,
            "severity": severity,
            "threshold": threshold,
            "current_value": current_value,
            "description": rule.get("description", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

    return None


def evaluate_all_rules(
    metrics: Dict[str, float], metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Evaluate all alert rules against current metrics.

    Args:
        metrics: Dictionary of metric names to values
        metadata: Optional additional metadata

    Returns:
        List of triggered alerts
    """
    triggered_alerts = []

    for rule_name, rule_config in _alert_rules.items():
        if not rule_config.get("enabled", True):
            continue

        # Map rule names to metric names
        metric_name = rule_name.replace("_critical", "").replace("_high", "")
        if metric_name in metrics:
            alert = evaluate_alert_rule(rule_name, metrics[metric_name], metadata)
            if alert:
                triggered_alerts.append(alert)

    return triggered_alerts


def get_enabled_rules() -> List[str]:
    """Get list of enabled alert rule names.

    Returns:
        List of enabled rule names
    """
    return [name for name, config in _alert_rules.items() if config.get("enabled", True)]


def disable_rule(rule_name: str) -> bool:
    """Disable an alert rule.

    Args:
        rule_name: Name of the alert rule to disable

    Returns:
        True if rule was disabled, False if not found
    """
    rule = get_alert_rule(rule_name)
    if rule:
        rule["enabled"] = False
        logger.info(f"Disabled alert rule: {rule_name}")
        return True
    return False


def enable_rule(rule_name: str) -> bool:
    """Enable an alert rule.

    Args:
        rule_name: Name of the alert rule to enable

    Returns:
        True if rule was enabled, False if not found
    """
    rule = get_alert_rule(rule_name)
    if rule:
        rule["enabled"] = True
        logger.info(f"Enabled alert rule: {rule_name}")
        return True
    return False


def reset_alert_rules() -> None:
    """Reset alert rules to default configuration."""
    global _alert_rules
    _alert_rules = config.DEFAULT_ALERT_RULES.copy()
    logger.info("Reset alert rules to default configuration")


__all__ = [
    "load_alert_rules",
    "get_alert_rule",
    "get_all_alert_rules",
    "add_alert_rule",
    "remove_alert_rule",
    "evaluate_alert_rule",
    "evaluate_all_rules",
    "get_enabled_rules",
    "disable_rule",
    "enable_rule",
    "reset_alert_rules",
]
