# -*- coding: utf-8 -*-
"""Core orchestrator for the RAG microservice."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import math
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple, cast

from loguru import logger

from . import metrics
from .cache import CacheManager
from .config import settings
from .retry import RAGRetryEngine
from .schemas import (
    BatchSearchRequest,
    BatchVectorizeRequest,
    ContextRequest,
    ContextResponse,
    DeleteRequest,
    GenerateRequest,
    GenerateResponse,
    HybridRequest,
    IndexRequest,
    IndexResponse,
    KnowledgeGraphLinkageRequest,
    MarkStaleRequest,
    RebuildIndexRequest,
    RecallRequest,
    RecallResponse,
    RerankRequest,
    RetrieveRequest,
    RetrieveResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    VectorizeRequest,
    VectorizeResponse,
)


def _normalize(vector: List[float]) -> List[float]:
    """L2-normalize a vector."""
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _parse_date(value: Any) -> Optional[datetime.date]:
    """Parse a date string or datetime into a date object."""
    if value is None:
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    text = str(value).split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _freshness_boost(updated_at: Optional[Any], base_score: float, recency_weight: float) -> float:
    """Boost score for newer documents, penalize documents older than 90 days."""
    if recency_weight <= 0:
        return base_score
    date = _parse_date(updated_at)
    if date is None:
        return base_score
    days_old = (datetime.date.today() - date).days
    # Exponential decay: newer docs get up to +recency_weight, old docs decay
    decay = math.exp(-days_old / 90.0)
    return base_score + recency_weight * (decay - 0.5)


def _normalize_scores(scores: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """Normalize cosine/dot scores to [0, 1] range.

    If all scores are identical (span is zero), treat them as equally relevant
    and boost just above the default threshold so single-document cases still
    pass when no other signal exists.
    """
    if not scores:
        return scores
    max_score = max(s for _, s in scores)
    min_score = min(s for _, s in scores)
    span = max_score - min_score
    if span < 1e-9:
        return [(cid, 1.1) for cid, _ in scores]
    return [(cid, (s - min_score) / span) for cid, s in scores]


def _chunk_text_simple(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Boundary-aware sliding-window chunker preserving lines and numbered steps."""
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            # Try to break at a newline boundary
            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start + chunk_size // 4:
                end = newline_pos + 1
            else:
                # Try to break before a numbered step/header
                boundary = r"\n(?=\s*(?:\d+\.\s+|#{1,6}\s|\-+|\*+))"
                match = re.search(boundary, text[start:end])
                if match:
                    end = start + match.start() + 1
        chunks.append(text[start:end].strip())
        if end >= length:
            break
        start = max(start + 1, end - chunk_overlap)
    return [c for c in chunks if c]


class LangChainAdapter:
    """Optional LangChain adapter for document parsing and splitting."""

    def __init__(self) -> None:
        self.text_splitter: Any = None
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            self.text_splitter = RecursiveCharacterTextSplitter
            logger.info("LangChain text splitter loaded")
        except Exception as exc:
            logger.warning(f"LangChain unavailable: {exc}")

    def split(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text using LangChain or a simple fallback."""
        if self.text_splitter is not None:
            try:
                splitter = self.text_splitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len,
                )
                return cast(List[str], splitter.split_text(text))
            except Exception as exc:
                logger.warning(f"LangChain split failed: {exc}")
        return _chunk_text_simple(text, chunk_size, chunk_overlap)

    def to_documents(self, chunks: List[str], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert chunks into LangChain Document-like dicts."""
        return [{"page_content": c, "metadata": metadata} for c in chunks]


class RAGOrchestrator:
    """Orchestrates RAG operations across vectorization, indexing, retrieval and
    answer generation.
    """

    def __init__(
        self,
        embedding_model: Optional[Any] = None,
        vector_dimension: Optional[int] = None,
        cache: Optional[CacheManager] = None,
        retry_engine: Optional[RAGRetryEngine] = None,
    ) -> None:
        self.settings = settings
        self.vector_dimension = vector_dimension or settings.vector_dimension
        metrics.RAG_EMBEDDING_DIMENSION.set(self.vector_dimension)
        self._embedding_model = embedding_model
        self._embedding_cache: Dict[str, List[float]] = {}
        self._rerank_model: Optional[Any] = None
        self.langchain = LangChainAdapter()
        self.cache = cache or CacheManager(settings.redis_url)
        self.retry_engine = retry_engine or RAGRetryEngine(settings.retry_policy)
        self._index: Dict[str, Dict[str, Any]] = {}
        self._documents: Dict[str, List[str]] = {}
        self._request_counts: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Embedding (32.4 document vectorization helper)
    # ------------------------------------------------------------------
    @property
    def embedding_model(self) -> Any:
        """Lazy-load the embedding model, trying primary then fallback."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            primary = settings.embedding_model
            fallback = settings.fallback_embedding_model
            for model_name in (primary, fallback):
                try:
                    self._embedding_model = SentenceTransformer(model_name)
                    logger.info(f"Loaded SentenceTransformer model: {model_name}")
                    self.vector_dimension = self._embedding_model.get_sentence_embedding_dimension()
                    metrics.RAG_EMBEDDING_DIMENSION.set(self.vector_dimension)
                    break
                except Exception as exc:
                    logger.warning(f"Failed to load SentenceTransformer {model_name}: {exc}")
            else:
                logger.warning(
                    "All SentenceTransformer models failed; using deterministic fallback"
                )
                self._embedding_model = "fallback"
        return self._embedding_model

    def _fallback_embedding(self, texts: List[str]) -> List[List[float]]:
        """Deterministic fallback embedding using hash-based features."""
        vectors: List[List[float]] = []
        dim = self.vector_dimension
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], "big")
            rng = hashlib.sha256(f"{seed}".encode()).digest()
            vector = [
                (int.from_bytes(rng[i * 4 : (i + 1) * 4], "big") % 1000) / 1000.0
                for i in range(dim)
            ]
            vectors.append(_normalize(vector))
        return vectors

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute embeddings for a list of texts."""
        model = self.embedding_model
        if model == "fallback":
            return self._fallback_embedding(texts)
        try:
            embeddings: List[List[float]] = model.encode(texts, convert_to_numpy=True).tolist()
            return [_normalize(v) for v in embeddings]
        except Exception as exc:
            logger.warning(f"Embedding model failed ({exc}); using fallback")
            return self._fallback_embedding(texts)

    # ------------------------------------------------------------------
    # Chunking / parsing
    # ------------------------------------------------------------------
    def split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split a document into chunks using LangChain or fallback."""
        return self.langchain.split(text, chunk_size, chunk_overlap)

    # ------------------------------------------------------------------
    # 32.4 Document vectorization
    # ------------------------------------------------------------------
    async def vectorize_document(self, request: VectorizeRequest) -> VectorizeResponse:
        """Vectorize a document into chunks and embeddings."""
        start = time.time()
        metrics.RAG_REQUESTS_TOTAL.labels(operation="vectorize").inc()
        chunks = self.split_text(request.content, request.chunk_size, request.chunk_overlap)
        if not chunks:
            chunks = [request.content]
        vectors = await self.embed(chunks)
        # Ensure vectors match the current model dimension
        if vectors and len(vectors[0]) != self.vector_dimension:
            self.vector_dimension = len(vectors[0])
            metrics.RAG_EMBEDDING_DIMENSION.set(self.vector_dimension)
        latency = (time.time() - start) * 1000
        metrics.RAG_BATCH_SIZE.labels(operation="vectorize").observe(len(chunks))
        return VectorizeResponse(
            chunks=chunks,
            vectors=vectors,
            dimension=self.vector_dimension,
            chunk_count=len(chunks),
            latency_ms=latency,
        )

    # ------------------------------------------------------------------
    # 32.3 Knowledge base indexing
    # ------------------------------------------------------------------
    def _validate_index_request(self, request: IndexRequest) -> Tuple[bool, str]:
        """Quality gate: validate document before indexing."""
        if not request.content or len(request.content.strip()) < 3:
            return False, "content too short (< 3 characters)"
        if len(request.content) > 1_000_000:
            return False, "content too large (> 1MB)"
        if not request.document_id or not re.match(r"^[A-Za-z0-9_\-]+$", request.document_id):
            return False, "document_id must be alphanumeric with _ or -"
        # Dangerous / obviously wrong runbook patterns
        forbidden = ["rm -rf /", "rm -rf /*", ":(){ :|:& };:", "drop database", "drop table"]
        lower = request.content.lower()
        for phrase in forbidden:
            if phrase in lower:
                return False, f"forbidden dangerous pattern detected: {phrase!r}"
        return True, ""

    async def index_document(self, request: IndexRequest) -> IndexResponse:
        """Index a document into the knowledge base with validation."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="index").inc()
        valid, reason = self._validate_index_request(request)
        if not valid:
            logger.warning(f"Index rejected for {request.document_id}: {reason}")
            return IndexResponse(
                document_id=request.document_id,
                chunks_indexed=0,
                status="rejected",
                reason=reason,
            )

        # Add automatic updated_at if missing
        metadata = dict(request.metadata)
        if "updated_at" not in metadata:
            metadata["updated_at"] = datetime.date.today().isoformat()

        vectorize_request = VectorizeRequest(
            content=request.content,
            source=request.source,
            metadata=metadata,
        )
        vectorized = await self.vectorize_document(vectorize_request)

        chunk_ids: List[str] = []
        for idx, (chunk, vector) in enumerate(zip(vectorized.chunks, vectorized.vectors)):
            chunk_id = f"{request.document_id}::{idx}"
            self._index[chunk_id] = {
                "content": chunk,
                "vector": vector,
                "metadata": {**metadata, "chunk_index": idx},
                "document_id": request.document_id,
            }
            chunk_ids.append(chunk_id)
            self._embedding_cache[chunk] = vector

        self._documents[request.document_id] = chunk_ids
        metrics.RAG_DOCUMENTS_INDEXED.labels(source=request.source.value).inc()
        self._increment_count("index")
        return IndexResponse(
            document_id=request.document_id,
            chunks_indexed=len(chunk_ids),
            status="indexed",
        )

    # ------------------------------------------------------------------
    # 32.5 Semantic search
    # ------------------------------------------------------------------
    async def semantic_search(self, request: SearchRequest) -> SearchResponse:
        """Execute semantic search over the knowledge base."""
        start = time.time()
        metrics.RAG_REQUESTS_TOTAL.labels(operation="search").inc()
        threshold = (
            request.score_threshold
            if request.score_threshold is not None
            else self.settings.score_threshold
        )
        cache_key = f"search:{request.query}:{request.top_k}:{threshold}"
        cached = await self.cache.get(cache_key) if request.use_cache else None
        if cached:
            return SearchResponse(**cached)

        query_vector = (await self.embed([request.query]))[0]
        results = self._score_chunks(query_vector, request.top_k, threshold=threshold)
        latency = (time.time() - start) * 1000
        response = SearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            latency_ms=latency,
        )
        if request.use_cache:
            await self.cache.set(cache_key, response.model_dump(), self.settings.cache_ttl_seconds)
        metrics.RAG_QUERIES_TOTAL.labels(operation="search").inc()
        metrics.RAG_TOP_K_RESULTS.labels(operation="search").observe(len(results))
        self._increment_count("search")
        return response

    def _score_chunks(
        self,
        query_vector: List[float],
        top_k: int,
        threshold: float = 0.0,
        recency_weight: float = 0.0,
    ) -> List[SearchResult]:
        """Score and rank chunks by cosine similarity, then apply freshness boost and threshold."""
        scored: List[Tuple[str, float]] = []
        for chunk_id, item in self._index.items():
            if item.get("metadata", {}).get("stale"):
                continue
            score = _dot(query_vector, item["vector"])
            score = _freshness_boost(item["metadata"].get("updated_at"), score, recency_weight)
            scored.append((chunk_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = _normalize_scores(scored)
        results: List[SearchResult] = []
        for chunk_id, score in scored[:top_k]:
            if threshold and score < threshold:
                break
            item = self._index[chunk_id]
            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    content=item["content"],
                    score=round(score, 4),
                    metadata=item["metadata"],
                )
            )
            metrics.RAG_RETRIEVER_SCORE.labels(operation="search").observe(score)
        return results

    # ------------------------------------------------------------------
    # 32.3 Knowledge base retrieval (explicit filter support)
    # ------------------------------------------------------------------
    async def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        """Retrieve chunks from the knowledge base with optional filters and thresholds."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="retrieve").inc()
        threshold = (
            request.score_threshold
            if request.score_threshold is not None
            else self.settings.score_threshold
        )
        query_vector = (await self.embed([request.query]))[0]
        candidates = self._score_chunks(query_vector, request.top_k * 2, threshold=threshold)
        if request.filters:
            candidates = [c for c in candidates if self._matches_filters(c, request.filters)]
        results = candidates[: request.top_k]
        metrics.RAG_QUERIES_TOTAL.labels(operation="retrieve").inc()
        metrics.RAG_TOP_K_RESULTS.labels(operation="retrieve").observe(len(results))
        self._increment_count("retrieve")
        return RetrieveResponse(
            query=request.query,
            results=results,
            total=len(results),
        )

    def _matches_filters(self, result: SearchResult, filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if result.metadata.get(key) != value:
                return False
        return True

    # ------------------------------------------------------------------
    # 32.6 Context building
    # ------------------------------------------------------------------
    async def build_context(self, request: ContextRequest) -> ContextResponse:
        """Build a context string from search results for a query."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="context").inc()
        results = request.search_results
        if results is None:
            search_response = await self.semantic_search(
                SearchRequest(query=request.query, top_k=request.top_k)
            )
            results = search_response.results
        if not results:
            return ContextResponse(
                query=request.query,
                context="",
                source_count=0,
                token_estimate=0,
            )
        context_parts: List[str] = []
        for result in results:
            updated_at = result.metadata.get("updated_at", "")
            fresh_note = f" (updated: {updated_at})" if updated_at else ""
            context_parts.append(f"[Source {result.chunk_id}{fresh_note}] {result.content}")
        context = "\n\n".join(context_parts)
        token_estimate = len(context) // 4
        if token_estimate > request.max_context_length:
            context = context[: request.max_context_length * 4]
            token_estimate = request.max_context_length
        self._increment_count("context")
        return ContextResponse(
            query=request.query,
            context=context,
            source_count=len(results),
            token_estimate=token_estimate,
        )

    # ------------------------------------------------------------------
    # 32.7 Answer generation
    # ------------------------------------------------------------------
    async def generate_answer(self, request: GenerateRequest) -> GenerateResponse:
        """Generate an answer for a query using retrieved context with threshold."""
        start = time.time()
        metrics.RAG_REQUESTS_TOTAL.labels(operation="generate").inc()
        if request.context is None:
            search_request = SearchRequest(
                query=request.query,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
            )
            context_response = await self.build_context(
                ContextRequest(query=request.query, top_k=request.top_k)
            )
            context = context_response.context
            sources = (await self.semantic_search(search_request)).results
        else:
            context = request.context
            sources = []

        answer = await self._call_llm(request.query, context, request)
        latency = (time.time() - start) * 1000
        self._increment_count("generate")
        return GenerateResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            latency_ms=latency,
        )

    def _rag_system_prompt(self) -> str:
        return (
            "You are an AIOps assistant. Answer based primarily on the retrieved context below. "
            "If multiple sources conflict, prefer the one with the most recent 'updated' date. "
            "If the retrieved context is insufficient or irrelevant, clearly state that no "
            "relevant knowledge was found. "
            "Do not use your internal knowledge to override the retrieved runbooks or incident "
            "reports."
        )

    async def _call_llm(self, query: str, context: str, request: GenerateRequest) -> str:
        """Call an LLM for answer generation with multiple fallback strategies."""
        if not self.settings.openai_api_key:
            return self._template_answer(query, context)

        system_prompt = self._rag_system_prompt()
        user_prompt = (
            "Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        )

        try:
            from langchain.schema import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(  # type: ignore[call-arg]
                model="gpt-3.5-turbo",
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                openai_api_key=self.settings.openai_api_key or None,
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            result = await model.ainvoke(messages)
            content = result.content if hasattr(result, "content") else str(result)
            return str(content)
        except Exception as exc:
            logger.warning(f"LLM generation failed ({exc}); using fallback answer")

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.settings.openai_api_key or "test-key")
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning(f"OpenAI fallback failed ({exc}); using template answer")

        return self._template_answer(query, context)

    def _template_answer(self, query: str, context: str) -> str:
        """Generate a deterministic template answer when no LLM is available."""
        if not context:
            return f"未找到相关知识，无法回答: {query}"
        sentences = re.split(r"(?<=[.!?])\s+", context)
        best = sentences[0] if sentences else context
        return f"Based on the retrieved context: {best[:500]}"

    # ------------------------------------------------------------------
    # 32.8 Hybrid retrieval
    # ------------------------------------------------------------------
    async def hybrid_search(self, request: HybridRequest) -> SearchResponse:
        """Combine semantic and keyword retrieval with threshold and freshness."""
        start = time.time()
        metrics.RAG_REQUESTS_TOTAL.labels(operation="hybrid").inc()
        threshold = (
            request.score_threshold
            if request.score_threshold is not None
            else self.settings.score_threshold
        )
        query = request.query.lower()
        semantic_results = await self.semantic_search(
            SearchRequest(query=request.query, top_k=request.top_k * 3, score_threshold=0.0)
        )
        keyword_results = self._keyword_search(query, request.top_k * 3)

        # Normalize semantic scores to [0, 1] and apply freshness
        semantic_normalized = _normalize_scores(
            [(r.chunk_id, r.score) for r in semantic_results.results]
        )
        semantic_map: Dict[str, float] = {
            cid: _freshness_boost(
                self._index[cid]["metadata"].get("updated_at"),
                score,
                request.recency_weight,
            )
            for cid, score in semantic_normalized
            if cid in self._index
        }

        # Normalize keyword scores
        keyword_raw = [(r.chunk_id, r.score) for r in keyword_results]
        keyword_normalized = _normalize_scores(keyword_raw)
        keyword_map: Dict[str, float] = {
            cid: _freshness_boost(
                self._index[cid]["metadata"].get("updated_at"),
                score,
                request.recency_weight,
            )
            for cid, score in keyword_normalized
            if cid in self._index
        }

        fused: Dict[str, float] = {}
        for cid, score in semantic_map.items():
            fused[cid] = fused.get(cid, 0.0) + request.semantic_weight * score
        for cid, score in keyword_map.items():
            fused[cid] = fused.get(cid, 0.0) + request.keyword_weight * score

        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)
        if threshold:
            ranked = [(cid, s) for cid, s in ranked if s >= threshold]
        results = [
            self._to_search_result(chunk_id, score) for chunk_id, score in ranked[: request.top_k]
        ]
        latency = (time.time() - start) * 1000
        metrics.RAG_QUERIES_TOTAL.labels(operation="hybrid").inc()
        metrics.RAG_TOP_K_RESULTS.labels(operation="hybrid").observe(len(results))
        self._increment_count("hybrid")
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            latency_ms=latency,
        )

    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """Simple keyword overlap search; skips stale documents."""
        query_tokens = set(re.findall(r"\w+", query.lower()))
        scores: List[Tuple[str, float]] = []
        for chunk_id, item in self._index.items():
            if item.get("metadata", {}).get("stale"):
                continue
            tokens = re.findall(r"\w+", item["content"].lower())
            counter = Counter(tokens)
            score = sum(counter[t] for t in query_tokens)
            if score:
                scores.append((chunk_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [self._to_search_result(chunk_id, score) for chunk_id, score in scores[:top_k]]

    def _to_search_result(self, chunk_id: str, score: float) -> SearchResult:
        item = self._index[chunk_id]
        return SearchResult(
            chunk_id=chunk_id,
            content=item["content"],
            score=score,
            metadata=item["metadata"],
        )

    # ------------------------------------------------------------------
    # 32.9 Reranking
    # ------------------------------------------------------------------
    async def rerank(self, request: RerankRequest) -> SearchResponse:
        """Rerank candidates for a query using a cross-encoder or fallback."""
        start = time.time()
        metrics.RAG_REQUESTS_TOTAL.labels(operation="rerank").inc()
        query = request.query
        candidates = request.candidates or []
        if not candidates and self._index:
            candidates = (
                await self.semantic_search(SearchRequest(query=query, top_k=request.top_k * 2))
            ).results

        scores = self._cross_encoder_score(query, candidates)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        results = [
            SearchResult(
                chunk_id=c.chunk_id,
                content=c.content,
                score=score,
                metadata=c.metadata,
            )
            for c, score in ranked[: request.top_k]
        ]
        latency = (time.time() - start) * 1000
        metrics.RAG_QUERIES_TOTAL.labels(operation="rerank").inc()
        metrics.RAG_TOP_K_RESULTS.labels(operation="rerank").observe(len(results))
        self._increment_count("rerank")
        return SearchResponse(
            query=query,
            results=results,
            total=len(results),
            latency_ms=latency,
        )

    def _cross_encoder_score(self, query: str, candidates: List[SearchResult]) -> List[float]:
        """Score query-candidate pairs with a cross-encoder or keyword fallback."""
        if not self.settings.rerank_model:
            return self._keyword_overlap_score(query, candidates)

        if self._rerank_model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._rerank_model = CrossEncoder(self.settings.rerank_model)
            except Exception as exc:
                logger.debug(f"Cross-encoder unavailable ({exc}); using keyword fallback")
                return self._keyword_overlap_score(query, candidates)

        try:
            pairs = [[query, c.content] for c in candidates]
            return cast(List[float], self._rerank_model.predict(pairs).tolist())
        except Exception as exc:
            logger.debug(f"Cross-encoder scoring failed ({exc}); using keyword fallback")
            return self._keyword_overlap_score(query, candidates)

    def _keyword_overlap_score(self, query: str, candidates: List[SearchResult]) -> List[float]:
        """Score candidates by keyword overlap."""
        query_tokens = set(re.findall(r"\w+", query.lower()))
        scores: List[float] = []
        for candidate in candidates:
            tokens = re.findall(r"\w+", candidate.content.lower())
            counter = Counter(tokens)
            score = sum(counter[t] for t in query_tokens) / max(1, len(query_tokens))
            scores.append(score)
        return scores

    # ------------------------------------------------------------------
    # 32.10 Multi-way recall
    # ------------------------------------------------------------------
    async def multi_recall(self, request: RecallRequest) -> RecallResponse:
        """Recall chunks using multiple strategies and fuse results."""
        start = time.time()
        metrics.RAG_REQUESTS_TOTAL.labels(operation="recall").inc()
        threshold = (
            request.score_threshold
            if request.score_threshold is not None
            else self.settings.score_threshold
        )
        strategy_results: Dict[str, List[SearchResult]] = {}
        tasks: List[asyncio.Task[List[SearchResult]]] = []

        for strategy in request.strategies:
            if strategy == "semantic":
                task = asyncio.create_task(
                    self._semantic_recall(request.query, request.top_k, threshold)
                )
            elif strategy == "keyword":
                task = asyncio.create_task(self._keyword_recall(request.query, request.top_k))
            elif strategy == "vector":
                task = asyncio.create_task(
                    self._vector_recall(request.query, request.top_k, threshold)
                )
            else:
                task = asyncio.create_task(
                    self._semantic_recall(request.query, request.top_k, threshold)
                )
            tasks.append(task)

        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        for strategy, result in zip(request.strategies, results_list):
            if isinstance(result, BaseException):
                logger.warning(f"Strategy {strategy} failed: {result}")
                strategy_results[strategy] = []
            else:
                strategy_results[strategy] = result

        fused = self._fuse_results(
            strategy_results, request.top_k, threshold, request.recency_weight
        )
        latency = (time.time() - start) * 1000
        _ = latency  # reserved for future metrics
        metrics.RAG_QUERIES_TOTAL.labels(operation="recall").inc()
        metrics.RAG_TOP_K_RESULTS.labels(operation="recall").observe(len(fused))
        self._increment_count("recall")
        return RecallResponse(
            query=request.query,
            strategy_results=strategy_results,
            fused_results=fused,
            total=len(fused),
        )

    async def _semantic_recall(
        self, query: str, top_k: int, threshold: float = 0.0
    ) -> List[SearchResult]:
        response = await self.semantic_search(
            SearchRequest(query=query, top_k=top_k, score_threshold=threshold)
        )
        return response.results

    async def _keyword_recall(self, query: str, top_k: int) -> List[SearchResult]:
        return self._keyword_search(query.lower(), top_k)

    async def _vector_recall(
        self, query: str, top_k: int, threshold: float = 0.0
    ) -> List[SearchResult]:
        return self._score_chunks((await self.embed([query]))[0], top_k, threshold=threshold)

    def _fuse_results(
        self,
        strategy_results: Dict[str, List[SearchResult]],
        top_k: int,
        threshold: float = 0.0,
        recency_weight: float = 0.0,
    ) -> List[SearchResult]:
        """Reciprocal rank fusion across strategy results with freshness and threshold."""
        scores: Dict[str, float] = {}
        rank_info: Dict[str, Dict[str, Any]] = {}
        for strategy, results in strategy_results.items():
            for rank, result in enumerate(results):
                chunk_id = result.chunk_id
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rank + 1)
                if chunk_id not in rank_info:
                    rank_info[chunk_id] = {
                        "content": result.content,
                        "metadata": result.metadata,
                    }
        # Apply freshness boost
        boosted = [
            (
                chunk_id,
                _freshness_boost(
                    rank_info[chunk_id]["metadata"].get("updated_at"),
                    score,
                    recency_weight,
                ),
            )
            for chunk_id, score in scores.items()
        ]
        ranked = sorted(boosted, key=lambda x: x[1], reverse=True)
        if threshold:
            ranked = [(cid, s) for cid, s in ranked if s >= threshold]
        return [
            SearchResult(
                chunk_id=chunk_id,
                content=rank_info[chunk_id]["content"],
                score=round(score, 4),
                metadata=rank_info[chunk_id]["metadata"],
            )
            for chunk_id, score in ranked[:top_k]
        ]

    # ------------------------------------------------------------------
    # Batch operations (performance optimization)
    # ------------------------------------------------------------------
    async def batch_vectorize(self, request: BatchVectorizeRequest) -> List[VectorizeResponse]:
        """Vectorize multiple documents in parallel."""
        metrics.RAG_BATCH_SIZE.labels(operation="vectorize").observe(len(request.documents))
        tasks = [self.vectorize_document(doc) for doc in request.documents]
        return await asyncio.gather(*tasks)

    async def batch_search(self, request: BatchSearchRequest) -> List[SearchResponse]:
        """Search multiple queries in parallel."""
        metrics.RAG_BATCH_SIZE.labels(operation="search").observe(len(request.queries))
        tasks = [
            self.semantic_search(SearchRequest(query=q, top_k=request.top_k))
            for q in request.queries
        ]
        return await asyncio.gather(*tasks)

    async def batch_index(self, documents: List[IndexRequest]) -> List[IndexResponse]:
        """Index multiple documents in parallel."""
        metrics.RAG_BATCH_SIZE.labels(operation="index").observe(len(documents))
        tasks = [self.index_document(doc) for doc in documents]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # 32.11 Maintenance: delete / mark stale / rebuild / KG linkage
    # ------------------------------------------------------------------
    async def delete_document(self, request: DeleteRequest) -> IndexResponse:
        """Delete a document and all its chunks from the index."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="delete").inc()
        chunk_ids = self._documents.pop(request.document_id, [])
        removed = 0
        for chunk_id in chunk_ids:
            if chunk_id in self._index:
                del self._index[chunk_id]
                removed += 1
        removed_contents = {self._index.get(cid, {}).get("content", "") for cid in chunk_ids}
        self._embedding_cache = {
            k: v for k, v in self._embedding_cache.items() if k not in removed_contents
        }
        self._increment_count("delete")
        return IndexResponse(
            document_id=request.document_id,
            chunks_indexed=removed,
            status="deleted" if removed > 0 else "not_found",
        )

    async def mark_document_stale(self, request: MarkStaleRequest) -> IndexResponse:
        """Mark a document as stale so it is excluded from future retrieval."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="mark_stale").inc()
        chunk_ids = self._documents.get(request.document_id, [])
        if not chunk_ids:
            return IndexResponse(
                document_id=request.document_id,
                chunks_indexed=0,
                status="not_found",
                reason="document not in index",
            )
        for chunk_id in chunk_ids:
            if chunk_id in self._index:
                self._index[chunk_id]["metadata"]["stale"] = True
                self._index[chunk_id]["metadata"]["stale_reason"] = request.reason
        self._increment_count("mark_stale")
        return IndexResponse(
            document_id=request.document_id,
            chunks_indexed=len(chunk_ids),
            status="marked_stale",
            stale=True,
        )

    async def rebuild_index(self, request: RebuildIndexRequest) -> IndexResponse:
        """Rebuild embeddings for selected or all documents."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="rebuild").inc()
        doc_ids = request.document_ids or list(self._documents.keys())
        rebuilt = 0
        for doc_id in doc_ids:
            chunk_ids = self._documents.get(doc_id, [])
            contents = [self._index[cid]["content"] for cid in chunk_ids if cid in self._index]
            if not contents:
                continue
            vectors = await self.embed(contents)
            for cid, vector in zip(chunk_ids, vectors):
                if cid in self._index:
                    self._index[cid]["vector"] = vector
                    rebuilt += 1
        self._increment_count("rebuild")
        return IndexResponse(
            document_id="*",
            chunks_indexed=rebuilt,
            status="rebuilt",
        )

    async def link_to_knowledge_graph(
        self, request: KnowledgeGraphLinkageRequest
    ) -> Dict[str, Any]:
        """Link a doc to the knowledge graph as service/runbook/incident nodes."""
        metrics.RAG_REQUESTS_TOTAL.labels(operation="kg_link").inc()
        chunk_ids = self._documents.get(request.document_id, [])
        if not chunk_ids:
            return {"linked": False, "reason": "document not found"}
        first_chunk = self._index.get(chunk_ids[0], {})
        metadata = first_chunk.get("metadata", {})
        service = request.service or metadata.get("service", "unknown")
        doc_type = request.document_type or metadata.get("type", "document")
        nodes = [
            {"node_id": f"service:{service}", "label": service, "node_type": "service"},
            {
                "node_id": f"{doc_type}:{request.document_id}",
                "label": request.document_id,
                "node_type": doc_type,
            },
        ]
        edges = [
            {
                "edge_id": f"{service}_HAS_{doc_type}_{request.document_id}",
                "source_id": f"service:{service}",
                "target_id": f"{doc_type}:{request.document_id}",
                "relation": "HAS_KNOWLEDGE",
            }
        ]
        self._increment_count("kg_link")
        return {
            "linked": True,
            "document_id": request.document_id,
            "service": service,
            "document_type": doc_type,
            "nodes": nodes,
            "edges": edges,
        }

    # ------------------------------------------------------------------
    # Monitoring / stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        return {
            "index_size": len(self._index),
            "document_count": len(self._documents),
            "request_counts": dict(self._request_counts),
            "cache_hits": 0,
            "cache_misses": 0,
            "embedding_dimension": self.vector_dimension,
            "retry_policies": self.retry_engine.list_policies(),
            "embedding_model": self.settings.embedding_model,
        }

    def list_methods(self) -> List[str]:
        return [
            "vectorize_document",
            "index_document",
            "semantic_search",
            "retrieve",
            "build_context",
            "generate_answer",
            "hybrid_search",
            "rerank",
            "multi_recall",
            "batch_vectorize",
            "batch_search",
            "batch_index",
            "delete_document",
            "mark_document_stale",
            "rebuild_index",
            "link_to_knowledge_graph",
        ]

    def _increment_count(self, operation: str) -> None:
        self._request_counts[operation] = self._request_counts.get(operation, 0) + 1
