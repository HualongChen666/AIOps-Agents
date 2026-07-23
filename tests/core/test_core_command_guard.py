# -*- coding: utf-8 -*-
"""测试命令守护模块"""

import pytest

from core.command_guard import (
    RiskLevel,
    analyze_command,
    clear_audit_log,
    dry_run_preview,
    get_audit_log,
    get_protected_pids,
    is_command_allowed,
    record_audit,
    register_self_pid,
    rewrite_to_safe,
    unregister_self_pid,
)


class TestRiskLevelAndPid:
    def test_risk_level_serialize(self):
        assert RiskLevel.HIGH.serialize_to_json() == "high"

    def test_register_self_pid_valid_invalid(self):
        register_self_pid(12345)
        assert 12345 in get_protected_pids()
        unregister_self_pid(12345)
        assert 12345 not in get_protected_pids()

    def test_register_self_pid_invalid(self):
        register_self_pid(-1)
        assert -1 not in get_protected_pids()


class TestCommandAnalysis:
    def test_empty_command(self):
        r = analyze_command("")
        assert r["risk_level"] == RiskLevel.SAFE
        assert r["action"] == "skip"

    def test_safe_exact_and_prefix(self):
        assert analyze_command("ls")["risk_level"] == RiskLevel.SAFE
        assert analyze_command("ps aux")["risk_level"] == RiskLevel.SAFE
        assert analyze_command("df -h")["risk_level"] == RiskLevel.SAFE
        assert analyze_command("cat /etc/os-release")["risk_level"] == RiskLevel.SAFE

    def test_blocked_patterns(self):
        r = analyze_command("rm -rf /")
        assert r["risk_level"] == RiskLevel.BLOCKED
        assert r["action"] == "block"
        assert "safe_alternative" in r

        assert analyze_command("mkfs /dev/sda")["risk_level"] == RiskLevel.BLOCKED
        assert analyze_command("DROP TABLE users")["risk_level"] == RiskLevel.BLOCKED
        assert analyze_command("taskkill /F /IM python.exe")["risk_level"] == RiskLevel.BLOCKED
        assert analyze_command("Stop-Process -Id $PID")["risk_level"] == RiskLevel.BLOCKED

    def test_high_risk_patterns(self):
        assert analyze_command("shutdown -r now")["risk_level"] == RiskLevel.HIGH
        assert analyze_command("iptables -F")["risk_level"] == RiskLevel.HIGH
        assert analyze_command("TRUNCATE TABLE users")["risk_level"] == RiskLevel.HIGH

    def test_chained_command_uses_worst(self):
        r = analyze_command("echo 'a;b' && rm -rf /")
        assert r["risk_level"] == RiskLevel.BLOCKED
        assert r.get("is_chained") is True

    def test_self_pid_protection(self):
        register_self_pid(12345)
        try:
            r = analyze_command("kill -9 12345")
            assert r["risk_level"] == RiskLevel.BLOCKED
            assert "AI 自杀防护" in r["risk_name"]
        finally:
            unregister_self_pid(12345)

    def test_unknown_command_low(self):
        r = analyze_command("some_custom_tool arg")
        assert r["risk_level"] == RiskLevel.LOW
        assert r["action"] == "execute"

    def test_is_command_allowed(self):
        assert is_command_allowed("ls") is True
        assert is_command_allowed("rm -rf /") is False


class TestRewriteAndPreview:
    def test_rewrite_to_safe_for_rm(self):
        out = rewrite_to_safe("rm /tmp/old_file")
        assert out.startswith("mkdir -p")
        assert "mv" in out

    def test_rewrite_to_safe_non_rm(self):
        assert rewrite_to_safe("ls /tmp") == "ls /tmp"

    def test_dry_run_preview(self):
        preview = dry_run_preview("rm /tmp/a")
        assert "将要删除的文件" in preview

        preview = dry_run_preview("systemctl restart sshd")
        assert "即将重启服务" in preview
        assert "sshd" in preview

        preview = dry_run_preview("echo hi")
        assert "Dry-run 预览" in preview


class TestAuditLog:
    def test_record_and_get_audit(self):
        clear_audit_log()
        record_audit("host1", "ls", "safe", "tester", "success")
        record_audit("host1", "rm -rf /", "blocked", "tester", "blocked")
        logs = get_audit_log(2)
        assert len(logs) == 2
        assert logs[0]["risk_level"] == "blocked"

    def test_get_audit_log_limit_clamped(self):
        clear_audit_log()
        record_audit("h", "c", "safe")
        assert len(get_audit_log(0)) == 1
        assert len(get_audit_log(999999)) == 1

    def test_clear_audit_log(self):
        clear_audit_log()
        record_audit("h", "c", "safe")
        assert clear_audit_log() == 1
        assert clear_audit_log() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
