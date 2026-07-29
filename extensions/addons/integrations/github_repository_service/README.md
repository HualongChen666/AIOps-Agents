---
pack: integrations
enabled_by: INTEGRATIONS_ENABLED
docker_profile: integrations
core_dependency: False
---

# GitHub Repository Service

A FastAPI microservice for GitHub Repository operations.

## Run

```bash
uvicorn services.github_repository_service.main_app:app --host 0.0.0.0 --port 9554
```

## Docker Compose

```bash
cd services/github_repository_service
docker-compose up -d
```
