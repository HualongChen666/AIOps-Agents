---
pack: ai-plus
enabled_by: RAG_ENABLED
docker_profile: ai-plus
core_dependency: False
---

# RAG Service

Microservice for Retrieval-Augmented Generation: document vectorization,
knowledge base indexing, semantic search, context building, answer generation,
hybrid retrieval, reranking and multi-way recall.

## Run locally

```bash
uvicorn services.rag_service.main_app:app --host 0.0.0.0 --port 9406
```

## Docker Compose

```bash
docker-compose -f services/rag_service/docker-compose.yml up --build
```
