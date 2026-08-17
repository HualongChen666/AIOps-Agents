# -*- coding: utf-8 -*-
"""Real-execution branch coverage for infra_executor with mocked subprocess only."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from extensions.addons.engines.infra_executor import (
    AnsibleExecutor,
    BaseInfraService,
    CliExecutor,
    HelmExecutor,
    K8sExecutor,
    TerraformExecutor,
)
from modules.execute.auto_heal.playbook_manager import PlaybookManager


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    """Fake subprocess.CompletedProcess-like object."""
    return MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)


# ------------------------------------------------------------------
# CliExecutor Tests
# ------------------------------------------------------------------
def test_cli_executor_list_command_with_args(monkeypatch):
    """Test CliExecutor with list command and args."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run(["echo", "hello"], args=["world"])
    assert result["status"] == "ok"
    assert result["command"] == "echo hello world"


def test_cli_executor_string_command_with_args(monkeypatch):
    """Test CliExecutor with string command and args."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello", "world"])
    assert result["status"] == "ok"
    assert result["command"] == "echo hello world"


def test_cli_executor_env_merging(monkeypatch):
    """Test CliExecutor with environment variable merging."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello"], env={"TEST_VAR": "test_value"})
    assert result["status"] == "ok"


def test_cli_executor_json_stdout(monkeypatch):
    """Test CliExecutor with JSON stdout parsing."""
    json_output = json.dumps({"key": "value"})
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout=json_output, returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello"])
    assert result["status"] == "ok"
    assert result["data"] == {"key": "value"}


def test_cli_executor_json_decode_error(monkeypatch):
    """Test CliExecutor with invalid JSON stdout."""
    invalid_json = '{"key": invalid}'
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout=invalid_json, returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello"])
    assert result["status"] == "ok"
    assert result["data"] == invalid_json


def test_cli_executor_non_json_stdout(monkeypatch):
    """Test CliExecutor with non-JSON stdout."""
    plain_output = "plain text output"
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout=plain_output, returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello"])
    assert result["status"] == "ok"
    assert result["data"] == plain_output


def test_cli_executor_called_process_error(monkeypatch):
    """Test CliExecutor with CalledProcessError."""
    def fake_run(cmd, **kwargs):
        exc = subprocess.CalledProcessError(1, cmd)
        exc.stdout = "error output"
        exc.stderr = "error message"
        raise exc

    monkeypatch.setattr("subprocess.run", fake_run)

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello"], check=True)
    assert result["status"] == "error"
    assert result["returncode"] == 1


def test_cli_executor_list_stdout(monkeypatch):
    """Test CliExecutor with list-style JSON stdout."""
    json_output = json.dumps([{"key": "value"}])
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout=json_output, returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=["hello"])
    assert result["status"] == "ok"
    assert result["data"] == [{"key": "value"}]


def test_cli_executor_dry_run():
    """Test CliExecutor in dry-run mode."""
    cli = CliExecutor(dry_run=True)
    result = cli.run("echo", args=["hello"])
    assert result["status"] == "ok"
    assert result["dry_run"] is True
    assert result["stdout"] == ""


# ------------------------------------------------------------------
# AnsibleExecutor Tests
# ------------------------------------------------------------------
def test_ansible_executor_args_none(monkeypatch, tmp_path):
    """Test AnsibleExecutor with args=None."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=None)
    assert result["status"] == "ok"
    assert result["command"] == "ansible-playbook"


def test_ansible_executor_args_string(monkeypatch, tmp_path):
    """Test AnsibleExecutor with string args."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args="site.yml --check")
    assert result["status"] == "ok"
    assert "site.yml" in result["command"]


def test_ansible_executor_empty_args_fallback(monkeypatch, tmp_path):
    """Test AnsibleExecutor with empty args falls back to CliExecutor."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=[])
    assert result["status"] == "ok"
    assert result["command"] == "ansible-playbook"


def test_ansible_executor_absolute_playbook_path(monkeypatch, tmp_path):
    """Test AnsibleExecutor with absolute playbook path."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    # Mock both subprocess.run and asyncio.create_subprocess_exec
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=[str(playbooks / "site.yml")])
    assert result["status"] == "ok"


def test_ansible_executor_relative_playbook_with_cwd(monkeypatch, tmp_path):
    """Test AnsibleExecutor with relative playbook path and cwd."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_relative_playbook_parent_dot(monkeypatch, tmp_path):
    """Test AnsibleExecutor with relative playbook path, parent is '.'."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    # Change to playbooks directory so relative path "site.yml" has parent "."
    original_cwd = os.getcwd()
    try:
        os.chdir(str(playbooks))
        ansible = AnsibleExecutor(dry_run=False)
        result = ansible.run(args=["site.yml"])
        assert result["status"] == "ok"
    finally:
        os.chdir(original_cwd)


def test_ansible_executor_relative_playbook_parent_not_dot(monkeypatch, tmp_path):
    """Test AnsibleExecutor with relative playbook path, parent not '.'."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    original_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        ansible = AnsibleExecutor(dry_run=False)
        result = ansible.run(args=["playbooks/site.yml"])
        assert result["status"] == "ok"
    finally:
        os.chdir(original_cwd)


def test_ansible_executor_playbook_not_found(monkeypatch, tmp_path):
    """Test AnsibleExecutor when playbook file doesn't exist."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_extra_vars_json(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --extra-vars JSON."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(
        args=["site.yml", "--extra-vars", '{"key": "value"}'], cwd=str(playbooks)
    )
    assert result["status"] == "ok"


def test_ansible_executor_extra_vars_key_value(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --extra-vars key=value."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(
        args=["site.yml", "--extra-vars", "key1=value1 key2=value2"], cwd=str(playbooks)
    )
    assert result["status"] == "ok"


def test_ansible_executor_extra_vars_pair_without_equals(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --extra-vars pair that has no = after split."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    # This will have a pair that splits but doesn't have = in the second part
    result = ansible.run(
        args=["site.yml", "--extra-vars", "key1=value1 key2"], cwd=str(playbooks)
    )
    assert result["status"] == "ok"


def test_ansible_executor_extra_vars_flag(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --extra-vars flag (no =)."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--extra-vars", "someflag"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_extra_vars_missing_value(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --extra-vars missing value."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--extra-vars"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_tags_missing_value(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --tags missing value."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--tags"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_limit_missing_value(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --limit missing value."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--limit"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_unrecognised_args(monkeypatch, tmp_path):
    """Test AnsibleExecutor with unrecognised args."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--unknown-flag"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_check_flag(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --check flag."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--check"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_load_playbook_failure(monkeypatch, tmp_path):
    """Test AnsibleExecutor when load_playbook fails."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    # Create invalid YAML
    (playbooks / "invalid.yml").write_text("invalid: yaml: content: [")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["invalid.yml"], cwd=str(playbooks))
    assert result["status"] == "ok"


def test_ansible_executor_execute_playbook_success_false(monkeypatch, tmp_path):
    """Test AnsibleExecutor when execute_playbook returns success=False."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    # Mock PlaybookManager to return success=False
    class FakePlaybookManager:
        def __init__(self, playbook_dir=None, dry_run=False):
            self.playbook_dir = playbook_dir or ""
            self.dry_run = dry_run

        def load_playbook(self, name):
            return True

        async def execute_playbook(self, name, **kwargs):
            return {"success": False, "return_code": 1, "stdout": "error", "stderr": "failed"}

    monkeypatch.setattr(
        "extensions.addons.engines.infra_executor.PlaybookManager",
        FakePlaybookManager,
    )

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml"], cwd=str(playbooks))
    assert result["status"] == "error"
    assert result["returncode"] == 1


def test_ansible_executor_dry_run():
    """Test AnsibleExecutor in dry-run mode."""
    ansible = AnsibleExecutor(dry_run=True)
    result = ansible.run(args=["site.yml"])
    assert result["status"] == "ok"
    assert result["dry_run"] is True


def test_ansible_executor_with_real_playbook_manager(monkeypatch, tmp_path):
    """Test AnsibleExecutor with real PlaybookManager in dry_run mode."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    # Mock subprocess for PlaybookManager's execute_playbook
    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(args=["site.yml", "--check"], cwd=str(playbooks))
    assert result["status"] == "ok"


# ------------------------------------------------------------------
# K8sExecutor Tests
# ------------------------------------------------------------------
def test_k8s_executor_string_input(monkeypatch):
    """Test K8sExecutor with string input."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run("kubectl get pods")
    assert result["status"] == "ok"


def test_k8s_executor_unsupported_token_defaults_kubectl(monkeypatch):
    """Test K8sExecutor with unsupported first token defaults to kubectl."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["unknown", "get", "pods"])
    assert result["status"] == "ok"
    assert "kubectl" in result["command"]


def test_k8s_executor_empty_args():
    """Test K8sExecutor with empty args raises ValueError."""
    k8s = K8sExecutor(dry_run=False)
    with pytest.raises(ValueError, match="non-empty command arguments"):
        k8s.run([])


def test_k8s_executor_namespace_kubectl(monkeypatch):
    """Test K8sExecutor with namespace for kubectl."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["kubectl", "get", "pods"], namespace="test-ns")
    assert result["status"] == "ok"
    assert "--namespace" in result["command"]
    assert "test-ns" in result["command"]


def test_k8s_executor_namespace_helm(monkeypatch):
    """Test K8sExecutor with namespace for helm."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["helm", "list"], namespace="test-ns")
    assert result["status"] == "ok"
    assert "--namespace" in result["command"]


def test_k8s_executor_namespace_istioctl(monkeypatch):
    """Test K8sExecutor with namespace for istioctl."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["istioctl", "get", "routes"], namespace="test-ns")
    assert result["status"] == "ok"
    assert "--namespace" in result["command"]


def test_k8s_executor_namespace_chaosctl(monkeypatch):
    """Test K8sExecutor with namespace for chaosctl."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["chaosctl", "list"], namespace="test-ns")
    assert result["status"] == "ok"
    assert "--namespace" in result["command"]


def test_k8s_executor_namespace_velero(monkeypatch):
    """Test K8sExecutor with namespace for velero."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["velero", "get", "backups"], namespace="test-ns")
    assert result["status"] == "ok"
    assert "--namespace" in result["command"]


def test_k8s_executor_kubectl_write_dry_run():
    """Test K8sExecutor with kubectl write verb in dry-run mode."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "apply", "-f", "config.yaml"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_kubectl_read_dry_run():
    """Test K8sExecutor with kubectl read verb in dry-run mode (no --dry-run)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "get", "pods"])
    assert result["status"] == "ok"
    assert "--dry-run" not in result["command"]


def test_k8s_executor_helm_dry_run():
    """Test K8sExecutor with helm in dry-run mode."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["helm", "install", "release", "chart"])
    assert result["status"] == "ok"
    assert "--dry-run" in result["command"]


def test_k8s_executor_istioctl_dry_run():
    """Test K8sExecutor with istioctl in dry-run mode (no --dry-run)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["istioctl", "get", "routes"])
    assert result["status"] == "ok"
    # istioctl doesn't get --dry-run in the current implementation


def test_k8s_executor_all_supported_tools(monkeypatch):
    """Test K8sExecutor with all supported tools."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    for tool in ["kubectl", "helm", "istioctl", "chaosctl", "velero", "pgbackrest"]:
        result = k8s.run([tool, "version"])
        assert result["status"] == "ok"


def test_k8s_executor_dry_run_false(monkeypatch):
    """Test K8sExecutor with dry_run=False."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["kubectl", "get", "pods"])
    assert result["status"] == "ok"
    assert "--dry-run" not in result["command"]


# ------------------------------------------------------------------
# BaseInfraService Tests
# ------------------------------------------------------------------
def test_base_infra_service_env_driven_dry_run(monkeypatch):
    """Test BaseInfraService with env-driven dry_run."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    service = BaseInfraService()
    assert service.dry_run is False

    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    service = BaseInfraService()
    assert service.dry_run is True

    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    service = BaseInfraService()
    assert service.dry_run is True


def test_base_infra_service_explicit_dry_run():
    """Test BaseInfraService with explicit dry_run parameter."""
    service = BaseInfraService(dry_run=True)
    assert service.dry_run is True

    service = BaseInfraService(dry_run=False)
    assert service.dry_run is False


def test_base_infra_service_unknown_operation():
    """Test BaseInfraService with unknown operation."""
    service = BaseInfraService()
    result = service.execute_operation("unknown_operation")
    assert result["success"] is False
    assert result["status"] == "unknown"


def test_base_infra_service_unmapped_operation():
    """Test BaseInfraService with unmapped operation (in OPERATIONS but not in COMMAND_MAP)."""
    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {}

    service = TestService()
    result = service.execute_operation("test_op")
    assert result["success"] is False
    assert result["status"] == "not_mapped"


def test_base_infra_service_empty_command():
    """Test BaseInfraService with empty command."""
    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "cli", "command": []}
        }

    service = TestService()
    result = service.execute_operation("test_op")
    assert result["success"] is False
    assert result["status"] == "error"
    assert "Empty command" in result["message"]


def test_base_infra_service_error_state_transition(monkeypatch):
    """Test BaseInfraService when executor returns error status."""
    def fake_run(cmd, **kwargs):
        exc = subprocess.CalledProcessError(1, cmd)
        exc.stdout = "error output"
        exc.stderr = "error message"
        raise exc

    monkeypatch.setattr("subprocess.run", fake_run)

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "cli", "command": ["echo", "error"]}
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is False
    assert result["status"] == "error"


def test_base_infra_service_list_methods():
    """Test BaseInfraService list_methods operation."""
    service = BaseInfraService()
    result = service.execute_operation("list_methods")
    assert result["success"] is True
    assert "methods" in result["result"]


def test_base_infra_service_get_state():
    """Test BaseInfraService get_state operation."""
    service = BaseInfraService()
    result = service.execute_operation("get_state")
    assert result["success"] is True
    assert "state" in result["result"]


def test_base_infra_service_get_stats():
    """Test BaseInfraService get_stats operation."""
    service = BaseInfraService()
    result = service.execute_operation("get_stats")
    assert result["success"] is True
    assert "operations" in result["result"]


def test_base_infra_service_backup_state():
    """Test BaseInfraService backup_state operation."""
    service = BaseInfraService()
    result = service.execute_operation("backup_state", {"name": "snapshot1"})
    assert result["success"] is True
    assert result["result"]["snapshot"] == "snapshot1"


def test_base_infra_service_restore_state():
    """Test BaseInfraService restore_state operation."""
    service = BaseInfraService()
    result = service.execute_operation("restore_state", {"name": "snapshot1"})
    assert result["success"] is True
    assert result["result"]["snapshot"] == "snapshot1"


def test_base_infra_service_k8s_executor(monkeypatch):
    """Test BaseInfraService with k8s executor."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "k8s", "command": ["kubectl", "get", "pods"]}
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_ansible_executor(monkeypatch, tmp_path):
    """Test BaseInfraService with ansible executor."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "ansible", "command": ["site.yml"]}
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_terraform_executor(monkeypatch):
    """Test BaseInfraService with terraform executor."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "terraform", "command": ["plan"]}
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_helm_executor(monkeypatch):
    """Test BaseInfraService with helm executor."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "helm", "command": ["list"]}
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_cli_executor(monkeypatch):
    """Test BaseInfraService with cli executor (default)."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {"executor": "cli", "command": ["echo", "hello"]}
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_with_namespace(monkeypatch):
    """Test BaseInfraService with namespace in command spec."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {
                "executor": "k8s",
                "command": ["kubectl", "get", "pods"],
                "namespace": "test-ns"
            }
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_unknown_executor_type(monkeypatch):
    """Test BaseInfraService with unknown executor type falls back to cli."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    class TestService(BaseInfraService):
        OPERATIONS = ["test_op"]
        COMMAND_MAP = {
            "test_op": lambda params: {
                "executor": "unknown_type",
                "command": ["echo", "hello"]
            }
        }

    service = TestService(dry_run=False)
    result = service.execute_operation("test_op")
    assert result["success"] is True


def test_base_infra_service_executor_method_fallback():
    """Test BaseInfraService _executor method fallback to cli."""
    service = BaseInfraService()
    # Test with a non-existent executor type
    executor = service._executor("nonexistent_executor")
    assert executor == service.cli


# ------------------------------------------------------------------
# TerraformExecutor and HelmExecutor Tests
# ------------------------------------------------------------------
def test_terraform_executor_real_branches(monkeypatch):
    """Test TerraformExecutor real branches."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    terraform = TerraformExecutor(dry_run=False)
    result = terraform.run(["plan"])
    assert result["status"] == "ok"
    assert "terraform" in result["command"]


def test_helm_executor_real_branches(monkeypatch):
    """Test HelmExecutor real branches."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    helm = HelmExecutor(dry_run=False)
    result = helm.run(["list"])
    assert result["status"] == "ok"
    assert "helm" in result["command"]


# ------------------------------------------------------------------
# Additional edge cases
# ------------------------------------------------------------------
def test_cli_executor_args_as_string(monkeypatch):
    """Test CliExecutor with args as string (not list)."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args="hello")
    assert result["status"] == "ok"
    assert result["command"] == "echo hello"


def test_cli_executor_args_as_tuple(monkeypatch):
    """Test CliExecutor with args as tuple."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run("echo", args=("hello", "world"))
    assert result["status"] == "ok"
    assert result["command"] == "echo hello world"


def test_cli_executor_list_command_args_as_string(monkeypatch):
    """Test CliExecutor with list command and args as string."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    result = cli.run(["echo"], args="hello")
    assert result["status"] == "ok"
    assert result["command"] == "echo hello"


def test_ansible_executor_extra_vars_multiple_pairs(monkeypatch, tmp_path):
    """Test AnsibleExecutor with multiple key=value pairs in --extra-vars."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(
        args=["site.yml", "--extra-vars", "key1=value1 key2=value2 key3=value3"],
        cwd=str(playbooks)
    )
    assert result["status"] == "ok"


def test_ansible_executor_limit_with_value(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --limit with a value."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(
        args=["site.yml", "--limit", "host1,host2"], cwd=str(playbooks)
    )
    assert result["status"] == "ok"


def test_ansible_executor_tags_with_spaces(monkeypatch, tmp_path):
    """Test AnsibleExecutor with --tags containing spaces."""
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")

    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    async def fake_subprocess_exec(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 0
        async def fake_communicate():
            return (b"stdout", b"stderr")
        proc.communicate = fake_communicate
        return proc

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess_exec)

    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run(
        args=["site.yml", "--tags", "tag1, tag2 , tag3"],
        cwd=str(playbooks)
    )
    assert result["status"] == "ok"


def test_k8s_executor_write_verb_apply():
    """Test K8sExecutor with apply verb (write)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "apply", "-f", "config.yaml"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_write_verb_create():
    """Test K8sExecutor with create verb (write)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "create", "-f", "config.yaml"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_write_verb_delete():
    """Test K8sExecutor with delete verb (write)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "delete", "pod", "test"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_write_verb_replace():
    """Test K8sExecutor with replace verb (write)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "replace", "-f", "config.yaml"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_write_verb_patch():
    """Test K8sExecutor with patch verb (write)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "patch", "deployment", "test", "-p", "{}"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_write_verb_run():
    """Test K8sExecutor with run verb (write)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "run", "test", "--image=nginx"])
    assert result["status"] == "ok"
    assert "--dry-run=client" in result["command"]


def test_k8s_executor_read_verb_get():
    """Test K8sExecutor with get verb (read)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "get", "pods"])
    assert result["status"] == "ok"
    assert "--dry-run" not in result["command"]


def test_k8s_executor_read_verb_describe():
    """Test K8sExecutor with describe verb (read)."""
    k8s = K8sExecutor(dry_run=True)
    result = k8s.run(["kubectl", "describe", "pod", "test"])
    assert result["status"] == "ok"
    assert "--dry-run" not in result["command"]


def test_k8s_executor_pgbackrest(monkeypatch):
    """Test K8sExecutor with pgbackrest tool."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["pgbackrest", "info"])
    assert result["status"] == "ok"
    assert "pgbackrest" in result["command"]


def test_k8s_executor_pgbackrest_namespace(monkeypatch):
    """Test K8sExecutor with pgbackrest and namespace (should not add namespace)."""
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(stdout="output", returncode=0),
    )

    k8s = K8sExecutor(dry_run=False)
    result = k8s.run(["pgbackrest", "info"], namespace="test-ns")
    assert result["status"] == "ok"
    # pgbackrest is not in the namespace list, so --namespace should not be added
    assert "--namespace" not in result["command"]
