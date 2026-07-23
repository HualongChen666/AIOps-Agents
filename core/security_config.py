# -*- coding: utf-8 -*-
"""
Enhanced Security Configuration
增强安全配置

Centralized security configuration management for TLS, MFA, and other security features.
Provides easy enablement and configuration of enterprise security features.
"""

import os
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from core.security_middleware import (
    MFAManager,
    RateLimiter,
    SecurityHeaders,
    TLSEnforcer,
)


class SecurityConfig:
    """Centralized security configuration management"""

    def __init__(self):
        """Initialize security configuration"""
        self.config = self._load_security_config()
        self.mfa_manager = MFAManager()
        self.rate_limiter = RateLimiter()
        self.security_headers = SecurityHeaders()
        self.tls_enforcer = TLSEnforcer(enforce_tls=self.config.get("tls_enabled", False))

        # Apply configuration
        self._apply_configuration()

    def _load_security_config(self) -> Dict[str, Any]:
        """Load security configuration from environment variables"""
        return {
            "tls_enabled": os.getenv("TLS_ENABLED", "false").lower() == "true",
            "mfa_enabled": os.getenv("MFA_ENABLED", "false").lower() == "true",
            "rate_limiting_enabled": os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true",
            "security_headers_enabled": (
                os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true"
            ),
            "password_policy_enabled": (
                os.getenv("PASSWORD_POLICY_ENABLED", "true").lower() == "true"
            ),
            "rate_limit_max_requests": int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100")),
            "rate_limit_time_window": int(os.getenv("RATE_LIMIT_TIME_WINDOW", "60")),
            "tls_cert_path": os.getenv("TLS_CERT_PATH", ""),
            "tls_key_path": os.getenv("TLS_KEY_PATH", ""),
        }

    def _apply_configuration(self):
        """Apply security configuration"""
        # Enable/disable MFA
        if self.config["mfa_enabled"]:
            self.mfa_manager.enable_mfa()
            logger.info("MFA enabled")
        else:
            self.mfa_manager.disable_mfa()
            logger.info("MFA disabled")

        # Configure rate limiting
        if self.config["rate_limiting_enabled"]:
            self.rate_limiter._max_requests = self.config["rate_limit_max_requests"]
            self.rate_limiter._time_window = self.config["rate_limit_time_window"]
            logger.info(
                f"Rate limiting enabled: {self.config['rate_limit_max_requests']} "
                f"requests per {self.config['rate_limit_time_window']} seconds"
            )
        else:
            logger.info("Rate limiting disabled")

        # Configure TLS
        if self.config["tls_enabled"]:
            self.tls_enforcer._enforce_tls = True
            logger.info("TLS enforcement enabled")
        else:
            self.tls_enforcer._enforce_tls = False
            logger.info("TLS enforcement disabled (development mode)")

        # Security headers
        if self.config["security_headers_enabled"]:
            logger.info("Security headers enabled")
        else:
            logger.info("Security headers disabled")

        # Password policy
        if self.config["password_policy_enabled"]:
            logger.info("Password policy enabled")
        else:
            logger.info("Password policy disabled")

    def enable_tls(self, cert_path: str, key_path: str):
        """
        Enable TLS with certificate paths

        Args:
            cert_path: Path to TLS certificate
            key_path: Path to TLS private key
        """
        self.config["tls_enabled"] = True
        self.config["tls_cert_path"] = cert_path
        self.config["tls_key_path"] = key_path
        self.tls_enforcer._enforce_tls = True
        logger.info(f"TLS enabled with cert: {cert_path}")

    def enable_mfa(self):
        """Enable MFA"""
        self.config["mfa_enabled"] = True
        self.mfa_manager.enable_mfa()
        logger.info("MFA enabled")

    def disable_mfa(self):
        """Disable MFA"""
        self.config["mfa_enabled"] = False
        self.mfa_manager.disable_mfa()
        logger.info("MFA disabled")

    def enable_rate_limiting(self, max_requests: int = 100, time_window: int = 60):
        """
        Enable rate limiting

        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.config["rate_limiting_enabled"] = True
        self.config["rate_limit_max_requests"] = max_requests
        self.config["rate_limit_time_window"] = time_window
        self.rate_limiter._max_requests = max_requests
        self.rate_limiter._time_window = time_window
        logger.info(f"Rate limiting enabled: {max_requests} requests per {time_window} seconds")

    def disable_rate_limiting(self):
        """Disable rate limiting"""
        self.config["rate_limiting_enabled"] = False
        logger.info("Rate limiting disabled")

    def get_security_status(self) -> Dict[str, Any]:
        """
        Get current security status

        Returns:
            Dictionary with security status
        """
        return {
            "tls_enabled": self.config["tls_enabled"],
            "mfa_enabled": self.config["mfa_enabled"],
            "rate_limiting_enabled": self.config["rate_limiting_enabled"],
            "security_headers_enabled": self.config["security_headers_enabled"],
            "password_policy_enabled": self.config["password_policy_enabled"],
            "rate_limit_config": {
                "max_requests": self.config["rate_limit_max_requests"],
                "time_window": self.config["rate_limit_time_window"],
            },
        }

    def validate_tls_certificates(self) -> Dict[str, Any]:
        """
        Validate TLS certificates

        Returns:
            Dictionary with validation results
        """
        if not self.config["tls_enabled"]:
            return {"valid": False, "reason": "TLS not enabled"}

        cert_path = self.config["tls_cert_path"]
        key_path = self.config["tls_key_path"]

        if not cert_path or not key_path:
            return {"valid": False, "reason": "Certificate paths not configured"}

        if not Path(cert_path).exists():
            return {"valid": False, "reason": f"Certificate file not found: {cert_path}"}

        if not Path(key_path).exists():
            return {"valid": False, "reason": f"Key file not found: {key_path}"}

        try:
            # Basic certificate validation
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Check certificate expiration
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before:
                return {"valid": False, "reason": "Certificate not yet valid"}
            if now > cert.not_valid_after:
                return {"valid": False, "reason": "Certificate has expired"}

            return {
                "valid": True,
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "not_valid_before": cert.not_valid_before.isoformat(),
                "not_valid_after": cert.not_valid_after.isoformat(),
            }

        except Exception as e:
            return {"valid": False, "reason": f"Certificate validation failed: {str(e)}"}


# Global security configuration instance
security_config = SecurityConfig()


def setup_enterprise_security():
    """
    Setup enterprise security features

    Returns:
        Dictionary with setup results
    """
    results = {
        "security_status": security_config.get_security_status(),
        "tls_validation": security_config.validate_tls_certificates(),
        "timestamp": "",
        "error": "",
    }

    try:
        # Log security status
        logger.info(f"Security setup completed: {results['security_status']}")

        # Validate TLS if enabled
        if security_config.config["tls_enabled"]:
            tls_validation = security_config.validate_tls_certificates()
            if not tls_validation.get("valid"):
                logger.warning(f"TLS validation failed: {tls_validation.get('reason')}")

        results["timestamp"] = "success"
        logger.info("Enterprise security setup completed successfully")

        return results

    except Exception as e:
        logger.error(f"Enterprise security setup failed: {e}")
        results["timestamp"] = "error"
        results["error"] = str(e)
        return results
