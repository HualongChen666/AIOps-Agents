---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Cloud Monitoring Service

A FastAPI microservice for Cloud Monitoring operations.

## Run

```bash
uvicorn services.cloud_monitoring_service.main_app:app --host 0.0.0.0 --port 9534
```

## Docker Compose

```bash
cd services/cloud_monitoring_service
docker-compose up -d
```
