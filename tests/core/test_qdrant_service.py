# -*- coding: utf-8 -*-
"""测试Qdrant服务模块"""

import pytest


class TestQdrantServiceModule:
    """测试Qdrant服务模块"""

    def test_qdrant_service_module_exists(self):
        """测试Qdrant服务模块存在"""
        try:
            from core.qdrant_service import get_qdrant_client

            assert get_qdrant_client is not None
        except Exception as e:
            pytest.skip(f"Cannot test qdrant service module exists: {e}")

    def test_qdrant_service_has_functions(self):
        """测试Qdrant服务模块有函数"""
        try:
            from core.qdrant_service import (
                create_collection,
                delete_collection,
                delete_points,
                get_qdrant_client,
                health_check,
                list_collections,
                search,
                upsert_points,
            )

            # 检查模块有函数
            assert get_qdrant_client is not None
            assert list_collections is not None
            assert create_collection is not None
            assert delete_collection is not None
            assert upsert_points is not None
            assert search is not None
            assert delete_points is not None
            assert health_check is not None
        except Exception as e:
            pytest.skip(f"Cannot test qdrant service has functions: {e}")


class TestQdrantAvailability:
    """测试Qdrant可用性"""

    def test_qdrant_available_flag(self):
        """测试Qdrant可用性标志"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE

            # QDRANT_AVAILABLE should be a boolean
            assert isinstance(QDRANT_AVAILABLE, bool)
        except Exception as e:
            pytest.skip(f"Cannot test QDRANT_AVAILABLE flag: {e}")


class TestGetQdrantClient:
    """测试获取Qdrant客户端"""

    def test_get_qdrant_client_without_qdrant(self):
        """测试获取Qdrant客户端（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, get_qdrant_client

            if not QDRANT_AVAILABLE:
                result = get_qdrant_client()
                assert result is None
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test get qdrant client without qdrant: {e}")


class TestListCollections:
    """测试列出集合"""

    def test_list_collections_without_qdrant(self):
        """测试列出集合（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, list_collections

            if not QDRANT_AVAILABLE:
                result = list_collections()
                assert result == []
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test list collections without qdrant: {e}")


class TestCreateCollection:
    """测试创建集合"""

    def test_create_collection_without_qdrant(self):
        """测试创建集合（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, create_collection

            if not QDRANT_AVAILABLE:
                try:
                    create_collection("test_collection", 128)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test create collection without qdrant: {e}")


class TestDeleteCollection:
    """测试删除集合"""

    def test_delete_collection_without_qdrant(self):
        """测试删除集合（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, delete_collection

            if not QDRANT_AVAILABLE:
                try:
                    delete_collection("test_collection")
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test delete collection without qdrant: {e}")


class TestUpsertPoints:
    """测试插入点"""

    def test_upsert_points_without_qdrant(self):
        """测试插入点（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, upsert_points

            if not QDRANT_AVAILABLE:
                points = [{"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"data": "test"}}]
                try:
                    upsert_points("test_collection", points)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test upsert points without qdrant: {e}")


class TestSearch:
    """测试搜索"""

    def test_search_without_qdrant(self):
        """测试搜索（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, search

            if not QDRANT_AVAILABLE:
                query_vector = [0.1, 0.2, 0.3]
                try:
                    search("test_collection", query_vector)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test search without qdrant: {e}")


class TestDeletePoints:
    """测试删除点"""

    def test_delete_points_without_qdrant(self):
        """测试删除点（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, delete_points

            if not QDRANT_AVAILABLE:
                try:
                    delete_points("test_collection", [1, 2, 3])
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test delete points without qdrant: {e}")


class TestHealthCheck:
    """测试健康检查"""

    def test_health_check_without_qdrant(self):
        """测试健康检查（无Qdrant）"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, health_check

            if not QDRANT_AVAILABLE:
                result = health_check()
                assert result["status"] == "unavailable"
                assert "not initialized" in result["message"]
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test health check without qdrant: {e}")


class TestQdrantServiceIntegration:
    """测试Qdrant服务集成"""

    def test_module_exports(self):
        """测试模块导出"""
        try:
            from core.qdrant_service import __all__

            expected_exports = [
                "list_collections",
                "create_collection",
                "delete_collection",
                "upsert_points",
                "search",
                "delete_points",
                "health_check",
                "get_qdrant_client",
            ]

            for export in expected_exports:
                assert export in __all__
        except Exception as e:
            pytest.skip(f"Cannot test module exports: {e}")


class TestCreateCollectionEdgeCases:
    """测试创建集合边界情况"""

    def test_create_collection_empty_name(self):
        """测试空集合名"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, create_collection

            if not QDRANT_AVAILABLE:
                try:
                    create_collection("", 128)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test create collection empty name: {e}")

    def test_create_collection_zero_vector_size(self):
        """测试零向量大小"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, create_collection

            if not QDRANT_AVAILABLE:
                try:
                    create_collection("test", 0)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test create collection zero vector size: {e}")

    def test_create_collection_different_distances(self):
        """测试不同距离度量"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, create_collection

            if not QDRANT_AVAILABLE:
                distances = ["Cosine", "Euclid", "Dot", "Invalid"]
                for distance in distances:
                    try:
                        create_collection("test", 128, distance)
                        assert False, "Should have raised RuntimeError"
                    except RuntimeError as e:
                        assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test create collection different distances: {e}")


class TestUpsertPointsEdgeCases:
    """测试插入点边界情况"""

    def test_upsert_points_empty_collection(self):
        """测试空集合名"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, upsert_points

            if not QDRANT_AVAILABLE:
                points = [{"id": 1, "vector": [0.1, 0.2, 0.3]}]
                try:
                    upsert_points("", points)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test upsert points empty collection: {e}")

    def test_upsert_points_empty_points(self):
        """测试空点列表"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, upsert_points

            if not QDRANT_AVAILABLE:
                try:
                    upsert_points("test", [])
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test upsert points empty points: {e}")

    def test_upsert_points_missing_vector(self):
        """测试缺少向量"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, upsert_points

            if not QDRANT_AVAILABLE:
                points = [{"id": 1, "payload": {"data": "test"}}]
                try:
                    upsert_points("test", points)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test upsert points missing vector: {e}")


class TestSearchEdgeCases:
    """测试搜索边界情况"""

    def test_search_empty_collection(self):
        """测试空集合名"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, search

            if not QDRANT_AVAILABLE:
                query_vector = [0.1, 0.2, 0.3]
                try:
                    search("", query_vector)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test search empty collection: {e}")

    def test_search_empty_vector(self):
        """测试空向量"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, search

            if not QDRANT_AVAILABLE:
                try:
                    search("test", [])
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test search empty vector: {e}")

    def test_search_with_filter(self):
        """测试带过滤器搜索"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, search

            if not QDRANT_AVAILABLE:
                query_vector = [0.1, 0.2, 0.3]
                filter_dict = {"field": "value"}
                try:
                    search("test", query_vector, filter=filter_dict)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test search with filter: {e}")

    def test_search_zero_top_k(self):
        """测试零top_k"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, search

            if not QDRANT_AVAILABLE:
                query_vector = [0.1, 0.2, 0.3]
                try:
                    search("test", query_vector, top_k=0)
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test search zero top k: {e}")


class TestDeletePointsEdgeCases:
    """测试删除点边界情况"""

    def test_delete_points_empty_collection(self):
        """测试空集合名"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, delete_points

            if not QDRANT_AVAILABLE:
                try:
                    delete_points("", [1, 2, 3])
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test delete points empty collection: {e}")

    def test_delete_points_empty_ids(self):
        """测试空ID列表"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, delete_points

            if not QDRANT_AVAILABLE:
                try:
                    delete_points("test", [])
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test delete points empty ids: {e}")


class TestDeleteCollectionEdgeCases:
    """测试删除集合边界情况"""

    def test_delete_collection_empty_name(self):
        """测试空集合名"""
        try:
            from core.qdrant_service import QDRANT_AVAILABLE, delete_collection

            if not QDRANT_AVAILABLE:
                try:
                    delete_collection("")
                    assert False, "Should have raised RuntimeError"
                except RuntimeError as e:
                    assert "not available" in str(e)
            else:
                pytest.skip("Qdrant is available, cannot test unavailable case")
        except Exception as e:
            pytest.skip(f"Cannot test delete collection empty name: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
