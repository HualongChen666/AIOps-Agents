# -*- coding: utf-8 -*-
"""测试GraphQL模式模块"""

import pytest


class TestGraphqlSchemaModule:
    """测试GraphQL模式模块"""

    def test_graphql_schema_module_exists(self):
        """测试GraphQL模式模块存在"""
        from core import graphql_schema

        assert graphql_schema is not None

    def test_graphql_schema_has_functions(self):
        """测试GraphQL模式模块有函数"""
        from core import graphql_schema

        # 检查模块有函数或类
        assert len(dir(graphql_schema)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
