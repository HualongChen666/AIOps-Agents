---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Chaos Mesh Service

A FastAPI microservice for Chaos Mesh operations.

## Run

```bash
uvicorn services.chaos_mesh_service.main_app:app --host 0.0.0.0 --port 9546
```

## Docker Compose

```bash
cd services/chaos_mesh_service
docker-compose up -d
```
