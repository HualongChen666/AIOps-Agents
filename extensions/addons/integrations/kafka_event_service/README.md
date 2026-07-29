---
pack: integrations
enabled_by: INTEGRATIONS_ENABLED
docker_profile: integrations
core_dependency: False
---

# Kafka Event Service

A FastAPI microservice for Kafka Event operations.

## Run

```bash
uvicorn services.kafka_event_service.main_app:app --host 0.0.0.0 --port 9525
```

## Docker Compose

```bash
cd services/kafka_event_service
docker-compose up -d
```
