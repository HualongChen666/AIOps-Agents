# -*- coding: utf-8 -*-
# tests/test_password_policy.py
# 🔧 P0-7: 密码复杂度策略单元测试

import pytest  # noqa: F401

from core.authentication import hash_password, validate_password_complexity, verify_password


class TestPasswordComplexity:
    """密码复杂度策略测试"""

    def test_password_too_short(self):
        """测试密码过短"""
        is_valid, error = validate_password_complexity("Short1!")
        assert not is_valid
        assert "12个字符" in error

    def test_password_missing_uppercase(self):
        """测试密码缺少大写字母"""
        is_valid, error = validate_password_complexity("lowercase123!")
        assert not is_valid
        assert "大写字母" in error

    def test_password_missing_lowercase(self):
        """测试密码缺少小写字母"""
        is_valid, error = validate_password_complexity("UPPERCASE123!")
        assert not is_valid
        assert "小写字母" in error

    def test_password_missing_digit(self):
        """测试密码缺少数字"""
        is_valid, error = validate_password_complexity("NoDigitsHere!")
        assert not is_valid
        assert "数字" in error

    def test_password_missing_special(self):
        """测试密码缺少特殊字符"""
        is_valid, error = validate_password_complexity("NoSpecial123")
        assert not is_valid
        assert "特殊字符" in error

    def test_password_common_weak(self):
        """测试常见弱密码"""
        is_valid, error = validate_password_complexity("Password123!")
        assert not is_valid
        assert "过于简单" in error

    def test_password_valid(self):
        """测试有效密码"""
        is_valid, error = validate_password_complexity("ValidPassword123!")
        assert is_valid
        assert error == ""

    def test_password_valid_with_all_requirements(self):
        """测试满足所有要求的密码"""
        is_valid, error = validate_password_complexity("SecureP@ssw0rd2024!")
        assert is_valid
        assert error == ""


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        # bcrypt hash starts with $2b$
        assert hashed.startswith("$2b$")

    def test_verify_password_success(self):
        """测试验证密码 - 成功"""
        password = "TestPassword123!"
        hashed = hash_password(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_failure(self):
        """测试验证密码 - 失败"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)

        result = verify_password(wrong_password, hashed)
        assert result is False

    def test_hash_password_truncation(self):
        """测试密码截断（bcrypt限制72字节）"""
        # bcrypt只使用前72字节
        long_password = "a" * 100 + "A1!"
        hashed = hash_password(long_password)

        # Should not raise error
        assert hashed is not None
        assert hashed.startswith("$2b$")
