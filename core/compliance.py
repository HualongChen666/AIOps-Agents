# -*- coding: utf-8 -*-
"""``compliance`` module.

Top-level functions: find_compliance_violations, check_compliance, mask_sensitive, mask_sensitive_dict"""

# core/compliance.py
# component module for compliance functionality

from typing import Any, Dict, List

#: Placeholder / empty values that must never survive into a compliant config.
_PLACEHOLDER_SECRET_VALUES = {
    "",
    "changeme",
    "change-me",
    "change_me",
    "password",
    "postgres",
    "postgres_password",
    "redis_password",
    "admin",
    "secret",
    "your_internal_api_key_here",
    "your_jwt_secret_key_here_min_32_chars",
    "your_postgres_password_here",
    "your_encryption_key_here",
    "your_redis_password_here",
}

#: Keys that hold credentials.
_SECRET_KEY_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "access_key",
)

#: Flags that must be disabled when running in production.
_MUST_BE_FALSE_IN_PRODUCTION = (
    "debug",
    "dev_mode",
    "allow_anonymous",
    "disable_auth",
    "skip_tls_verify",
    "insecure",
)

#: Keys whose presence as ``False`` disables TLS verification.
_TLS_VERIFY_KEYS = ("verify_ssl", "verify_tls", "ssl_verify", "tls_verify")


def find_compliance_violations(config: Dict[str, Any]) -> List[str]:
    """Return the compliance violations found in ``config``.

    A configuration is compliant only when it contains no placeholder/empty
    credentials, does not relax security flags while running in production and
    does not disable TLS verification.
    """
    violations: List[str] = []
    if not isinstance(config, dict):
        return ["configuration is not a mapping"]

    environment = str(config.get("environment") or config.get("ENVIRONMENT") or "").lower()

    for key, value in config.items():
        lowered = str(key).lower()

        if any(marker in lowered for marker in _SECRET_KEY_MARKERS):
            if value is None:
                violations.append(f"{key}: credential is None")
            elif isinstance(value, str) and value.strip().lower() in _PLACEHOLDER_SECRET_VALUES:
                violations.append(f"{key}: placeholder or empty credential")

        if lowered in _MUST_BE_FALSE_IN_PRODUCTION and environment == "production" and bool(value):
            violations.append(f"{key}: must be disabled in production")

    for key in _TLS_VERIFY_KEYS:
        if key in config and config[key] is False:
            violations.append(f"{key}: TLS verification disabled")

    return violations


def check_compliance(config: Dict[str, Any]) -> bool:
    """Check if configuration meets compliance requirements.

    Args:
        config: Configuration to check

    Returns:
        True if compliant, False otherwise
    """
    return not find_compliance_violations(config)


def mask_sensitive(data: str, mask_char: str = "*") -> str:
    """Mask sensitive data for logging/display.

    Args:
        data: Data to mask
        mask_char: Character to use for masking

    Returns:
        Masked data
    """
    if not data or len(data) <= 4:
        return mask_char * len(data) if data else ""
    return data[:2] + mask_char * (len(data) - 4) + data[-2:]


def mask_sensitive_dict(data: Dict[str, Any], mask_char: str = "*") -> Dict[str, Any]:
    """Mask sensitive fields in a dictionary.

    Args:
        data: Dictionary to mask
        mask_char: Character to use for masking

    Returns:
        Dictionary with sensitive fields masked
    """
    sensitive_keys = ["password", "token", "secret", "key", "api_key", "auth"]
    masked = data.copy()
    for key in masked:
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            value = masked[key]
            if isinstance(value, str):
                if len(value) <= 4:
                    masked[key] = mask_char * len(value)
                else:
                    masked[key] = value[:2] + mask_char * (len(value) - 4) + value[-2:]
    return masked
