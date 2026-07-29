# RAG Service Architecture (Task 32.1)

## Overview

The RAG Service is a FastAPI microservice that provides retrieval-augmented
generation capabilities over a vector knowledge base.

## Service Decomposition

- **Document parsing / chunking**: `LangChainAdapter` with `RecursiveCharacterTextSplitter`
- **Document vectorization**: `RAGOrchestrator.vectorize_document` with embedding fallback
- **Knowledge base indexing**: `RAGOrchestrator.index_document` (in-memory + Redis cache)
- **Semantic search**: `RAGOrchestrator.semantic_search` with cosine similarity
- **Context building**: `RAGOrchestrator.build_context` from search results
- **Answer generation**: `RAGOrchestrator.generate_answer` with LLM fallback
- **Hybrid retrieval**: `RAGOrchestrator.hybrid_search` (semantic + keyword fusion)
- **Reranking**: `RAGOrchestrator.rerank` with cross-encoder / keyword fallback
- **Multi-way recall**: `RAGOrchestrator.multi_recall` (semantic, keyword, vector)
- **Batch / parallel processing**: `RAGOrchestrator.batch_*` methods with `asyncio.gather`
- **Monitoring**: Prometheus metrics
- **gRPC**: in-memory RPC server/client for inter-service communication
- **REST API**: `/health`, `/metrics`, `/vectorize`, `/index`, `/search`, `/retrieve`,
  `/context`, `/generate`, `/hybrid`, `/rerank`, `/recall`, `/batch/*`, `/rpc/{method}`

## Deployment

- Docker Compose for local development
- Kubernetes for production
- Prometheus for monitoring
