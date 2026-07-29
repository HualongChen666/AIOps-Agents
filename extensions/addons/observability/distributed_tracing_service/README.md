---
pack: observability
enabled_by: TRACING_ENABLED
docker_profile: observability
core_dependency: False
---

# Distributed Tracing Service

A FastAPI microservice for Distributed Tracing operations.

## Run

```bash
uvicorn services.distributed_tracing_service.main_app:app --host 0.0.0.0 --port 9569
```

## Docker Compose

```bash
cd services/distributed_tracing_service
docker-compose up -d
```
