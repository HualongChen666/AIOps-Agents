---
pack: security
enabled_by: PENETRATION_TESTING_ENABLED
docker_profile: security
core_dependency: False
---

# Penetration Testing Service

A FastAPI microservice for Penetration Testing operations.

## Run

```bash
uvicorn services.penetration_testing_service.main_app:app --host 0.0.0.0 --port 9564
```

## Docker Compose

```bash
cd services/penetration_testing_service
docker-compose up -d
```
