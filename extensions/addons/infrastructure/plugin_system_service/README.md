---
pack: infrastructure
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Plugin System Service

A FastAPI microservice for Plugin System operations.

## Run

```bash
uvicorn services.plugin_system_service.main_app:app --host 0.0.0.0 --port 9556
```

## Docker Compose

```bash
cd services/plugin_system_service
docker-compose up -d
```
