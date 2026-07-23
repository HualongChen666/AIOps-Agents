# -*- coding: utf-8 -*-
"""
Context Fusion Strategies
Imelligent context combination for RAG
"""

from typing import Any, Dict, List

from .retriever import RetrievalResult


class FusionStrategy:
    """Base fusion strategy"""

    def fuse(
        self, query: str, results: List[RetrievalResult], max_context_length: int = 4000
    ) -> str:
        """Fuse retrieval results into context"""
        raise NotImplementedError


class ConcatenationFusion(FusionStrategy):
    """Simple concatenation fusion"""

    def fuse(
        self, query: str, results: List[RetrievalResult], max_context_length: int = 4000
    ) -> str:
        """Concatenate all results"""
        context_parts = []
        current_length = 0

        for result in results:
            chunk_content = result.chunk.content
            if current_length + len(chunk_content) <= max_context_length:
                context_parts.append(chunk_content)
                current_length += len(chunk_content)
            else:
                break

        return "\n\n".join(context_parts)


class RelevanceFusion(FusionStrategy):
    """Relevance-weighted fusion"""

    def fuse(
        self, query: str, results: List[RetrievalResult], max_context_length: int = 4000
    ) -> str:
        """Fuse with relevance ordering"""
        # Sort by score
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

        context_parts = []
        current_length = 0

        for result in sorted_results:
            chunk_content = f"[Score: {result.score:.2f}] {result.chunk.content}"
            if current_length + len(chunk_content) <= max_context_length:
                context_parts.append(chunk_content)
                current_length += len(chunk_content)
            else:
                break

        return "\n\n".join(context_parts)


class RAGPipeline:
    """
    Complete RAG pipeline
    """

    def __init__(self, retriever, reranker=None, fusion_strategy: FusionStrategy = None):
        """
        Initialize RAG pipeline

        Args:
            retriever: Retriever instance
            reranker: Optional reranker
            fusion_strategy: Fusion strategy
        """
        self.retriever = retriever
        self.reranker = reranker
        self.fusion_strategy = fusion_strategy or ConcatenationFusion()

    async def query(
        self, query: str, top_k: int = 5, rerank: bool = True, max_context_length: int = 4000
    ) -> Dict[str, Any]:
        """
        Execute RAG query

        Args:
            query: Query text
            top_k: Number of results
            rerank: Whether to rerank
            max_context_length: Max context length

        Returns:
            RAG result with context
        """
        # Retrieve
        results = await self.retriever.retrieve(query, top_k)

        # Rerank
        if rerank and self.reranker:
            results = await self.reranker.rerank(query, results, top_k)

        # Fuse context
        context = self.fusion_strategy.fuse(query, results, max_context_length)

        return {
            "query": query,
            "context": context,
            "sources": [
                {"chunk_id": r.chunk.id, "document_id": r.chunk.document_id, "score": r.score}
                for r in results
            ],
        }
