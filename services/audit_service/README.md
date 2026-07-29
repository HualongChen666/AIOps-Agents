---
pack: core
enabled_by: N/A (always on)
docker_profile: core
core_dependency: True
---

# Audit Service

Microservice for audit logging, event tracking, compliance reports, encryption, retention, and alerts.

## Run locally

```bash
uvicorn services.audit_service.main_app:app --host 0.0.0.0 --port 9301
```

## Docker Compose

```bash
docker-compose -f services/audit_service/docker-compose.yml up --build
```
