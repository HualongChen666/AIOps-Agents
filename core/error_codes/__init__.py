# -*- coding: utf-8 -*-
"""
错误码模块

导出错误码定义和管理器。
"""

from .definitions import ErrorCode
from .manager import get_error_code_manager, get_error_message

__all__ = [
    "ErrorCode",
    "get_error_message",
    "get_error_code_manager",
]
