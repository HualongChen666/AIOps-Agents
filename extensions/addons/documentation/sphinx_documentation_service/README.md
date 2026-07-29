---
pack: documentation
enabled_by: DOC_GENERATION_ENABLED
docker_profile: documentation
core_dependency: False
---

# Sphinx Documentation Service

A FastAPI microservice for Sphinx Documentation operations.

## Run

```bash
uvicorn services.sphinx_documentation_service.main_app:app --host 0.0.0.0 --port 9550
```

## Docker Compose

```bash
cd services/sphinx_documentation_service
docker-compose up -d
```
