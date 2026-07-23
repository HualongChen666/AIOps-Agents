# -*- coding: utf-8 -*-
"""
Qdrant Service Module for AIOps Platform

Provides Qdrant vector database operations for RAG functionality.
This module serves as an interface between the application and Qdrant.
"""

import logging
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

    if _qdrant_client is None:
        try:
            from config import QDRANT_HOST, QDRANT_PORT

            _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
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


__all__ = [
    "list_collections",
    "create_collection",
    "delete_collection",
    "upsert_points",
    "search",
    "delete_points",
    "health_check",
    "get_qdrant_client",
]
