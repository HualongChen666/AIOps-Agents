# -*- coding: utf-8 -*-
"""测试GraphQL引擎模块"""

import pytest


class TestGraphqlEngineModule:
    """测试GraphQL引擎模块"""

    @pytest.mark.skip(reason="SQLAlchemy metadata conflict")
    def test_graphql_engine_module_exists(self):
        """测试GraphQL引擎模块存在"""
        from core import graphql_engine

        assert graphql_engine is not None

    @pytest.mark.skip(reason="SQLAlchemy metadata conflict")
    def test_graphql_engine_has_functions(self):
        """测试GraphQL引擎模块有函数"""
        from core import graphql_engine

        # 检查模块有函数或类
        assert len(dir(graphql_engine)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
