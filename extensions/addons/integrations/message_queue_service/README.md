---
pack: integrations
enabled_by: INTEGRATIONS_ENABLED
docker_profile: integrations
core_dependency: False
---

# Message Queue Service

A FastAPI microservice for Message Queue operations.

## Run

```bash
uvicorn services.message_queue_service.main_app:app --host 0.0.0.0 --port 9523
```

## Docker Compose

```bash
cd services/message_queue_service
docker-compose up -d
```
