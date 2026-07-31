# -*- coding: utf-8 -*-
"""
Environment Configuration Manager
环境配置管理器

Manages environment-specific configuration files and provides
automatic environment detection and configuration loading.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from core.unified_config import AppConfig, ConfigManager, Environment, setup_unified_configuration


class EnvironmentConfigManager:
    """Environment-specific configuration manager"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize environment configuration manager

        Args:
            config_dir: Directory containing environment configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_manager = ConfigManager()
        self.environment = self._detect_environment()
        self.config_file = self._get_config_file_for_environment()

    def _detect_environment(self) -> Environment:
        """Detect current environment"""
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            logger.warning(f"Invalid environment '{env_str}', defaulting to development")
            return Environment.DEVELOPMENT

    def _get_config_file_for_environment(self) -> Optional[Path]:
        """Get configuration file for current environment"""
        config_files = {
            Environment.DEVELOPMENT: self.config_dir / "development.yaml",
            Environment.STAGING: self.config_dir / "staging.yaml",
            Environment.PRODUCTION: self.config_dir / "production.yaml",
            Environment.TEST: self.config_dir / "test.yaml",
        }

        config_file = config_files.get(self.environment)
        if config_file and config_file.exists():
            return config_file

        # Fallback to development config if environment-specific config doesn't exist
        fallback = self.config_dir / "development.yaml"
        if fallback.exists():
            logger.warning(
                f"Config file for {self.environment.value} not found, using development config"
            )
            return fallback

        logger.warning(f"No configuration file found for environment: {self.environment.value}")
        return None

    def load_environment_config(self) -> AppConfig:
        """
        Load configuration for current environment

        Returns:
            Loaded application configuration
        """
        config_file_str = str(self.config_file) if self.config_file else None

        # Load configuration
        config = self.config_manager.load_config(config_file_str)

        # Override environment-specific settings
        config.environment = self.environment

        # Set debug mode based on environment
        config.debug = self.environment == Environment.DEVELOPMENT

        # Adjust worker count based on environment
        if self.environment == Environment.PRODUCTION:
            config.workers = 4
        elif self.environment == Environment.STAGING:
            config.workers = 2
        else:
            config.workers = 1

        logger.info(f"Loaded {self.environment.value} environment configuration")

        return config

    def get_current_environment(self) -> Environment:
        """Get current environment"""
        return self.environment

    def get_config_file_path(self) -> Optional[str]:
        """Get current configuration file path"""
        return str(self.config_file) if self.config_file else None

    def list_available_environments(self) -> Dict[str, bool]:
        """
        List available environment configurations

        Returns:
            Dictionary mapping environment names to availability status
        """
        environments = {}
        for env in Environment:
            config_file = self.config_dir / f"{env.value}.yaml"
            environments[env.value] = config_file.exists()

        return environments

    def validate_environment_config(self) -> Dict[str, Any]:
        """
        Validate environment configuration

        Returns:
            Dictionary with validation results
        """
        results: Dict[str, Any] = {
            "environment": self.environment.value,
            "config_file_exists": self.config_file is not None,
            "config_file_path": str(self.config_file) if self.config_file else None,
            "validation_errors": [],
        }

        if not self.config_file:
            results["validation_errors"].append(
                f"No configuration file found for {self.environment.value}"
            )
            return results

        try:
            config = self.load_environment_config()

            # Validate critical settings for production
            if self.environment == Environment.PRODUCTION:
                if config.debug:
                    results["validation_errors"].append(
                        "Debug mode should not be enabled in production"
                    )

                if config.security.jwt_secret_key == os.environ.get(
                    "JWT_SECRET_KEY", "dev-secret-key-change-me"
                ):
                    results["validation_errors"].append(
                        "Default JWT secret key must be changed in production"
                    )

                if not config.security.tls_enabled:
                    results["validation_errors"].append("TLS should be enabled in production")

            results["valid"] = len(results["validation_errors"]) == 0

        except Exception as e:
            results["validation_errors"].append(f"Configuration validation failed: {str(e)}")
            results["valid"] = False

        return results


# Global environment configuration manager instance
environment_config_manager = EnvironmentConfigManager()


def setup_environment_configuration() -> Dict[str, Any]:
    """
    Setup environment-specific configuration

    Returns:
        Dictionary with setup results
    """
    try:
        # Validate environment configuration
        validation = environment_config_manager.validate_environment_config()

        if not validation.get("valid", False):
            logger.warning(
                f"Environment configuration validation failed: {validation['validation_errors']}"
            )

        # Load environment configuration
        environment_config_manager.load_environment_config()

        # Setup unified configuration with environment file
        setup_result = setup_unified_configuration(
            config_file=environment_config_manager.get_config_file_path()
        )

        logger.info(
            "Environment configuration setup completed for: "
            f"{environment_config_manager.environment.value}"
        )

        return {
            "status": "success",
            "environment": environment_config_manager.environment.value,
            "config_file": environment_config_manager.get_config_file_path(),
            "validation": validation,
            "unified_config_setup": setup_result,
        }

    except Exception as e:
        logger.error(f"Environment configuration setup failed: {e}")
        return {"status": "error", "error": str(e)}
