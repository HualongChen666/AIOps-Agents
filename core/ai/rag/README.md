# RAG (Retrieval Augmented Generation) Module

## Overview
This module implements RAG for enhancing LLM responses with retrieved knowledge.

## Architecture
- **Vector Store**: Qdrant for vector embeddings storage
- **Embedding Pipeline**: Document chunking and vectorization
- **Retrieval**: Similarity search with multiple strategies
- **Reranking**: Cross-encoder for result refinement
- **Context Fusion**: Intelligent context combination

## Components
- `vectorizer.py`: Document embedding pipeline
- `retriever.py`: Vector similarity search
- `reranker.py`: Cross-encoder reranking
- `fusion.py`: Context fusion strategies
- `knowledge_base.py`: Knowledge base management

## Usage
```python
from aiops_core.ai.rag import RAGPipeline, KnowledgeBase

# Initialize knowledge base
kb = KnowledgeBase("incident_kb")
kb.add_document("Server downtime procedure", content)

# Create RAG pipeline
rag = RAGPipeline(kb)
result = await rag.query("How to fix server downtime?")
```
