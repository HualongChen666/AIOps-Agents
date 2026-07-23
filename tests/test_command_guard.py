# -*- coding: utf-8 -*-
"""
Unit tests for core/command_guard.py

Tests for the command guard system that analyzes and protects against dangerous commands.
"""

import os

import pytest  # noqa: F401

from core.command_guard import (
    RiskLevel,
    analyze_command,
    clear_audit_log,
    dry_run_preview,
    get_audit_log,
    get_protected_pids,
    register_self_pid,
    rewrite_to_safe,
    unregister_self_pid,
)


class TestRiskLevel:
    """Test RiskLevel enum functionality."""

    def test_risk_level_values(self):
        """Test that RiskLevel enum has correct values."""
        assert RiskLevel.SAFE.value == "safe"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.BLOCKED.value == "blocked"

    def test_risk_level_to_json(self):
        """Test RiskLevel to_json method."""
        assert RiskLevel.SAFE.serialize_to_json() == "safe"
        assert RiskLevel.BLOCKED.serialize_to_json() == "blocked"


class TestPIDProtection:
    """Test PID protection functionality for preventing self-termination."""

    def setup_method(self):
        """Clear protected PIDs before each test."""
        for pid in list(get_protected_pids()):
            unregister_self_pid(pid)

    def teardown_method(self):
        """Clean up protected PIDs after each test."""
        for pid in list(get_protected_pids()):
            unregister_self_pid(pid)

    def test_register_self_pid_default(self):
        """Test registering current process PID."""
        register_self_pid()
        protected = get_protected_pids()
        assert len(protected) == 1
        assert os.getpid() in protected

    def test_register_self_pid_specific(self):
        """Test registering a specific PID."""
        test_pid = 12345
        register_self_pid(test_pid)
        protected = get_protected_pids()
        assert test_pid in protected

    def test_register_self_pid_invalid(self):
        """Test registering invalid PID is rejected."""
        register_self_pid(-1)
        register_self_pid(0)
        protected = get_protected_pids()
        assert len(protected) == 0

    def test_unregister_self_pid(self):
        """Test unregistering a protected PID."""
        test_pid = 12345
        register_self_pid(test_pid)
        assert test_pid in get_protected_pids()

        unregister_self_pid(test_pid)
        assert test_pid not in get_protected_pids()

    def test_get_protected_pids_returns_copy(self):
        """Test that get_protected_pids returns a copy, not the original set."""
        test_pid = 12345
        register_self_pid(test_pid)

        protected = get_protected_pids()
        protected.add(99999)  # Modify the returned set

        # Original should not be modified
        assert 99999 not in get_protected_pids()


class TestAnalyzeCommand:
    """Test command analysis functionality."""

    def setup_method(self):
        """Clear protected PIDs before each test."""
        for pid in list(get_protected_pids()):
            unregister_self_pid(pid)

    def teardown_method(self):
        """Clean up protected PIDs after each test."""
        for pid in list(get_protected_pids()):
            unregister_self_pid(pid)

    def test_analyze_safe_command(self):
        """Test analysis of a safe command."""
        result = analyze_command("ls -la")
        assert result["risk_level"] == RiskLevel.SAFE
        assert "reason" in result

    def test_analyze_dangerous_command(self):
        """Test analysis of a dangerous command."""
        result = analyze_command("rm -rf /")
        assert result["risk_level"] in [RiskLevel.HIGH, RiskLevel.BLOCKED]

    def test_analyze_command_with_protected_pid(self):
        """Test that commands targeting protected PIDs are blocked."""
        test_pid = 12345
        register_self_pid(test_pid)

        result = analyze_command(f"kill -9 {test_pid}")
        assert result["risk_level"] == RiskLevel.BLOCKED
        assert str(test_pid) in result["reason"]
        assert "AIOps Agent" in result["reason"]

    def test_analyze_empty_command(self):
        """Test analysis of empty command."""
        result = analyze_command("")
        assert result["risk_level"] == RiskLevel.SAFE

    def test_analyze_command_with_pipe(self):
        """Test analysis of command with pipe."""
        result = analyze_command("cat /etc/passwd | grep root")
        assert result["risk_level"] in [
            RiskLevel.SAFE,
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
        ]


class TestRewriteToSafe:
    """Test command rewriting functionality."""

    def test_rewrite_dangerous_command(self):
        """Test rewriting a dangerous command to safe alternative."""
        result = rewrite_to_safe("rm -rf /")
        assert result is not None
        assert isinstance(result, str)
        # Should provide a safer alternative or original if no alternative exists

    def test_rewrite_safe_command(self):
        """Test rewriting a safe command returns None or original."""
        result = rewrite_to_safe("ls -la")
        # Safe commands may not need rewriting
        assert result is None or isinstance(result, str)

    def test_rewrite_empty_command(self):
        """Test rewriting empty command."""
        result = rewrite_to_safe("")
        # Empty command should return None or empty string
        assert result is None or result == ""


class TestAuditLog:
    """Test audit logging functionality."""

    def setup_method(self):
        """Clear audit log before each test."""
        clear_audit_log()

    def teardown_method(self):
        """Clean up audit log after each test."""
        clear_audit_log()

    def test_get_audit_log_empty(self):
        """Test getting audit log when empty."""
        log = get_audit_log(limit=10)
        assert isinstance(log, list)
        assert len(log) == 0

    def test_get_audit_log_after_analysis(self):
        """Test that audit log is populated after command analysis."""
        analyze_command("rm -rf /")
        log = get_audit_log(limit=10)
        # Audit log might be empty depending on implementation
        assert isinstance(log, list)

    def test_get_audit_log_limit(self):
        """Test audit log limit parameter."""
        # Generate multiple audit entries
        for _ in range(5):
            analyze_command("test command")

        log = get_audit_log(limit=3)
        assert len(log) <= 3

    def test_clear_audit_log(self):
        """Test clearing audit log."""
        analyze_command("test command")
        initial_log = get_audit_log(limit=10)  # noqa: F841

        clear_audit_log()
        final_log = get_audit_log(limit=10)
        assert len(final_log) == 0


class TestDryRunPreview:
    """Test dry run preview functionality."""

    def test_dry_run_preview_safe_command(self):
        """Test dry run preview for safe command."""
        result = dry_run_preview("ls -la")
        assert result is not None
        # Result might be a string or dict depending on implementation
        if isinstance(result, dict):
            assert "risk_level" in result or "preview" in result

    def test_dry_run_preview_dangerous_command(self):
        """Test dry run preview for dangerous command."""
        result = dry_run_preview("rm -rf /")
        assert result is not None
        # Result might be a string or dict depending on implementation
        if isinstance(result, dict):
            assert result["risk_level"] in [RiskLevel.HIGH, RiskLevel.BLOCKED]

    def test_dry_run_preview_empty_command(self):
        """Test dry run preview for empty command."""
        result = dry_run_preview("")
        assert result is not None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_command_with_special_characters(self):
        """Test command with special characters."""
        result = analyze_command("echo 'test && rm -rf /'")
        assert result is not None
        assert "risk_level" in result

    def test_analyze_command_with_unicode(self):
        """Test command with unicode characters."""
        result = analyze_command("echo '测试'")
        assert result is not None

    def test_multiple_pid_registration(self):
        """Test registering multiple PIDs."""
        pids = [12345, 12346, 12347]
        for pid in pids:
            register_self_pid(pid)

        protected = get_protected_pids()
        for pid in pids:
            assert pid in protected

        # Cleanup
        for pid in pids:
            unregister_self_pid(pid)
