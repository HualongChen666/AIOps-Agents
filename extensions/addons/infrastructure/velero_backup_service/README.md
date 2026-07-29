---
pack: infrastructure
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Velero Backup Service

A FastAPI microservice for Velero Backup operations.

## Run

```bash
uvicorn services.velero_backup_service.main_app:app --host 0.0.0.0 --port 9543
```

## Docker Compose

```bash
cd services/velero_backup_service
docker-compose up -d
```
