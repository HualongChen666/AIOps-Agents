---
pack: integrations
enabled_by: INTEGRATIONS_ENABLED
docker_profile: integrations
core_dependency: False
---

# Prometheus Integration Service

A FastAPI microservice for Prometheus Integration operations.

## Run

```bash
uvicorn services.prometheus_integration_service.main_app:app --host 0.0.0.0 --port 9530
```

## Docker Compose

```bash
cd services/prometheus_integration_service
docker-compose up -d
```
