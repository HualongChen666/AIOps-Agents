# Config Service Architecture (Task 30.1)

## Overview
The config service is a FastAPI microservice:
- `config-orchestrator` (port 9501): API gateway and config lifecycle

## Service Decomposition
- **Centralized config management**: config_manager (pydantic-settings)
- **Version control**: version_control (Git-like commit hashes)
- **Hot updates**: hot_update (WebSocket push)
- **Encrypted storage**: encryption (AES-256)
- **Audit logs**: audit_logger (event sourcing)
- **Rollback**: rollback (snapshots)
- **Environment isolation**: namespace
- **Inter-service communication**: gRPC client/server
- **Distributed transactions**: saga

## Deployment
- Docker Compose for local development
- Kubernetes for production
- Prometheus for monitoring
