# -*- coding: utf-8 -*-
"""
Unit tests for log filter strategy
日志过滤策略单元测试
"""

import logging

from core.logging.level.filter_strategy import (
    CompositeFilter,
    KeywordFilter,
    LevelFilter,
    ModuleFilter,
)
from core.logging.level.level_manager import LogLevel


class TestModuleFilter:
    """Test cases for ModuleFilter"""

    def create_log_record(
        self, module_name: str, level: int = logging.INFO, message: str = "test message"
    ):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name=module_name,
            level=level,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return record

    def test_default_include_all(self):
        """Test default filter includes all modules"""
        filter_instance = ModuleFilter()
        record = self.create_log_record("test_module")
        assert filter_instance.should_log(record) is True

    def test_exclude_module(self):
        """Test excluding specific module"""
        filter_instance = ModuleFilter(exclude_modules={"excluded_module"})

        record1 = self.create_log_record("excluded_module")
        record2 = self.create_log_record("other_module")

        assert filter_instance.should_log(record1) is False
        assert filter_instance.should_log(record2) is True

    def test_include_module(self):
        """Test including only specific modules"""
        filter_instance = ModuleFilter(include_modules={"module1", "module2"})

        record1 = self.create_log_record("module1")
        record2 = self.create_log_record("module2")
        record3 = self.create_log_record("module3")

        assert filter_instance.should_log(record1) is True
        assert filter_instance.should_log(record2) is True
        assert filter_instance.should_log(record3) is False

    def test_include_pattern(self):
        """Test including modules matching pattern"""
        filter_instance = ModuleFilter(include_patterns=[r"test\..*"])

        record1 = self.create_log_record("test.module1")
        record2 = self.create_log_record("test.module2")
        record3 = self.create_log_record("other.module")

        assert filter_instance.should_log(record1) is True
        assert filter_instance.should_log(record2) is True
        assert filter_instance.should_log(record3) is False

    def test_exclude_pattern(self):
        """Test excluding modules matching pattern"""
        filter_instance = ModuleFilter(exclude_patterns=[r"debug\..*"])

        record1 = self.create_log_record("debug.module1")
        record2 = self.create_log_record("prod.module1")

        assert filter_instance.should_log(record1) is False
        assert filter_instance.should_log(record2) is True

    def test_default_action_exclude(self):
        """Test default action set to exclude"""
        filter_instance = ModuleFilter(default_action=False)
        record = self.create_log_record("test_module")
        assert filter_instance.should_log(record) is False


class TestLevelFilter:
    """Test cases for LevelFilter"""

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

    def test_min_level_filter(self):
        """Test filtering by minimum level"""
        filter_instance = LevelFilter(min_level=LogLevel.WARNING)

        debug_record = self.create_log_record(logging.DEBUG)
        info_record = self.create_log_record(logging.INFO)
        warning_record = self.create_log_record(logging.WARNING)
        error_record = self.create_log_record(logging.ERROR)

        assert filter_instance.should_log(debug_record) is False
        assert filter_instance.should_log(info_record) is False
        assert filter_instance.should_log(warning_record) is True
        assert filter_instance.should_log(error_record) is True

    def test_max_level_filter(self):
        """Test filtering by maximum level"""
        filter_instance = LevelFilter(max_level=LogLevel.WARNING)

        debug_record = self.create_log_record(logging.DEBUG)
        info_record = self.create_log_record(logging.INFO)
        warning_record = self.create_log_record(logging.WARNING)
        error_record = self.create_log_record(logging.ERROR)

        assert filter_instance.should_log(debug_record) is True
        assert filter_instance.should_log(info_record) is True
        assert filter_instance.should_log(warning_record) is True
        assert filter_instance.should_log(error_record) is False

    def test_range_filter(self):
        """Test filtering by level range"""
        filter_instance = LevelFilter(min_level=LogLevel.INFO, max_level=LogLevel.ERROR)

        debug_record = self.create_log_record(logging.DEBUG)
        info_record = self.create_log_record(logging.INFO)
        warning_record = self.create_log_record(logging.WARNING)
        error_record = self.create_log_record(logging.ERROR)
        critical_record = self.create_log_record(logging.CRITICAL)

        assert filter_instance.should_log(debug_record) is False
        assert filter_instance.should_log(info_record) is True
        assert filter_instance.should_log(warning_record) is True
        assert filter_instance.should_log(error_record) is True
        assert filter_instance.should_log(critical_record) is False

    def test_allowed_levels(self):
        """Test filtering by specific allowed levels"""
        filter_instance = LevelFilter(allowed_levels={LogLevel.INFO, LogLevel.ERROR})

        debug_record = self.create_log_record(logging.DEBUG)
        info_record = self.create_log_record(logging.INFO)
        warning_record = self.create_log_record(logging.WARNING)
        error_record = self.create_log_record(logging.ERROR)

        assert filter_instance.should_log(debug_record) is False
        assert filter_instance.should_log(info_record) is True
        assert filter_instance.should_log(warning_record) is False
        assert filter_instance.should_log(error_record) is True


class TestKeywordFilter:
    """Test cases for KeywordFilter"""

    def create_log_record(self, message: str):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return record

    def test_include_keyword(self):
        """Test including logs with specific keyword"""
        filter_instance = KeywordFilter(include_keywords={"important", "critical"})

        record1 = self.create_log_record("This is an important message")
        record2 = self.create_log_record("This is a critical error")
        record3 = self.create_log_record("This is a normal message")

        assert filter_instance.should_log(record1) is True
        assert filter_instance.should_log(record2) is True
        assert filter_instance.should_log(record3) is False

    def test_exclude_keyword(self):
        """Test excluding logs with specific keyword"""
        filter_instance = KeywordFilter(exclude_keywords={"debug", "trace"})

        record1 = self.create_log_record("Debug information")
        record2 = self.create_log_record("Trace data")
        record3 = self.create_log_record("Normal message")

        assert filter_instance.should_log(record1) is False
        assert filter_instance.should_log(record2) is False
        assert filter_instance.should_log(record3) is True

    def test_case_sensitive(self):
        """Test case sensitivity"""
        filter_instance = KeywordFilter(include_keywords={"ERROR"}, case_sensitive=True)

        record1 = self.create_log_record("This is an ERROR")
        record2 = self.create_log_record("This is an error")

        assert filter_instance.should_log(record1) is True
        assert filter_instance.should_log(record2) is False

    def test_case_insensitive(self):
        """Test case insensitivity"""
        filter_instance = KeywordFilter(include_keywords={"ERROR"}, case_sensitive=False)

        record1 = self.create_log_record("This is an ERROR")
        record2 = self.create_log_record("This is an error")
        record3 = self.create_log_record("This is an Error")

        assert filter_instance.should_log(record1) is True
        assert filter_instance.should_log(record2) is True
        assert filter_instance.should_log(record3) is True

    def test_include_pattern(self):
        """Test including logs matching pattern"""
        filter_instance = KeywordFilter(include_patterns=[r"error.*code"])

        record1 = self.create_log_record("Error code 500")
        record2 = self.create_log_record("error code 404")
        record3 = self.create_log_record("Success code 200")

        assert filter_instance.should_log(record1) is True
        assert filter_instance.should_log(record2) is True
        assert filter_instance.should_log(record3) is False

    def test_exclude_pattern(self):
        """Test excluding logs matching pattern"""
        filter_instance = KeywordFilter(exclude_patterns=[r"password.*=.*"])

        record1 = self.create_log_record("password=secret123")
        record2 = self.create_log_record("username=admin")

        assert filter_instance.should_log(record1) is False
        assert filter_instance.should_log(record2) is True


class TestCompositeFilter:
    """Test cases for CompositeFilter"""

    def create_log_record(self, module_name: str, level: int = logging.INFO, message: str = "test"):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name=module_name,
            level=level,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return record

    def test_and_operator(self):
        """Test AND operator"""
        module_filter = ModuleFilter(include_modules={"test_module"})
        level_filter = LevelFilter(min_level=LogLevel.WARNING)

        composite = CompositeFilter(filters=[module_filter, level_filter], operator="AND")

        record1 = self.create_log_record("test_module", logging.WARNING)
        record2 = self.create_log_record("test_module", logging.INFO)
        record3 = self.create_log_record("other_module", logging.WARNING)

        assert composite.should_log(record1) is True
        assert composite.should_log(record2) is False
        assert composite.should_log(record3) is False

    def test_or_operator(self):
        """Test OR operator"""
        module_filter = ModuleFilter(include_modules={"test_module"})
        level_filter = LevelFilter(min_level=LogLevel.ERROR)

        composite = CompositeFilter(filters=[module_filter, level_filter], operator="OR")

        record1 = self.create_log_record("test_module", logging.INFO)
        record2 = self.create_log_record("other_module", logging.ERROR)
        record3 = self.create_log_record("other_module", logging.INFO)

        assert composite.should_log(record1) is True
        assert composite.should_log(record2) is True
        assert composite.should_log(record3) is False

    def test_empty_filters(self):
        """Test empty filters list"""
        composite = CompositeFilter(filters=[])
        record = self.create_log_record("test_module")
        assert composite.should_log(record) is True

    def test_add_filter(self):
        """Test adding filter to composite"""
        composite = CompositeFilter(filters=[])
        module_filter = ModuleFilter(include_modules={"test_module"})

        composite.add_filter(module_filter)

        record1 = self.create_log_record("test_module")
        record2 = self.create_log_record("other_module")

        assert composite.should_log(record1) is True
        assert composite.should_log(record2) is False

    def test_remove_filter(self):
        """Test removing filter from composite"""
        module_filter = ModuleFilter(include_modules={"test_module"})
        composite = CompositeFilter(filters=[module_filter])

        composite.remove_filter(module_filter)

        record = self.create_log_record("test_module")
        assert composite.should_log(record) is True

    def test_invalid_operator_defaults_to_and(self):
        """Test invalid operator defaults to AND"""
        module_filter = ModuleFilter(include_modules={"test_module"})
        level_filter = LevelFilter(min_level=LogLevel.WARNING)

        composite = CompositeFilter(filters=[module_filter, level_filter], operator="INVALID")

        record1 = self.create_log_record("test_module", logging.WARNING)
        record2 = self.create_log_record("test_module", logging.INFO)

        assert composite.should_log(record1) is True
        assert composite.should_log(record2) is False
