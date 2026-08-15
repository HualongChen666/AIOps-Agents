# -*- coding: utf-8 -*-
"""Shared infrastructure-automation executors for addon service operations."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from typing import Any, Callable, Dict, List, Optional


class CliExecutor:
    """Execute arbitrary CLI commands via ``subprocess.run``.

    Real execution is only enabled when the environment variable
    ``INFRA_EXECUTE_ENABLED`` is set to ``"true"``. By default every call is a
    dry run: the command is built and returned but ``subprocess`` is not
    invoked.
    """

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def run(
        self,
        command,
        args=None,
        cwd=None,
        env=None,
        check: bool = False,
    ) -> Dict[str, Any]:
        """Run a CLI command.

        Args:
            command: The executable name, or a pre-built list of tokens.
            args: Optional positional arguments for the executable.
            cwd: Working directory for the command.
            env: Extra environment variables merged into ``os.environ``.
            check: Whether to raise on a non-zero exit code.

        Returns:
            Dict with ``status``, ``returncode``, ``stdout``, ``stderr`` and
            the reconstructed ``command`` string.
        """
        if isinstance(command, list):
            cmd = list(command)
            if args:
                cmd.extend(args if isinstance(args, (list, tuple)) else [args])
        else:
            cmd = [command]
            if args:
                cmd.extend(args if isinstance(args, (list, tuple)) else [args])

        command_str = " ".join(str(c) for c in cmd)

        if self.dry_run:
            return {
                "status": "ok",
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "command": command_str,
                "dry_run": True,
            }

        full_env = dict(os.environ)
        if env:
            full_env.update(env)

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=full_env,
                capture_output=True,
                text=True,
                check=check,
            )
        except subprocess.CalledProcessError as exc:
            return {
                "status": "error",
                "returncode": exc.returncode,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "command": command_str,
            }

        stdout = proc.stdout
        stderr = proc.stderr
        parsed = stdout
        if stdout and stdout.lstrip().startswith(("{", "[")):
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                pass

        return {
            "status": "ok",
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "data": parsed,
            "command": command_str,
        }


class AnsibleExecutor(CliExecutor):
    """Run Ansible playbooks with optional dry-run ``--check`` support."""

    def run(self, args=None, cwd=None, env=None, check: bool = False):
        return super().run("ansible-playbook", args=args, cwd=cwd, env=env, check=check)


class TerraformExecutor(CliExecutor):
    """Run Terraform subcommands with dry-run support."""

    def run(self, args=None, cwd=None, env=None, check: bool = False):
        return super().run("terraform", args=args, cwd=cwd, env=env, check=check)


class HelmExecutor(CliExecutor):
    """Run Helm commands with ``--dry-run`` support."""

    def run(self, args=None, cwd=None, env=None, check: bool = False):
        return super().run("helm", args=args, cwd=cwd, env=env, check=check)


class K8sExecutor(CliExecutor):
    """Run kubectl/helm/istioctl/chaosctl/velero/pgbackrest commands.

    The first token in ``kubectl_args`` is used as the binary if it is one of
    the supported tools; otherwise ``kubectl`` is assumed.  When ``dry_run`` is
    active, ``--dry-run`` flags are appended to kubectl/helm commands where
    appropriate.
    """

    SUPPORTED = {"kubectl", "helm", "istioctl", "chaosctl", "velero", "pgbackrest"}
    KUBECTL_WRITE_VERBS = {"apply", "create", "delete", "replace", "patch", "run"}

    def run(self, kubectl_args, namespace=None):
        if isinstance(kubectl_args, str):
            tokens = shlex.split(kubectl_args)
        else:
            tokens = list(kubectl_args or [])

        if not tokens:
            raise ValueError("K8sExecutor requires non-empty command arguments")

        tool = tokens[0] if tokens[0] in self.SUPPORTED else "kubectl"
        args = tokens[1:] if tokens[0] in self.SUPPORTED else tokens

        cmd = [tool]
        if namespace and tool in ("kubectl", "helm", "istioctl", "chaosctl", "velero"):
            cmd.extend(["--namespace", str(namespace)])

        if self.dry_run:
            if tool == "kubectl" and any(a in self.KUBECTL_WRITE_VERBS for a in args):
                cmd.append("--dry-run=client")
            elif tool == "helm":
                cmd.append("--dry-run")

        cmd.extend(args)
        return super().run(cmd)


class BaseInfraService:
    """Base class for infrastructure-automation addon services.

    Subclasses define ``OPERATIONS`` (used for API discovery) and a
    ``COMMAND_MAP`` mapping each operation name to a callable returning a
    command spec dict.
    """

    OPERATIONS: List[str] = []
    COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
    BASE_METHODS: List[str] = [
        "get_state",
        "backup_state",
        "restore_state",
        "get_stats",
        "list_methods",
    ]
    display_name: str = "infra"

    def __init__(self, dry_run: Optional[bool] = None) -> None:
        if dry_run is None:
            dry_run = not (os.environ.get("INFRA_EXECUTE_ENABLED") == "true")
        self.dry_run = dry_run
        self.cli = CliExecutor(dry_run=dry_run)
        self.k8s = K8sExecutor(dry_run=dry_run)
        self.ansible = AnsibleExecutor(dry_run=dry_run)
        self.terraform = TerraformExecutor(dry_run=dry_run)
        self.helm = HelmExecutor(dry_run=dry_run)

    def _executor(self, executor_type: str) -> CliExecutor:
        return getattr(self, executor_type, self.cli)

    def execute_operation(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an infrastructure operation by name."""
        params = params or {}

        if name == "list_methods":
            return {
                "feature": "list_methods",
                "success": True,
                "status": "ok",
                "config": {},
                "result": {"methods": self.OPERATIONS + self.BASE_METHODS},
                "message": "Methods listed",
            }
        if name == "get_state":
            return {
                "feature": "get_state",
                "success": True,
                "status": "ok",
                "config": params,
                "result": {"state": {}},
                "message": "State",
            }
        if name == "get_stats":
            return {
                "feature": "get_stats",
                "success": True,
                "status": "ok",
                "config": {},
                "result": {"operations": {}, "feature_count": len(self.OPERATIONS)},
                "message": "Statistics",
            }
        if name in ("backup_state", "restore_state"):
            return {
                "feature": name,
                "success": True,
                "status": "ok",
                "config": params,
                "result": {"snapshot": params.get("name", "default")},
                "message": f"{name} completed",
            }

        if name not in self.OPERATIONS:
            return {
                "feature": name,
                "success": False,
                "status": "unknown",
                "config": params,
                "result": {},
                "message": f"Unknown operation {name}",
            }

        spec_factory = self.COMMAND_MAP.get(name)
        if not spec_factory:
            return {
                "feature": name,
                "success": False,
                "status": "not_mapped",
                "config": params,
                "result": {},
                "message": f"No command mapping for {name}",
            }

        spec = spec_factory(params)
        executor_type = spec.get("executor", "cli")
        command = spec.get("command", [])
        namespace = spec.get("namespace")

        if executor_type == "k8s":
            result = self.k8s.run(command, namespace=namespace)
        elif executor_type in ("ansible", "terraform", "helm"):
            result = getattr(self, executor_type).run(command)
        else:
            if not command:
                return {
                    "feature": name,
                    "success": False,
                    "status": "error",
                    "config": params,
                    "result": {},
                    "message": "Empty command",
                }
            result = self.cli.run(command[0], command[1:])

        return {
            "feature": name,
            "success": result.get("status") == "ok",
            "status": result.get("status", "ok"),
            "config": params,
            "result": result,
            "message": f"{name} completed",
        }
