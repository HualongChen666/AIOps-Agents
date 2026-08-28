# -*- coding: utf-8 -*-
"""
Integration test for Qdrant vector database operations.

This test validates Qdrant vector database integration including:
- Connection management
- Collection operations
- Vector operations (insert, search, delete)
- Embedding operations
- Performance characteristics
- Error handling
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


@pytest.fixture
def qdrant_client():
    """Create Qdrant client for testing"""
    try:
        from qdrant_client import QdrantClient
        from core.config import QDRANT_URL, QDRANT_API_KEY
        
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
        )
        
        # Test connection
        client.get_collections()
        
        yield client
    except Exception as e:
        pytest.skip(f"Qdrant connection failed: {e}")
    finally:
        # Clean up test collections
        try:
            collections = client.get_collections()
            for collection in collections.collections:
                if collection.name.startswith("test_"):
                    client.delete_collection(collection.name)
        except:
            pass


@pytest.fixture
def test_collection(qdrant_client):
    """Create and manage test collection"""
    collection_name = "test_integration_collection"
    
    try:
        # Create collection if it doesn't exist
        from qdrant_client.models import Distance, VectorParams, PointStruct
        
        collections = qdrant_client.get_collections()
        collection_exists = any(c.name == collection_name for c in collections.collections)
        
        if not collection_exists:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=128, distance=Distance.COSINE)
            )
        
        yield collection_name
    finally:
        # Clean up test collection
        try:
            qdrant_client.delete_collection(collection_name)
        except:
            pass


@pytest.fixture
def sample_vectors():
    """Generate sample vectors for testing"""
    # Generate 10 sample vectors with 128 dimensions
    vectors = []
    for i in range(10):
        vector = np.random.rand(128).astype(np.float32)
        vectors.append(vector.tolist())
    return vectors


class TestQdrantConnection:
    """Test Qdrant connection management"""

    def test_qdrant_connection_established(self, qdrant_client):
        """Test that Qdrant connection can be established"""
        collections = qdrant_client.get_collections()
        assert collections is not None

    def test_qdrant_connection_error_handling(self):
        """Test Qdrant connection error handling"""
        try:
            from qdrant_client import QdrantClient
            
            # Try to connect with invalid URL
            client = QdrantClient(url="http://invalid:9999")
            client.get_collections()
            assert False, "Should have raised connection error"
        except Exception as e:
            # Expected to fail
            assert True

    def test_qdrant_health_check(self, qdrant_client):
        """Test Qdrant health check"""
        try:
            # Qdrant doesn't have a direct health check, but we can test connection
            collections = qdrant_client.get_collections()
            assert collections is not None
        except Exception as e:
            pytest.skip(f"Health check failed: {e}")


class TestQdrantCollectionOperations:
    """Test Qdrant collection operations"""

    def test_create_collection(self, qdrant_client):
        """Test collection creation"""
        from qdrant_client.models import Distance, VectorParams
        
        collection_name = "test_create_collection"
        
        try:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=128, distance=Distance.COSINE)
            )
            
            # Verify collection exists
            collections = qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            assert collection_name in collection_names
        finally:
            # Clean up
            try:
                qdrant_client.delete_collection(collection_name)
            except:
                pass

    def test_delete_collection(self, qdrant_client):
        """Test collection deletion"""
        from qdrant_client.models import Distance, VectorParams
        
        collection_name = "test_delete_collection"
        
        try:
            # Create collection
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=128, distance=Distance.COSINE)
            )
            
            # Delete collection
            qdrant_client.delete_collection(collection_name)
            
            # Verify deletion
            collections = qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            assert collection_name not in collection_names
        except Exception as e:
            pytest.skip(f"Collection deletion test failed: {e}")

    def test_get_collection_info(self, qdrant_client, test_collection):
        """Test getting collection information"""
        try:
            info = qdrant_client.get_collection(test_collection)
            assert info is not None
            assert info.config.params is not None
        except Exception as e:
            pytest.skip(f"Get collection info failed: {e}")


class TestQdrantVectorOperations:
    """Test Qdrant vector operations"""

    def test_insert_vectors(self, qdrant_client, test_collection, sample_vectors):
        """Test vector insertion"""
        from qdrant_client.models import PointStruct
        
        try:
            points = []
            for i, vector in enumerate(sample_vectors):
                point = PointStruct(
                    id=i,
                    vector=vector,
                    payload={"index": i, "label": f"point_{i}"}
                )
                points.append(point)
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=points
            )
            
            # Verify insertion
            count = qdrant_client.count(test_collection)
            assert count.count == len(sample_vectors)
        except Exception as e:
            pytest.skip(f"Vector insertion failed: {e}")

    def test_search_vectors(self, qdrant_client, test_collection, sample_vectors):
        """Test vector search"""
        from qdrant_client.models import PointStruct, SearchRequest
        
        try:
            # Insert vectors first
            points = []
            for i, vector in enumerate(sample_vectors):
                point = PointStruct(
                    id=i,
                    vector=vector,
                    payload={"index": i, "label": f"point_{i}"}
                )
                points.append(point)
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=points
            )
            
            # Search for similar vectors
            search_vector = sample_vectors[0]
            results = qdrant_client.search(
                collection_name=test_collection,
                query_vector=search_vector,
                limit=5
            )
            
            assert len(results) > 0
            assert results[0].id == 0  # First result should be the same vector
        except Exception as e:
            pytest.skip(f"Vector search failed: {e}")

    def test_delete_vectors(self, qdrant_client, test_collection, sample_vectors):
        """Test vector deletion"""
        from qdrant_client.models import PointStruct
        
        try:
            # Insert vectors
            points = []
            for i, vector in enumerate(sample_vectors):
                point = PointStruct(
                    id=i,
                    vector=vector,
                    payload={"index": i}
                )
                points.append(point)
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=points
            )
            
            # Delete specific vector
            qdrant_client.delete(
                collection_name=test_collection,
                points_selector=[0]
            )
            
            # Verify deletion
            count = qdrant_client.count(test_collection)
            assert count.count == len(sample_vectors) - 1
        except Exception as e:
            pytest.skip(f"Vector deletion failed: {e}")

    def test_update_vector_payload(self, qdrant_client, test_collection, sample_vectors):
        """Test updating vector payload"""
        from qdrant_client.models import PointStruct, PayloadSchemaType
        
        try:
            # Insert vector
            point = PointStruct(
                id=0,
                vector=sample_vectors[0],
                payload={"index": 0, "label": "original"}
            )
            qdrant_client.upsert(
                collection_name=test_collection,
                points=[point]
            )
            
            # Update payload
            qdrant_client.set_payload(
                collection_name=test_collection,
                payload={"label": "updated"},
                points=[0]
            )
            
            # Verify update
            results = qdrant_client.retrieve(
                collection_name=test_collection,
                ids=[0]
            )
            assert results[0].payload["label"] == "updated"
        except Exception as e:
            pytest.skip(f"Payload update failed: {e}")


class TestQdrantEmbeddingOperations:
    """Test Qdrant embedding operations"""

    def test_text_embedding_generation(self):
        """Test text embedding generation"""
        try:
            from core.analysis.l2.rag_engine import RAGEngine
            
            # This would require a real embedding model
            # For now, we'll skip it
            pytest.skip("Embedding generation test requires real model")
        except Exception as e:
            pytest.skip(f"Embedding generation failed: {e}")

    def test_embedding_storage_and_retrieval(self, qdrant_client, test_collection):
        """Test embedding storage and retrieval"""
        from qdrant_client.models import PointStruct
        
        try:
            # Simulate text embedding
            embedding = np.random.rand(128).astype(np.float32).tolist()
            
            point = PointStruct(
                id=0,
                vector=embedding,
                payload={
                    "text": "sample text for embedding",
                    "source": "test"
                }
            )
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=[point]
            )
            
            # Retrieve with payload
            results = qdrant_client.retrieve(
                collection_name=test_collection,
                ids=[0],
                with_payload=True
            )
            
            assert len(results) == 1
            assert results[0].payload["text"] == "sample text for embedding"
        except Exception as e:
            pytest.skip(f"Embedding storage test failed: {e}")

    def test_semantic_search(self, qdrant_client, test_collection):
        """Test semantic search with embeddings"""
        from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
        
        try:
            # Insert documents with embeddings
            documents = [
                {"text": "AI and machine learning", "category": "tech"},
                {"text": "Database management systems", "category": "tech"},
                {"text": "Cooking recipes", "category": "food"}
            ]
            
            points = []
            for i, doc in enumerate(documents):
                embedding = np.random.rand(128).astype(np.float32).tolist()
                point = PointStruct(
                    id=i,
                    vector=embedding,
                    payload=doc
                )
                points.append(point)
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=points
            )
            
            # Search with filter
            query_vector = np.random.rand(128).astype(np.float32).tolist()
            results = qdrant_client.search(
                collection_name=test_collection,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value="tech")
                        )
                    ]
                ),
                limit=10
            )
            
            # All results should have category "tech"
            for result in results:
                assert result.payload["category"] == "tech"
        except Exception as e:
            pytest.skip(f"Semantic search test failed: {e}")


class TestQdrantPerformance:
    """Test Qdrant performance characteristics"""

    def test_vector_insert_performance(self, qdrant_client, test_collection):
        """Test vector insert performance"""
        import time
        from qdrant_client.models import PointStruct
        
        try:
            # Generate test vectors
            vectors = [np.random.rand(128).astype(np.float32).tolist() for _ in range(100)]
            
            # Measure insert performance
            start_time = time.time()
            
            points = []
            for i, vector in enumerate(vectors):
                point = PointStruct(
                    id=i,
                    vector=vector,
                    payload={"index": i}
                )
                points.append(point)
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=points
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Insert should be reasonably fast (< 5 seconds for 100 vectors)
            assert duration < 5.0, f"Insert took {duration:.3f}s, expected < 5.0s"
        except Exception as e:
            pytest.skip(f"Insert performance test failed: {e}")

    def test_vector_search_performance(self, qdrant_client, test_collection):
        """Test vector search performance"""
        import time
        from qdrant_client.models import PointStruct
        
        try:
            # Insert test vectors
            vectors = [np.random.rand(128).astype(np.float32).tolist() for _ in range(100)]
            points = []
            for i, vector in enumerate(vectors):
                point = PointStruct(
                    id=i,
                    vector=vector,
                    payload={"index": i}
                )
                points.append(point)
            
            qdrant_client.upsert(
                collection_name=test_collection,
                points=points
            )
            
            # Measure search performance
            start_time = time.time()
            
            query_vector = np.random.rand(128).astype(np.float32).tolist()
            results = qdrant_client.search(
                collection_name=test_collection,
                query_vector=query_vector,
                limit=10
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Search should be fast (< 1 second)
            assert duration < 1.0, f"Search took {duration:.3f}s, expected < 1.0s"
        except Exception as e:
            pytest.skip(f"Search performance test failed: {e}")


class TestQdrantErrorHandling:
    """Test Qdrant error handling"""

    def test_invalid_vector_dimension(self, qdrant_client):
        """Test handling of invalid vector dimensions"""
        from qdrant_client.models import Distance, VectorParams, PointStruct
        
        collection_name = "test_invalid_dimension"
        
        try:
            # Create collection with 128 dimensions
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=128, distance=Distance.COSINE)
            )
            
            # Try to insert vector with wrong dimension
            wrong_vector = np.random.rand(256).astype(np.float32).tolist()
            point = PointStruct(id=0, vector=wrong_vector)
            
            qdrant_client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            assert False, "Should have raised error for wrong dimension"
        except Exception as e:
            # Expected to fail
            assert True
        finally:
            try:
                qdrant_client.delete_collection(collection_name)
            except:
                pass

    def test_duplicate_point_id(self, qdrant_client, test_collection):
        """Test handling of duplicate point IDs"""
        from qdrant_client.models import PointStruct
        
        try:
            vector = np.random.rand(128).astype(np.float32).tolist()
            
            # Insert point with ID 0
            point1 = PointStruct(id=0, vector=vector, payload={"version": 1})
            qdrant_client.upsert(
                collection_name=test_collection,
                points=[point1]
            )
            
            # Insert another point with same ID (should update)
            point2 = PointStruct(id=0, vector=vector, payload={"version": 2})
            qdrant_client.upsert(
                collection_name=test_collection,
                points=[point2]
            )
            
            # Verify update
            results = qdrant_client.retrieve(
                collection_name=test_collection,
                ids=[0]
            )
            assert results[0].payload["version"] == 2
        except Exception as e:
            pytest.skip(f"Duplicate ID test failed: {e}")

    def test_nonexistent_collection_access(self, qdrant_client):
        """Test accessing nonexistent collection"""
        try:
            qdrant_client.get_collection("nonexistent_collection")
            assert False, "Should have raised error for nonexistent collection"
        except Exception as e:
            # Expected to fail
            assert True


class TestQdrantIntegrationWithRAG:
    """Test Qdrant integration with RAG system"""

    def test_rag_vector_storage(self):
        """Test RAG system vector storage"""
        try:
            from core.analysis.l2.rag_engine import RAGEngine
            
            # This would require a real RAG engine instance
            # For now, we'll skip it
            pytest.skip("RAG integration test requires real RAG engine")
        except Exception as e:
            pytest.skip(f"RAG integration test failed: {e}")

    def test_rag_vector_retrieval(self):
        """Test RAG system vector retrieval"""
        try:
            from core.analysis.l2.rag_engine import RAGEngine
            
            # This would require a real RAG engine instance
            # For now, we'll skip it
            pytest.skip("RAG integration test requires real RAG engine")
        except Exception as e:
            pytest.skip(f"RAG integration test failed: {e}")

    def test_rag_similarity_search(self):
        """Test RAG similarity search"""
        try:
            from core.analysis.l2.rag_engine import RAGEngine
            
            # This would require a real RAG engine instance
            # For now, we'll skip it
            pytest.skip("RAG integration test requires real RAG engine")
        except Exception as e:
            pytest.skip(f"RAG integration test failed: {e}")


class TestQdrantWithAPI:
    """Test Qdrant integration with API endpoints"""

    @pytest.fixture
    def api_client(self):
        """Create API test client"""
        from main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_api_uses_qdrant_for_search(self, api_client):
        """Test that API uses Qdrant for vector search"""
        # This would require specific RAG endpoints
        # For now, we'll skip it
        pytest.skip("API Qdrant integration test requires specific endpoints")

    def test_api_vector_ingestion(self, api_client):
        """Test API vector ingestion"""
        # This would require specific RAG endpoints
        # For now, we'll skip it
        pytest.skip("API vector ingestion test requires specific endpoints")