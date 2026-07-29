---
pack: infrastructure
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Backup Recovery Drill Service

A FastAPI microservice for Backup Recovery Drill operations.

## Run

```bash
uvicorn services.backup_recovery_drill_service.main_app:app --host 0.0.0.0 --port 9552
```

## Docker Compose

```bash
cd services/backup_recovery_drill_service
docker-compose up -d
```
