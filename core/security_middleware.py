# -*- coding: utf-8 -*-
# core/security_middleware.py
# Security Middleware for Enterprise-grade Security
# Implements MFA, password policy, TLS enforcement, and security headers

import logging
import re
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Request, Response
from fastapi.security import HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class PasswordPolicy:
    """Enterprise password policy enforcement"""

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password against enterprise policy

        Requirements:
        - Minimum 12 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        - At least 1 special character
        - Not in common password list
        """
        if len(password) < 12:
            return False, "Password must be at least 12 characters"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least 1 uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least 1 lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least 1 number"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least 1 special character"

        # Check for common passwords (simplified list)
        common_passwords = [
            "password",
            "Password123",
            "Admin123",
            "12345678",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
        ]
        if password.lower() in [p.lower() for p in common_passwords]:
            return False, "Password is too common"

        return True, "Password meets security requirements"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt (or PBKDF2 as fallback)"""
        try:
            import bcrypt

            return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        except ImportError:
            # Fallback to PBKDF2
            import hashlib

            salt = secrets.token_hex(32)
            key = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            )
            return f"pbkdf2:{salt}:{key.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            import bcrypt

            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ImportError:
            # Fallback to PBKDF2
            if hashed.startswith("pbkdf2:"):
                parts = hashed.split(":")
                if len(parts) == 3:
                    salt, key = parts[1], parts[2]
                    import hashlib

                    computed_key = hashlib.pbkdf2_hmac(
                        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
                    )
                    return secrets.compare_digest(computed_key.hex(), key)
            return False


class MFAManager:
    """Multi-Factor Authentication Manager"""

    def __init__(self):
        self._mfa_enabled = False
        self._totp_secret_cache = {}

    def enable_mfa(self):
        """Enable MFA for the application"""
        self._mfa_enabled = True
        logger.info("MFA enabled for the application")

    def disable_mfa(self):
        """Disable MFA for the application"""
        self._mfa_enabled = False
        logger.info("MFA disabled for the application")

    def generate_totp_secret(self, user_id: str) -> str:
        """Generate TOTP secret for a user"""
        import pyotp

        secret = pyotp.random_base32()
        self._totp_secret_cache[user_id] = secret
        return secret

    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        if not self._mfa_enabled:
            return True  # If MFA is disabled, allow

        secret = self._totp_secret_cache.get(user_id)
        if not secret:
            return False

        try:
            import pyotp

            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except ImportError:
            logger.warning("pyotp not installed, MFA verification skipped")
            return True

    def get_totp_qr_code(self, user_id: str, secret: str) -> Optional[str]:
        """Generate QR code for TOTP setup"""
        try:
            import pyotp

            totp = pyotp.TOTP(secret)
            return totp.provisioning_uri(name=user_id, issuer_name="AIOps Agent")
        except ImportError:
            return None


class RateLimiter:
    """Rate limiter for API endpoints"""

    def __init__(self):
        self._request_counts = {}
        self._max_requests = 100
        self._time_window = 60  # 60 seconds

    def check_rate_limit(self, client_id: str) -> tuple[bool, Optional[int]]:
        """
        Check if client is within rate limit

        Returns:
            (allowed, retry_after_seconds)
        """
        now = datetime.now()

        # Clean old entries
        self._request_counts = {
            k: v
            for k, v in self._request_counts.items()
            if (now - v["timestamp"]).total_seconds() < self._time_window
        }

        if client_id not in self._request_counts:
            self._request_counts[client_id] = {"count": 1, "timestamp": now}
            return True, None

        client_data = self._request_counts[client_id]

        # Reset if time window passed
        if (now - client_data["timestamp"]).total_seconds() >= self._time_window:
            client_data["count"] = 1
            client_data["timestamp"] = now
            return True, None

        # Check limit
        if client_data["count"] >= self._max_requests:
            retry_after = int(self._time_window - (now - client_data["timestamp"]).total_seconds())
            return False, retry_after

        client_data["count"] += 1
        return True, None


class SecurityHeaders:
    """Security headers middleware"""

    @staticmethod
    def add_security_headers(response: Response) -> Response:
        """Add enterprise security headers to response"""
        # HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # CSP (Content Security Policy)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline';"
        )

        # X-Frame-Options (Clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options (MIME sniffing protection)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection (XSS protection)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class TLSEnforcer:
    """TLS enforcement middleware"""

    def __init__(self, enforce_tls: bool = True):
        self._enforce_tls = enforce_tls

    def check_tls(self, request: Request) -> bool:
        """Check if request uses HTTPS"""
        if not self._enforce_tls:
            return True  # Allow HTTP in development

        # Check for HTTPS
        if request.url.scheme != "https":
            # Check for forwarded headers (behind proxy)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            if forwarded_proto.lower() != "https":
                return False

        return True


# Global instances
password_policy = PasswordPolicy()
mfa_manager = MFAManager()
rate_limiter = RateLimiter()
security_headers = SecurityHeaders()
tls_enforcer = TLSEnforcer()
