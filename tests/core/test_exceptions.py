# -*- coding: utf-8 -*-
"""
异常类单元测试

测试所有自定义异常类的功能。
"""

from core.exceptions import (
    AIModelException,
    AIOpsBaseException,
    AuthenticationException,
    AuthorizationException,
    BusinessException,
    BusinessLogicException,
    CacheException,
    ConfigurationException,
    CriticalException,
    DatabaseException,
    DataCorruptionException,
    ErrorCategory,
    ErrorSeverity,
    ExternalServiceException,
    IntegrationException,
    NetworkException,
    PermissionDeniedException,
    QuotaExceededException,
    ResourceException,
    ResourceNotFoundException,
    SecurityException,
    StateInvalidException,
    SystemException,
    SystemFatalException,
    ThirdPartyException,
    ValidationException,
    VersionMismatchException,
    WorkflowException,
)


class TestAIOpsBaseException:
    """测试基础异常类"""

    def test_basic_exception_creation(self):
        """测试基础异常创建"""
        exc = AIOpsBaseException(
            message="Test error",
            error_code="01_01_0001",
        )
        assert exc.message == "Test error"
        assert exc.error_code == "01_01_0001"
        assert exc.severity == ErrorSeverity.ERROR
        assert exc.category == ErrorCategory.BUSINESS
        assert exc.error_id is not None
        assert exc.timestamp is not None

    def test_exception_with_context(self):
        """测试带上下文的异常"""
        exc = AIOpsBaseException(
            message="Test error",
            context={"key": "value"},
        )
        assert exc.context == {"key": "value"}

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        exc = AIOpsBaseException(message="Test error")
        exc_dict = exc.to_dict()
        assert "error_id" in exc_dict
        assert "error_code" in exc_dict
        assert "message" in exc_dict
        assert "severity" in exc_dict
        assert "category" in exc_dict
        assert "timestamp" in exc_dict

    def test_exception_to_json(self):
        """测试异常转换为JSON"""
        exc = AIOpsBaseException(message="Test error")
        exc_json = exc.to_json()
        assert isinstance(exc_json, str)
        assert "Test error" in exc_json

    def test_exception_with_context_method(self):
        """测试with_context方法"""
        exc = AIOpsBaseException(message="Test error")
        exc.with_context(key1="value1", key2="value2")
        assert exc.context == {"key1": "value1", "key2": "value2"}

    def test_exception_str(self):
        """测试异常字符串表示"""
        exc = AIOpsBaseException(message="Test error", error_code="01_01_0001")
        assert str(exc) == "[01_01_0001] Test error"

    def test_exception_repr(self):
        """测试异常对象表示"""
        exc = AIOpsBaseException(message="Test error", error_code="01_01_0001")
        repr_str = repr(exc)
        assert "AIOpsBaseException" in repr_str
        assert "01_01_0001" in repr_str
        assert "Test error" in repr_str


class TestBusinessExceptions:
    """测试业务异常类"""

    def test_validation_exception(self):
        """测试验证异常"""
        exc = ValidationException(
            message="用户名不能为空",
            field="username",
            value="",
        )
        assert exc.message == "用户名不能为空"
        assert exc.error_code == "01_01_0001"
        assert exc.field == "username"
        assert exc.value == ""
        assert exc.context["field"] == "username"
        assert exc.context["value"] == ""

    def test_resource_not_found_exception(self):
        """测试资源未找到异常"""
        exc = ResourceNotFoundException(
            message="用户不存在",
            resource_type="User",
            resource_id=123,
        )
        assert exc.message == "用户不存在"
        assert exc.error_code == "01_02_0001"
        assert exc.resource_type == "User"
        assert exc.resource_id == 123
        assert exc.context["resource_type"] == "User"
        assert exc.context["resource_id"] == "123"

    def test_business_logic_exception(self):
        """测试业务逻辑异常"""
        exc = BusinessLogicException(
            message="用户余额不足",
            operation="withdraw",
        )
        assert exc.message == "用户余额不足"
        assert exc.error_code == "01_04_0001"
        assert exc.operation == "withdraw"
        assert exc.context["operation"] == "withdraw"

    def test_state_invalid_exception(self):
        """测试状态无效异常"""
        exc = StateInvalidException(
            message="订单状态不允许取消",
            current_state="shipped",
            required_state="pending",
        )
        assert exc.message == "订单状态不允许取消"
        assert exc.error_code == "01_05_0001"
        assert exc.current_state == "shipped"
        assert exc.required_state == "pending"
        assert exc.context["current_state"] == "shipped"
        assert exc.context["required_state"] == "pending"

    def test_workflow_exception(self):
        """测试工作流异常"""
        exc = WorkflowException(
            message="工作流执行失败",
            workflow_id="wf-123",
            step="approval",
        )
        assert exc.message == "工作流执行失败"
        assert exc.error_code == "13_04_0001"
        assert exc.workflow_id == "wf-123"
        assert exc.step == "approval"
        assert exc.context["workflow_id"] == "wf-123"
        assert exc.context["step"] == "approval"

    def test_quota_exceeded_exception(self):
        """测试配额超限异常"""
        exc = QuotaExceededException(
            message="API调用配额超限",
            quota_type="api_calls",
            current_usage=1000,
            quota_limit=500,
        )
        assert exc.message == "API调用配额超限"
        assert exc.error_code == "18_06_0003"
        assert exc.quota_type == "api_calls"
        assert exc.current_usage == 1000
        assert exc.quota_limit == 500
        assert exc.context["quota_type"] == "api_calls"
        assert exc.context["current_usage"] == 1000
        assert exc.context["quota_limit"] == 500


class TestSystemExceptions:
    """测试系统异常类"""

    def test_database_exception(self):
        """测试数据库异常"""
        exc = DatabaseException(
            message="数据库连接失败",
            host="localhost",
            port=5432,
            database="aiops",
        )
        assert exc.message == "数据库连接失败"
        assert exc.error_code == "09_06_0001"
        assert exc.host == "localhost"
        assert exc.port == 5432
        assert exc.database == "aiops"
        assert exc.context["host"] == "localhost"
        assert exc.context["port"] == 5432
        assert exc.context["database"] == "aiops"

    def test_network_exception(self):
        """测试网络异常"""
        exc = NetworkException(
            message="连接超时",
            url="https://api.example.com",
            timeout=30,
        )
        assert exc.message == "连接超时"
        assert exc.error_code == "17_06_0001"
        assert exc.url == "https://api.example.com"
        assert exc.timeout == 30
        assert exc.context["url"] == "https://api.example.com"
        assert exc.context["timeout"] == 30

    def test_cache_exception(self):
        """测试缓存异常"""
        exc = CacheException(
            message="缓存写入失败",
            cache_type="redis",
            key="user:123",
        )
        assert exc.message == "缓存写入失败"
        assert exc.error_code == "10_06_0001"
        assert exc.cache_type == "redis"
        assert exc.key == "user:123"
        assert exc.severity == ErrorSeverity.WARNING
        assert exc.context["cache_type"] == "redis"
        assert exc.context["key"] == "user:123"

    def test_configuration_exception(self):
        """测试配置异常"""
        exc = ConfigurationException(
            message="配置项缺失",
            config_key="DATABASE_URL",
            config_file="config.yaml",
        )
        assert exc.message == "配置项缺失"
        assert exc.error_code == "16_14_0001"
        assert exc.config_key == "DATABASE_URL"
        assert exc.config_file == "config.yaml"
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.context["config_key"] == "DATABASE_URL"
        assert exc.context["config_file"] == "config.yaml"

    def test_resource_exception(self):
        """测试资源异常"""
        exc = ResourceException(
            message="内存不足",
            resource_type="memory",
            available=100,
            required=500,
        )
        assert exc.message == "内存不足"
        assert exc.error_code == "18_06_0001"
        assert exc.resource_type == "memory"
        assert exc.available == 100
        assert exc.required == 500
        assert exc.context["resource_type"] == "memory"
        assert exc.context["available"] == 100
        assert exc.context["required"] == 500

    def test_version_mismatch_exception(self):
        """测试版本不匹配异常"""
        exc = VersionMismatchException(
            message="版本不兼容",
            current_version="1.0.0",
            required_version="2.0.0",
            component="database",
        )
        assert exc.message == "版本不兼容"
        assert exc.error_code == "16_14_0002"
        assert exc.current_version == "1.0.0"
        assert exc.required_version == "2.0.0"
        assert exc.component == "database"
        assert exc.context["current_version"] == "1.0.0"
        assert exc.context["required_version"] == "2.0.0"
        assert exc.context["component"] == "database"


class TestSecurityExceptions:
    """测试安全异常类"""

    def test_authentication_exception(self):
        """测试认证异常"""
        exc = AuthenticationException(
            message="Token已过期",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            expired_at="2024-01-01T00:00:00Z",
        )
        assert exc.message == "Token已过期"
        assert exc.error_code == "02_01_0001"
        assert exc.token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        assert exc.expired_at == "2024-01-01T00:00:00Z"
        assert exc.context["token"] == "eyJhbGci...VCJ9"  # 脱敏处理
        assert exc.context["expired_at"] == "2024-01-01T00:00:00Z"

    def test_authorization_exception(self):
        """测试授权异常"""
        exc = AuthorizationException(
            message="权限不足",
            required_role="admin",
            current_role="user",
        )
        assert exc.message == "权限不足"
        assert exc.error_code == "02_03_0001"
        assert exc.required_role == "admin"
        assert exc.current_role == "user"
        assert exc.context["required_role"] == "admin"
        assert exc.context["current_role"] == "user"

    def test_permission_denied_exception(self):
        """测试权限拒绝异常"""
        exc = PermissionDeniedException(
            message="无权访问该资源",
            resource="user:123",
            action="delete",
        )
        assert exc.message == "无权访问该资源"
        assert exc.error_code == "02_03_0002"
        assert exc.resource == "user:123"
        assert exc.action == "delete"
        assert exc.context["resource"] == "user:123"
        assert exc.context["action"] == "delete"


class TestThirdPartyExceptions:
    """测试第三方异常类"""

    def test_external_service_exception(self):
        """测试外部服务异常"""
        exc = ExternalServiceException(
            message="外部服务不可用",
            service_name="OpenAI API",
            service_url="https://api.openai.com",
        )
        assert exc.message == "外部服务不可用"
        assert exc.error_code == "15_06_0001"
        assert exc.service_name == "OpenAI API"
        assert exc.service_url == "https://api.openai.com"
        assert exc.context["service_name"] == "OpenAI API"
        assert exc.context["service_url"] == "https://api.openai.com"

    def test_ai_model_exception(self):
        """测试AI模型异常"""
        exc = AIModelException(
            message="模型推理失败",
            model_name="gpt-4",
            error_type="timeout",
        )
        assert exc.message == "模型推理失败"
        assert exc.error_code == "11_12_0001"
        assert exc.model_name == "gpt-4"
        assert exc.error_type == "timeout"
        assert exc.context["model_name"] == "gpt-4"
        assert exc.context["error_type"] == "timeout"

    def test_integration_exception(self):
        """测试集成异常"""
        exc = IntegrationException(
            message="数据同步失败",
            integration_type="GitLab",
            sync_operation="pull",
        )
        assert exc.message == "数据同步失败"
        assert exc.error_code == "19_06_0001"
        assert exc.integration_type == "GitLab"
        assert exc.sync_operation == "pull"
        assert exc.context["integration_type"] == "GitLab"
        assert exc.context["sync_operation"] == "pull"


class TestCriticalExceptions:
    """测试严重异常类"""

    def test_system_fatal_exception(self):
        """测试系统致命异常"""
        exc = SystemFatalException(
            message="系统核心服务崩溃",
            service="database",
            error_code_detail="FATAL_ERROR",
        )
        assert exc.message == "系统核心服务崩溃"
        assert exc.error_code == "20_15_0001"
        assert exc.service == "database"
        assert exc.error_code_detail == "FATAL_ERROR"
        assert exc.severity == ErrorSeverity.FATAL
        assert exc.context["service"] == "database"
        assert exc.context["error_code_detail"] == "FATAL_ERROR"

    def test_data_corruption_exception(self):
        """测试数据损坏异常"""
        exc = DataCorruptionException(
            message="数据完整性检查失败",
            table="users",
            constraint="unique_username",
        )
        assert exc.message == "数据完整性检查失败"
        assert exc.error_code == "09_13_0001"
        assert exc.table == "users"
        assert exc.constraint == "unique_username"
        assert exc.severity == ErrorSeverity.FATAL
        assert exc.context["table"] == "users"
        assert exc.context["constraint"] == "unique_username"


class TestExceptionInheritance:
    """测试异常继承关系"""

    def test_business_exception_inheritance(self):
        """测试业务异常继承"""
        exc = ValidationException(message="Test")
        assert isinstance(exc, BusinessException)
        assert isinstance(exc, AIOpsBaseException)

    def test_system_exception_inheritance(self):
        """测试系统异常继承"""
        exc = DatabaseException(message="Test")
        assert isinstance(exc, SystemException)
        assert isinstance(exc, AIOpsBaseException)

    def test_security_exception_inheritance(self):
        """测试安全异常继承"""
        exc = AuthenticationException(message="Test")
        assert isinstance(exc, SecurityException)
        assert isinstance(exc, AIOpsBaseException)

    def test_third_party_exception_inheritance(self):
        """测试第三方异常继承"""
        exc = ExternalServiceException(message="Test")
        assert isinstance(exc, ThirdPartyException)
        assert isinstance(exc, AIOpsBaseException)

    def test_critical_exception_inheritance(self):
        """测试严重异常继承"""
        exc = SystemFatalException(message="Test")
        assert isinstance(exc, CriticalException)
        assert isinstance(exc, AIOpsBaseException)


class TestExceptionCategories:
    """测试异常分类"""

    def test_business_exception_category(self):
        """测试业务异常分类"""
        exc = ValidationException(message="Test")
        assert exc.category == ErrorCategory.BUSINESS

    def test_system_exception_category(self):
        """测试系统异常分类"""
        exc = DatabaseException(message="Test")
        assert exc.category == ErrorCategory.SYSTEM

    def test_security_exception_category(self):
        """测试安全异常分类"""
        exc = AuthenticationException(message="Test")
        assert exc.category == ErrorCategory.SECURITY

    def test_third_party_exception_category(self):
        """测试第三方异常分类"""
        exc = ExternalServiceException(message="Test")
        assert exc.category == ErrorCategory.THIRD_PARTY

    def test_critical_exception_category(self):
        """测试严重异常分类"""
        exc = SystemFatalException(message="Test")
        assert exc.category == ErrorCategory.CRITICAL


class TestExceptionSeverities:
    """测试异常严重程度"""

    def test_validation_exception_severity(self):
        """测试验证异常严重程度"""
        exc = ValidationException(message="Test")
        assert exc.severity == ErrorSeverity.WARNING

    def test_cache_exception_severity(self):
        """测试缓存异常严重程度"""
        exc = CacheException(message="Test")
        assert exc.severity == ErrorSeverity.WARNING

    def test_configuration_exception_severity(self):
        """测试配置异常严重程度"""
        exc = ConfigurationException(message="Test")
        assert exc.severity == ErrorSeverity.CRITICAL

    def test_critical_exception_severity(self):
        """测试严重异常严重程度"""
        exc = SystemFatalException(message="Test")
        assert exc.severity == ErrorSeverity.FATAL
