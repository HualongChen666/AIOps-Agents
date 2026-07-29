# -*- coding: utf-8 -*-
"""Real RAG add-on microservice.

Provides in-memory document indexing and similarity search using lightweight
numpy embeddings. In production, swap the ``HashEmbedding`` model for an
OpenAI/SentenceTransformer backend.
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

SERVICE_NAME = "rag_service"
PORT = int(os.getenv("PORT", "8000"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)


@dataclass
class DocumentChunk:
    id: str
    source_id: str
    text: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IndexRequest(BaseModel):
    documents: List[Dict[str, Any]] = Field(
        ..., description="List of {'id', 'content', 'metadata'}"
    )


class IndexResponse(BaseModel):
    indexed: int
    chunks: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query text")
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    chunk_id: str
    source_id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]


class HealthResponse(BaseModel):
    status: str
    service: str
    indexed_chunks: int


class HashEmbedding:
    """Deterministic, lightweight embedding for self-contained demos."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


class FixedSizeChunker:
    def __init__(self, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.size = size
        self.overlap = overlap

    def chunk(self, source_id: str, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.size
            piece = text[start:end]
            chunk_id = f"{source_id}-{start}"
            chunks.append(DocumentChunk(chunk_id, source_id, piece, metadata=metadata))
            start = end - self.overlap if end < len(text) else end
        return chunks


class VectorStore:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self._matrix: Optional[np.ndarray] = None

    def add(self, chunks: List[DocumentChunk], embedder: HashEmbedding):
        for c in chunks:
            c.embedding = embedder.embed(c.text)
        self.chunks.extend(chunks)
        self._matrix = None

    def _rebuild(self):
        if self._matrix is None and self.chunks:
            self._matrix = np.vstack([c.embedding for c in self.chunks])

    def search(
        self, query: str, top_k: int, embedder: HashEmbedding, filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        if not self.chunks:
            return []
        self._rebuild()
        q = embedder.embed(query)
        scores = self._matrix @ q
        top = np.argsort(scores)[-top_k:][::-1]
        results = []
        for idx in top:
            c = self.chunks[idx]
            if filters:
                if not all(c.metadata.get(k) == v for k, v in filters.items()):
                    continue
            results.append(
                SearchResult(
                    chunk_id=c.id,
                    source_id=c.source_id,
                    text=c.text,
                    score=float(scores[idx]),
                    metadata=c.metadata,
                )
            )
        return results


store = VectorStore()
chunker = FixedSizeChunker()
embedder = HashEmbedding()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, indexed_chunks=len(store.chunks))


@app.post("/index", response_model=IndexResponse)
async def index(req: IndexRequest) -> IndexResponse:
    """Index documents by chunking and embedding."""
    all_chunks = []
    for doc in req.documents:
        doc_id = doc.get("id") or f"doc-{hash(doc.get('content',''))}"
        content = doc.get("content") or ""
        meta = doc.get("metadata", {})
        all_chunks.extend(chunker.chunk(doc_id, content, meta))
    store.add(all_chunks, embedder)
    logger.info("Indexed %s documents into %s chunks", len(req.documents), len(all_chunks))
    return IndexResponse(indexed=len(req.documents), chunks=len(all_chunks))


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    """Semantic search over indexed chunks."""
    results = store.search(req.query, req.top_k, embedder, req.filters)
    return SearchResponse(query=req.query, results=results)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
