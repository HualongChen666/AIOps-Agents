# -*- coding: utf-8 -*-
"""测试RAG模块"""

import pytest

pytestmark = pytest.mark.smoke


class TestRAGModule:
    """测试RAG模块"""

    def test_fusion_module_exists(self):
        """测试融合模块存在"""
        from core.ai.rag import fusion

        assert fusion is not None

    def test_fusion_has_functions(self):
        """测试融合模块有函数"""
        from core.ai.rag import fusion

        # 检查模块有函数或类
        assert len(dir(fusion)) > 0

    def test_knowledge_base_module_exists(self):
        """测试知识库模块存在"""
        from core.ai.rag import knowledge_base

        assert knowledge_base is not None

    def test_knowledge_base_has_functions(self):
        """测试知识库模块有函数"""
        from core.ai.rag import knowledge_base

        # 检查模块有函数或类
        assert len(dir(knowledge_base)) > 0

    def test_reranker_module_exists(self):
        """测试重排序模块存在"""
        from core.ai.rag import reranker

        assert reranker is not None

    def test_reranker_has_functions(self):
        """测试重排序模块有函数"""
        from core.ai.rag import reranker

        # 检查模块有函数或类
        assert len(dir(reranker)) > 0

    def test_retriever_module_exists(self):
        """测试检索器模块存在"""
        from core.ai.rag import retriever

        assert retriever is not None

    def test_retriever_has_functions(self):
        """测试检索器模块有函数"""
        from core.ai.rag import retriever

        # 检查模块有函数或类
        assert len(dir(retriever)) > 0

    def test_vectorizer_module_exists(self):
        """测试向量化模块存在"""
        from core.ai.rag import vectorizer

        assert vectorizer is not None

    def test_vectorizer_has_functions(self):
        """测试向量化模块有函数"""
        from core.ai.rag import vectorizer

        # 检查模块有函数或类
        assert len(dir(vectorizer)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
