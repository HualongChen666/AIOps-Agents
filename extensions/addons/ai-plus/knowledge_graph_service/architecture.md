# Knowledge Graph Service Architecture (Task 35.1)

## Overview

The Knowledge Graph Service is a FastAPI microservice that provides graph
management capabilities for the AIOps Agent platform.

## Service Decomposition

- **Entity/Relation modeling** (`modeler.py`): normalizes entity and relation
  requests into graph nodes and edges.
- **Graph construction** (`builder.py`): deduplicates and assembles graphs.
- **Neo4j graph store** (`graph_store.py`): optional Neo4j backend with an
  in-memory fallback.
- **Graph query** (`query.py`): entity/relation/path queries.
- **Graph reasoning** (`reasoning.py`): neighbors, transitive closure,
  PageRank, and path enumeration.
- **Graph visualization** (`visualizer.py`): circular 2D layout generation.
- **Service dependency graph** (`dependency_graph.py`): builds DEPENDS_ON graphs.
- **Infrastructure graph** (`infrastructure_graph.py`): builds CONNECTS_TO
  topology graphs.
- **Fault propagation graph** (`fault_graph.py`): builds PROPAGATES_TO graphs
  from fault states and rules.

## Inter-service Communication

- REST API documented in `README.md`.
- gRPC/REST RPC: `KnowledgeGraphRPCServer` and `KnowledgeGraphRPCClient`.

## Deployment

- Docker Compose for local development (includes Neo4j and Redis).
- Kubernetes for production.
- Prometheus for monitoring.
