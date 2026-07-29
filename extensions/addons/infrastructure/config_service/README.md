---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Config Service

Microservice for centralized configuration management, version control, hot updates, encryption, and rollback.

## Run locally

```bash
uvicorn services.config_service.main_app:app --host 0.0.0.0 --port 9501
```

## Docker Compose

```bash
docker-compose -f services/config_service/docker-compose.yml up --build
```
