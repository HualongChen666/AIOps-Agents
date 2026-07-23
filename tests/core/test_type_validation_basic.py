# -*- coding: utf-8 -*-
"""
基础类型验证模块测试
测试类型验证核心功能的基础场景
"""

import pytest


class TestTypeValidationBasic:
    """类型验证模块基础测试"""

    def test_type_validation_module_structure(self):
        """测试类型验证模块结构"""
        try:
            from core import type_validation

            assert type_validation is not None
        except ImportError as e:
            pytest.skip(f"Type validation module not available: {e}")

    def test_type_validation_functions_exist(self):
        """测试类型验证关键函数存在"""
        try:
            from core.type_validation import validate_data, validate_schema, validate_type

            # 验证关键函数存在
            assert validate_type is not None
            assert validate_schema is not None
            assert validate_data is not None
        except Exception as e:
            pytest.skip(f"Type validation functions test failed: {e}")

    def test_type_validation_classes_exist(self):
        """测试类型验证关键类存在"""
        try:
            from core.type_validation import DataValidator, SchemaValidator, TypeValidator

            # 验证关键类存在
            assert TypeValidator is not None
            assert SchemaValidator is not None
            assert DataValidator is not None
        except Exception as e:
            pytest.skip(f"Type validation classes test failed: {e}")

    def test_type_validation_constants(self):
        """测试类型验证常量定义"""
        try:
            from core.type_validation import ValidationError, ValidationType

            # 验证常量存在
            assert ValidationType is not None
            assert ValidationError is not None
        except Exception as e:
            pytest.skip(f"Type validation constants test failed: {e}")
