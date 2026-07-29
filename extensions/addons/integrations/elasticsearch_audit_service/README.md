---
pack: integrations
enabled_by: INTEGRATIONS_ENABLED
docker_profile: integrations
core_dependency: False
---

# Elasticsearch Audit Service

A FastAPI microservice for Elasticsearch Audit operations.

## Run

```bash
uvicorn services.elasticsearch_audit_service.main_app:app --host 0.0.0.0 --port 9542
```

## Docker Compose

```bash
cd services/elasticsearch_audit_service
docker-compose up -d
```
