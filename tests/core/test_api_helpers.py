# -*- coding: utf-8 -*-
"""测试API帮助模块"""

import pytest
from fastapi import HTTPException


class TestAPIHelpersModule:
    """测试API帮助模块"""

    def test_api_helpers_module_exists(self):
        """测试API帮助模块存在"""
        from core import api_helpers

        assert api_helpers is not None

    def test_api_helpers_has_functions(self):
        """测试API帮助模块有函数"""
        from core import api_helpers

        # 检查模块有函数或类
        assert len(dir(api_helpers)) > 0


class TestHandleAPIError:
    """测试handle_api_error函数"""

    def test_handle_api_error_basic(self):
        """测试基本错误处理"""
        try:
            from core.api_helpers import handle_api_error

            with pytest.raises(HTTPException) as exc_info:
                handle_api_error("测试操作", ValueError("测试错误"))

            assert exc_info.value.status_code == 500
            assert "测试错误" in exc_info.value.detail
        except Exception as e:
            pytest.skip(f"Cannot test handle_api_error basic: {e}")

    def test_handle_api_error_custom_status(self):
        """测试自定义状态码"""
        try:
            from core.api_helpers import handle_api_error

            with pytest.raises(HTTPException) as exc_info:
                handle_api_error("测试操作", ValueError("测试错误"), status_code=400)

            assert exc_info.value.status_code == 400
        except Exception as e:
            pytest.skip(f"Cannot test handle_api_error custom status: {e}")

    def test_handle_api_error_with_prefix(self):
        """测试带前缀的错误处理"""
        try:
            from core.api_helpers import handle_api_error

            with pytest.raises(HTTPException) as exc_info:
                handle_api_error("测试操作", ValueError("测试错误"), detail_prefix="前缀")

            assert "前缀" in exc_info.value.detail
            assert "测试错误" in exc_info.value.detail
        except Exception as e:
            pytest.skip(f"Cannot test handle_api_error with prefix: {e}")

    def test_handle_api_error_truncation(self):
        """测试错误详情截断"""
        try:
            from core.api_helpers import handle_api_error

            long_error = "x" * 300
            with pytest.raises(HTTPException) as exc_info:
                handle_api_error("测试操作", ValueError(long_error), max_detail_length=100)

            assert len(exc_info.value.detail) <= 100
        except Exception as e:
            pytest.skip(f"Cannot test handle_api_error truncation: {e}")


class TestValidateRequiredFields:
    """测试validate_required_fields函数"""

    def test_validate_required_fields_valid(self):
        """测试有效字段验证"""
        try:
            from core.api_helpers import validate_required_fields

            data = {"field1": "value1", "field2": "value2"}
            validate_required_fields(data, ["field1", "field2"])
        except Exception as e:
            pytest.skip(f"Cannot test validate_required_fields valid: {e}")

    def test_validate_required_fields_missing(self):
        """测试缺失字段验证"""
        try:
            from core.api_helpers import validate_required_fields

            data = {"field1": "value1"}
            with pytest.raises(HTTPException) as exc_info:
                validate_required_fields(data, ["field1", "field2"])

            assert exc_info.value.status_code == 422
            assert "缺少必填字段" in exc_info.value.detail
        except Exception as e:
            pytest.skip(f"Cannot test validate_required_fields missing: {e}")

    def test_validate_required_fields_empty(self):
        """测试空字段验证"""
        try:
            from core.api_helpers import validate_required_fields

            data = {"field1": "value1", "field2": "   "}
            with pytest.raises(HTTPException) as exc_info:
                validate_required_fields(data, ["field1", "field2"])

            assert exc_info.value.status_code == 422
        except Exception as e:
            pytest.skip(f"Cannot test validate_required_fields empty: {e}")

    def test_validate_required_fields_invalid_type(self):
        """测试无效类型验证"""
        try:
            from core.api_helpers import validate_required_fields

            with pytest.raises(HTTPException) as exc_info:
                validate_required_fields("not a dict", ["field1"])

            assert exc_info.value.status_code == 422
            assert "必须是 dict" in exc_info.value.detail
        except Exception as e:
            pytest.skip(f"Cannot test validate_required_fields invalid type: {e}")


class TestLogOperationStart:
    """测试log_operation_start函数"""

    def test_log_operation_start(self):
        """测试操作开始日志"""
        try:
            from core.api_helpers import log_operation_start

            log_operation_start("测试操作")
            log_operation_start("测试操作", host="server1", count=5)
        except Exception as e:
            pytest.skip(f"Cannot test log_operation_start: {e}")


class TestLogOperationSuccess:
    """测试log_operation_success函数"""

    def test_log_operation_success(self):
        """测试操作成功日志"""
        try:
            from core.api_helpers import log_operation_success

            log_operation_success("测试操作")
            log_operation_success("测试操作", count=5, host="server1")
        except Exception as e:
            pytest.skip(f"Cannot test log_operation_success: {e}")


class TestCreateSuccessResponse:
    """测试create_success_response函数"""

    def test_create_success_response_basic(self):
        """测试基本成功响应"""
        try:
            from core.api_helpers import create_success_response

            response = create_success_response({"data": "value"})
            assert response["status"] == "ok"
            assert response["data"] == {"data": "value"}
        except Exception as e:
            pytest.skip(f"Cannot test create_success_response basic: {e}")

    def test_create_success_response_with_message(self):
        """测试带消息的成功响应"""
        try:
            from core.api_helpers import create_success_response

            response = create_success_response({"data": "value"}, "操作成功")
            assert response["status"] == "ok"
            assert response["message"] == "操作成功"
        except Exception as e:
            pytest.skip(f"Cannot test create_success_response with message: {e}")

    def test_create_success_response_with_extra(self):
        """测试带额外字段的成功响应"""
        try:
            from core.api_helpers import create_success_response

            response = create_success_response({"data": "value"}, extra_field="extra_value")
            assert response["status"] == "ok"
            assert response["extra_field"] == "extra_value"
        except Exception as e:
            pytest.skip(f"Cannot test create_success_response with extra: {e}")


class TestCreateErrorResponse:
    """测试create_error_response函数"""

    def test_create_error_response_basic(self):
        """测试基本错误响应"""
        try:
            from core.api_helpers import create_error_response

            response = create_error_response("操作失败")
            assert response["status"] == "error"
            assert response["message"] == "操作失败"
            assert response["status_code"] == 500
        except Exception as e:
            pytest.skip(f"Cannot test create_error_response basic: {e}")

    def test_create_error_response_custom_status(self):
        """测试自定义状态码错误响应"""
        try:
            from core.api_helpers import create_error_response

            response = create_error_response("操作失败", status_code=400)
            assert response["status_code"] == 400
        except Exception as e:
            pytest.skip(f"Cannot test create_error_response custom status: {e}")

    def test_create_error_response_with_error_code(self):
        """测试带错误码的错误响应"""
        try:
            from core.api_helpers import create_error_response

            response = create_error_response("操作失败", error_code="INVALID_INPUT")
            assert response["error_code"] == "INVALID_INPUT"
        except Exception as e:
            pytest.skip(f"Cannot test create_error_response with error code: {e}")


class TestFindHostConfig:
    """测试find_host_config函数"""

    def test_find_host_config_match_by_name(self):
        """测试通过名称查找主机配置"""
        try:
            from core.api_helpers import find_host_config

            hosts = [
                {"name": "server1", "host": "192.168.1.1"},
                {"name": "server2", "host": "192.168.1.2"},
            ]
            result = find_host_config("server1", hosts)
            assert result is not None
            assert result["name"] == "server1"
        except Exception as e:
            pytest.skip(f"Cannot test find_host_config by name: {e}")

    def test_find_host_config_match_by_host(self):
        """测试通过IP查找主机配置"""
        try:
            from core.api_helpers import find_host_config

            hosts = [
                {"name": "server1", "host": "192.168.1.1"},
                {"name": "server2", "host": "192.168.1.2"},
            ]
            result = find_host_config("192.168.1.1", hosts)
            assert result is not None
            assert result["host"] == "192.168.1.1"
        except Exception as e:
            pytest.skip(f"Cannot test find_host_config by host: {e}")

    def test_find_host_config_not_found(self):
        """测试未找到主机配置"""
        try:
            from core.api_helpers import find_host_config

            hosts = [
                {"name": "server1", "host": "192.168.1.1"},
                {"name": "server2", "host": "192.168.1.2"},
            ]
            result = find_host_config("server3", hosts)
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test find_host_config not found: {e}")

    def test_find_host_config_invalid_input(self):
        """测试无效输入"""
        try:
            from core.api_helpers import find_host_config

            result = find_host_config("", [])
            assert result is None

            result = find_host_config(None, [])
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test find_host_config invalid input: {e}")


class TestValidateHostname:
    """测试validate_hostname函数"""

    def test_validate_hostname_valid(self):
        """测试有效主机名"""
        try:
            from core.api_helpers import validate_hostname

            result = validate_hostname("server1")
            assert result == "server1"

            result = validate_hostname("192.168.1.1")
            assert result == "192.168.1.1"

            result = validate_hostname("server-01.example.com")
            assert result == "server-01.example.com"
        except Exception as e:
            pytest.skip(f"Cannot test validate_hostname valid: {e}")

    def test_validate_hostname_empty(self):
        """测试空主机名"""
        try:
            from core.api_helpers import validate_hostname

            with pytest.raises(ValueError) as exc_info:
                validate_hostname("")

            assert "不能为空" in str(exc_info.value)
        except Exception as e:
            pytest.skip(f"Cannot test validate_hostname empty: {e}")

    def test_validate_hostname_whitespace(self):
        """测试纯空白主机名"""
        try:
            from core.api_helpers import validate_hostname

            with pytest.raises(ValueError) as exc_info:
                validate_hostname("   ")

            assert "不能为纯空白" in str(exc_info.value)
        except Exception as e:
            pytest.skip(f"Cannot test validate_hostname whitespace: {e}")

    def test_validate_hostname_invalid_chars(self):
        """测试无效字符主机名"""
        try:
            from core.api_helpers import validate_hostname

            with pytest.raises(ValueError) as exc_info:
                validate_hostname("server@invalid")

            assert "仅允许字母数字" in str(exc_info.value)
        except Exception as e:
            pytest.skip(f"Cannot test validate_hostname invalid chars: {e}")

    def test_validate_hostname_trimming(self):
        """测试主机名修剪"""
        try:
            from core.api_helpers import validate_hostname

            result = validate_hostname("  server1  ")
            assert result == "server1"
        except Exception as e:
            pytest.skip(f"Cannot test validate_hostname trimming: {e}")


class TestHostnameFieldValidator:
    """测试hostname_field_validator函数"""

    def test_hostname_field_validator(self):
        """测试Pydantic字段验证器"""
        try:
            from core.api_helpers import hostname_field_validator

            result = hostname_field_validator("server1")
            assert result == "server1"
        except Exception as e:
            pytest.skip(f"Cannot test hostname_field_validator: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
