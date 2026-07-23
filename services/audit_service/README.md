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
