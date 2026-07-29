---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Automated Deployment Service

A FastAPI microservice for Automated Deployment operations.

## Run

```bash
uvicorn services.automated_deployment_service.main_app:app --host 0.0.0.0 --port 9565
```

## Docker Compose

```bash
cd services/automated_deployment_service
docker-compose up -d
```
