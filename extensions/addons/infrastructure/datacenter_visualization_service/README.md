---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Datacenter Visualization Service

A FastAPI microservice for Datacenter Visualization operations.

## Run

```bash
uvicorn services.datacenter_visualization_service.main_app:app --host 0.0.0.0 --port 9545
```

## Docker Compose

```bash
cd services/datacenter_visualization_service
docker-compose up -d
```
