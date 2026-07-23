# -*- coding: utf-8 -*-
"""
错误码管理器模块

提供错误码的管理和国际化支持。
"""

from typing import Dict


class ErrorCodeManager:
    """
    错误码管理器

    负责错误码的消息管理和国际化支持。
    """

    def __init__(self):
        """初始化错误码管理器"""
        self._error_messages: Dict[str, Dict[str, str]] = {}
        self._load_error_messages()

    def _load_error_messages(self):
        """加载错误消息"""
        self._error_messages = {
            # 通用错误
            "01_01_0001": {
                "en": "Parameter validation failed",
                "zh": "参数验证失败",
            },
            "01_01_0002": {
                "en": "Invalid parameter format",
                "zh": "参数格式错误",
            },
            "01_01_0003": {
                "en": "Missing required parameter",
                "zh": "参数缺失",
            },
            "01_01_0004": {
                "en": "Invalid parameter type",
                "zh": "参数类型错误",
            },
            "01_01_0005": {
                "en": "Parameter value out of range",
                "zh": "参数范围错误",
            },
            "01_02_0001": {
                "en": "Resource not found",
                "zh": "资源未找到",
            },
            "01_02_0002": {
                "en": "Endpoint not found",
                "zh": "接口不存在",
            },
            "01_02_0003": {
                "en": "File not found",
                "zh": "文件未找到",
            },
            "01_03_0001": {
                "en": "Permission denied",
                "zh": "权限不足",
            },
            "01_03_0002": {
                "en": "Role permission insufficient",
                "zh": "角色权限不足",
            },
            "01_03_0003": {
                "en": "Access denied",
                "zh": "访问被拒绝",
            },
            "01_04_0001": {
                "en": "Business logic error",
                "zh": "业务逻辑错误",
            },
            "01_04_0002": {
                "en": "Operation failed",
                "zh": "操作失败",
            },
            "01_05_0001": {
                "en": "Invalid state",
                "zh": "状态无效",
            },
            "01_05_0002": {
                "en": "State transition error",
                "zh": "状态转换错误",
            },
            "01_09_0001": {
                "en": "Request timeout",
                "zh": "请求超时",
            },
            "01_09_0002": {
                "en": "Operation timeout",
                "zh": "操作超时",
            },
            "01_10_0001": {
                "en": "Rate limit exceeded",
                "zh": "请求限流",
            },
            "01_10_0002": {
                "en": "Frequency limit exceeded",
                "zh": "频率限制",
            },
            "01_15_0001": {
                "en": "Internal error",
                "zh": "内部错误",
            },
            "01_15_0002": {
                "en": "Service unavailable",
                "zh": "服务不可用",
            },
            "01_15_0003": {
                "en": "Unexpected error",
                "zh": "未知错误",
            },
            # 认证授权错误
            "02_01_0001": {
                "en": "Invalid credentials",
                "zh": "用户名或密码错误",
            },
            "02_01_0002": {
                "en": "Invalid token",
                "zh": "Token格式错误",
            },
            "02_01_0003": {
                "en": "Token expired",
                "zh": "Token已过期",
            },
            "02_01_0004": {
                "en": "Token revoked",
                "zh": "Token已撤销",
            },
            "02_01_0005": {
                "en": "Invalid token signature",
                "zh": "Token签名无效",
            },
            "02_03_0001": {
                "en": "Permission denied",
                "zh": "权限不足",
            },
            "02_03_0002": {
                "en": "Role permission insufficient",
                "zh": "角色权限不足",
            },
            "02_03_0003": {
                "en": "Resource access denied",
                "zh": "资源访问被拒绝",
            },
            "02_03_0004": {
                "en": "Operation not allowed",
                "zh": "操作不允许",
            },
            "02_09_0001": {
                "en": "Authentication service timeout",
                "zh": "认证服务超时",
            },
            "02_09_0002": {
                "en": "Authorization service timeout",
                "zh": "授权服务超时",
            },
            "02_11_0001": {
                "en": "Authentication service unavailable",
                "zh": "认证服务不可用",
            },
            "02_11_0002": {
                "en": "Authentication provider error",
                "zh": "认证提供者错误",
            },
            # 数据库错误
            "09_06_0001": {
                "en": "Database connection failed",
                "zh": "数据库连接失败",
            },
            "09_06_0002": {
                "en": "Database connection pool exhausted",
                "zh": "数据库连接池耗尽",
            },
            "09_06_0003": {
                "en": "Database connection timeout",
                "zh": "数据库连接超时",
            },
            "09_06_0004": {
                "en": "Database connection lost",
                "zh": "数据库连接丢失",
            },
            "09_07_0001": {
                "en": "Database query error",
                "zh": "数据库查询错误",
            },
            "09_07_0002": {
                "en": "SQL syntax error",
                "zh": "SQL语法错误",
            },
            "09_07_0003": {
                "en": "SQL execution error",
                "zh": "SQL执行错误",
            },
            "09_08_0001": {
                "en": "Unique constraint violation",
                "zh": "唯一约束冲突",
            },
            "09_08_0002": {
                "en": "Foreign key constraint violation",
                "zh": "外键约束冲突",
            },
            "09_08_0003": {
                "en": "Not null constraint violation",
                "zh": "非空约束冲突",
            },
            "09_08_0004": {
                "en": "Check constraint violation",
                "zh": "检查约束冲突",
            },
            "09_09_0001": {
                "en": "Database query timeout",
                "zh": "数据库查询超时",
            },
            "09_09_0002": {
                "en": "Database transaction timeout",
                "zh": "数据库事务超时",
            },
            "09_09_0003": {
                "en": "Database lock timeout",
                "zh": "数据库锁超时",
            },
            "09_13_0001": {
                "en": "Data corruption",
                "zh": "数据损坏",
            },
            "09_13_0002": {
                "en": "Data inconsistency",
                "zh": "数据不一致",
            },
            "09_13_0003": {
                "en": "Data integrity error",
                "zh": "数据完整性错误",
            },
            "09_15_0001": {
                "en": "Database system error",
                "zh": "数据库系统错误",
            },
            "09_15_0002": {
                "en": "Database disk full",
                "zh": "数据库磁盘空间不足",
            },
            # AI引擎错误
            "11_06_0001": {
                "en": "LLM connection failed",
                "zh": "LLM连接失败",
            },
            "11_06_0002": {
                "en": "AI API connection error",
                "zh": "AI API连接错误",
            },
            "11_09_0001": {
                "en": "LLM inference timeout",
                "zh": "LLM推理超时",
            },
            "11_09_0002": {
                "en": "AI request timeout",
                "zh": "AI请求超时",
            },
            "11_12_0001": {
                "en": "Model load failed",
                "zh": "模型加载失败",
            },
            "11_12_0002": {
                "en": "Model inference error",
                "zh": "模型推理错误",
            },
            "11_12_0003": {
                "en": "Model not found",
                "zh": "模型未找到",
            },
            "11_12_0004": {
                "en": "Model version error",
                "zh": "模型版本错误",
            },
            "11_10_0001": {
                "en": "API rate limit exceeded",
                "zh": "API调用限流",
            },
            "11_10_0002": {
                "en": "Token limit exceeded",
                "zh": "Token使用超限",
            },
            "11_10_0003": {
                "en": "Quota exceeded",
                "zh": "配额超限",
            },
            "11_11_0001": {
                "en": "AI service unavailable",
                "zh": "AI服务不可用",
            },
            "11_11_0002": {
                "en": "AI API error",
                "zh": "AI API错误",
            },
            "11_13_0001": {
                "en": "Invalid input data",
                "zh": "输入数据错误",
            },
            "11_13_0002": {
                "en": "Output parse error",
                "zh": "输出解析错误",
            },
            "11_13_0003": {
                "en": "Invalid response",
                "zh": "无效响应",
            },
            "11_13_0004": {
                "en": "Response too large",
                "zh": "响应过大",
            },
            # RAG系统错误
            "12_06_0001": {
                "en": "Vector database connection failed",
                "zh": "向量数据库连接失败",
            },
            "12_06_0002": {
                "en": "Embedding service error",
                "zh": "嵌入服务错误",
            },
            "12_07_0001": {
                "en": "Vector search error",
                "zh": "向量检索错误",
            },
            "12_07_0002": {
                "en": "Retrieval error",
                "zh": "检索错误",
            },
            "12_09_0001": {
                "en": "Vector search timeout",
                "zh": "向量检索超时",
            },
            "12_09_0002": {
                "en": "Embedding timeout",
                "zh": "嵌入超时",
            },
            "12_13_0001": {
                "en": "Document parse error",
                "zh": "文档解析错误",
            },
            "12_13_0002": {
                "en": "Document index error",
                "zh": "文档索引错误",
            },
            "12_13_0003": {
                "en": "Document chunk error",
                "zh": "文档分块错误",
            },
            "12_11_0001": {
                "en": "RAG service unavailable",
                "zh": "RAG服务不可用",
            },
            "12_11_0002": {
                "en": "RAG pipeline error",
                "zh": "RAG管道错误",
            },
            # 代理编排错误
            "13_06_0001": {
                "en": "Agent connection failed",
                "zh": "代理连接失败",
            },
            "13_06_0002": {
                "en": "Agent communication error",
                "zh": "代理通信错误",
            },
            "13_09_0001": {
                "en": "Agent execution timeout",
                "zh": "代理执行超时",
            },
            "13_09_0002": {
                "en": "Agent response timeout",
                "zh": "代理响应超时",
            },
            "13_05_0001": {
                "en": "Agent invalid state",
                "zh": "代理状态错误",
            },
            "13_05_0002": {
                "en": "Agent state transition error",
                "zh": "代理状态转换错误",
            },
            "13_11_0001": {
                "en": "Agent service unavailable",
                "zh": "代理服务不可用",
            },
            "13_11_0002": {
                "en": "Agent orchestration error",
                "zh": "代理编排错误",
            },
            "13_04_0001": {
                "en": "Workflow execution error",
                "zh": "工作流执行错误",
            },
            "13_04_0002": {
                "en": "Workflow state error",
                "zh": "工作流状态错误",
            },
            "13_04_0003": {
                "en": "Workflow validation error",
                "zh": "工作流验证错误",
            },
            # 外部服务错误
            "15_06_0001": {
                "en": "External service connection failed",
                "zh": "外部服务连接失败",
            },
            "15_06_0002": {
                "en": "External service network error",
                "zh": "外部服务网络错误",
            },
            "15_09_0001": {
                "en": "External service timeout",
                "zh": "外部服务超时",
            },
            "15_09_0002": {
                "en": "External request timeout",
                "zh": "外部请求超时",
            },
            "15_11_0001": {
                "en": "External service unavailable",
                "zh": "外部服务不可用",
            },
            "15_11_0002": {
                "en": "External service error",
                "zh": "外部服务错误",
            },
            "15_13_0001": {
                "en": "Invalid external service response",
                "zh": "外部服务响应错误",
            },
            "15_13_0002": {
                "en": "External service data error",
                "zh": "外部服务数据错误",
            },
            "15_13_0003": {
                "en": "External service parse error",
                "zh": "外部服务解析错误",
            },
            # 系统错误
            "20_06_0001": {
                "en": "System resource insufficient",
                "zh": "系统资源不足",
            },
            "20_06_0002": {
                "en": "Memory insufficient",
                "zh": "内存不足",
            },
            "20_06_0003": {
                "en": "Disk space insufficient",
                "zh": "磁盘空间不足",
            },
            "20_06_0004": {
                "en": "CPU usage high",
                "zh": "CPU使用率过高",
            },
            "20_14_0001": {
                "en": "CPU usage high",
                "zh": "CPU使用率过高",
            },
            "20_14_0002": {
                "en": "Memory usage high",
                "zh": "内存使用率过高",
            },
            "20_14_0003": {
                "en": "Disk usage high",
                "zh": "磁盘使用率过高",
            },
            "20_15_0001": {
                "en": "System fatal error",
                "zh": "系统致命错误",
            },
            "20_15_0002": {
                "en": "System crash",
                "zh": "系统崩溃",
            },
            "20_15_0003": {
                "en": "System panic",
                "zh": "系统恐慌",
            },
            # 缓存错误
            "10_06_0001": {
                "en": "Cache connection failed",
                "zh": "缓存连接失败",
            },
            "10_06_0002": {
                "en": "Cache write error",
                "zh": "缓存写入失败",
            },
            "10_06_0003": {
                "en": "Cache read error",
                "zh": "缓存读取失败",
            },
            "10_06_0004": {
                "en": "Cache serialization error",
                "zh": "缓存序列化错误",
            },
            # 配置错误
            "16_14_0001": {
                "en": "Configuration missing",
                "zh": "配置项缺失",
            },
            "16_14_0002": {
                "en": "Configuration invalid",
                "zh": "配置项无效",
            },
            "16_14_0003": {
                "en": "Configuration parse error",
                "zh": "配置解析错误",
            },
            "16_14_0004": {
                "en": "Configuration file not found",
                "zh": "配置文件未找到",
            },
            # 网络错误
            "17_06_0001": {
                "en": "Network connection failed",
                "zh": "网络连接失败",
            },
            "17_09_0001": {
                "en": "Network timeout",
                "zh": "网络超时",
            },
            "17_06_0002": {
                "en": "DNS resolution error",
                "zh": "DNS解析错误",
            },
            "17_06_0003": {
                "en": "Connection refused",
                "zh": "连接被拒绝",
            },
            # 资源错误
            "18_06_0001": {
                "en": "Resource insufficient",
                "zh": "资源不足",
            },
            "18_06_0002": {
                "en": "Resource exhausted",
                "zh": "资源耗尽",
            },
            "18_06_0003": {
                "en": "Resource quota exceeded",
                "zh": "资源配额超限",
            },
            # 集成错误
            "19_06_0001": {
                "en": "Integration connection failed",
                "zh": "集成连接失败",
            },
            "19_06_0002": {
                "en": "Integration sync error",
                "zh": "集成同步错误",
            },
            "19_06_0003": {
                "en": "Integration config error",
                "zh": "集成配置错误",
            },
        }

    def get_message(self, error_code: str, language: str = "en") -> str:
        """
        获取错误消息

        Args:
            error_code: 错误码
            language: 语言（en或zh）

        Returns:
            错误消息
        """
        if error_code not in self._error_messages:
            return "Unknown error"

        messages = self._error_messages[error_code]
        return messages.get(language, messages.get("en", "Unknown error"))

    def add_message(self, error_code: str, language: str, message: str):
        """
        添加错误消息

        Args:
            error_code: 错误码
            language: 语言
            message: 错误消息
        """
        if error_code not in self._error_messages:
            self._error_messages[error_code] = {}

        self._error_messages[error_code][language] = message

    def get_all_messages(self, error_code: str) -> Dict[str, str]:
        """
        获取错误码的所有语言消息

        Args:
            error_code: 错误码

        Returns:
            所有语言的消息字典
        """
        return self._error_messages.get(error_code, {})

    def get_all_error_codes(self) -> list:
        """
        获取所有错误码

        Returns:
            错误码列表
        """
        return list(self._error_messages.keys())


# 全局错误码管理器实例
_error_code_manager = ErrorCodeManager()


def get_error_message(error_code: str, language: str = "en") -> str:
    """
    获取错误消息（便捷函数）

    Args:
        error_code: 错误码
        language: 语言（en或zh）

    Returns:
        错误消息
    """
    return _error_code_manager.get_message(error_code, language)


def get_error_code_manager() -> ErrorCodeManager:
    """
    获取错误码管理器实例

    Returns:
        错误码管理器实例
    """
    return _error_code_manager
