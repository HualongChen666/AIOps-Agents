# -*- coding: utf-8 -*-
"""
Qdrant Service Module for AIOps Platform

Provides Qdrant vector database operations for RAG functionality.
This module serves as an interface between the application and Qdrant.
"""

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union  # noqa: F401

logger = logging.getLogger(__name__)

# Try to import qdrant-client, handle if not installed
QDRANT_AVAILABLE = False
if TYPE_CHECKING:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )
else:
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import (  # noqa: F401
            Distance,
            FieldCondition,
            Filter,
            MatchValue,
            PointStruct,
            VectorParams,
        )

        QDRANT_AVAILABLE = True
    except ImportError:
        logger.warning("qdrant-client not installed. Qdrant features will be unavailable.")
        QdrantClient = None  # type: ignore

# Global Qdrant client
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> Optional[QdrantClient]:
    """Get or create Qdrant client instance"""
    global _qdrant_client
    if not QDRANT_AVAILABLE:
        return None

    if os.environ.get("QDRANT_DISABLED", "").lower() in ("1", "true"):
        return None

    if _qdrant_client is None:
        try:
            from config import QDRANT_HOST, QDRANT_PORT

            _qdrant_client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                timeout=int(float(os.environ.get("QDRANT_TIMEOUT", "2.0"))),
            )
            logger.info(f"Qdrant client initialized: {QDRANT_HOST}:{QDRANT_PORT}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            return None

    return _qdrant_client


def list_collections() -> List[str]:
    """List all Qdrant collections"""
    client = get_qdrant_client()
    if not client:
        return []

    try:
        collections = client.get_collections().collections
        return [collection.name for collection in collections]
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        return []


def create_collection(name: str, vector_size: int, distance: str = "Cosine") -> Dict[str, Any]:
    """Create a new Qdrant collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        distance_map = {"Cosine": Distance.COSINE, "Euclid": Distance.EUCLID, "Dot": Distance.DOT}

        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size, distance=distance_map.get(distance, Distance.COSINE)
            ),
        )

        logger.info(f"Created collection: {name}")
        return {"status": "success", "collection": name}
    except Exception as e:
        logger.error(f"Failed to create collection {name}: {e}")
        raise


def delete_collection(name: str) -> Dict[str, Any]:
    """Delete a Qdrant collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        client.delete_collection(collection_name=name)
        logger.info(f"Deleted collection: {name}")
        return {"status": "success", "collection": name}
    except Exception as e:
        logger.error(f"Failed to delete collection {name}: {e}")
        raise


def upsert_points(collection: str, points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Upsert points to a collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        qdrant_points = [
            PointStruct(id=point["id"], vector=point["vector"], payload=point.get("payload", {}))
            for point in points
        ]

        client.upsert(collection_name=collection, points=qdrant_points)

        logger.info(f"Upserted {len(points)} points to collection: {collection}")
        return {"status": "success", "collection": collection, "count": len(points)}
    except Exception as e:
        logger.error(f"Failed to upsert points to {collection}: {e}")
        raise


def search(
    collection: str,
    query_vector: List[float],
    top_k: int = 5,
    filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search for similar vectors in a collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        search_filter = None
        if filter:
            # Convert filter dict to Qdrant filter
            from qdrant_client.models import Filter as QdrantFilter

            conditions = []
            for field, value in filter.items():
                conditions.append(FieldCondition(key=field, match=MatchValue(value=value)))
            search_filter = QdrantFilter(must=conditions)  # type: ignore

        results = client.search(  # type: ignore
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
        )

        return [
            {"id": result.id, "score": result.score, "payload": result.payload}
            for result in results
        ]
    except Exception as e:
        logger.error(f"Failed to search in collection {collection}: {e}")
        raise


def delete_points(collection: str, ids: List[Any]) -> Dict[str, Any]:
    """Delete points from a collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        client.delete(collection_name=collection, points_selector=ids)

        logger.info(f"Deleted {len(ids)} points from collection: {collection}")
        return {"status": "success", "collection": collection, "count": len(ids)}
    except Exception as e:
        logger.error(f"Failed to delete points from {collection}: {e}")
        raise


def health_check() -> Dict[str, str]:
    """Check Qdrant health status"""
    client = get_qdrant_client()
    if not client:
        return {"status": "unavailable", "message": "Qdrant client not initialized"}

    try:
        # Try to get collections to verify connection
        client.get_collections()
        return {"status": "healthy", "message": "Qdrant connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Qdrant connection failed: {str(e)}"}


def upsert_points_batch(
    collection: str, points: List[Dict[str, Any]], batch_size: int = 100
) -> Dict[str, Any]:
    """Upsert points to a collection in batches to avoid rate limiting"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        total_points = len(points)
        upserted_count = 0
        
        for i in range(0, total_points, batch_size):
            batch = points[i : i + batch_size]
            qdrant_points = [
                PointStruct(id=point["id"], vector=point["vector"], payload=point.get("payload", {}))
                for point in batch
            ]
            client.upsert(collection_name=collection, points=qdrant_points)
            upserted_count += len(batch)
            logger.info(f"Batch upserted {len(batch)} points to collection: {collection}")

        logger.info(f"Total upserted {upserted_count} points to collection: {collection}")
        return {"status": "success", "collection": collection, "count": upserted_count}
    except Exception as e:
        logger.error(f"Failed to batch upsert points to {collection}: {e}")
        raise


def search_hybrid(
    collection: str,
    query_vector: List[float],
    query_text: str,
    top_k: int = 5,
    alpha: float = 0.7,
) -> List[Dict[str, Any]]:
    """Hybrid search combining vector similarity and text matching"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        # Perform vector search
        vector_results = search(collection=collection, query_vector=query_vector, top_k=top_k)
        
        # Simple text matching in payload (can be enhanced with full-text search)
        text_results = []
        all_collections = list_collections()
        if collection in all_collections:
            # Get all points and filter by text (simplified approach)
            from qdrant_client.models import ScrollRequest, Filter, FieldCondition, MatchText
            try:
                scroll_result = client.scroll(
                    collection_name=collection,
                    limit=100,
                    with_payload=True,
                )
                for point in scroll_result[0]:
                    payload = point.payload or {}
                    for key, value in payload.items():
                        if isinstance(value, str) and query_text.lower() in value.lower():
                            text_results.append({
                                "id": point.id,
                                "score": 0.8,
                                "payload": payload,
                            })
                            break
            except Exception:
                pass
        
        # Combine results with weighted scoring
        combined_results = {}
        for result in vector_results:
            combined_results[str(result["id"])] = {
                "id": result["id"],
                "vector_score": result["score"],
                "text_score": 0.0,
                "payload": result["payload"],
            }
        
        for result in text_results:
            point_id = str(result["id"])
            if point_id in combined_results:
                combined_results[point_id]["text_score"] = result["score"]
            else:
                combined_results[point_id] = {
                    "id": result["id"],
                    "vector_score": 0.0,
                    "text_score": result["score"],
                    "payload": result["payload"],
                }
        
        # Calculate combined score
        final_results = []
        for point_id, data in combined_results.items():
            combined_score = alpha * data["vector_score"] + (1 - alpha) * data["text_score"]
            final_results.append({
                "id": data["id"],
                "score": combined_score,
                "payload": data["payload"],
            })
        
        # Sort by combined score and return top_k
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results[:top_k]
    except Exception as e:
        logger.error(f"Failed to hybrid search in collection {collection}: {e}")
        raise


def search_multi_vector(
    collection: str,
    query_vectors: List[List[float]],
    weights: Optional[List[float]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Search with multiple query vectors and optional weights"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        if weights is None:
            weights = [1.0 / len(query_vectors)] * len(query_vectors)
        
        if len(weights) != len(query_vectors):
            raise ValueError("Number of weights must match number of query vectors")
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Perform searches for each query vector
        all_results = {}
        for query_vector, weight in zip(query_vectors, weights):
            results = search(collection=collection, query_vector=query_vector, top_k=top_k * 2)
            for result in results:
                point_id = str(result["id"])
                if point_id in all_results:
                    all_results[point_id]["score"] += result["score"] * weight
                else:
                    all_results[point_id] = {
                        "id": result["id"],
                        "score": result["score"] * weight,
                        "payload": result["payload"],
                    }
        
        # Sort by combined score and return top_k
        final_results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
        return final_results[:top_k]
    except Exception as e:
        logger.error(f"Failed to multi-vector search in collection {collection}: {e}")
        raise


def get_collection_info(name: str) -> Dict[str, Any]:
    """Get detailed information about a collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        collection_info = client.get_collection(collection_name=name)
        return {
            "name": name,
            "vector_size": collection_info.config.params.vectors.size,
            "distance": str(collection_info.config.params.vectors.distance),
            "points_count": collection_info.points_count,
            "status": collection_info.status,
        }
    except Exception as e:
        logger.error(f"Failed to get collection info for {name}: {e}")
        raise


def get_point_count(collection: str) -> Dict[str, Any]:
    """Get the number of points in a collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        collection_info = client.get_collection(collection_name=collection)
        return {
            "collection": collection,
            "count": collection_info.points_count,
        }
    except Exception as e:
        logger.error(f"Failed to get point count for collection {collection}: {e}")
        raise


def get_vector_stats() -> Dict[str, Any]:
    """Get overall vector service statistics"""
    client = get_qdrant_client()
    if not client:
        return {
            "status": "unavailable",
            "collections": [],
            "total_points": 0,
        }

    try:
        collections = client.get_collections().collections
        total_points = sum(col.points_count for col in collections)
        
        collection_details = []
        for col in collections:
            collection_details.append({
                "name": col.name,
                "points_count": col.points_count,
                "vector_size": col.config.params.vectors.size if hasattr(col.config.params, 'vectors') else 0,
            })
        
        return {
            "status": "healthy",
            "collections": collection_details,
            "total_collections": len(collections),
            "total_points": total_points,
        }
    except Exception as e:
        logger.error(f"Failed to get vector stats: {e}")
        return {
            "status": "error",
            "error": str(e),
            "collections": [],
            "total_points": 0,
        }


def clear_collection(name: str) -> Dict[str, Any]:
    """Clear all points from a collection"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        # Get all point IDs first
        from qdrant_client.models import Filter, ScrollRequest
        
        scroll_result = client.scroll(
            collection_name=name,
            limit=10000,
            with_payload=False,
        )
        
        point_ids = [point.id for point in scroll_result[0]]
        
        if point_ids:
            client.delete(collection_name=name, points_selector=point_ids)
            logger.info(f"Cleared {len(point_ids)} points from collection: {name}")
            return {"status": "success", "collection": name, "cleared_count": len(point_ids)}
        
        return {"status": "success", "collection": name, "cleared_count": 0}
    except Exception as e:
        logger.error(f"Failed to clear collection {name}: {e}")
        raise


def update_collection_config(collection: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update collection configuration"""
    client = get_qdrant_client()
    if not client:
        raise RuntimeError("Qdrant client not available")

    try:
        # Qdrant has limited update capabilities, mainly for optimizers
        # This is a placeholder for future enhancements
        logger.info(f"Update config requested for collection {collection} with params: {params}")
        return {
            "status": "success",
            "collection": collection,
            "message": "Configuration update logged (actual update depends on Qdrant version)",
        }
    except Exception as e:
        logger.error(f"Failed to update config for collection {collection}: {e}")
        raise


__all__ = [
    "list_collections",
    "create_collection",
    "delete_collection",
    "upsert_points",
    "upsert_points_batch",
    "search",
    "search_hybrid",
    "search_multi_vector",
    "delete_points",
    "health_check",
    "get_qdrant_client",
    "get_collection_info",
    "get_point_count",
    "get_vector_stats",
    "clear_collection",
    "update_collection_config",
]
