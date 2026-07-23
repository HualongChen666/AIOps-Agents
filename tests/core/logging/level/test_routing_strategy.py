# -*- coding: utf-8 -*-
"""
Unit tests for log routing strategy
日志路由策略单元测试
"""

import logging

from core.logging.level.level_manager import LogLevel
from core.logging.level.routing_strategy import (
    ConditionalRouter,
    FileRouter,
    LogLevelRouter,
    SystemRouter,
)


class TestLogLevelRouter:
    """Test cases for LogLevelRouter"""

    def create_log_record(self, level: int):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_default_routes(self):
        """Test default routing"""
        router = LogLevelRouter(default_routes=["default_target"])
        record = self.create_log_record(logging.INFO)

        assert router.route(record) == ["default_target"]

    def test_level_specific_routes(self):
        """Test level-specific routing"""
        router = LogLevelRouter(
            level_routes={
                LogLevel.ERROR: ["error_target"],
                LogLevel.CRITICAL: ["critical_target"],
            },
            default_routes=["default_target"],
        )

        error_record = self.create_log_record(logging.ERROR)
        critical_record = self.create_log_record(logging.CRITICAL)
        info_record = self.create_log_record(logging.INFO)

        assert router.route(error_record) == ["error_target"]
        assert router.route(critical_record) == ["critical_target"]
        assert router.route(info_record) == ["default_target"]

    def test_add_level_route(self):
        """Test adding level route"""
        router = LogLevelRouter()
        router.add_level_route(LogLevel.WARNING, ["warning_target"])

        record = self.create_log_record(logging.WARNING)
        assert router.route(record) == ["warning_target"]

    def test_remove_level_route(self):
        """Test removing level route"""
        router = LogLevelRouter(
            level_routes={LogLevel.WARNING: ["warning_target"]}, default_routes=["default_target"]
        )

        router.remove_level_route(LogLevel.WARNING)

        record = self.create_log_record(logging.WARNING)
        assert router.route(record) == ["default_target"]

    def test_set_default_routes(self):
        """Test setting default routes"""
        router = LogLevelRouter()
        router.set_default_routes(["new_default"])

        record = self.create_log_record(logging.INFO)
        assert router.route(record) == ["new_default"]


class TestFileRouter:
    """Test cases for FileRouter"""

    def create_log_record(self, level: int):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_default_file(self):
        """Test default file routing"""
        router = FileRouter()
        record = self.create_log_record(logging.INFO)

        routes = router.route(record)
        assert len(routes) == 1
        assert "app.log" in routes[0]

    def test_level_specific_files(self):
        """Test level-specific file routing"""
        router = FileRouter()
        router.set_level_file(LogLevel.ERROR, "error.log")
        router.set_level_file(LogLevel.CRITICAL, "critical.log")

        error_record = self.create_log_record(logging.ERROR)
        critical_record = self.create_log_record(logging.CRITICAL)
        info_record = self.create_log_record(logging.INFO)

        assert "error.log" in router.route(error_record)[0]
        assert "critical.log" in router.route(critical_record)[0]
        assert "app.log" in router.route(info_record)[0]

    def test_get_file_path(self):
        """Test getting file path for specific level"""
        router = FileRouter()
        router.set_level_file(LogLevel.ERROR, "error.log")

        assert "error.log" in router.get_file_path(LogLevel.ERROR)
        assert "app.log" in router.get_file_path(LogLevel.INFO)

    def test_set_default_file(self):
        """Test setting default file"""
        router = FileRouter()
        router.set_default_file("custom.log")

        record = self.create_log_record(logging.INFO)
        assert "custom.log" in router.route(record)[0]


class TestSystemRouter:
    """Test cases for SystemRouter"""

    def create_log_record(self, level: int):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_default_systems(self):
        """Test default system routing"""
        router = SystemRouter(default_systems=["default_system"])
        record = self.create_log_record(logging.INFO)

        assert router.route(record) == ["default_system"]

    def test_system_level_routes(self):
        """Test system-level routing"""
        router = SystemRouter()
        router.add_system_route("elk", LogLevel.ERROR, True)
        router.add_system_route("syslog", LogLevel.CRITICAL, True)

        error_record = self.create_log_record(logging.ERROR)
        critical_record = self.create_log_record(logging.CRITICAL)
        info_record = self.create_log_record(logging.INFO)

        assert router.route(error_record) == ["elk"]
        assert router.route(critical_record) == ["syslog"]
        assert router.route(info_record) == []

    def test_multiple_systems_for_level(self):
        """Test multiple systems for same level"""
        router = SystemRouter()
        router.add_system_route("elk", LogLevel.ERROR, True)
        router.add_system_route("syslog", LogLevel.ERROR, True)

        error_record = self.create_log_record(logging.ERROR)
        routes = router.route(error_record)

        assert "elk" in routes
        assert "syslog" in routes

    def test_remove_system_route(self):
        """Test removing system route"""
        router = SystemRouter()
        router.add_system_route("elk", LogLevel.ERROR, True)
        router.remove_system_route("elk", LogLevel.ERROR)

        error_record = self.create_log_record(logging.ERROR)
        assert router.route(error_record) == []

    def test_set_default_systems(self):
        """Test setting default systems"""
        router = SystemRouter()
        router.set_default_systems(["system1", "system2"])

        record = self.create_log_record(logging.INFO)
        assert router.route(record) == ["system1", "system2"]

    def test_system_config(self):
        """Test system configuration"""
        router = SystemRouter()
        config = {"host": "localhost", "port": 9200}
        router.set_system_config("elk", config)

        assert router.get_system_config("elk") == config
        assert router.get_system_config("nonexistent") is None


class TestConditionalRouter:
    """Test cases for ConditionalRouter"""

    def create_log_record(self, level: int, message: str = "test"):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return record

    def test_condition_based_routing(self):
        """Test condition-based routing"""
        router = ConditionalRouter()

        # Add condition: route to target1 if level is ERROR
        router.add_condition(lambda r: r.levelno >= logging.ERROR, ["target1"])
        router.set_default_routes(["default_target"])

        error_record = self.create_log_record(logging.ERROR)
        info_record = self.create_log_record(logging.INFO)

        assert router.route(error_record) == ["target1"]
        assert router.route(info_record) == ["default_target"]

    def test_multiple_conditions(self):
        """Test multiple conditions"""
        router = ConditionalRouter()

        router.add_condition(lambda r: r.levelno == logging.CRITICAL, ["critical_target"])
        router.add_condition(lambda r: r.levelno == logging.ERROR, ["error_target"])
        router.set_default_routes(["default_target"])

        critical_record = self.create_log_record(logging.CRITICAL)
        error_record = self.create_log_record(logging.ERROR)
        info_record = self.create_log_record(logging.INFO)

        assert router.route(critical_record) == ["critical_target"]
        assert router.route(error_record) == ["error_target"]
        assert router.route(info_record) == ["default_target"]

    def test_message_based_condition(self):
        """Test message-based condition"""
        router = ConditionalRouter()

        router.add_condition(lambda r: "password" in r.getMessage().lower(), ["security_target"])
        router.set_default_routes(["default_target"])

        password_record = self.create_log_record(logging.INFO, "User password changed")
        normal_record = self.create_log_record(logging.INFO, "User logged in")

        assert router.route(password_record) == ["security_target"]
        assert router.route(normal_record) == ["default_target"]

    def test_empty_conditions(self):
        """Test empty conditions list"""
        router = ConditionalRouter()
        router.set_default_routes(["default_target"])

        record = self.create_log_record(logging.INFO)
        assert router.route(record) == ["default_target"]

    def test_condition_no_route(self):
        """Test condition with no associated route"""
        router = ConditionalRouter()
        router.add_condition(lambda r: r.levelno >= logging.ERROR, [])
        router.set_default_routes(["default_target"])

        error_record = self.create_log_record(logging.ERROR)
        assert router.route(error_record) == ["default_target"]
