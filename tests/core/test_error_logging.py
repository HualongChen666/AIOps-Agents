# -*- coding: utf-8 -*-
"""
错误日志单元测试

测试错误日志记录器和处理器的功能。
"""

from core.error_logging import (
    get_error_count,
    get_error_log_handler,
    get_error_stats,
    get_structured_error_logger,
    log_error,
    log_exception,
    record_error,
)
from core.error_logging.handler import ErrorLogHandler
from core.error_logging.logger import StructuredErrorLogger
from core.exceptions import ValidationException


class TestStructuredErrorLogger:
    """测试结构化错误日志记录器"""

    def test_logger_initialization(self):
        """测试日志记录器初始化"""
        logger = StructuredErrorLogger()
        assert logger is not None

    def test_log_error_basic(self):
        """测试基本错误日志记录"""
        logger = StructuredErrorLogger()
        logger.log_error(
            error_code="01_01_0001",
            message="Test error",
            severity="error",
            category="business",
        )
        # 应该不抛出异常

    def test_log_error_with_context(self):
        """测试带上下文的错误日志记录"""
        logger = StructuredErrorLogger()
        logger.log_error(
            error_code="01_01_0001",
            message="Test error",
            context={"key": "value"},
        )
        # 应该不抛出异常

    def test_log_error_with_error_id(self):
        """测试带错误ID的错误日志记录"""
        logger = StructuredErrorLogger()
        logger.log_error(
            error_code="01_01_0001",
            message="Test error",
            error_id="test_error_id",
        )
        # 应该不抛出异常

    def test_log_error_with_stack_trace(self):
        """测试带堆栈追踪的错误日志记录"""
        logger = StructuredErrorLogger()
        logger.log_error(
            error_code="01_01_0001",
            message="Test error",
            stack_trace="Traceback...",
        )
        # 应该不抛出异常

    def test_log_exception_aiops_exception(self):
        """测试记录AIOps异常"""
        logger = StructuredErrorLogger()
        exc = ValidationException(message="Test validation error", field="username")
        logger.log_exception(exc)
        # 应该不抛出异常

    def test_log_exception_standard_exception(self):
        """测试记录标准异常"""
        logger = StructuredErrorLogger()
        exc = ValueError("Test error")
        logger.log_exception(exc)
        # 应该不抛出异常

    def test_get_structured_error_logger(self):
        """测试获取全局日志记录器"""
        logger = get_structured_error_logger()
        assert logger is not None
        assert isinstance(logger, StructuredErrorLogger)


class TestErrorLogHandler:
    """测试错误日志处理器"""

    def test_handler_initialization(self):
        """测试处理器初始化"""
        handler = ErrorLogHandler()
        assert handler is not None
        assert handler.get_error_stats() == {}

    def test_record_error(self):
        """测试记录错误"""
        handler = ErrorLogHandler()
        handler.record_error(
            error_code="01_01_0001",
            severity="error",
            category="business",
        )
        stats = handler.get_error_stats()
        assert stats.get("01_01_0001") == 1

    def test_record_multiple_errors(self):
        """测试记录多个错误"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        stats = handler.get_error_stats()
        assert stats.get("01_01_0001") == 2
        assert stats.get("01_02_0001") == 1

    def test_get_error_stats(self):
        """测试获取错误统计"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        stats = handler.get_error_stats()
        assert len(stats) == 2
        assert "01_01_0001" in stats
        assert "01_02_0001" in stats

    def test_get_error_count_total(self):
        """测试获取总错误数量"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        count = handler.get_error_count()
        assert count == 3

    def test_get_error_count_specific(self):
        """测试获取特定错误码的数量"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        count = handler.get_error_count("01_01_0001")
        assert count == 2

    def test_get_error_history(self):
        """测试获取错误历史"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        history = handler.get_error_history()
        assert len(history) == 2

    def test_get_error_history_with_limit(self):
        """测试获取错误历史（带限制）"""
        handler = ErrorLogHandler()
        for i in range(10):
            handler.record_error(f"01_01_{i:04d}", "error", "business")
        history = handler.get_error_history(limit=5)
        assert len(history) == 5

    def test_get_error_history_with_filter(self):
        """测试获取错误历史（带过滤）"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        handler.record_error("01_01_0001", "warning", "business")
        history = handler.get_error_history(error_code="01_01_0001")
        assert len(history) == 2

    def test_get_error_trends(self):
        """测试获取错误趋势"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        trends = handler.get_error_trends("01_01_0001", hours=24)
        assert len(trends) == 2

    def test_get_error_rate(self):
        """测试获取错误率"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        rate = handler.get_error_rate("01_01_0001", hours=1)
        assert rate == 2.0

    def test_get_top_errors(self):
        """测试获取最频繁的错误"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        top_errors = handler.get_top_errors(limit=2)
        assert len(top_errors) == 2
        assert top_errors[0] == ("01_01_0001", 3)
        assert top_errors[1] == ("01_02_0001", 1)

    def test_get_category_stats(self):
        """测试获取分类统计"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("09_06_0001", "error", "system")
        handler.record_error("01_02_0001", "error", "business")
        stats = handler.get_category_stats()
        assert stats.get("business") == 2
        assert stats.get("system") == 1

    def test_get_severity_stats(self):
        """测试获取严重程度统计"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "warning", "business")
        handler.record_error("01_03_0001", "error", "business")
        stats = handler.get_severity_stats()
        assert stats.get("error") == 2
        assert stats.get("warning") == 1

    def test_clear_history(self):
        """测试清空历史"""
        handler = ErrorLogHandler()
        handler.record_error("01_01_0001", "error", "business")
        handler.record_error("01_02_0001", "error", "business")
        handler.clear_history()
        assert handler.get_error_stats() == {}
        assert handler.get_error_history() == []


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_log_error_function(self):
        """测试log_error便捷函数"""
        log_error(
            error_code="01_01_0001",
            message="Test error",
            severity="error",
            category="business",
        )
        # 应该不抛出异常

    def test_log_exception_function(self):
        """测试log_exception便捷函数"""
        exc = ValidationException(message="Test error")
        log_exception(exc)
        # 应该不抛出异常

    def test_record_error_function(self):
        """测试record_error便捷函数"""
        record_error(
            error_code="01_01_0001",
            severity="error",
            category="business",
        )
        # 应该不抛出异常

    def test_get_error_stats_function(self):
        """测试get_error_stats便捷函数"""
        record_error("01_01_0001", "error", "business")
        stats = get_error_stats()
        assert "01_01_0001" in stats

    def test_get_error_count_function(self):
        """测试get_error_count便捷函数"""
        record_error("01_01_0001", "error", "business")
        count = get_error_count()
        assert count >= 1

    def test_get_error_log_handler_function(self):
        """测试get_error_log_handler便捷函数"""
        handler = get_error_log_handler()
        assert handler is not None
        assert isinstance(handler, ErrorLogHandler)
