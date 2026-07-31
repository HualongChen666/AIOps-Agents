# -*- coding: utf-8 -*-
"""Configuration manager built on top of pydantic-settings based models.

ConfigManager loads configuration from .env files, environment variables and
optional JSON/YAML configuration files.  It exposes the same public API as the
legacy dataclass-based ConfigManager so existing callers keep working.
"""

from __future__ import annotations

import json
import os
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel

from core.config_models import AppConfig, Environment

# Optional python-dotenv support; required package is listed in requirements.txt.
DOTENV_AVAILABLE = False
_DOTENV_LOAD = None

try:
    from dotenv import load_dotenv

    _DOTENV_LOAD = load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover - environment dependency
    pass

# Optional watchdog support for hot reloading configuration files.
WATCHDOG_AVAILABLE = False
FileSystemEventHandler = object

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover - environment dependency
    pass


class ConfigFormat(Enum):
    """Supported configuration file formats."""

    JSON = "json"
    YAML = "yaml"
    ENV = "env"


class ConfigSource(Enum):
    """Configuration value sources."""

    ENV = "env"
    FILE = "file"
    DEFAULT = "default"


class ConfigManager:
    """Thread-safe configuration manager using pydantic-settings."""

    def __init__(self) -> None:
        self._config: Optional[AppConfig] = None
        self._config_file: Optional[Path] = None
        self._config_lock = threading.Lock()
        self._environment: Environment = self._detect_environment()
        self._config_history: List[Dict[str, Any]] = []
        self._audit_log: List[Dict[str, Any]] = []
        self._observer: Any = None

    def _detect_environment(self) -> Environment:
        """Detect the current environment from ENVIRONMENT or default to development."""
        env_value = os.getenv("ENVIRONMENT", "development").lower()
        try:
            return Environment(env_value)
        except ValueError:
            logger.warning(f"Unknown environment '{env_value}', using development")
            return Environment.DEVELOPMENT

    def _load_dotenv(self) -> None:
        """Load .env file into os.environ if python-dotenv is available."""
        if DOTENV_AVAILABLE and _DOTENV_LOAD is not None:
            try:
                _DOTENV_LOAD(encoding="utf-8")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Failed to load .env file: {exc}")

    def _load_from_file(self, config_file: Path) -> AppConfig:
        """Load configuration from a JSON or YAML file.

        Environment variables have higher precedence, so after building the model
        from the file, the model is re-instantiated so BaseSettings' env sources
        override file values.
        """
        suffix = config_file.suffix.lower()
        data: Dict[str, Any] = {}

        if suffix == ".json":
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml

                with open(config_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except ImportError as exc:  # pragma: no cover - optional dependency
                logger.error(f"PyYAML not installed, cannot load YAML config: {exc}")
        else:
            logger.warning(f"Unsupported config file extension: {suffix}")

        if not isinstance(data, dict):
            data = {}

        # Environment is always driven by the ENVIRONMENT variable / ConfigManager.
        data.pop("environment", None)

        # BaseSettings env sources will override the init kwargs (file values).
        return AppConfig(environment=self._environment, **data)  # type: ignore[call-arg]

    def _update_config_from_dict(self, config: AppConfig, data: Dict[str, Any]) -> AppConfig:
        """Update an existing AppConfig from a plain dictionary.

        Used for compatibility with the previous ConfigManager implementation.
        """
        for key, value in data.items():
            if not hasattr(config, key):
                continue
            attr = getattr(config, key)
            if isinstance(attr, BaseModel) and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if hasattr(attr, sub_key):
                        setattr(attr, sub_key, sub_value)
            else:
                setattr(config, key, value)
        return config

    def _load_from_env(self, config: AppConfig) -> AppConfig:
        """Apply environment-specific overrides and defaults that pydantic-settings
        cannot express directly (comma-separated CORS values, JWT defaults, etc.).
        """
        # JWT secret validation and default
        _jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if not _jwt_secret:
            _jwt_secret = config.security.jwt_secret_key

        if not _jwt_secret:
            if config.environment == Environment.PRODUCTION:
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production environment. "
                    "Please set a strong, unique secret key via: "
                    "export JWT_SECRET_KEY=<your-secret-key>"
                )
            _jwt_secret = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-me")
            logger.warning(
                "Using default JWT secret key! This is insecure for production. "
                "Please set JWT_SECRET_KEY environment variable for production use."
            )
        elif _jwt_secret in ("dev-secret-key-change-me", "default-secret-key"):
            if config.environment == Environment.PRODUCTION:
                raise ValueError(
                    "JWT_SECRET_KEY is set to a default/insecure value in production. "
                    "Please set a strong, unique secret key via: "
                    "export JWT_SECRET_KEY=<your-secret-key>"
                )
            logger.warning(
                "JWT_SECRET_KEY is set to a default/insecure value. "
                "Please set a strong, unique secret key for production use."
            )

        config.security.jwt_secret_key = _jwt_secret

        # CORS values are commonly comma-separated; BaseSettings expects JSON lists.
        if "CORS_ORIGINS" in os.environ:
            config.cors_origins = [
                x.strip() for x in os.environ["CORS_ORIGINS"].split(",") if x.strip()
            ]
        if "CORS_ALLOW_METHODS" in os.environ:
            config.cors_allow_methods = [
                x.strip() for x in os.environ["CORS_ALLOW_METHODS"].split(",") if x.strip()
            ]
        if "CORS_ALLOW_HEADERS" in os.environ:
            config.cors_allow_headers = [
                x.strip() for x in os.environ["CORS_ALLOW_HEADERS"].split(",") if x.strip()
            ]

        # AI API key fallback to AI_API_KEY
        if not config.ai.api_key:
            config.ai.api_key = os.getenv("AI_API_KEY", "")

        return config

    def _validate_config(self, config: AppConfig) -> None:
        """Validate configuration for production safety."""
        errors: List[str] = []

        if config.environment == Environment.PRODUCTION and config.security.tls_enabled:
            if not config.security.tls_cert_path or not config.security.tls_key_path:
                errors.append("TLS_CERT_PATH and TLS_KEY_PATH must be set when TLS is enabled")

        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug("Configuration validation passed")

    def load_config(self, config_file: Optional[str] = None) -> AppConfig:
        """Load and validate configuration.

        Priority (highest first): environment variables, .env values, config file, defaults.
        """
        with self._config_lock:
            self._load_dotenv()

            if config_file:
                self._config_file = Path(config_file)
                if self._config_file.exists():
                    config = self._load_from_file(self._config_file)
                else:
                    logger.warning(f"Config file not found: {config_file}")
                    config = AppConfig(environment=self._environment)  # type: ignore[call-arg]
            else:
                self._config_file = None
                config = AppConfig(environment=self._environment)  # type: ignore[call-arg]

            # Always honour the detected environment and sensible debug default.
            config.environment = self._environment
            config.debug = _safe_bool("DEBUG", self._environment == Environment.DEVELOPMENT)

            config = self._load_from_env(config)
            self._validate_config(config)

            self._config = config
            self._record_config_version(config)
            return config

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration from the previously loaded file."""
        if self._config_file:
            logger.info("Reloading configuration...")
            return self.load_config(str(self._config_file))
        logger.warning("No config file to reload from")
        return self.load_config()

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as a dictionary, excluding sensitive values."""
        config = self.get_config()
        return config.model_dump(
            mode="json",
            exclude={
                "database": {"password"},
                "redis": {"password"},
                "security": {"jwt_secret_key"},
                "ai": {"api_key"},
                "teams": {"client_secret"},
            },
        )

    def save_config(self, path: str) -> Dict[str, Any]:
        """Save current configuration to a JSON or YAML file."""
        config_path = Path(path)
        config_dict = self.get_config_dict()
        suffix = config_path.suffix.lower()

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                if suffix == ".json":
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
                elif suffix in (".yaml", ".yml"):
                    import yaml

                    yaml.safe_dump(config_dict, f, default_flow_style=False, allow_unicode=True)
                else:
                    raise ValueError(f"Unsupported config file extension: {suffix}")
        except Exception as exc:
            logger.error(f"Failed to save config to {path}: {exc}")
            raise

        return {"status": "success", "path": str(config_path)}

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a nested configuration value by dot-separated key."""
        try:
            current: Any = self.get_config()
            for part in key.split("."):
                current = getattr(current, part)
            return current
        except AttributeError:
            return default

    def set_config_value(self, key: str, value: Any) -> None:
        """Set a nested configuration value by dot-separated key."""
        config = self.get_config()
        parts = key.split(".")
        current: Any = config
        for part in parts[:-1]:
            current = getattr(current, part)
        setattr(current, parts[-1], value)

    def setup_unified_configuration(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Setup unified configuration and return a summary."""
        try:
            config = self.load_config(config_file)
            logger.info(
                f"Unified configuration setup completed for environment: {config.environment}"
            )
            return {
                "status": "success",
                "environment": config.environment,
                "config_file": str(self._config_file) if self._config_file else None,
                "config_summary": self.get_config_dict(),
            }
        except Exception as exc:
            logger.error(f"Unified configuration setup failed: {exc}")
            return {"status": "error", "error": str(exc)}

    def _record_config_version(self, config: AppConfig) -> None:
        """Store a snapshot of the current config for rollback and audit."""
        self._config_history.append(
            {
                "timestamp": time.time(),
                "config": config.model_dump(
                    mode="json",
                    exclude={
                        "security": {"jwt_secret_key"},
                        "ai": {"api_key"},
                        "database": {"password"},
                        "redis": {"password"},
                    },
                ),
            }
        )
        # Keep a bounded history to avoid unbounded memory growth.
        self._config_history = self._config_history[-10:]

    def audit_config_change(self, user: str, change: str, details: Dict[str, Any]) -> None:
        """Record a configuration change in the audit log."""
        self._audit_log.append(
            {
                "timestamp": time.time(),
                "user": user,
                "change": change,
                "details": details,
            }
        )
        logger.info(f"Config audit: {user} changed {change}")

    def rollback_config(self, steps: int = 1) -> Dict[str, Any]:
        """Rollback the configuration to a previous version."""
        if not self._config_history:
            return {"status": "error", "error": "no configuration history available"}
        target = self._config_history[-steps]
        try:
            self._config = AppConfig.model_validate(target["config"])
            self.audit_config_change("system", "rollback", {"steps": steps})
            return {"status": "success", "steps": steps}
        except Exception as exc:
            logger.error(f"Config rollback failed: {exc}")
            return {"status": "error", "error": str(exc)}

    def start_hot_reload(self, config_file: str) -> Dict[str, Any]:
        """Start watching the configuration file for changes and reload automatically."""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog is not installed; hot reload is disabled")
            return {"status": "disabled", "reason": "watchdog not installed"}
        if self._observer is not None:
            return {"status": "already_running"}
        config_path = Path(config_file).resolve()
        self._config_file = config_path
        self._observer = Observer()
        self._observer.schedule(
            self._ConfigReloadHandler(self),
            str(config_path.parent),
            recursive=False,
        )
        self._observer.start()
        logger.info(f"Started hot reload watcher for {config_path}")
        return {"status": "started", "path": str(config_path)}

    def stop_hot_reload(self) -> Dict[str, Any]:
        """Stop the configuration file watcher."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped hot reload watcher")
            return {"status": "stopped"}
        return {"status": "not_running"}

    class _ConfigReloadHandler(FileSystemEventHandler):
        """watchdog event handler that triggers a config reload."""

        def __init__(self, manager: "ConfigManager") -> None:
            self.manager = manager

        def on_modified(self, event: Any) -> None:
            if not self.manager._config_file:
                return
            if str(Path(event.src_path).resolve()) == str(self.manager._config_file.resolve()):
                logger.info("Config file modified, reloading")
                self.manager.reload_config()
                self.manager.audit_config_change(
                    "system", "hot_reload", {"file": str(self.manager._config_file)}
                )


class ConfigLoader:
    """Convenience loader for config files."""

    def load(self, config_file: Optional[str] = None) -> AppConfig:
        return config_manager.load_config(config_file)

    def save(self, path: str) -> Dict[str, Any]:
        return config_manager.save_config(path)


class ConfigValidator:
    """Public validator wrapper."""

    def validate(self, config: Optional[AppConfig] = None) -> List[str]:
        target = config or config_manager.get_config()
        try:
            AppConfig.model_validate(target)
        except Exception as exc:
            return [str(exc)]
        return []


def _safe_bool(name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""
    value = os.getenv(name, str(default)).lower()
    return value in ("true", "1", "yes", "on", "t")


def load_config(config_file: Optional[str] = None) -> AppConfig:
    return config_manager.load_config(config_file)


def save_config(path: str) -> Dict[str, Any]:
    return config_manager.save_config(path)


def get_config_value(key: str, default: Any = None) -> Any:
    return config_manager.get_config_value(key, default)


def setup_unified_configuration(config_file: Optional[str] = None) -> Dict[str, Any]:
    return config_manager.setup_unified_configuration(config_file)


# Global ConfigManager instance
config_manager = ConfigManager()
