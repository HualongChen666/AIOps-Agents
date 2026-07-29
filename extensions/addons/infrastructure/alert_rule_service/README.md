---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Alert Rule Service

A FastAPI microservice for Alert Rule operations.

## Run

```bash
uvicorn services.alert_rule_service.main_app:app --host 0.0.0.0 --port 9522
```

## Docker Compose

```bash
cd services/alert_rule_service
docker-compose up -d
```
