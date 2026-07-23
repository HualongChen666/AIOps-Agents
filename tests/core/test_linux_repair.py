# -*- coding: utf-8 -*-
"""测试 Linux 修复脚本库"""

import asyncio
import os

import pytest

import core.linux_repair as lr


@pytest.fixture(autouse=True)
def cleanup_db():
    lr.clear_linux_repair_history()
    try:
        os.remove("linux_repair_history.db")
    except FileNotFoundError:
        pass
    yield
    lr.clear_linux_repair_history()
    try:
        os.remove("linux_repair_history.db")
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_ssh(monkeypatch):
    async def fake_run(host, command, username="root", password=None, timeout=30):
        return {"success": True, "output": "ok", "error": ""}

    monkeypatch.setattr(lr, "_run_ssh_command", fake_run)


class TestScriptsAndConfig:
    def test_get_linux_repair_scripts(self):
        scripts = lr.get_linux_repair_scripts()
        assert "clear_temp" in scripts
        assert isinstance(scripts, dict)

        # 深拷贝不应影响内部
        scripts["clear_temp"]["name"] = "changed"
        scripts2 = lr.get_linux_repair_scripts()
        assert scripts2["clear_temp"]["name"] != "changed"

    def test_find_host_config(self, monkeypatch):
        monkeypatch.setattr(lr, "LINUX_HOSTS", [{"name": "h1", "host": "10.0.0.1"}])
        assert lr._find_host_config("h1")["host"] == "10.0.0.1"

        monkeypatch.setattr(lr, "LINUX_HOSTS", {"hosts": [{"name": "h2", "host": "10.0.0.2"}]})
        assert lr._find_host_config("h2")["host"] == "10.0.0.2"

        assert lr._find_host_config("unknown")["host"] == "unknown"
        assert lr._find_host_config("") is None


class TestParamSanitization:
    def test_sanitize_valid_pid(self, monkeypatch):
        assert lr._sanitize_param("pid", "12345") == "12345"

    def test_sanitize_invalid_pid(self):
        with pytest.raises(ValueError):
            lr._sanitize_param("pid", "abc")
        with pytest.raises(ValueError):
            lr._sanitize_param("pid", "99999999")
        with pytest.raises(ValueError):
            lr._sanitize_param("pid", "5")

    def test_sanitize_protected_pid(self, monkeypatch):
        monkeypatch.setattr("core.command_guard.get_protected_pids", lambda: {99999})
        with pytest.raises(ValueError):
            lr._sanitize_param("pid", "99999")

    def test_sanitize_service_name(self):
        assert lr._sanitize_param("service_name", "sshd") == "sshd"
        with pytest.raises(ValueError):
            lr._sanitize_param("service_name", "sshd; rm -rf /")
        with pytest.raises(ValueError):
            lr._sanitize_param("service_name", "../etc")

    def test_sanitize_other_key(self):
        assert lr._sanitize_param("foo", "bar") == "bar"
        assert lr._sanitize_param("foo", "a;b") == "ab"

    def test_prepare_safe_params_missing(self):
        script = {"params": ["service_name"]}
        safe, error = lr._prepare_safe_params({}, script)
        assert error == "缺少参数: 'service_name'"

    def test_prepare_safe_params_ok(self):
        script = {"params": ["service_name"]}
        safe, error = lr._prepare_safe_params({"service_name": "sshd"}, script)
        assert error is None
        assert safe["service_name"] == "sshd"


class TestCommandRenderingAndValidation:
    def test_render_command(self):
        script = {"command": ["systemctl restart {service_name}"]}
        result = lr._render_command(script, {"service_name": "sshd"})
        assert result == "systemctl restart sshd"

    def test_validate_script_key(self):
        assert lr._validate_script_key("clear_temp")["name"] == "清理临时文件"
        assert lr._validate_script_key("not_exist") is None

    def test_validate_repair_request(self):
        host, script, err = lr._validate_repair_request("h", "clear_temp", {})
        assert err is None
        assert script["name"] == "清理临时文件"

        _, _, err = lr._validate_repair_request("h", "missing", {})
        assert err is not None

        _, _, err = lr._validate_repair_request("h", "restart_service", {})
        assert "缺少参数" in err


class TestExecutionAndHelpers:
    def test_normalize_ssh_output(self):
        assert lr._normalize_ssh_output(None) == ""
        assert lr._normalize_ssh_output(b"hi") == "hi"
        assert lr._normalize_ssh_output("hi") == "hi"
        assert lr._normalize_ssh_output({}) == "{}"

    def test_is_execution_success(self):
        assert lr._is_execution_success("ok") is True
        assert lr._is_execution_success("TIMEOUT") is False
        assert lr._is_execution_success("") is False
        assert lr._is_execution_success("ERROR: fail") is False

    def test_record_to_sqlite_sync(self):
        assert lr._record_to_sqlite_sync(True, "rule", "clear_temp", "out") is True
        assert (
            lr._record_to_sqlite_sync(
                {
                    "success": True,
                    "host": "h",
                    "rule_name": "r",
                    "script_key": "s",
                    "params": {"a": "1"},
                    "output": "o",
                    "timestamp": "2026-01-01T00:00:00",
                }
            )
            is True
        )

    def test_record_to_sqlite_sync_bad(self):
        # 模拟 SQLite 失败: 通过 patch sqlite3.connect 抛出异常
        import sqlite3

        original = sqlite3.connect
        try:
            sqlite3.connect = lambda x: (_ for _ in ()).throw(Exception("fail"))
            assert lr._record_to_sqlite_sync(True, "rule", "key", "out") is False
        finally:
            sqlite3.connect = original


class TestExecuteLinuxRepair:
    def test_execute_clear_temp(self, mock_ssh):
        result = asyncio.run(lr.execute_linux_repair("localhost", "clear_temp"))
        assert result["success"] is True
        assert result["output"] == "ok"
        assert result["host"] == "localhost"

        history = lr.get_linux_repair_history(1)
        assert len(history) == 1
        assert history[0]["script_key"] == "clear_temp"

    def test_execute_kill_high_cpu(self, mock_ssh, monkeypatch):
        monkeypatch.setattr("core.command_guard.get_protected_pids", lambda: set())
        result = asyncio.run(
            lr.execute_linux_repair("localhost", "kill_high_cpu", {"pid": "12345"})
        )
        assert result["success"] is True
        assert result["script_name"] == "终止高 CPU 进程"

    def test_execute_missing_param(self):
        result = asyncio.run(lr.execute_linux_repair("localhost", "restart_service", {}))
        assert result["success"] is False
        assert "缺少参数" in result["error"]


class TestHistory:
    def test_history_and_clear(self, mock_ssh):
        asyncio.run(lr.execute_linux_repair("localhost", "clear_temp"))
        assert len(lr.get_linux_repair_history(10)) == 1
        assert lr.clear_linux_repair_history() == 1
        assert lr.get_linux_repair_history(10) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
