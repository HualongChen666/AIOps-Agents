# -*- coding: utf-8 -*-
"""
Reranking with Cross-Encoder
Implements result refinement using cross-encoder models
"""

from typing import List

from loguru import logger

from .retriever import RetrievalResult


class Reranker:
    """
    Base reranker interface
    """

    async def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int
    ) -> List[RetrievalResult]:
        """Rerank retrieval results"""
        raise NotImplementedError


class CrossEncoderReranker(Reranker):
    """
    Cross-encoder based reranker
    """

    def __init__(
        self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu"
    ):
        """
        Initialize cross-encoder reranker

        Args:
            model_name: Model name
            device: Device to run on
        """
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        """Load model lazily"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name, device=self.device)
                logger.info(f"Loaded cross-encoder: {self.model_name}")
            except ImportError:
                logger.warning("sentence-transformers not available")

    async def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank using cross-encoder

        Args:
            query: Query text
            results: Retrieval results to rerank
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        if not results:
            return results

        try:
            self._load_model()
            if self._model is None:
                # Return original results if model not available
                return results[:top_k]

            # Prepare query-document pairs
            pairs = [[query, result.chunk.content] for result in results]

            # Compute cross-encoder scores
            scores = self._model.predict(pairs)

            # Update scores and rerank
            for result, score in zip(results, scores):
                result.score = float(score)

            # Sort by new scores
            results.sort(key=lambda x: x.score, reverse=True)

            logger.info(f"Reranked {len(results)} results to {top_k}")
            return results[:top_k]

        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            return results[:top_k]


class MMRReranker(Reranker):
    """
    MMR (Maximal Marginal Relevance) reranker
    """

    def __init__(self, lambda_param: float = 0.5):
        """
        Initialize MMR reranker

        Args:
            lambda_param: Balance between relevance and diversity (0-1)
        """
        self.lambda_param = lambda_param

    async def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank using MMR

        Args:
            query: Query text
            results: Retrieval results to rerank
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        if not results:
            return results

        try:
            selected: List[RetrievalResult] = []
            candidates = results.copy()

            while len(selected) < top_k and candidates:
                # Select best candidate considering relevance and diversity
                best_idx = 0
                best_score = -float("inf")

                for i, candidate in enumerate(candidates):
                    # Relevance score
                    relevance = candidate.score

                    # Diversity penalty
                    diversity_penalty = 0.0
                    for selected_item in selected:
                        similarity = self._compute_similarity(candidate.chunk, selected_item.chunk)
                        diversity_penalty = max(diversity_penalty, similarity)

                    # MMR score
                    mmr_score = (
                        self.lambda_param * relevance - (1 - self.lambda_param) * diversity_penalty
                    )

                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_idx = i

                selected.append(candidates.pop(best_idx))

            # Update scores
            for result in selected:
                result.score = result.score * self.lambda_param  # Adjust for display

            logger.info(f"MMR reranked to {len(selected)} results")
            return selected

        except Exception as e:
            logger.error(f"MMR reranking failed: {e}")
            return results[:top_k]

    def _compute_similarity(self, chunk1, chunk2) -> float:
        """Compute similarity between chunks"""
        # Placeholder - use cosine similarity of embeddings
        if chunk1.embedding and chunk2.embedding:
            pass

            emb1 = chunk1.embedding
            emb2 = chunk2.embedding
            dot = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = sum(a * a for a in emb1) ** 0.5
            norm2 = sum(b * b for b in emb2) ** 0.5
            return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0
        return 0.0


class RerankingPipeline:
    """
    Pipeline with multiple reranking stages
    """

    def __init__(self, rerankers: List[Reranker]):
        """
        Initialize reranking pipeline

        Args:
            rerankers: List of rerankers to apply sequentially
        """
        self.rerankers = rerankers

    async def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int
    ) -> List[RetrievalResult]:
        """
        Apply all rerankers sequentially

        Args:
            query: Query text
            results: Retrieval results
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        current_results = results

        for reranker in self.rerankers:
            current_results = await reranker.rerank(query, current_results, top_k)

        return current_results
