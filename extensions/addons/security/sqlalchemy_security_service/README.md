---
pack: security
enabled_by: SECURITY_SCANNING_ENABLED
docker_profile: security
core_dependency: False
---

# SQLAlchemy Security Service

A FastAPI microservice for SQLAlchemy Security operations.

## Run

```bash
uvicorn services.sqlalchemy_security_service.main_app:app --host 0.0.0.0 --port 9541
```

## Docker Compose

```bash
cd services/sqlalchemy_security_service
docker-compose up -d
```
