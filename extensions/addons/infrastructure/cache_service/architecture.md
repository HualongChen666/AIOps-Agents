# CacheService Architecture

## Overview

CacheService is a FastAPI microservice that provides CacheService capabilities.

## Service Decomposition

- REST API: `/health`, `/metrics`, `/stats`, `/rpc/{method}`, domain endpoints
- gRPC-like RPC server/client for inter-service communication
- Optional Redis caching with in-memory fallback
- Prometheus metrics
- Retry engine with configurable policies
- Docker Compose for local development and Kubernetes for production
