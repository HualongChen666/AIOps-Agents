# Audit Service Architecture (Task 28.1)

## Overview
The audit service is split into three FastAPI sub-services:
- `audit-orchestrator` (port 9301): API gateway, event ingestion, reports
- `audit-analyzer` (port 9302): Event analysis and anomaly detection
- `audit-reporter` (port 9303): Compliance report generation

## Service Decomposition
- **Operation log recording**: event_store, log_recorder, query, analyzer
- **Event tracking**: event_tracker, event_router
- **Compliance reporting**: compliance, report_generator
- **Encryption**: encryption (AES-256)
- **Retention**: retention
- **GraphQL queries**: graphql_api
- **Alerting**: alerting
- **Inter-service communication**: gRPC client/server
- **Distributed transactions**: saga

## Deployment
- Docker Compose for local development
- Kubernetes for production
- Prometheus for monitoring
