# -*- coding: utf-8 -*-
"""测试 core/log_collector 的日志采集、清理和解析逻辑"""

import json
import subprocess
from unittest.mock import MagicMock

import pytest


class TestSanitizeKeyword:
    def test_sanitize_removes_dangerous_chars(self):
        from core.log_collector import _sanitize_keyword

        assert _sanitize_keyword("a;b") == "ab"

    def test_sanitize_non_string(self):
        from core.log_collector import _sanitize_keyword

        assert _sanitize_keyword(123) == ""


class TestClampNewest:
    def test_clamp_within_range(self):
        from core.log_collector import _clamp_newest

        assert _clamp_newest(50) == 50

    def test_clamp_default_on_invalid(self):
        from core.log_collector import _clamp_newest

        assert _clamp_newest("abc", default=10) == 10

    def test_clamp_hard_max(self):
        from core.log_collector import _clamp_newest

        assert _clamp_newest(999999) == 1000


class TestParsePowershellJsonOutput:
    def test_parse_list(self):
        from core.log_collector import _parse_powershell_json_output

        data = [{"TimeGenerated": "2024-01-01", "Message": "msg"}]
        assert _parse_powershell_json_output(json.dumps(data)) == data

    def test_parse_dict(self):
        from core.log_collector import _parse_powershell_json_output

        data = {"TimeGenerated": "2024-01-01", "Message": "msg"}
        assert _parse_powershell_json_output(json.dumps(data)) == [data]

    def test_parse_invalid(self):
        from core.log_collector import _parse_powershell_json_output

        assert _parse_powershell_json_output("not-json") == []

    def test_parse_unexpected_type(self):
        from core.log_collector import _parse_powershell_json_output

        assert _parse_powershell_json_output("123") == []


class TestSanitizeLogEntries:
    def test_truncate_message(self):
        from core.log_collector import _sanitize_log_entries

        entries = [{"TimeGenerated": 1, "Message": "x" * 3000}]
        result = _sanitize_log_entries(entries)
        assert result[0]["Message"].endswith("...(已截断)")


class TestExecutePowershellWithTimeout:
    def test_powershell_not_found(self, monkeypatch):
        from core.log_collector import _execute_powershell_with_timeout

        monkeypatch.setattr(
            "core.log_collector.subprocess_runner.Popen",
            MagicMock(side_effect=FileNotFoundError("no ps")),
        )
        assert _execute_powershell_with_timeout("cmd") == (None, None, None)

    def test_powershell_timeout(self, monkeypatch):
        from core.log_collector import _execute_powershell_with_timeout

        proc = MagicMock()
        proc.communicate = MagicMock(side_effect=subprocess.TimeoutExpired("cmd", timeout=30))
        monkeypatch.setattr(
            "core.log_collector.subprocess_runner.Popen", MagicMock(return_value=proc)
        )
        assert _execute_powershell_with_timeout("cmd") == (None, None, None)

    def test_powershell_success(self, monkeypatch):
        from core.log_collector import _execute_powershell_with_timeout

        proc = MagicMock()
        proc.communicate = MagicMock(return_value=("stdout", "stderr"))
        monkeypatch.setattr(
            "core.log_collector.subprocess_runner.Popen", MagicMock(return_value=proc)
        )
        assert _execute_powershell_with_timeout("cmd") == (proc, "stdout", "stderr")


class TestRunPsJson:
    def test_run_ps_json_success(self, monkeypatch):
        from core.log_collector import _run_ps_json

        proc = MagicMock()
        proc.communicate = MagicMock(return_value=(json.dumps([{"a": 1}]), ""))
        monkeypatch.setattr(
            "core.log_collector.subprocess_runner.Popen", MagicMock(return_value=proc)
        )
        assert _run_ps_json("cmd") == [{"a": 1}]

    def test_run_ps_json_no_stdout(self, monkeypatch):
        from core.log_collector import _run_ps_json

        proc = MagicMock()
        proc.communicate = MagicMock(return_value=("", "err"))
        monkeypatch.setattr(
            "core.log_collector.subprocess_runner.Popen", MagicMock(return_value=proc)
        )
        assert _run_ps_json("cmd") == []

    def test_run_ps_json_process_none(self, monkeypatch):
        from core.log_collector import _run_ps_json

        monkeypatch.setattr(
            "core.log_collector.subprocess_runner.Popen", MagicMock(side_effect=FileNotFoundError)
        )
        assert _run_ps_json("cmd") == []


class TestExtractTimestampFromLine:
    def test_extract_iso(self):
        from core.log_collector import _extract_timestamp_from_line

        line = "2024-01-15T10:30:45 server message"
        assert _extract_timestamp_from_line(line) == "2024-01-15T10:30:45"

    def test_extract_syslog(self):
        from core.log_collector import _extract_timestamp_from_line

        line = "Jan 15 10:30:45 server message"
        assert _extract_timestamp_from_line(line) == "Jan 15 10:30:45"

    def test_extract_empty(self):
        from core.log_collector import _extract_timestamp_from_line

        assert _extract_timestamp_from_line("") == ""


@pytest.mark.asyncio
class TestGetEventLogs:
    async def test_get_event_logs_success(self, monkeypatch):
        from core.log_collector import get_event_logs

        async def fake_to_thread(func, cmd):
            return [{"TimeGenerated": "t", "Message": "m"}]

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await get_event_logs("System", "Error", 10)
        assert result == [{"TimeGenerated": "t", "Message": "m"}]

    async def test_get_event_logs_invalid_log_name(self, monkeypatch):
        from core.log_collector import get_event_logs

        # ensure the command is built even for weird input; to_thread returns empty
        async def fake_to_thread(func, cmd):
            return []

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await get_event_logs("../etc/passwd", "Error", 10)
        assert result == []

    async def test_get_event_logs_exception(self, monkeypatch):
        from core.log_collector import get_event_logs

        async def fake_to_thread(func, cmd):
            raise RuntimeError("ps fail")

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await get_event_logs()
        assert result == []


@pytest.mark.asyncio
class TestSystemAndApplicationErrors:
    async def test_get_system_errors(self, monkeypatch):
        from core.log_collector import get_system_errors

        async def fake_to_thread(func, cmd):
            return [{"TimeGenerated": "t", "Message": "m"}]

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await get_system_errors(5)
        assert result == [{"TimeGenerated": "t", "Message": "m"}]

    async def test_get_application_errors(self, monkeypatch):
        from core.log_collector import get_application_errors

        async def fake_to_thread(func, cmd):
            return [{"TimeGenerated": "t", "Message": "m"}]

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await get_application_errors(5)
        assert result == [{"TimeGenerated": "t", "Message": "m"}]


@pytest.mark.asyncio
class TestSearchLogs:
    async def test_search_logs_success(self, monkeypatch):
        from core.log_collector import search_logs

        async def fake_to_thread(func, cmd):
            return [{"TimeGenerated": "t", "Message": "error"}]

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await search_logs("error", 10)
        assert len(result) == 1

    async def test_search_logs_empty_keyword(self):
        from core.log_collector import search_logs

        result = await search_logs("")
        assert result == []

    async def test_search_logs_exception(self, monkeypatch):
        from core.log_collector import search_logs

        async def fake_to_thread(func, cmd):
            raise RuntimeError("fail")

        monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
        result = await search_logs("error", 10)
        assert result == []


@pytest.mark.asyncio
class TestGetLinuxLogs:
    async def test_get_linux_logs_invalid_host(self):
        from core.log_collector import get_linux_logs

        result = await get_linux_logs("not-a-dict")
        assert result == []

    async def test_get_linux_logs_timeout(self, monkeypatch):
        from core.log_collector import get_linux_logs

        async def fake_ssh_execute(host_config, cmd, semaphore=None):
            return "TIMEOUT"

        monkeypatch.setattr("core.linux_collector._get_host_semaphore", lambda host: None)
        monkeypatch.setattr("core.linux_collector._ssh_execute", fake_ssh_execute)
        result = await get_linux_logs({"name": "h1"}, source="syslog", newest=10)
        assert result == []

    async def test_get_linux_logs_success(self, monkeypatch):
        from core.log_collector import get_linux_logs

        async def fake_ssh_execute(host_config, cmd, semaphore=None):
            return "Jan 15 10:30:45 server message\n\nline two"

        monkeypatch.setattr("core.linux_collector._get_host_semaphore", lambda host: None)
        monkeypatch.setattr("core.linux_collector._ssh_execute", fake_ssh_execute)
        result = await get_linux_logs({"name": "h1"}, source="syslog", newest=10)
        assert len(result) == 2
        assert result[0]["Source"] == "syslog"


@pytest.mark.asyncio
class TestSearchLinuxLogs:
    async def test_search_linux_logs_invalid_host(self):
        from core.log_collector import search_linux_logs

        result = await search_linux_logs("not-a-dict", "error")
        assert result == []

    async def test_search_linux_logs_success(self, monkeypatch):
        from core.log_collector import search_linux_logs

        async def fake_ssh_execute(host_config, cmd, semaphore=None):
            return "Jan 15 10:30:45 server error"

        monkeypatch.setattr("core.linux_collector._get_host_semaphore", lambda host: None)
        monkeypatch.setattr("core.linux_collector._ssh_execute", fake_ssh_execute)
        result = await search_linux_logs({"name": "h1"}, "error", 10)
        assert len(result) == 1
        assert result[0]["Keyword"] == "error"

    async def test_search_linux_logs_empty_keyword(self):
        from core.log_collector import search_linux_logs

        result = await search_linux_logs({"name": "h1"}, ";rm -rf")
        assert result == []

    async def test_get_linux_errors(self, monkeypatch):
        from core.log_collector import get_linux_errors

        async def fake_ssh_execute(host_config, cmd, semaphore=None):
            return "Jan 15 10:30:45 kernel error"

        monkeypatch.setattr("core.linux_collector._get_host_semaphore", lambda host: None)
        monkeypatch.setattr("core.linux_collector._ssh_execute", fake_ssh_execute)
        result = await get_linux_errors({"name": "h1"}, 10)
        assert len(result) == 1
