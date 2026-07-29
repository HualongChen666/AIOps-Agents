---
pack: infrastructure
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# pgBackRest Backup Service

A FastAPI microservice for pgBackRest Backup operations.

## Run

```bash
uvicorn services.pgbackrest_backup_service.main_app:app --host 0.0.0.0 --port 9544
```

## Docker Compose

```bash
cd services/pgbackrest_backup_service
docker-compose up -d
```
