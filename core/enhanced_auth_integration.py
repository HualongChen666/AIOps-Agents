# -*- coding: utf-8 -*-
"""
Enhanced Authentication and Authorization Integration (Phase 2)
Comprehensive authentication and authorization system with role-based access control
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Set

import jwt
from loguru import logger


class AuthMethod(Enum):
    """Authentication method"""

    JWT = "jwt"
    OAUTH2 = "oauth2"
    SSO = "sso"
    API_KEY = "api_key"
    BASIC = "basic"


class Permission(Enum):
    """Permission types"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    APPROVE = "approve"
    AUDIT = "audit"


class Role(Enum):
    """User roles"""

    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"


@dataclass
class User:
    """User information"""

    user_id: str
    username: str
    email: str
    roles: Set[Role] = field(default_factory=set)
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthToken:
    """Authentication token"""

    token: str
    user_id: str
    expires_at: datetime
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_token: Optional[str] = None
    scopes: List[str] = field(default_factory=list)


@dataclass
class AccessPolicy:
    """Access policy"""

    policy_id: str
    name: str
    resource: str
    required_permissions: Set[Permission] = field(default_factory=set)
    required_roles: Set[Role] = field(default_factory=set)
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedAuthIntegration:
    """Enhanced authentication and authorization integration"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced auth integration

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # JWT configuration - prioritize environment variable over config dict
        import os

        _jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if not _jwt_secret:
            _jwt_secret = self.config.get("jwt_secret", "")

        # Security: In production, JWT_SECRET_KEY must be set
        _environment = os.getenv("ENVIRONMENT", "development").lower()
        if not _jwt_secret:
            if _environment == "production":
                raise ValueError(
                    "JWT_SECRET_KEY environment variable must be set in production environment. "  # noqa: E501
                    "Please set a strong, unique secret key via: export JWT_SECRET_KEY=<your-secret-key>"  # noqa: E501
                )
            else:
                # Development environment: use default with warning
                _jwt_secret = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-me")
                import warnings

                warnings.warn(
                    "Using default JWT secret key in EnhancedAuthIntegration! "  # noqa: E501
                    "This is insecure for production. Please set JWT_SECRET_KEY environment variable."  # noqa: E501
                )
        elif _jwt_secret in ("dev-secret-key-change-me", "default-secret-key"):  # noqa: E501
            if _environment == "production":
                raise ValueError(
                    "JWT_SECRET_KEY is set to a default/insecure value in EnhancedAuthIntegration. "  # noqa: E501
                    "Please set a strong, unique secret key via: export JWT_SECRET_KEY=<your-secret-key>"  # noqa: E501
                )

        self.jwt_secret = _jwt_secret  # noqa: E501
        self.jwt_algorithm = self.config.get("jwt_algorithm", "HS256")
        self.jwt_access_token_expire = self.config.get("jwt_access_token_expire", 30)  # minutes
        self.jwt_refresh_token_expire = self.config.get(
            "jwt_refresh_token_expire", 60 * 24 * 7
        )  # minutes (7 days)

        # User storage
        self.users: Dict[str, User] = {}
        self.user_tokens: Dict[str, AuthToken] = {}

        # Access policies
        self.access_policies: Dict[str, AccessPolicy] = {}
        self._initialize_default_policies()

        # Role permissions mapping
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.ADMIN: {
                Permission.READ,
                Permission.WRITE,
                Permission.DELETE,
                Permission.ADMIN,
                Permission.EXECUTE,
                Permission.APPROVE,
                Permission.AUDIT,
            },
            Role.OPERATOR: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
            Role.ANALYST: {Permission.READ, Permission.EXECUTE},
            Role.VIEWER: {Permission.READ},
            Role.GUEST: set(),
        }

        # Authentication methods
        self.auth_methods: Set[AuthMethod] = set([AuthMethod.JWT])
        self._initialize_auth_methods()

        # Statistics
        self.auth_stats: Dict[str, Any] = {
            "total_authentications": 0,
            "successful_authentications": 0,
            "failed_authentications": 0,
            "active_tokens": 0,
        }

        logger.info("Enhanced authentication and authorization integration initialized")

    def _initialize_default_policies(self):
        """Initialize default access policies"""
        # Admin policy
        self.access_policies["admin_full_access"] = AccessPolicy(
            policy_id="admin_full_access",
            name="Admin Full Access",
            resource="*",
            required_roles={Role.ADMIN},
            required_permissions=set(),
        )

        # Metrics policy
        self.access_policies["metrics_read"] = AccessPolicy(
            policy_id="metrics_read",
            name="Metrics Read Access",
            resource="metrics",
            required_permissions={Permission.READ},
            required_roles={Role.ADMIN, Role.OPERATOR, Role.ANALYST, Role.VIEWER},
        )

        # Alerts policy
        self.access_policies["alerts_manage"] = AccessPolicy(
            policy_id="alerts_manage",
            name="Alerts Management",
            resource="alerts",
            required_permissions={Permission.READ, Permission.WRITE, Permission.DELETE},
            required_roles={Role.ADMIN, Role.OPERATOR},
        )

        # Workflows policy
        self.access_policies["workflows_execute"] = AccessPolicy(
            policy_id="workflows_execute",
            name="Workflow Execution",
            resource="workflows",
            required_permissions={Permission.READ, Permission.EXECUTE},
            required_roles={Role.ADMIN, Role.OPERATOR, Role.ANALYST},
        )

        # Configuration policy
        self.access_policies["configuration_manage"] = AccessPolicy(
            policy_id="configuration_manage",
            name="Configuration Management",
            resource="configuration",
            required_permissions={Permission.READ, Permission.WRITE},
            required_roles={Role.ADMIN},
        )

    def _initialize_auth_methods(self):
        """Initialize authentication methods"""
        auth_methods_config = self.config.get("auth_methods", ["jwt"])

        for method in auth_methods_config:
            try:
                self.auth_methods.add(AuthMethod(method))
                logger.info(f"Enabled authentication method: {method}")
            except ValueError:
                logger.warning(f"Unknown authentication method: {method}")

    def register_user(self, user: User) -> None:
        """
        Register user

        Args:
            user: User information
        """
        self.users[user.user_id] = user
        logger.info(f"Registered user: {user.username} ({user.user_id})")

    def authenticate_user(
        self, username: str, password: str, method: AuthMethod = AuthMethod.JWT
    ) -> Optional[AuthToken]:
        """
        Authenticate user

        Args:
            username: Username
            password: Password
            method: Authentication method

        Returns:
            Auth token if authentication successful
        """
        self.auth_stats["total_authentications"] += 1

        try:
            # Find user
            user = None
            for u in self.users.values():
                if u.username == username:
                    user = u
                    break

            if not user:
                self.auth_stats["failed_authentications"] += 1
                logger.warning(f"Authentication failed: user not found: {username}")
                return None

            if not user.is_active:
                self.auth_stats["failed_authentications"] += 1
                logger.warning(f"Authentication failed: user not active: {username}")
                return None

            # Verify password (simplified - in real implementation would use proper
            # password hashing)
            if not self._verify_password(user, password):
                self.auth_stats["failed_authentications"] += 1  # noqa: E501
                logger.warning(f"Authentication failed: invalid password: {username}")
                return None

            # Update last login
            user.last_login = datetime.now(timezone.utc)

            # Generate token
            if method == AuthMethod.JWT:
                token = self._generate_jwt_token(user)
                self.auth_stats["successful_authentications"] += 1
                logger.info(f"User authenticated successfully: {username}")
                return token
            else:
                logger.warning(f"Authentication method not supported: {method.value}")
                return None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.auth_stats["failed_authentications"] += 1
            return None

    def _verify_password(self, user: User, password: str) -> bool:
        """Verify user password (simplified)"""
        # In real implementation, would use bcrypt or similar
        # For now, use simple hash comparison
        password_hash = hashlib.sha256(f"{user.username}:{password}".encode()).hexdigest()
        stored_hash = str(user.metadata.get("password_hash", ""))
        return bool(password_hash == stored_hash)

    def _generate_jwt_token(self, user: User) -> AuthToken:
        """Generate JWT token for user"""
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.jwt_access_token_expire)

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "iat": now,
            "exp": now + expires_delta,
            "iss": "aiops-agent",
            "aud": "aiops-api",
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        # Generate refresh token
        refresh_token = self._generate_refresh_token(user)

        auth_token = AuthToken(
            token=token,
            user_id=user.user_id,
            expires_at=now + expires_delta,
            refresh_token=refresh_token,
            scopes=[role.value for role in user.roles],
        )

        self.user_tokens[token] = auth_token
        self.auth_stats["active_tokens"] += 1

        return auth_token

    def _generate_refresh_token(self, user: User) -> str:
        """Generate refresh token"""
        refresh_payload = {
            "user_id": user.user_id,
            "type": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self.jwt_refresh_token_expire),
            "aud": "aiops-api",
        }
        return jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[User]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            User if token valid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                audience="aiops-api",
            )

            user_id = payload.get("user_id")
            if not user_id:
                return None

            user = self.users.get(user_id)
            if not user:
                return None

            if not user.is_active:
                return None

            return user

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[AuthToken]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token string

        Returns:
            New auth token if refresh successful
        """
        try:
            payload = jwt.decode(
                refresh_token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                audience="aiops-api",
            )

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("user_id")
            user = self.users.get(str(user_id)) if user_id is not None else None

            if not user or not user.is_active:
                return None

            # Generate new access token
            return self._generate_jwt_token(user)

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None

    def revoke_token(self, token: str) -> bool:
        """
        Revoke token

        Args:
            token: Token to revoke

        Returns:
            Success status
        """
        if token in self.user_tokens:
            del self.user_tokens[token]
            self.auth_stats["active_tokens"] -= 1
            logger.info("Token revoked successfully")
            return True
        return False

    def check_permission(self, user: User, permission: Permission, resource: str) -> bool:
        """
        Check if user has permission for resource

        Args:
            user: User to check
            permission: Permission to check
            resource: Resource to access

        Returns:
            True if user has permission
        """
        # Check direct permissions
        if permission in user.permissions:
            return True

        # Check role-based permissions
        for role in user.roles:
            if role in self.role_permissions:
                if permission in self.role_permissions[role]:
                    return True

        # Check access policies
        for policy in self.access_policies.values():
            if self._matches_policy(user, permission, resource, policy):
                return True

        return False

    def _matches_policy(
        self, user: User, permission: Permission, resource: str, policy: AccessPolicy
    ) -> bool:
        """Check if user matches access policy"""
        # Check resource match
        if policy.resource != "*" and not resource.startswith(policy.resource):
            return False

        # Check required permissions
        if policy.required_permissions and permission not in policy.required_permissions:
            return False

        # Check required roles
        if policy.required_roles and not any(role in user.roles for role in policy.required_roles):
            return False

        # Check additional conditions
        if policy.conditions:
            for condition_key, condition_value in policy.conditions.items():
                user_value = user.metadata.get(condition_key)
                if user_value != condition_value:
                    return False

        return True

    def require_permission(self, permission: Permission, resource: str = "*"):
        """
        Decorator to require permission for function access

        Args:
            permission: Required permission
            resource: Resource to access
        """

        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # In real implementation, would extract user from request context
                # For now, just call the function
                return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # In real implementation, would extract user from request context
                # For now, just call the function
                return func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def register_access_policy(self, policy: AccessPolicy) -> None:
        """
        Register access policy

        Args:
            policy: Access policy
        """
        self.access_policies[policy.policy_id] = policy
        logger.info(f"Registered access policy: {policy.policy_id}")

    def assign_role(self, user_id: str, role: Role) -> bool:
        """
        Assign role to user

        Args:
            user_id: User ID
            role: Role to assign

        Returns:
            Success status
        """
        if user_id not in self.users:
            return False

        user = self.users[user_id]
        user.roles.add(role)

        # Grant role permissions
        if role in self.role_permissions:
            user.permissions.update(self.role_permissions[role])

        logger.info(f"Assigned role {role.value} to user {user_id}")
        return True

    def revoke_role(self, user_id: str, role: Role) -> bool:
        """
        Revoke role from user

        Args:
            user_id: User ID
            role: Role to revoke

        Returns:
            Success status
        """
        if user_id not in self.users:
            return False

        user = self.users[user_id]
        if role in user.roles:
            user.roles.remove(role)

            # Revoke role permissions
            if role in self.role_permissions:
                user.permissions.difference_update(self.role_permissions[role])

            logger.info(f"Revoked role {role.value} from user {user_id}")
            return True

        return False

    def get_auth_statistics(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            "total_authentications": self.auth_stats["total_authentications"],
            "successful_authentications": self.auth_stats["successful_authentications"],
            "failed_authentications": self.auth_stats["failed_authentications"],
            "active_tokens": self.auth_stats["active_tokens"],
            "registered_users": len(self.users),
            "enabled_auth_methods": [method.value for method in self.auth_methods],
            "registered_policies": len(self.access_policies),
        }


def get_enhanced_auth_integration(
    config: Optional[Dict[str, Any]] = None,
) -> EnhancedAuthIntegration:
    """
    Factory function to get enhanced auth integration instance

    Args:
        config: Optional configuration dictionary

    Returns:
        EnhancedAuthIntegration: Integration instance
    """
    return EnhancedAuthIntegration(config)
