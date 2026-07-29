---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Automated Operations Service

A FastAPI microservice for Automated Operations operations.

## Run

```bash
uvicorn services.automated_ops_service.main_app:app --host 0.0.0.0 --port 9566
```

## Docker Compose

```bash
cd services/automated_ops_service
docker-compose up -d
```
