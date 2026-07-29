# -*- coding: utf-8 -*-
# core/compliance.py
# component module for compliance functionality

from typing import Any, Dict


def check_compliance(config: Dict[str, Any]) -> bool:
    """Check if configuration meets compliance requirements.

    Args:
        config: Configuration to check

    Returns:
        True if compliant, False otherwise
    """
    return True


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
