# -*- coding: utf-8 -*-
"""
错误码单元测试

测试错误码定义和管理器的功能。
"""

from core.error_codes import ErrorCode, get_error_code_manager, get_error_message


class TestErrorCodeEnum:
    """测试错误码枚举类"""

    def test_error_code_values(self):
        """测试错误码值"""
        assert ErrorCode.GEN_VALIDATION_FAILED == "01_01_0001"
        assert ErrorCode.GEN_RESOURCE_NOT_FOUND == "01_02_0001"
        assert ErrorCode.AUTH_INVALID_CREDENTIALS == "02_01_0001"
        assert ErrorCode.DB_CONNECTION_FAILED == "09_06_0001"
        assert ErrorCode.AI_CONNECTION_FAILED == "11_06_0001"

    def test_error_code_is_string(self):
        """测试错误码是字符串类型"""
        assert isinstance(ErrorCode.GEN_VALIDATION_FAILED, str)
        assert isinstance(ErrorCode.AUTH_INVALID_CREDENTIALS, str)

    def test_error_code_format(self):
        """测试错误码格式"""
        # 格式: MM_TT_NNNN
        for error_code in ErrorCode:
            parts = error_code.value.split("_")
            assert len(parts) == 3
            assert len(parts[0]) == 2  # 模块码
            assert len(parts[1]) == 2  # 类型码
            assert len(parts[2]) == 4  # 序号

    def test_error_code_count(self):
        """测试错误码数量"""
        # 至少100个错误码
        error_codes = list(ErrorCode)
        assert len(error_codes) >= 100


class TestErrorCodeManager:
    """测试错误码管理器"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = get_error_code_manager()
        assert manager is not None
        assert isinstance(manager, object)

    def test_get_message_english(self):
        """测试获取英文消息"""
        message = get_error_message("01_01_0001", "en")
        assert message == "Parameter validation failed"

    def test_get_message_chinese(self):
        """测试获取中文消息"""
        message = get_error_message("01_01_0001", "zh")
        assert message == "参数验证失败"

    def test_get_message_default_language(self):
        """测试默认语言"""
        message = get_error_message("01_01_0001")
        assert message == "Parameter validation failed"

    def test_get_message_unknown_error_code(self):
        """测试未知错误码"""
        message = get_error_message("99_99_9999")
        assert message == "Unknown error"

    def test_get_message_unsupported_language(self):
        """测试不支持的语言"""
        message = get_error_message("01_01_0001", "fr")
        # 应该回退到英文
        assert message == "Parameter validation failed"

    def test_add_message(self):
        """测试添加错误消息"""
        manager = get_error_code_manager()
        manager.add_message("99_99_9999", "en", "Custom error")
        message = get_error_message("99_99_9999", "en")
        assert message == "Custom error"

    def test_get_all_messages(self):
        """测试获取所有消息"""
        manager = get_error_code_manager()
        messages = manager.get_all_messages("01_01_0001")
        assert "en" in messages
        assert "zh" in messages
        assert messages["en"] == "Parameter validation failed"
        assert messages["zh"] == "参数验证失败"

    def test_get_all_error_codes(self):
        """测试获取所有错误码"""
        manager = get_error_code_manager()
        error_codes = manager.get_all_error_codes()
        assert isinstance(error_codes, list)
        assert len(error_codes) >= 100
        assert "01_01_0001" in error_codes

    def test_database_error_messages(self):
        """测试数据库错误消息"""
        message_en = get_error_message("09_06_0001", "en")
        message_zh = get_error_message("09_06_0001", "zh")
        assert message_en == "Database connection failed"
        assert message_zh == "数据库连接失败"

    def test_ai_error_messages(self):
        """测试AI错误消息"""
        message_en = get_error_message("11_12_0001", "en")
        message_zh = get_error_message("11_12_0001", "zh")
        assert message_en == "Model load failed"
        assert message_zh == "模型加载失败"

    def test_authentication_error_messages(self):
        """测试认证错误消息"""
        message_en = get_error_message("02_01_0003", "en")
        message_zh = get_error_message("02_01_0003", "zh")
        assert message_en == "Token expired"
        assert message_zh == "Token已过期"


class TestErrorCodeCategories:
    """测试错误码分类"""

    def test_general_error_codes(self):
        """测试通用错误码"""
        assert ErrorCode.GEN_VALIDATION_FAILED.startswith("01_")
        assert ErrorCode.GEN_RESOURCE_NOT_FOUND.startswith("01_")
        assert ErrorCode.GEN_INTERNAL_ERROR.startswith("01_")

    def test_auth_error_codes(self):
        """测试认证授权错误码"""
        assert ErrorCode.AUTH_INVALID_CREDENTIALS.startswith("02_")
        assert ErrorCode.AUTH_TOKEN_EXPIRED.startswith("02_")
        assert ErrorCode.AUTH_PERMISSION_DENIED.startswith("02_")

    def test_database_error_codes(self):
        """测试数据库错误码"""
        assert ErrorCode.DB_CONNECTION_FAILED.startswith("09_")
        assert ErrorCode.DB_QUERY_ERROR.startswith("09_")
        assert ErrorCode.DB_DATA_CORRUPTION.startswith("09_")

    def test_ai_error_codes(self):
        """测试AI错误码"""
        assert ErrorCode.AI_CONNECTION_FAILED.startswith("11_")
        assert ErrorCode.AI_MODEL_LOAD_FAILED.startswith("11_")
        assert ErrorCode.AI_RATE_LIMIT_EXCEEDED.startswith("11_")

    def test_rag_error_codes(self):
        """测试RAG错误码"""
        assert ErrorCode.RAG_VECTOR_DB_CONNECTION_FAILED.startswith("12_")
        assert ErrorCode.RAG_VECTOR_SEARCH_ERROR.startswith("12_")

    def test_agent_error_codes(self):
        """测试代理编排错误码"""
        assert ErrorCode.AGENT_CONNECTION_FAILED.startswith("13_")
        assert ErrorCode.WORKFLOW_EXECUTION_ERROR.startswith("13_")

    def test_external_error_codes(self):
        """测试外部服务错误码"""
        assert ErrorCode.EXT_CONNECTION_FAILED.startswith("15_")
        assert ErrorCode.EXT_SERVICE_UNAVAILABLE.startswith("15_")

    def test_system_error_codes(self):
        """测试系统错误码"""
        assert ErrorCode.SYSTEM_FATAL_ERROR.startswith("20_")
        assert ErrorCode.SYSTEM_CRASH.startswith("20_")


class TestErrorCodeTypes:
    """测试错误码类型"""

    def test_validation_error_codes(self):
        """测试验证错误码"""
        assert ErrorCode.GEN_VALIDATION_FAILED.endswith("_01_0001")
        assert ErrorCode.GEN_INVALID_FORMAT.endswith("_01_0002")

    def test_not_found_error_codes(self):
        """测试未找到错误码"""
        assert ErrorCode.GEN_RESOURCE_NOT_FOUND.endswith("_02_0001")
        assert ErrorCode.GEN_ENDPOINT_NOT_FOUND.endswith("_02_0002")

    def test_permission_error_codes(self):
        """测试权限错误码"""
        assert ErrorCode.GEN_PERMISSION_DENIED.endswith("_03_0001")
        assert ErrorCode.AUTH_PERMISSION_DENIED.endswith("_03_0001")

    def test_connection_error_codes(self):
        """测试连接错误码"""
        assert ErrorCode.DB_CONNECTION_FAILED.endswith("_06_0001")
        assert ErrorCode.AI_CONNECTION_FAILED.endswith("_06_0001")

    def test_timeout_error_codes(self):
        """测试超时错误码"""
        assert ErrorCode.GEN_REQUEST_TIMEOUT.endswith("_09_0001")
        assert ErrorCode.DB_QUERY_TIMEOUT.endswith("_09_0001")

    def test_rate_limit_error_codes(self):
        """测试限流错误码"""
        assert ErrorCode.GEN_RATE_LIMIT_EXCEEDED.endswith("_10_0001")
        assert ErrorCode.AI_RATE_LIMIT_EXCEEDED.endswith("_10_0001")
