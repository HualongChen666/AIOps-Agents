# -*- coding: utf-8 -*-
"""
Vector Retrieval Interface
Implements similarity search with multiple strategies
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from .vectorizer import DocumentChunk


@dataclass
class RetrievalResult:
    """Retrieval result"""

    chunk: DocumentChunk
    score: float
    metadata: Dict[str, Any]


class RetrievalStrategy:
    """Base retrieval strategy"""

    async def retrieve(
        self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve relevant chunks"""
        raise NotImplementedError


class HybridRetrieval(RetrievalStrategy):
    """Hybrid retrieval combining multiple strategies"""

    def __init__(self, strategies: List[RetrievalStrategy], weights: Optional[List[float]] = None):
        """
        Initialize hybrid retrieval

        Args:
            strategies: List of retrieval strategies
            weights: Weights for each strategy
        """
        self.strategies = strategies
        self.weights = weights or [1.0] * len(strategies)

    async def retrieve(
        self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve using hybrid strategy

        Args:
            query: Query text
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            Combined retrieval results
        """
        all_results = []

        # Execute all strategies
        for strategy, weight in zip(self.strategies, self.weights):
            results = await strategy.retrieve(query, top_k, filters)

            # Adjust scores by weight
            for result in results:
                result.score *= weight

            all_results.extend(results)

        # Sort by score and return top_k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]


class BM25Retrieval(RetrievalStrategy):
    """BM25 keyword retrieval strategy"""

    def __init__(self, documents: List[DocumentChunk]):
        """
        Initialize BM25 retrieval

        Args:
            documents: Documents to index
        """
        self.documents = documents
        self._index = None

    def _build_index(self):
        """Build BM25 index"""
        try:
            from rank_bm25 import BM25Okapi

            tokenized_docs = [doc.content.split() for doc in self.documents]
            self._index = BM25Okapi(tokenized_docs)
            logger.info("BM25 index built")
        except ImportError:
            logger.warning("rank_bm25 not available")

    async def retrieve(
        self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve using BM25

        Args:
            query: Query text
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            Retrieval results
        """
        if self._index is None:
            self._build_index()

        if self._index is None:
            return []

        try:
            tokenized_query = query.split()
            scores = self._index.get_scores(tokenized_query)

            # Create results
            results = []
            for idx, score in enumerate(scores):
                if filters:
                    # Apply filters
                    doc = self.documents[idx]
                    if not all(doc.metadata.get(k) == v for k, v in filters.items()):
                        continue

                results.append(
                    RetrievalResult(
                        chunk=self.documents[idx], score=float(score), metadata={"strategy": "bm25"}
                    )
                )

            # Sort and return top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"BM25 retrieval failed: {e}")
            return []


class Retriever:
    """
    Main retriever with multiple strategies
    """

    def __init__(
        self,
        primary_strategy: RetrievalStrategy,
        fallback_strategies: Optional[List[RetrievalStrategy]] = None,
    ):
        """
        Initialize retriever

        Args:
            primary_strategy: Primary retrieval strategy
            fallback_strategies: Fallback strategies
        """
        self.primary_strategy = primary_strategy
        self.fallback_strategies = fallback_strategies or []

    async def retrieve(
        self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve with fallback

        Args:
            query: Query text
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            Retrieval results
        """
        try:
            results = await self.primary_strategy.retrieve(query, top_k, filters)
            if results:
                return results
        except Exception as e:
            logger.warning(f"Primary retrieval failed: {e}")

        # Try fallback strategies
        for strategy in self.fallback_strategies:
            try:
                results = await strategy.retrieve(query, top_k, filters)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Fallback retrieval failed: {e}")

        return []
