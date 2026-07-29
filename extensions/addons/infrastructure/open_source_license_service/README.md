---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Open Source License Service

A FastAPI microservice for Open Source License operations.

## Run

```bash
uvicorn services.open_source_license_service.main_app:app --host 0.0.0.0 --port 9555
```

## Docker Compose

```bash
cd services/open_source_license_service
docker-compose up -d
```
