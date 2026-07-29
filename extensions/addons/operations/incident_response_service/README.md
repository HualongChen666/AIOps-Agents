---
pack: operations
enabled_by: INCIDENT_RESPONSE_ENABLED
docker_profile: operations
core_dependency: False
---

# Incident Response Service

A FastAPI microservice for Incident Response operations.

## Run

```bash
uvicorn services.incident_response_service.main_app:app --host 0.0.0.0 --port 9553
```

## Docker Compose

```bash
cd services/incident_response_service
docker-compose up -d
```
