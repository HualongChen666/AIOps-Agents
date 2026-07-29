---
pack: observability
enabled_by: TRACING_ENABLED
docker_profile: observability
core_dependency: False
---

# Tracing Service

A FastAPI microservice for Tracing operations.

## Run

```bash
uvicorn services.tracing_service.main_app:app --host 0.0.0.0 --port 9521
```

## Docker Compose

```bash
cd services/tracing_service
docker-compose up -d
```
