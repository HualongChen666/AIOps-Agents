# -*- coding: utf-8 -*-
"""Tests for core/error_handling.py."""

import logging

from fastapi import status

from core.error_handling import (
    AIEngineError,
    AIOpsException,
    AIOpsHTTPException,
    AuthenticationError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    create_error_response,
    handle_aiops_exception,
    handle_generic_exception,
    log_error,
)


def test_exceptions():
    assert str(AIOpsException("msg")) == "msg"
    exc = AIOpsHTTPException("not found", status_code=status.HTTP_404_NOT_FOUND)
    assert exc.status_code == 404
    assert isinstance(ValidationError("bad"), AIOpsException)
    assert isinstance(NotFoundError("x"), AIOpsException)
    assert isinstance(PermissionDeniedError("x"), AIOpsException)
    assert isinstance(AIEngineError("x"), AIOpsException)
    assert isinstance(DatabaseError("x"), AIOpsException)
    assert isinstance(AuthenticationError("x"), AIOpsException)


def test_handlers():
    exc = AIOpsException("boom")
    response = handle_aiops_exception(exc)
    assert "error_code" in response
    assert response["message"] == "boom"

    generic = handle_generic_exception(ValueError("bad"))
    assert "error_type" in generic["details"]

    resp = create_error_response(ErrorCode.INVALID_REQUEST, "detail", status_code=400)
    assert resp.status_code == 400

    log_error(ErrorCode.INTERNAL_ERROR, "test error")


def test_all_error_codes():
    """测试所有错误码的枚举值"""
    # 通用错误 (1000-1999)
    assert ErrorCode.INTERNAL_ERROR.value == "GEN_1000"
    assert ErrorCode.INVALID_REQUEST.value == "GEN_1001"
    assert ErrorCode.NOT_FOUND.value == "GEN_1002"
    assert ErrorCode.PERMISSION_DENIED.value == "GEN_1003"
    assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "GEN_1004"

    # AI引擎错误 (2000-2999)
    assert ErrorCode.AI_ENGINE_ERROR.value == "AI_2000"
    assert ErrorCode.AI_MODEL_ERROR.value == "AI_2001"
    assert ErrorCode.AI_TIMEOUT.value == "AI_2002"
    assert ErrorCode.AI_RATE_LIMIT.value == "AI_2003"

    # 数据库错误 (3000-3999)
    assert ErrorCode.DB_CONNECTION_ERROR.value == "DB_3000"
    assert ErrorCode.DB_QUERY_ERROR.value == "DB_3001"
    assert ErrorCode.DB_NOT_FOUND.value == "DB_3002"
    assert ErrorCode.DB_CONSTRAINT_ERROR.value == "DB_3003"

    # 认证授权错误 (4000-4999)
    assert ErrorCode.AUTH_INVALID_TOKEN.value == "AUTH_4000"
    assert ErrorCode.AUTH_EXPIRED_TOKEN.value == "AUTH_4001"
    assert ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS.value == "AUTH_4002"

    # 外部服务错误 (5000-5999)
    assert ErrorCode.EXTERNAL_SERVICE_ERROR.value == "EXT_5000"
    assert ErrorCode.EXTERNAL_SERVICE_TIMEOUT.value == "EXT_5001"

    # 验证错误码是字符串类型
    assert isinstance(ErrorCode.INTERNAL_ERROR.value, str)
    assert isinstance(ErrorCode.AI_ENGINE_ERROR.value, str)


def test_exception_to_dict():
    """测试异常转换为字典"""
    # 测试基础异常转换
    exc = AIOpsException(
        message="Test error",
        error_code=ErrorCode.INTERNAL_ERROR,
        details={"key": "value"},
    )
    result = exc.to_dict()

    assert result["error_code"] == "GEN_1000"
    assert result["message"] == "Test error"
    assert result["details"] == {"key": "value"}

    # 测试空details
    exc_no_details = AIOpsException("No details")
    result_no_details = exc_no_details.to_dict()
    assert result_no_details["details"] == {}

    # 测试不同错误码
    exc_ai = AIOpsException(
        "AI error",
        error_code=ErrorCode.AI_ENGINE_ERROR,
        details={"model": "gpt-4"},
    )
    result_ai = exc_ai.to_dict()
    assert result_ai["error_code"] == "AI_2000"
    assert result_ai["details"]["model"] == "gpt-4"

    # 测试嵌套details
    exc_nested = AIOpsException(
        "Nested error",
        details={"nested": {"deep": "value"}, "array": [1, 2, 3]},
    )
    result_nested = exc_nested.to_dict()
    assert result_nested["details"]["nested"]["deep"] == "value"
    assert result_nested["details"]["array"] == [1, 2, 3]


def test_create_error_response_with_different_codes():
    """测试使用不同错误码创建响应"""
    # 测试通用错误码
    resp1 = create_error_response(
        ErrorCode.INTERNAL_ERROR, "Internal error", status_code=500
    )
    assert resp1.status_code == 500
    assert resp1.error_code == ErrorCode.INTERNAL_ERROR
    assert resp1.detail["error_code"] == "GEN_1000"

    # 测试AI错误码
    resp2 = create_error_response(
        ErrorCode.AI_ENGINE_ERROR, "AI engine failed", status_code=500
    )
    assert resp2.status_code == 500
    assert resp2.error_code == ErrorCode.AI_ENGINE_ERROR
    assert resp2.detail["error_code"] == "AI_2000"

    # 测试数据库错误码
    resp3 = create_error_response(
        ErrorCode.DB_CONNECTION_ERROR, "DB connection failed", status_code=503
    )
    assert resp3.status_code == 503
    assert resp3.error_code == ErrorCode.DB_CONNECTION_ERROR
    assert resp3.detail["error_code"] == "DB_3000"

    # 测试认证错误码
    resp4 = create_error_response(
        ErrorCode.AUTH_INVALID_TOKEN, "Invalid token", status_code=401
    )
    assert resp4.status_code == 401
    assert resp4.error_code == ErrorCode.AUTH_INVALID_TOKEN
    assert resp4.detail["error_code"] == "AUTH_4000"

    # 测试带details的响应
    resp5 = create_error_response(
        ErrorCode.INVALID_REQUEST,
        "Validation failed",
        details={"field": "email", "error": "invalid format"},
        status_code=400,
    )
    assert resp5.status_code == 400
    assert resp5.details["field"] == "email"
    assert resp5.details["error"] == "invalid format"


def test_log_error_with_different_levels():
    """测试不同日志级别"""
    # 测试ERROR级别
    log_error(ErrorCode.INTERNAL_ERROR, "Error message", level=logging.ERROR)

    # 测试WARNING级别
    log_error(ErrorCode.INVALID_REQUEST, "Warning message", level=logging.WARNING)

    # 测试INFO级别
    log_error(ErrorCode.NOT_FOUND, "Info message", level=logging.INFO)

    # 测试DEBUG级别
    log_error(ErrorCode.AI_ENGINE_ERROR, "Debug message", level=logging.DEBUG)

    # 测试CRITICAL级别
    log_error(ErrorCode.DB_CONNECTION_ERROR, "Critical message", level=logging.CRITICAL)

    # 测试带details的日志
    log_error(
        ErrorCode.PERMISSION_DENIED,
        "Permission denied",
        details={"user": "test", "action": "delete"},
        level=logging.ERROR,
    )

    # 测试空details
    log_error(ErrorCode.RATE_LIMIT_EXCEEDED, "Rate limit", details=None, level=logging.WARNING)


def test_validation_error_with_details():
    """测试带详细信息的验证错误"""
    # 测试基础验证错误
    validation_exc = ValidationError("Invalid input")
    assert validation_exc.message == "Invalid input"
    assert validation_exc.error_code == ErrorCode.INVALID_REQUEST
    assert validation_exc.status_code == 400
    assert isinstance(validation_exc, AIOpsException)

    # 测试带details的验证错误
    validation_exc_with_details = ValidationError(
        "Validation failed",
        details={
            "field": "email",
            "constraint": "required",
            "value": None,
        },
    )
    assert validation_exc_with_details.details["field"] == "email"
    assert validation_exc_with_details.details["constraint"] == "required"
    assert validation_exc_with_details.details["value"] is None

    # 测试嵌套details
    validation_exc_nested = ValidationError(
        "Complex validation",
        details={
            "errors": [
                {"field": "username", "message": "too short"},
                {"field": "password", "message": "too weak"},
            ]
        },
    )
    assert len(validation_exc_nested.details["errors"]) == 2
    assert validation_exc_nested.details["errors"][0]["field"] == "username"

    # 测试to_dict方法
    result = validation_exc_with_details.to_dict()
    assert result["error_code"] == "GEN_1001"
    assert result["message"] == "Validation failed"
    assert result["details"]["field"] == "email"


def test_not_found_error_with_resource():
    """测试带资源信息的未找到错误"""
    # 测试基础未找到错误
    not_found_exc = NotFoundError("Resource not found")
    assert not_found_exc.message == "Resource not found"
    assert not_found_exc.error_code == ErrorCode.NOT_FOUND
    assert not_found_exc.status_code == 404
    assert isinstance(not_found_exc, AIOpsException)

    # 测试带资源details的未找到错误
    not_found_exc_with_details = NotFoundError(
        "User not found",
        details={
            "resource_type": "User",
            "resource_id": "12345",
            "query": {"id": 12345},
        },
    )
    assert not_found_exc_with_details.details["resource_type"] == "User"
    assert not_found_exc_with_details.details["resource_id"] == "12345"
    assert not_found_exc_with_details.details["query"]["id"] == 12345

    # 测试不同资源类型
    post_not_found = NotFoundError(
        "Post not found",
        details={"resource_type": "Post", "resource_id": "post-001"},
    )
    assert post_not_found.details["resource_type"] == "Post"

    # 测试to_dict方法
    result = not_found_exc_with_details.to_dict()
    assert result["error_code"] == "GEN_1002"
    assert result["message"] == "User not found"
    assert result["details"]["resource_type"] == "User"


def test_permission_denied_with_action():
    """测试带动作信息的权限拒绝错误"""
    # 测试基础权限拒绝错误
    perm_denied_exc = PermissionDeniedError("Permission denied")
    assert perm_denied_exc.message == "Permission denied"
    assert perm_denied_exc.error_code == ErrorCode.PERMISSION_DENIED
    assert perm_denied_exc.status_code == 403
    assert isinstance(perm_denied_exc, AIOpsException)

    # 测试带动作details的权限拒绝错误
    perm_denied_exc_with_details = PermissionDeniedError(
        "Cannot delete resource",
        details={
            "required_permission": "delete",
            "resource": "document",
            "user_role": "viewer",
        },
    )
    assert perm_denied_exc_with_details.details["required_permission"] == "delete"
    assert perm_denied_exc_with_details.details["resource"] == "document"
    assert perm_denied_exc_with_details.details["user_role"] == "viewer"

    # 测试不同权限场景
    admin_access = PermissionDeniedError(
        "Admin access required",
        details={
            "required_permission": "admin",
            "current_permission": "user",
            "action": "system_config",
        },
    )
    assert admin_access.details["required_permission"] == "admin"
    assert admin_access.details["action"] == "system_config"

    # 测试to_dict方法
    result = perm_denied_exc_with_details.to_dict()
    assert result["error_code"] == "GEN_1003"
    assert result["message"] == "Cannot delete resource"
    assert result["details"]["required_permission"] == "delete"


def test_rate_limit_error_with_retry_after():
    """测试带重试时间的速率限制错误"""
    # 测试基础速率限制错误（使用AIOpsException创建）
    rate_limit_exc = AIOpsException(
        "Rate limit exceeded",
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        status_code=429,
    )
    assert rate_limit_exc.message == "Rate limit exceeded"
    assert rate_limit_exc.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
    assert rate_limit_exc.status_code == 429

    # 测试带重试时间的速率限制错误
    rate_limit_with_retry = AIOpsException(
        "Too many requests",
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        details={
            "retry_after": 60,
            "limit": 100,
            "current": 150,
            "window": "1h",
        },
        status_code=429,
    )
    assert rate_limit_with_retry.details["retry_after"] == 60
    assert rate_limit_with_retry.details["limit"] == 100
    assert rate_limit_with_retry.details["current"] == 150
    assert rate_limit_with_retry.details["window"] == "1h"

    # 测试不同重试时间
    short_retry = AIOpsException(
        "Short wait",
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        details={"retry_after": 5, "window": "1m"},
        status_code=429,
    )
    assert short_retry.details["retry_after"] == 5

    # 测试AI速率限制
    ai_rate_limit = AIOpsException(
        "AI API rate limit",
        error_code=ErrorCode.AI_RATE_LIMIT,
        details={"retry_after": 3600, "provider": "openai"},
        status_code=429,
    )
    assert ai_rate_limit.error_code == ErrorCode.AI_RATE_LIMIT
    assert ai_rate_limit.details["retry_after"] == 3600
    assert ai_rate_limit.details["provider"] == "openai"

    # 测试to_dict方法
    result = rate_limit_with_retry.to_dict()
    assert result["error_code"] == "GEN_1004"
    assert result["message"] == "Too many requests"
    assert result["details"]["retry_after"] == 60
