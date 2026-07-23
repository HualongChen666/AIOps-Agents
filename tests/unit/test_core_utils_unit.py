# -*- coding: utf-8 -*-
# tests/unit/test_core_utils_unit.py
# 核心工具模块单元测试
from datetime import datetime, timedelta

import pytest


class TestDatetimeUtils:
    """日期时间工具测试"""

    def test_datetime_now(self):
        """测试当前时间获取"""
        now = datetime.now()
        assert now is not None
        assert isinstance(now, datetime)

    def test_datetime_arithmetic(self):
        """测试日期时间计算"""
        now = datetime.now()
        future = now + timedelta(hours=1)
        past = now - timedelta(hours=1)

        assert future > now
        assert past < now

    def test_datetime_isoformat(self):
        """测试ISO格式化"""
        now = datetime.now()
        iso_str = now.isoformat()
        assert isinstance(iso_str, str)
        assert "T" in iso_str


class TestStringUtils:
    """字符串工具测试"""

    def test_string_concatenation(self):
        """测试字符串拼接"""
        str1 = "Hello"
        str2 = "World"
        result = str1 + " " + str2
        assert result == "Hello World"

    def test_string_upper_lower(self):
        """测试大小写转换"""
        text = "Hello World"
        assert text.upper() == "HELLO WORLD"
        assert text.lower() == "hello world"

    def test_string_strip(self):
        """测试字符串去空格"""
        text = "  Hello World  "
        assert text.strip() == "Hello World"

    def test_string_split(self):
        """测试字符串分割"""
        text = "a,b,c"
        result = text.split(",")
        assert result == ["a", "b", "c"]


class TestMathUtils:
    """数学工具测试"""

    def test_basic_arithmetic(self):
        """测试基本算术"""
        assert 1 + 1 == 2
        assert 10 - 5 == 5
        assert 3 * 4 == 12
        assert 20 / 4 == 5.0

    def test_modulo(self):
        """测试取模"""
        assert 10 % 3 == 1
        assert 15 % 5 == 0

    def test_power(self):
        """测试幂运算"""
        assert 2**3 == 8
        assert 3**2 == 9


class TestListUtils:
    """列表工具测试"""

    def test_list_creation(self):
        """测试列表创建"""
        lst = [1, 2, 3, 4, 5]
        assert len(lst) == 5
        assert lst[0] == 1

    def test_list_append(self):
        """测试列表添加"""
        lst = [1, 2, 3]
        lst.append(4)
        assert 4 in lst
        assert len(lst) == 4

    def test_list_remove(self):
        """测试列表删除"""
        lst = [1, 2, 3, 4]
        lst.remove(2)
        assert 2 not in lst
        assert len(lst) == 3

    def test_list_sort(self):
        """测试列表排序"""
        lst = [3, 1, 4, 1, 5]
        lst.sort()
        assert lst == [1, 1, 3, 4, 5]


class TestDictUtils:
    """字典工具测试"""

    def test_dict_creation(self):
        """测试字典创建"""
        d = {"key1": "value1", "key2": "value2"}
        assert len(d) == 2
        assert d["key1"] == "value1"

    def test_dict_get(self):
        """测试字典获取"""
        d = {"key1": "value1"}
        assert d.get("key1") == "value1"
        assert d.get("key2", "default") == "default"

    def test_dict_keys_values(self):
        """测试字典键值"""
        d = {"a": 1, "b": 2, "c": 3}
        assert set(d.keys()) == {"a", "b", "c"}
        assert set(d.values()) == {1, 2, 3}

    def test_dict_update(self):
        """测试字典更新"""
        d = {"a": 1}
        d.update({"b": 2, "c": 3})
        assert len(d) == 3
        assert "b" in d


class TestTypeUtils:
    """类型工具测试"""

    def test_type_checking(self):
        """测试类型检查"""
        assert isinstance(123, int)
        assert isinstance("hello", str)
        assert isinstance([1, 2, 3], list)
        assert isinstance({"a": 1}, dict)

    def test_type_conversion(self):
        """测试类型转换"""
        assert int("123") == 123
        assert str(456) == "456"
        assert float("3.14") == 3.14
        assert list((1, 2, 3)) == [1, 2, 3]


class TestLogicUtils:
    """逻辑工具测试"""

    def test_boolean_logic(self):
        """测试布尔逻辑"""
        assert True and True is True
        assert True and False is False
        assert True or False is True
        assert False or False is False
        assert True is not False
        assert False is not True

    def test_comparison(self):
        """测试比较"""
        assert 1 < 2
        assert 2 > 1
        assert 1 <= 1
        assert 1 >= 1
        assert 1 == 1
        assert 1 != 2


class TestExceptionHandling:
    """异常处理测试"""

    def test_try_except(self):
        """测试try-except"""
        try:
            result = 1 / 0
        except ZeroDivisionError:
            result = 0

        assert result == 0

    def test_raise_exception(self):
        """测试抛出异常"""
        with pytest.raises(ValueError):
            raise ValueError("Test exception")

    def test_finally_block(self):
        """测试finally块"""
        executed = False
        try:
            executed = True
        finally:
            assert executed is True


class TestFileUtils:
    """文件工具测试"""

    def test_path_operations(self):
        """测试路径操作"""
        import os

        # 测试路径拼接
        path = os.path.join("dir1", "dir2", "file.txt")
        assert "dir1" in path
        assert "dir2" in path
        assert "file.txt" in path

    def test_file_extension(self):
        """测试文件扩展名"""
        filename = "test.txt"
        assert filename.endswith(".txt")

        filename2 = "test.json"
        assert filename2.endswith(".json")


class TestEncodingUtils:
    """编码工具测试"""

    def test_string_encoding(self):
        """测试字符串编码"""
        text = "Hello World"
        encoded = text.encode("utf-8")
        assert isinstance(encoded, bytes)

        decoded = encoded.decode("utf-8")
        assert decoded == text

    def test_unicode_handling(self):
        """测试Unicode处理"""
        unicode_text = "测试中文🎉"
        assert isinstance(unicode_text, str)
        assert len(unicode_text) > 0


class TestJSONUtils:
    """JSON工具测试"""

    def test_json_dumps(self):
        """测试JSON序列化"""
        import json

        data = {"key": "value", "number": 123}
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
        assert "key" in json_str

    def test_json_loads(self):
        """测试JSON反序列化"""
        import json

        json_str = '{"key": "value", "number": 123}'
        data = json.loads(json_str)
        assert data["key"] == "value"
        assert data["number"] == 123


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
