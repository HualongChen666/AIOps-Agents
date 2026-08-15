# -*- coding: utf-8 -*-
"""Documentation and governance engines for the governance addon group."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None  # type: ignore

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


class _DryRunMixin:
    """Shared dry-run / real-execution gating helper."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def _execute_enabled(self) -> bool:
        return os.environ.get("INFRA_EXECUTE_ENABLED") == "true"

    def _should_run(self) -> bool:
        return (not self.dry_run) and self._execute_enabled()


class DocEngine(_DryRunMixin):
    """Engine for building and parsing Sphinx documentation."""

    def __init__(self, dry_run: bool = True) -> None:
        super().__init__(dry_run=dry_run)

    def build_docs(self, source: str, output: str) -> Dict[str, Any]:
        """Run ``sphinx-build`` for *source* into *output*.

        When ``dry_run`` is True or ``INFRA_EXECUTE_ENABLED`` is not ``"true"``,
        a dry-run report is returned without invoking Sphinx.
        """
        command = ["sphinx-build", str(source), str(output)]
        if not self._should_run():
            return {
                "dry_run": True,
                "command": " ".join(command),
                "source": source,
                "output": output,
                "warnings": 0,
                "errors": 0,
                "status": "would_run",
            }

        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        output_text = (proc.stdout or "") + (proc.stderr or "")
        warnings = (
            output_text.count("WARNING:")
            + output_text.lower().count("warning:")
        )
        errors = (
            output_text.count("ERROR:")
            + output_text.count("SEVERE:")
        )
        return {
            "dry_run": False,
            "returncode": proc.returncode,
            "command": " ".join(command),
            "source": source,
            "output": output,
            "warnings": warnings,
            "errors": errors,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "status": "completed" if proc.returncode == 0 else "failed",
        }


class PolicyEngine(_DryRunMixin):
    """Engine for validating schemas, OpenAPI, configs, users, and plugins."""

    def __init__(self, dry_run: bool = True) -> None:
        super().__init__(dry_run=dry_run)

    @staticmethod
    def _load_dict(spec: Any) -> Any:
        if isinstance(spec, dict):
            return spec
        if isinstance(spec, (str, os.PathLike)):
            path = Path(spec)
            if path.exists() and path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if path.suffix in {".yaml", ".yml"} and yaml is not None:
                    return yaml.safe_load(content) or {}
                return json.loads(content)
        return {}

    def lint_openapi(self, spec: Any) -> Dict[str, Any]:
        """Perform a basic OpenAPI structure check."""
        data = self._load_dict(spec)
        issues: List[str] = []
        if not isinstance(data, dict):
            issues.append("OpenAPI spec must be a dictionary")
            data = {}
        if "openapi" not in data or not data.get("openapi"):
            issues.append("missing or empty 'openapi' version")
        if not data.get("info", {}).get("title"):
            issues.append("missing or empty 'info.title'")
        if not isinstance(data.get("paths"), dict):
            issues.append("'paths' must be a dictionary")
        return {
            "dry_run": not self._should_run(),
            "valid": len(issues) == 0,
            "issues": issues,
            "version": data.get("openapi") if isinstance(data, dict) else None,
        }

    def validate_schema(self, obj: Any, schema: Any) -> Dict[str, Any]:
        """Validate *obj* against *schema* using ``jsonschema`` if available."""
        if jsonschema is not None:
            try:
                jsonschema.validate(instance=obj, schema=schema)
                return {
                    "dry_run": not self._should_run(),
                    "valid": True,
                    "errors": [],
                }
            except jsonschema.ValidationError as exc:
                return {
                    "dry_run": not self._should_run(),
                    "valid": False,
                    "errors": [str(exc)],
                }
            except Exception as exc:
                return {
                    "dry_run": not self._should_run(),
                    "valid": False,
                    "errors": [str(exc)],
                }

        # Basic fallback validator.
        errors: List[str] = []
        if not isinstance(obj, dict) or not isinstance(schema, dict):
            return {
                "dry_run": not self._should_run(),
                "valid": False,
                "errors": ["obj and schema must be dictionaries"],
            }

        expected = schema.get("type")
        type_map = {
            "object": dict,
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
        }
        if expected and expected in type_map:
            if not isinstance(obj, type_map[expected]):
                errors.append(f"expected type {expected}")

        for key in schema.get("required", []):
            if key not in obj:
                errors.append(f"missing required key: {key}")

        if isinstance(schema.get("properties"), dict):
            for key in schema["properties"]:
                if key in obj:
                    prop_schema = schema["properties"][key]
                    sub = self.validate_schema(obj[key], prop_schema)
                    if not sub.get("valid"):
                        errors.extend(sub.get("errors", []))

        return {
            "dry_run": not self._should_run(),
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def load_config(self, key: str) -> Dict[str, Any]:
        """Read configuration from JSON/YAML files, environment variables, or core.config_manager.

        In real execution, prefer core.config_manager.ConfigManager.get_config_value for
        dot-notation config keys, then fall back to direct file/env reading.
        """
        if self._should_run():
            try:
                from core.config_manager import ConfigManager

                cm = ConfigManager()
                cm.load_config()
                value = cm.get_config_value(key)
                if value is not None:
                    return {
                        "dry_run": False,
                        "source": "core.config_manager",
                        "value": value,
                    }
            except Exception:
                # ConfigManager unavailable or the key is not a known config path;
                # fall through to legacy file/env lookup.
                pass

        path = Path(key)
        if path.exists() and path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if path.suffix in {".yaml", ".yml"} and yaml is not None:
                    value = yaml.safe_load(content) or {}
                else:
                    value = json.loads(content)
                return {
                    "dry_run": not self._should_run(),
                    "source": str(path),
                    "value": value,
                }
            except Exception as exc:
                return {
                    "dry_run": not self._should_run(),
                    "source": str(path),
                    "value": None,
                    "error": str(exc),
                }

        env_value = os.environ.get(key)
        if env_value is not None:
            try:
                parsed = json.loads(env_value)
            except Exception:
                parsed = env_value
            return {
                "dry_run": not self._should_run(),
                "source": "env",
                "value": parsed,
            }

        return {
            "dry_run": not self._should_run(),
            "source": None,
            "value": None,
            "error": f"config not found: {key}",
        }

    def user_lookup(self, user_id: str) -> Dict[str, Any]:
        """Return simple user metadata, using ``core.authentication`` if available."""
        if not self._should_run():
            return {
                "dry_run": True,
                "found": True,
                "user_id": user_id,
                "source": "synthetic",
                "data": {"role": "user", "active": True},
            }

        auth_module = None
        try:
            import core.authentication as auth_module
        except Exception:
            auth_module = None

        getter = getattr(auth_module, "get_user_by_username", None) if auth_module is not None else None
        if getter is not None:
            try:
                user = getter(user_id)
                if user is not None:
                    return {
                        "dry_run": False,
                        "found": True,
                        "user_id": user_id,
                        "source": "core.authentication",
                        "data": user,
                    }
                return {
                    "dry_run": False,
                    "found": False,
                    "user_id": user_id,
                    "source": "core.authentication",
                }
            except Exception as exc:
                return {
                    "dry_run": False,
                    "found": False,
                    "user_id": user_id,
                    "source": "core.authentication",
                    "error": str(exc),
                }

        return {
            "dry_run": False,
            "found": True,
            "user_id": user_id,
            "source": "mock",
            "data": {"role": "user", "active": True},
        }

    def plugin_index(self) -> List[Dict[str, Any]]:
        """List plugin metadata discovered under ``extensions/addons``."""
        root = Path(__file__).resolve().parent.parent
        plugins: List[Dict[str, Any]] = []
        for path in root.rglob("service.py"):
            plugins.append(
                {
                    "id": path.parent.name,
                    "path": str(path.parent.relative_to(root.parent)),
                }
            )
        return plugins

    def plugin_load(self, plugin_id: str) -> Dict[str, Any]:
        """Safely import *plugin_id* when execution is enabled."""
        if not self._should_run():
            return {
                "dry_run": True,
                "loaded": False,
                "plugin_id": plugin_id,
                "message": "would load",
            }
        try:
            module = importlib.import_module(plugin_id)
            return {
                "dry_run": False,
                "loaded": True,
                "plugin_id": plugin_id,
                "module": module,
            }
        except Exception as exc:
            return {
                "dry_run": False,
                "loaded": False,
                "plugin_id": plugin_id,
                "error": str(exc),
            }

    def plugin_unload(self, plugin_id: str) -> Dict[str, Any]:
        """Safely remove *plugin_id* (and submodules) from ``sys.modules``."""
        removed: List[str] = []
        if self._should_run():
            for name in list(sys.modules):
                if name == plugin_id or name.startswith(plugin_id + "."):
                    sys.modules.pop(name, None)
                    removed.append(name)
        return {
            "dry_run": not self._should_run(),
            "unloaded": len(removed) > 0,
            "plugin_id": plugin_id,
            "removed": removed,
        }
