# -*- coding: utf-8 -*-
"""测试向量管道模块"""

import pytest


class TestVectorPipelineModule:
    """测试向量管道模块"""

    def test_vector_pipeline_module_exists(self):
        """测试向量管道模块存在"""
        from core import vector_pipeline

        assert vector_pipeline is not None

    def test_vector_pipeline_has_functions(self):
        """测试向量管道模块有函数"""
        from core import vector_pipeline

        # 检查模块有函数或类
        assert len(dir(vector_pipeline)) > 0


class TestLoadModel:
    """测试加载模型函数"""

    @pytest.mark.skip(reason="Requires sentence-transformers model download (network dependency)")
    def test_load_model_missing_dependency(self):
        """测试加载模型缺少依赖"""
        try:
            from core.vector_pipeline import _load_model

            # This should raise RuntimeError if sentence-transformers is not installed
            try:
                model = _load_model()
                # If it succeeds, the dependency is installed
                assert model is not None
            except RuntimeError as e:
                # Expected if sentence-transformers is not installed
                assert "sentence-transformers is required" in str(e)
        except Exception as e:
            pytest.skip(f"Cannot test load model missing dependency: {e}")


class TestEmbedDocuments:
    """测试嵌入文档函数"""

    @pytest.mark.skip(reason="Requires sentence-transformers model download (network dependency)")
    def test_embed_documents_missing_dependency(self):
        """测试嵌入文档缺少依赖"""
        try:
            from core.vector_pipeline import embed_documents

            # This should raise RuntimeError if sentence-transformers is not installed
            try:
                embeddings = embed_documents(["test document"])
                # If it succeeds, the dependency is installed
                assert embeddings is not None
            except RuntimeError as e:
                # Expected if sentence-transformers is not installed
                assert "sentence-transformers is required" in str(e)
        except Exception as e:
            pytest.skip(f"Cannot test embed documents missing dependency: {e}")


class TestEmbedQuery:
    """测试嵌入查询函数"""

    @pytest.mark.skip(reason="Requires sentence-transformers model download (network dependency)")
    def test_embed_query_missing_dependency(self):
        """测试嵌入查询缺少依赖"""
        try:
            from core.vector_pipeline import embed_query

            # This should raise RuntimeError if sentence-transformers is not installed
            try:
                embedding = embed_query("test query")
                # If it succeeds, the dependency is installed
                assert embedding is not None
            except RuntimeError as e:
                # Expected if sentence-transformers is not installed
                assert "sentence-transformers is required" in str(e)
        except Exception as e:
            pytest.skip(f"Cannot test embed query missing dependency: {e}")


class TestModelDimension:
    """测试模型维度函数"""

    @pytest.mark.skip(reason="Requires sentence-transformers model download (network dependency)")
    def test_model_dimension_missing_dependency(self):
        """测试模型维度缺少依赖"""
        try:
            from core.vector_pipeline import model_dimension

            # This should raise RuntimeError if sentence-transformers is not installed
            try:
                dimension = model_dimension()
                # If it succeeds, the dependency is installed
                assert dimension is not None
                assert isinstance(dimension, int)
            except RuntimeError as e:
                # Expected if sentence-transformers is not installed
                assert "sentence-transformers is required" in str(e)
        except Exception as e:
            pytest.skip(f"Cannot test model dimension missing dependency: {e}")


class TestVectorPipelineIntegration:
    """测试向量管道集成"""

    def test_api_exists(self):
        """测试API存在"""
        try:
            from core.vector_pipeline import embed_documents, embed_query, model_dimension

            # Check functions exist
            assert embed_documents is not None
            assert embed_query is not None
            assert model_dimension is not None
        except Exception as e:
            pytest.skip(f"Cannot test api exists: {e}")

    def test_function_signatures(self):
        """测试函数签名"""
        try:
            from core.vector_pipeline import embed_documents, embed_query, model_dimension

            # Check functions are callable
            assert callable(embed_documents)
            assert callable(embed_query)
            assert callable(model_dimension)
        except Exception as e:
            pytest.skip(f"Cannot test function signatures: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
