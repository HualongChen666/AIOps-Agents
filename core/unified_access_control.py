# -*- coding: utf-8 -*-
"""
Unified Access Control System
统一访问控制系统

Integrates RBAC and ABAC for comprehensive access control.
Provides policy management, permission checking, and audit logging.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from core.abac import ABACEngine, ActionType, Environment, Resource, ResourceType, Subject


class AccessControlPolicy(Enum):
    """Access control policy types"""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_AUTH = "require_auth"
    REQUIRE_MFA = "require_mfa"


@dataclass
class AccessRule:
    """Access control rule"""

    id: str
    name: str
    policy: AccessControlPolicy
    resources: List[str]
    actions: List[str]
    roles: List[str]
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0


class UnifiedAccessControl:
    """Unified access control system combining RBAC and ABAC"""

    def __init__(self, postgres_storage=None):
        """Initialize unified access control"""
        self.abac_engine = ABACEngine(postgres_storage) if postgres_storage else None
        self.access_rules: List[AccessRule] = []
        self.policy_cache: Dict[str, bool] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def add_access_rule(self, rule: AccessRule):
        """
        Add an access control rule

        Args:
            rule: Access rule to add
        """
        self.access_rules.append(rule)
        # Sort by priority (higher priority first)
        self.access_rules.sort(key=lambda x: x.priority, reverse=True)
        self._invalidate_cache()
        logger.info(f"Added access rule: {rule.name}")

    def remove_access_rule(self, rule_id: str):
        """
        Remove an access control rule

        Args:
            rule_id: ID of rule to remove
        """
        self.access_rules = [r for r in self.access_rules if r.id != rule_id]
        self._invalidate_cache()
        logger.info(f"Removed access rule: {rule_id}")

    def check_access(
        self,
        subject: Subject,
        resource: str,
        action: str,
        environment: Optional[Environment] = None,
    ) -> bool:
        """
        Check if subject has access to resource for action

        Args:
            subject: User/service requesting access
            resource: Resource being accessed
            action: Action being performed
            environment: Environmental context

        Returns:
            True if access is granted
        """
        # Check cache first
        cache_key = f"{subject.id}:{resource}:{action}"
        if cache_key in self.policy_cache:
            return self.policy_cache[cache_key]

        # Check access rules in priority order
        for rule in self.access_rules:
            if self._rule_matches(rule, subject, resource, action):
                result = rule.policy == AccessControlPolicy.ALLOW

                # Cache result
                self.policy_cache[cache_key] = result

                # Log access decision
                self._log_access_decision(
                    subject=subject,
                    resource=resource,
                    action=action,
                    granted=result,
                    rule_id=rule.id,
                )

                return result

        # Default to ABAC check
        # Map string resource type to ResourceType enum
        resource_type_map = {
            "anomaly": ResourceType.ANOMALY,
            "alert": ResourceType.ALERT,
            "metric": ResourceType.METRIC,
            "configuration": ResourceType.CONFIGURATION,
            "policy": ResourceType.POLICY,
            "workflow": ResourceType.WORKFLOW,
            "deployment": ResourceType.DEPLOYMENT,
            "service": ResourceType.SERVICE,
        }
        resource_type = resource_type_map.get(resource.lower(), ResourceType.SERVICE)
        abac_resource = Resource(id=resource, type=resource_type, attributes={})

        # Map string action to ActionType enum
        action_type_map = {
            "read": ActionType.READ,
            "write": ActionType.WRITE,
            "delete": ActionType.DELETE,
            "execute": ActionType.EXECUTE,
            "admin": ActionType.ADMIN,
        }
        abac_action = action_type_map.get(action.lower(), ActionType.READ)

        # Check if ABAC engine is available
        if self.abac_engine is None:
            # Default to deny if ABAC engine is not available
            result = False
        else:
            result = self.abac_engine.evaluate(
                subject=subject,
                resource=abac_resource,
                action=abac_action,
                environment=environment or Environment(attributes={}),
            )

        # Cache result
        self.policy_cache[cache_key] = result

        # Log access decision
        self._log_access_decision(
            subject=subject,
            resource=resource,
            action=action,
            granted=result,
            rule_id="abac_default",
        )

        return result

    def _rule_matches(self, rule: AccessRule, subject: Subject, resource: str, action: str) -> bool:
        """Check if rule matches the access request"""
        # Check resource match
        if resource not in rule.resources and "*" not in rule.resources:
            return False

        # Check action match
        if action not in rule.actions and "*" not in rule.actions:
            return False

        # Check role match
        if not any(role in subject.roles for role in rule.roles):
            return False

        # Check conditions if present
        if rule.conditions:
            for key, value in rule.conditions.items():
                subject_value = subject.get_attribute(key)
                if subject_value != value:
                    return False

        return True

    def _invalidate_cache(self):
        """Invalidate policy cache"""
        self.policy_cache.clear()
        logger.debug("Access control policy cache invalidated")

    def _log_access_decision(
        self, subject: Subject, resource: str, action: str, granted: bool, rule_id: str
    ):
        """Log access decision for audit"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subject_id": subject.id,
            "subject_type": subject.type,
            "resource": resource,
            "action": action,
            "granted": granted,
            "rule_id": rule_id,
            "subject_roles": list(subject.roles),
        }

        self.audit_log.append(log_entry)

        # Keep audit log size manageable
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]

        logger.debug(f"Access decision: {granted} for {subject.id} on {resource}:{action}")

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get access control audit log

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        return self.audit_log[-limit:]

    def get_access_stats(self) -> Dict[str, Any]:
        """
        Get access control statistics

        Returns:
            Dictionary with access statistics
        """
        total_decisions = len(self.audit_log)
        if total_decisions == 0:
            return {"total_decisions": 0}

        granted_count = sum(1 for entry in self.audit_log if entry["granted"])
        denied_count = total_decisions - granted_count

        # Count by resource
        resource_counts: Dict[str, int] = {}
        for entry in self.audit_log:
            resource = entry["resource"]
            resource_counts[resource] = resource_counts.get(resource, 0) + 1

        # Count by action
        action_counts: Dict[str, int] = {}
        for entry in self.audit_log:
            action = entry["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "total_decisions": total_decisions,
            "granted": granted_count,
            "denied": denied_count,
            "grant_rate": granted_count / total_decisions if total_decisions > 0 else 0,
            "top_resources": sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_actions": sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "active_rules": len(self.access_rules),
            "cache_size": len(self.policy_cache),
        }


# Global access control instance
unified_access_control = UnifiedAccessControl()


def require_permission(resource: str, action: str):
    """
    FastAPI dependency for permission checking

    Args:
        resource: Resource being accessed
        action: Action being performed

    Returns:
        Dependency function
    """

    async def check_access_dependency(request: Request):
        """Check access permission"""
        # Get user from request (assuming authentication middleware sets this)
        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        # Create subject
        subject = Subject(
            id=user.get("id", "unknown"),
            type=user.get("type", "user"),
            attributes=user.get("attributes", {}),
            roles=set(user.get("roles", [])),
            groups=set(user.get("groups", [])),
        )

        # Check access
        granted = unified_access_control.check_access(
            subject=subject, resource=resource, action=action
        )

        if not granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {resource}:{action}",
            )

        return True

    return Depends(check_access_dependency)


def setup_default_access_policies():
    """
    Setup default access control policies

    Returns:
        Dictionary with setup results
    """
    try:
        if unified_access_control.access_rules:
            return {
                "status": "already_initialized",
                "rules_added": 0,
                "active_rules": len(unified_access_control.access_rules),
            }
        # Add default access rules
        admin_rule = AccessRule(
            id="rule_admin_full",
            name="Admin Full Access",
            policy=AccessControlPolicy.ALLOW,
            resources=["*"],
            actions=["*"],
            roles=["admin"],
            priority=100,
        )

        read_only_rule = AccessRule(
            id="rule_read_only",
            name="Read Only Access",
            policy=AccessControlPolicy.ALLOW,
            resources=["alerts", "metrics", "topology"],
            actions=["read"],
            roles=["user", "viewer"],
            priority=50,
        )

        operator_rule = AccessRule(
            id="rule_operator",
            name="Operator Access",
            policy=AccessControlPolicy.ALLOW,
            resources=["alerts", "metrics", "workflows", "repairs"],
            actions=["read", "execute"],
            roles=["operator"],
            priority=75,
        )

        unified_access_control.add_access_rule(admin_rule)
        unified_access_control.add_access_rule(read_only_rule)
        unified_access_control.add_access_rule(operator_rule)

        logger.info("Default access policies setup completed")

        return {
            "status": "success",
            "rules_added": 3,
            "active_rules": len(unified_access_control.access_rules),
        }

    except Exception as e:
        logger.error(f"Default access policies setup failed: {e}")
        return {"status": "error", "error": str(e)}


def add_access_control_middleware(
    app: FastAPI,
    resource: str = "service",
    action: str = "read",
) -> None:
    """Add a global ABAC middleware (disabled by default; enable with AIOPS_ENFORCE_ABAC=true)."""
    enforce = os.getenv("AIOPS_ENFORCE_ABAC", "false").lower() == "true"

    @app.middleware("http")
    async def access_control_middleware(request: Request, call_next):
        # Skip CORS preflight requests (OPTIONS method)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        if enforce:
            user = getattr(request.state, "user", None)
            if not user:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                )
            subject = Subject(
                id=user.get("id", "unknown"),
                type=user.get("type", "user"),
                attributes=user.get("attributes", {}),
                roles=set(user.get("roles", [])),
                groups=set(user.get("groups", [])),
            )
            granted = unified_access_control.check_access(
                subject=subject, resource=resource, action=action
            )
            if not granted:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"Access denied to {resource}:{action}"},
                )
        return await call_next(request)
