# -*- coding: utf-8 -*-
"""
Security Input Validator Middleware

Provides comprehensive input validation to protect against:
- XSS (Cross-Site Scripting)
- SQL Injection
- Path Traversal
- Command Injection
- Other common injection attacks

This middleware should be integrated into the FastAPI application to validate
all incoming requests before they reach the application logic.
"""

import html
import logging
import re
import threading
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, status  # noqa: F401
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SecurityInputValidator:
    """
    Comprehensive input validation for security threats.

    Provides methods to validate and sanitize user input against various
    injection attacks including XSS, SQL injection, path traversal, and command injection.
    """

    # XSS attack patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers like onclick, onload
        r"<iframe[^>]*>",  # Iframe tags
        r"<object[^>]*>",  # Object tags
        r"<embed[^>]*>",  # Embed tags
        r"expression\s*\(",  # CSS expression
        r"@import",  # CSS import
        r"<style[^>]*>.*?</style>",  # Style tags
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",  # OR 1=1, AND 1=1
        r"(\bOR\b|\bAND\b)\s+['\"]\w+['\"]\s*=\s*['\"]\w+['\"]",  # OR '1'='1', AND "x"="x"
        r"(\bOR\b|\bAND\b)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",  # OR 1='1', AND 'x'=x
        r";\s*(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC|UNION|SELECT)\b",  # SQL commands
        r"--\s*$",  # SQL comments
        r"/\*.*\*/",  # SQL block comments
        r"\bUNION\s+ALL\s+SELECT\b",  # UNION ALL SELECT
        r"\bEXEC\s*\(",  # EXEC function
        r"['\"]\s*(OR|AND)\s*['\"]",  # ' OR ', " AND "
        r"\b(OR|AND)\s+['\"]",  # OR ', AND "
        r"['\"]\s*(OR|AND)\b",  # ' OR, " AND
        r"1['\"]\s*=\s*['\"]\s*1",  # 1'='1, 1"="1
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # ../
        r"\.\.\\",  # ..\
        r"%2e%2e/",  # URL encoded ../
        r"%2e%2e%5c",  # URL encoded ..\
        r"\.\.\/",  # Unicode ../
        r"\.\.\\",  # Unicode ..\
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r";\s*\w+\s",  # Command after semicolon
        r"\|\s*\w+\s",  # Pipe command
        r"&&\s*\w+\s",  # AND command
        r"\|\|\s*\w+\s",  # OR command
        r"\$\(",  # Command substitution
        r"`[^`]*`",  # Backtick command substitution
        r">\s*\w+",  # Output redirection
        r"<\s*\w+",  # Input redirection
    ]

    def __init__(self):
        """Initialize the validator with compiled regex patterns."""
        self.xss_regex = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.XSS_PATTERNS
        ]
        self.sql_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_INJECTION_PATTERNS
        ]
        self.path_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PATH_TRAVERSAL_PATTERNS
        ]
        self.command_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.COMMAND_INJECTION_PATTERNS
        ]

    def validate_string(
        self, input_string: str, input_type: str = "general"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a string input against all security patterns.

        Args:
            input_string: The string to validate
            input_type: Type of input (e.g., "filename", "username", "general")

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(input_string, str):
            return False, f"Input must be a string, got {type(input_string).__name__}"

        # Check for XSS attacks
        for pattern in self.xss_regex:
            if pattern.search(input_string):
                logger.warning(f"XSS attack detected in {input_type}: {input_string[:100]}")
                return False, f"Potential XSS attack detected in {input_type}"

        # Check for SQL injection
        for pattern in self.sql_regex:
            if pattern.search(input_string):
                logger.warning(f"SQL injection detected in {input_type}: {input_string[:100]}")
                return False, f"Potential SQL injection detected in {input_type}"

        # Check for path traversal (only for filename/path inputs)
        if input_type in ("filename", "path", "filepath"):
            for pattern in self.path_regex:
                if pattern.search(input_string):
                    logger.warning(f"Path traversal detected in {input_type}: {input_string[:100]}")
                    return False, f"Potential path traversal attack detected in {input_type}"

        # Check for command injection (only for command/shell inputs)
        if input_type in ("command", "shell", "arg"):
            for pattern in self.command_regex:
                if pattern.search(input_string):
                    logger.warning(
                        f"Command injection detected in {input_type}: {input_string[:100]}"
                    )
                    return False, f"Potential command injection detected in {input_type}"

        return True, None

    def sanitize_string(self, input_string: str) -> str:
        """
        Sanitize a string by escaping and removing dangerous content.

        This method provides comprehensive XSS protection by:
        1. Removing dangerous HTML tags and attributes
        2. Removing JavaScript code and dangerous functions
        3. Removing CSS injection attempts
        4. Removing URL-based attacks
        5. HTML escaping remaining content

        Args:
            input_string: The string to sanitize

        Returns:
            Sanitized string
        """
        if not isinstance(input_string, str):
            return str(input_string)

        sanitized = input_string

        # Step 1: Remove dangerous HTML tags
        # Script tags and their content
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )
        # Iframe, object, embed, form tags
        sanitized = re.sub(
            r"</?(iframe|object|embed|form|input|button)[^>]*>", "", sanitized, flags=re.IGNORECASE
        )
        # Style tags
        sanitized = re.sub(
            r"<style[^>]*>.*?</style>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )
        # Meta tags (for redirect attacks)
        sanitized = re.sub(r"<meta[^>]*>", "", sanitized, flags=re.IGNORECASE)
        # Link tags
        sanitized = re.sub(r"<link[^>]*>", "", sanitized, flags=re.IGNORECASE)
        # Base tags (for URL manipulation)
        sanitized = re.sub(r"<base[^>]*>", "", sanitized, flags=re.IGNORECASE)

        # Step 2: Remove dangerous HTML attributes
        # Event handlers (onclick, onload, onerror, etc.)
        sanitized = re.sub(r'\bon\w+\s*=\s*["\'][^"\']*["\']', "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\bon\w+\s*=\s*[^\s>]*", "", sanitized, flags=re.IGNORECASE)
        # Dangerous attributes (src, href with javascript:, data:, etc.)
        sanitized = re.sub(
            r'\bsrc\s*=\s*["\']?(javascript:|data:|vbscript:)', "", sanitized, flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r'\bhref\s*=\s*["\']?(javascript:|data:|vbscript:)', "", sanitized, flags=re.IGNORECASE
        )
        # Style attribute (CSS injection)
        sanitized = re.sub(
            r'\bstyle\s*=\s*["\'][^"\']*expression\s*\([^)]*\)[^"\']*["\']',
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

        # Step 3: Remove JavaScript code patterns
        # javascript: protocol
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        # vbscript: protocol
        sanitized = re.sub(r"vbscript:", "", sanitized, flags=re.IGNORECASE)
        # Dangerous JavaScript functions
        dangerous_functions = [
            r"alert\s*\([^)]*\)",
            r"confirm\s*\([^)]*\)",
            r"prompt\s*\([^)]*\)",
            r"eval\s*\([^)]*\)",
            r"exec\s*\([^)]*\)",
            r"Function\s*\([^)]*\)",
            r"document\.write\s*\([^)]*\)",
            r"document\.writeln\s*\([^)]*\)",
            r'window\.location\s*=\s*["\'][^"\']*["\']',
            r"window\.open\s*\([^)]*\)",
            r"setTimeout\s*\([^)]*\)",
            r"setInterval\s*\([^)]*\)",
        ]
        for func_pattern in dangerous_functions:
            sanitized = re.sub(func_pattern, "", sanitized, flags=re.IGNORECASE)

        # Step 4: Remove CSS injection attempts
        sanitized = re.sub(r"expression\s*\([^)]*\)", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"@import\s+[^;]+;", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"behavior\s*:\s*url\s*\([^)]*\)", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(
            r"-moz-binding\s*:\s*url\s*\([^)]*\)", "", sanitized, flags=re.IGNORECASE
        )

        # Step 5: Remove URL-based attacks
        sanitized = re.sub(r"data:text/html[^,]*,", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"data:application/[^,]*,", "", sanitized, flags=re.IGNORECASE)

        # Step 6: Remove encoded attacks (basic)
        # URL encoded script tags
        sanitized = re.sub(r"%3cscript%3e.*?%3c/script%3e", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"%3Cscript%3E.*?%3C/script%3E", "", sanitized, flags=re.IGNORECASE)
        # Hex encoded attacks
        sanitized = re.sub(r"&#x?[0-9a-f]+;", "", sanitized, flags=re.IGNORECASE)

        # Step 7: HTML escape to prevent any remaining XSS
        sanitized = html.escape(sanitized)

        # Step 8: Additional sanitization for special characters
        sanitized = sanitized.replace("\\", "\\\\")
        sanitized = sanitized.replace("'", "\\'")
        sanitized = sanitized.replace('"', '\\"')

        return sanitized

    def validate_dict(
        self, input_dict: Dict[str, Any], input_type: str = "general"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate all string values in a dictionary.

        Args:
            input_dict: The dictionary to validate
            input_type: Type of input

        Returns:
            Tuple of (is_valid, error_message)
        """
        for key, value in input_dict.items():
            if isinstance(value, str):
                is_valid, error = self.validate_string(value, f"{input_type}.{key}")
                if not is_valid:
                    return False, error
            elif isinstance(value, dict):
                is_valid, error = self.validate_dict(value, f"{input_type}.{key}")
                if not is_valid:
                    return False, error
            elif isinstance(value, list):
                is_valid, error = self.validate_list(value, f"{input_type}.{key}")
                if not is_valid:
                    return False, error

        return True, None

    def validate_list(
        self, input_list: List[Any], input_type: str = "general"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate all string values in a list.

        Args:
            input_list: The list to validate
            input_type: Type of input

        Returns:
            Tuple of (is_valid, error_message)
        """
        for i, value in enumerate(input_list):
            if isinstance(value, str):
                is_valid, error = self.validate_string(value, f"{input_type}[{i}]")
                if not is_valid:
                    return False, error
            elif isinstance(value, dict):
                is_valid, error = self.validate_dict(value, f"{input_type}[{i}]")
                if not is_valid:
                    return False, error
            elif isinstance(value, list):
                is_valid, error = self.validate_list(value, f"{input_type}[{i}]")
                if not is_valid:
                    return False, error

        return True, None

    def validate_any(
        self, input_data: Any, input_type: str = "general"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate any input data type.

        Args:
            input_data: The data to validate
            input_type: Type of input

        Returns:
            Tuple of (is_valid, error_message)
        """
        if isinstance(input_data, str):
            return self.validate_string(input_data, input_type)
        elif isinstance(input_data, dict):
            return self.validate_dict(input_data, input_type)
        elif isinstance(input_data, list):
            return self.validate_list(input_data, input_type)
        else:
            # Non-string types are generally safe from injection attacks
            return True, None


class SecurityInputValidatorMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic input validation.

    This middleware automatically validates all incoming request data
    before it reaches the application logic.
    """

    def __init__(self, app, validator: Optional[SecurityInputValidator] = None):
        """
        Initialize the middleware.

        Args:
            app: The FastAPI application
            validator: Optional validator instance (creates one if not provided)
        """
        super().__init__(app)
        self.validator = validator or SecurityInputValidator()

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and validate input data.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response from the next handler
        """
        # Skip validation for certain paths (health checks, static files, etc.)
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/static"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        try:
            # Validate query parameters
            if request.query_params:
                query_dict = dict(request.query_params)
                is_valid, error = self.validator.validate_dict(query_dict, "query")
                if not is_valid:
                    logger.warning(f"Invalid query parameters: {error}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": f"Invalid input: {error}"},
                    )

            # Validate request body if present
            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await request.json()
                    is_valid, error = self.validator.validate_any(body, "body")
                    if not is_valid:
                        logger.warning(f"Invalid request body: {error}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": f"Invalid input: {error}"},
                        )
                except Exception:
                    logger.debug("Request body is not JSON, skipping validation", exc_info=True)

            # Validate path parameters
            if request.path_params:
                path_dict = dict(request.path_params)
                is_valid, error = self.validator.validate_dict(path_dict, "path")
                if not is_valid:
                    logger.warning(f"Invalid path parameters: {error}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": f"Invalid input: {error}"},
                    )

            # Continue to the next middleware/route handler
            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Error in security validation middleware: {e}")
            # If validation fails, allow the request to continue (fail-open)
            # This prevents the middleware from breaking the application
            return await call_next(request)


# Global validator instance for singleton pattern with thread safety
_security_validator_instance = None
_security_validator_lock = threading.Lock()


def get_security_validator() -> SecurityInputValidator:
    """
    Get the global security validator instance (singleton pattern).

    This implementation uses double-checked locking for thread safety
    and performance optimization.

    Returns:
        The security validator instance
    """
    global _security_validator_instance

    # First check (without lock) for performance
    if _security_validator_instance is None:
        # Acquire lock for thread safety
        with _security_validator_lock:
            # Second check (with lock) to prevent race condition
            if _security_validator_instance is None:
                _security_validator_instance = SecurityInputValidator()

    return _security_validator_instance


def reset_security_validator() -> None:
    """
    Reset the global security validator instance.

    This is primarily used for testing purposes to ensure
    clean state between test runs.
    """
    global _security_validator_instance
    with _security_validator_lock:
        _security_validator_instance = None


def create_security_middleware() -> Middleware:
    """
    Create a security middleware instance for FastAPI.

    Returns:
        Middleware instance
    """
    return Middleware(SecurityInputValidatorMiddleware)


def add_input_validation_middleware(app) -> None:
    """
    Add input validation middleware to the FastAPI application.

    This function adds the security input validator middleware to the FastAPI app
    to protect against XSS, SQL injection, path traversal, and command injection attacks.

    Args:
        app: The FastAPI application instance
    """
    validator = SecurityInputValidator()
    app.add_middleware(SecurityInputValidatorMiddleware, validator=validator)
    logger.info("Security input validation middleware added to FastAPI application")
