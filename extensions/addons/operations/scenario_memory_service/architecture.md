# Scenario Memory Service Architecture (Task 34.1)

## Overview

The Scenario Memory Service is a FastAPI microservice that provides episodic
and semantic memory capabilities for the AIOps Agent platform.

## Service Decomposition

- **Event memory storage**: deterministic vector embedding, indexing by tags
  and event type, and Redis caching (`store_event`).
- **Similar event retrieval**: cosine-similarity based vector search over event
  embeddings (`search_similar`).
- **Experience learning**: accumulates (situation, action, outcome) triples
  with confidence decay (`learn_experience`).
- **Knowledge accumulation**: stores and weights (subject, predicate, object)
  triples (`accumulate_knowledge`).
- **Pattern recognition**: sequence, frequency, and correlation pattern mining
  (`recognize_pattern`).
- **Short-term memory**: TTL-based working state cache
  (`store_short_term`, `retrieve_short_term`).
- **Long-term memory**: importance-ranked historical memory
  (`store_long_term`, `retrieve_long_term`).
- **Semantic memory**: knowledge graph triples
  (`store_semantic`, `retrieve_semantic`).
- **Procedural memory**: operation flows with preconditions
  (`store_procedural`, `retrieve_procedural`).

## Inter-service Communication

- REST API: `/health`, `/metrics`, `/stats`, `/store/event`,
  `/search/similar`, `/learn/experience`, `/accumulate/knowledge`,
  `/recognize/pattern`, `/memory/short-term/{key}`, `/memory/long-term/{key}`,
  `/memory/semantic`, `/memory/procedural`, `/rpc/{method}`.
- gRPC/REST RPC: `ScenarioRPCServer` and `ScenarioRPCClient` for in-memory
  and HTTP-based service calls.

## Deployment

- Docker Compose for local development.
- Kubernetes for production.
- Prometheus for monitoring.
