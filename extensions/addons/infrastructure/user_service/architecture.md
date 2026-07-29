# User Service Architecture (Task 29.1)

## Overview
The user service is a FastAPI microservice with the following sub-services:
- `user-orchestrator` (port 9401): API gateway and user lifecycle

## Service Decomposition
- **User management**: user_manager (CRUD)
- **RBAC**: rbac
- **Organization tree**: organization
- **Authentication**: auth (OAuth2/JWT)
- **Sessions**: session (Redis)
- **Audit logs**: audit_logger (event sourcing)
- **Inter-service communication**: gRPC client/server
- **Distributed transactions**: saga

## Deployment
- Docker Compose for local development
- Kubernetes for production
- Prometheus for monitoring
