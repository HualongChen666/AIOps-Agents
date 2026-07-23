# -*- coding: utf-8 -*-
"""
Input Validation and Sanitization Module

🔧 P0 Security Enhancement:
- Centralized input validation and sanitization
- SQL injection prevention
- XSS attack prevention
- Command injection prevention
- Path traversal prevention
"""

import html
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger


class InputValidator:
    """Centralized input validation and sanitization"""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)(\s|$)",
        r"(\s|^)(OR|AND)\s+\d+\s*=\s*\d+",
        r"(\s|^)(OR|AND)\s+['\"][\w\s]+['\"]\s*=\s*['\"][\w\s]+['\"]",
        r"--\s*$",
        r"/\*.*\*/",
        r";\s*(\w+)",
        r"\bEXEC\b\s*\(",
        r"\bEXECUTE\b\s*\(",
    ]

    # XSS attack patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]]",
        r"\.\./",
        r"\.\.\\",
        r"`[^`]*`",
        r"\$[^$]*\$",
    ]

    @classmethod
    def sanitize_string(cls, input_string: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent XSS and injection attacks.

        Args:
            input_string: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(input_string, str):
            return ""

        # Truncate to max length
        if len(input_string) > max_length:
            logger.warning(f"Input string truncated from {len(input_string)} to {max_length}")
            input_string = input_string[:max_length]

        # HTML escape to prevent XSS
        sanitized = html.escape(input_string)

        # Remove null bytes
        sanitized = sanitized.replace("", "")

        return sanitized

    @classmethod
    def validate_sql_safe(cls, input_string: str) -> tuple[bool, str]:
        """Validate input is safe from SQL injection.

        Args:
            input_string: Input string to validate

        Returns:
            (is_safe, error_message)
        """
        if not isinstance(input_string, str):
            return False, "Input must be a string"

        # Check against SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE | re.MULTILINE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return False, "Input contains potentially dangerous SQL patterns"

        return True, ""

    @classmethod
    def validate_xss_safe(cls, input_string: str) -> tuple[bool, str]:
        """Validate input is safe from XSS attacks.

        Args:
            input_string: Input string to validate

        Returns:
            (is_safe, error_message)
        """
        if not isinstance(input_string, str):
            return False, "Input must be a string"

        # Check against XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE | re.DOTALL):
                logger.warning(f"XSS pattern detected: {pattern}")
                return False, "Input contains potentially dangerous XSS patterns"

        return True, ""

    @classmethod
    def validate_command_safe(cls, input_string: str) -> tuple[bool, str]:
        """Validate input is safe from command injection.

        Args:
            input_string: Input string to validate

        Returns:
            (is_safe, error_message)
        """
        if not isinstance(input_string, str):
            return False, "Input must be a string"

        # Check against command injection patterns
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_string):
                logger.warning(f"Command injection pattern detected: {pattern}")
                return False, "Input contains potentially dangerous command patterns"

        return True, ""

    @classmethod
    def validate_path_safe(cls, input_string: str) -> tuple[bool, str]:
        """Validate input is safe from path traversal attacks.

        Args:
            input_string: Input string to validate

        Returns:
            (is_safe, error_message)
        """
        if not isinstance(input_string, str):
            return False, "Input must be a string"

        # Check for path traversal patterns
        if ".." in input_string:
            logger.warning("Path traversal pattern detected")
            return False, "Input contains path traversal patterns"

        # Check for absolute paths
        if input_string.startswith("/") or (len(input_string) > 1 and input_string[1] == ":"):
            logger.warning("Absolute path detected")
            return False, "Absolute paths are not allowed"

        return True, ""

    @classmethod
    def validate_email(cls, email: str) -> tuple[bool, str]:
        """Validate email format.

        Args:
            email: Email address to validate

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(email, str):
            return False, "Email must be a string"

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return False, "Invalid email format"

        return True, ""

    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, str]:
        """Validate username format.

        Args:
            username: Username to validate

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(username, str):
            return False, "Username must be a string"

        if len(username) < 3 or len(username) > 50:
            return False, "Username must be between 3 and 50 characters"

        username_pattern = r"^[a-zA-Z0-9_-]+$"
        if not re.match(username_pattern, username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"

        return True, ""

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], max_string_length: int = 1000) -> Dict[str, Any]:
        """Sanitize all string values in a dictionary.

        Args:
            data: Dictionary to sanitize
            max_string_length: Maximum allowed string length

        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data

        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value, max_string_length)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_string_length)
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value, max_string_length)
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_list(cls, data: List[Any], max_string_length: int = 1000) -> List[Any]:
        """Sanitize all string values in a list.

        Args:
            data: List to sanitize
            max_string_length: Maximum allowed string length

        Returns:
            Sanitized list
        """
        if not isinstance(data, list):
            return data

        sanitized: List[Any] = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(cls.sanitize_string(item, max_string_length))
            elif isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, max_string_length))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, max_string_length))
            else:
                sanitized.append(item)

        return sanitized

    @classmethod
    def validate_json(cls, json_string: str) -> tuple[bool, str, Optional[Dict]]:
        """Validate and parse JSON string.

        Args:
            json_string: JSON string to validate

        Returns:
            (is_valid, error_message, parsed_dict)
        """
        if not isinstance(json_string, str):
            return False, "Input must be a string", None

        try:
            parsed = json.loads(json_string)
            return True, "", parsed
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}", None


# Convenience functions
def sanitize_input(input_data: Any, max_length: int = 1000) -> Any:
    """Convenience function to sanitize any input data."""
    if isinstance(input_data, str):
        return InputValidator.sanitize_string(input_data, max_length)
    elif isinstance(input_data, dict):
        return InputValidator.sanitize_dict(input_data, max_length)
    elif isinstance(input_data, list):
        return InputValidator.sanitize_list(input_data, max_length)
    else:
        return input_data


def validate_and_clean_input(input_string: str) -> str:
    """Validate and clean input against common injection attacks.

    Removes dangerous content (SQL keywords, script tags, path traversal)
    and HTML-escapes the result.
    """
    if not isinstance(input_string, str):
        return ""

    # Remove script tags and their content entirely
    cleaned = re.sub(
        r"<script[^>]*>.*?</script>",
        "",
        input_string,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Remove event handlers and javascript pseudo-protocol
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"on\w+\s*=", "", cleaned, flags=re.IGNORECASE)

    # Remove common SQL injection keywords and comment markers
    cleaned = re.sub(
        r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"(--|;)", "", cleaned)

    # Remove path traversal sequences
    cleaned = cleaned.replace("..", "")

    # HTML escape the remaining content
    cleaned = html.escape(cleaned)

    return cleaned


def validate_safe_input(input_string: str) -> tuple[bool, str]:
    """Convenience function to validate input against common injection attacks."""
    if not isinstance(input_string, str):
        return False, "Input must be a string"

    # Check SQL injection
    is_safe, error = InputValidator.validate_sql_safe(input_string)
    if not is_safe:
        return False, error

    # Check XSS
    is_safe, error = InputValidator.validate_xss_safe(input_string)
    if not is_safe:
        return False, error

    # Check command injection
    is_safe, error = InputValidator.validate_command_safe(input_string)
    if not is_safe:
        return False, error

    # Check path traversal
    is_safe, error = InputValidator.validate_path_safe(input_string)
    if not is_safe:
        return False, error

    return True, ""
