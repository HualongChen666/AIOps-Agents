import os

# -*- coding: utf-8 -*-
"""
Configuration Validation Mechanism
配置验证机制

Comprehensive configuration validation system for the AIOps Agent.
Provides validation rules, schema validation, and health checks.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from core.environment_config import environment_config_manager
from core.unified_config import AppConfig, Environment


class ValidationSeverity(Enum):
    """Validation severity levels"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Configuration validation result"""

    is_valid: bool
    severity: ValidationSeverity
    field: str
    message: str
    suggestion: Optional[str] = None


class ConfigValidator:
    """Configuration validator"""

    def __init__(self):
        """Initialize configuration validator"""
        self.validation_rules: List[Callable] = []
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default validation rules"""
        self.validation_rules = [
            self._validate_jwt_secret,
            self._validate_database_config,
            self._validate_redis_config,
            self._validate_tls_config,
            self._validate_ai_config,
            self._validate_monitoring_config,
            self._validate_security_config,
            self._validate_environment_specific_rules,
        ]

    def validate_config(self, config: AppConfig) -> List[ValidationResult]:
        """
        Validate configuration

        Args:
            config: Application configuration to validate

        Returns:
            List of validation results
        """
        results = []

        for rule in self.validation_rules:
            try:
                rule_results = rule(config)
                results.extend(rule_results)
            except Exception as e:
                logger.error(f"Validation rule failed: {e}")
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="validation",
                        message=f"Validation rule execution failed: {str(e)}",
                    )
                )

        return results

    def _validate_jwt_secret(self, config: AppConfig) -> List[ValidationResult]:
        """Validate JWT secret configuration"""
        results = []

        secret = config.security.jwt_secret_key

        # Check if using default secret
        if secret == os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-me"):
            severity = (
                ValidationSeverity.ERROR
                if config.environment == Environment.PRODUCTION
                else ValidationSeverity.WARNING
            )
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=severity,
                    field="security.jwt_secret_key",
                    message="Using default JWT secret key",
                    suggestion="Set a strong, unique JWT_SECRET_KEY environment variable",
                )
            )

        # Check secret length
        elif len(secret) < 32:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    field="security.jwt_secret_key",
                    message="JWT secret key is too short",
                    suggestion="Use a JWT secret key with at least 32 characters",
                )
            )

        return results

    def _validate_database_config(self, config: AppConfig) -> List[ValidationResult]:
        """Validate database configuration"""
        results = []

        db = config.database

        # Check required fields
        if not db.host:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    field="database.host",
                    message="Database host is not configured",
                )
            )

        if not db.database:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    field="database.database",
                    message="Database name is not configured",
                )
            )

        if not db.username:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    field="database.username",
                    message="Database username is not configured",
                )
            )

        # Check pool size for production
        if config.environment == Environment.PRODUCTION and db.pool_size < 10:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    field="database.pool_size",
                    message="Database pool size is too small for production",
                    suggestion="Increase pool_size to at least 10 for production",
                )
            )

        return results

    def _validate_redis_config(self, config: AppConfig) -> List[ValidationResult]:
        """Validate Redis configuration"""
        results = []

        redis = config.redis

        if not redis.host:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    field="redis.host",
                    message="Redis host is not configured",
                    suggestion="Redis is recommended for caching and session management",
                )
            )

        return results

    def _validate_tls_config(self, config: AppConfig) -> List[ValidationResult]:
        """Validate TLS configuration"""
        results = []

        security = config.security

        if security.tls_enabled:
            if not security.tls_cert_path:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="security.tls_cert_path",
                        message="TLS is enabled but certificate path is not configured",
                    )
                )

            if not security.tls_key_path:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="security.tls_key_path",
                        message="TLS is enabled but key path is not configured",
                    )
                )

            # Check if certificate files exist
            if security.tls_cert_path and not Path(security.tls_cert_path).exists():
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="security.tls_cert_path",
                        message=f"TLS certificate file not found: {security.tls_cert_path}",
                    )
                )

            if security.tls_key_path and not Path(security.tls_key_path).exists():
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="security.tls_key_path",
                        message=f"TLS key file not found: {security.tls_key_path}",
                    )
                )
        else:
            if config.environment == Environment.PRODUCTION:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="security.tls_enabled",
                        message="TLS should be enabled in production",
                        suggestion="Set TLS_ENABLED=true and configure certificate paths",
                    )
                )

        return results

    def _validate_ai_config(self, config: AppConfig) -> List[ValidationResult]:
        """Validate AI configuration"""
        results = []

        ai = config.ai

        if ai.enabled:
            if not ai.api_key:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        field="ai.api_key",
                        message="AI is enabled but API key is not configured",
                        suggestion="Set OPENAI_API_KEY environment variable",
                    )
                )

            if ai.model_name == "gpt-4" and config.environment == Environment.PRODUCTION:
                results.append(
                    ValidationResult(
                        is_valid=True,
                        severity=ValidationSeverity.INFO,
                        field="ai.model_name",
                        message="Using GPT-4 model in production (consider cost implications)",
                    )
                )

        return results

    def _validate_monitoring_config(self, config: AppConfig) -> List[ValidationResult]:
        """Validate monitoring configuration"""
        results = []

        monitoring = config.monitoring

        if not monitoring.enabled:
            if config.environment == Environment.PRODUCTION:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        field="monitoring.enabled",
                        message="Monitoring is disabled in production",
                        suggestion="Enable monitoring for production environments",
                    )
                )

        return results

    def _validate_security_config(self, config: AppConfig) -> List[ValidationResult]:
        """Validate security configuration"""
        results = []

        security = config.security

        if not security.mfa_enabled and config.environment == Environment.PRODUCTION:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    field="security.mfa_enabled",
                    message="MFA is disabled in production",
                    suggestion="Enable MFA for enhanced security",
                )
            )

        if not security.password_policy_enabled:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    field="security.password_policy_enabled",
                    message="Password policy is disabled",
                    suggestion="Enable password policy for better security",
                )
            )

        return results

    def _validate_environment_specific_rules(self, config: AppConfig) -> List[ValidationResult]:
        """Validate environment-specific rules"""
        results = []

        if config.environment == Environment.PRODUCTION:
            if config.debug:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field="debug",
                        message="Debug mode is enabled in production",
                        suggestion="Set DEBUG=false for production",
                    )
                )

            if config.workers < 2:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        field="workers",
                        message="Worker count is low for production",
                        suggestion="Increase workers to at least 2 for production",
                    )
                )

        return results

    def add_custom_rule(self, rule: Callable[[AppConfig], List[ValidationResult]]):
        """
        Add custom validation rule

        Args:
            rule: Validation function that takes config and returns list of results
        """
        self.validation_rules.append(rule)
        logger.info(f"Added custom validation rule: {rule.__name__}")


class ConfigHealthChecker:
    """Configuration health checker"""

    def __init__(self):
        """Initialize configuration health checker"""
        self.validator = ConfigValidator()

    def check_config_health(self, config: Optional[AppConfig] = None) -> Dict[str, Any]:
        """
        Check configuration health

        Args:
            config: Configuration to check (uses current if None)

        Returns:
            Dictionary with health check results
        """
        try:
            # Load current config if not provided
            if config is None:
                config = environment_config_manager.load_environment_config()

            # Validate configuration
            validation_results = self.validator.validate_config(config)

            # Count results by severity
            errors = [r for r in validation_results if r.severity == ValidationSeverity.ERROR]
            warnings = [r for r in validation_results if r.severity == ValidationSeverity.WARNING]
            info = [r for r in validation_results if r.severity == ValidationSeverity.INFO]

            # Overall health status
            is_healthy = len(errors) == 0

            return {
                "healthy": is_healthy,
                "environment": config.environment.value,
                "validation_results": {
                    "total": len(validation_results),
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "info": len(info),
                },
                "error_details": [
                    {"field": r.field, "message": r.message, "suggestion": r.suggestion}
                    for r in errors
                ],
                "warning_details": [
                    {"field": r.field, "message": r.message, "suggestion": r.suggestion}
                    for r in warnings
                ],
                "info_details": [
                    {"field": r.field, "message": r.message, "suggestion": r.suggestion}
                    for r in info
                ],
                "timestamp": "success",
            }

        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return {"healthy": False, "error": str(e), "timestamp": "error"}


# Global configuration health checker instance
config_health_checker = ConfigHealthChecker()


def setup_config_validation() -> Dict[str, Any]:
    """
    Setup configuration validation mechanism

    Returns:
        Dictionary with setup results
    """
    try:
        # Run configuration health check
        health_check = config_health_checker.check_config_health()

        # Log results
        if health_check["healthy"]:
            logger.info("Configuration validation passed")
        else:
            logger.warning(
                "Configuration validation found "
                f"{health_check['validation_results']['errors']} errors and "
                f"{health_check['validation_results']['warnings']} warnings"
            )

        return {"status": "success", "health_check": health_check}

    except Exception as e:
        logger.error(f"Configuration validation setup failed: {e}")
        return {"status": "error", "error": str(e)}
