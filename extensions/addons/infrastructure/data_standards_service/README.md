---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Data Standards Service

A FastAPI microservice for Data Standards operations.

## Run

```bash
uvicorn services.data_standards_service.main_app:app --host 0.0.0.0 --port 9559
```

## Docker Compose

```bash
cd services/data_standards_service
docker-compose up -d
```
