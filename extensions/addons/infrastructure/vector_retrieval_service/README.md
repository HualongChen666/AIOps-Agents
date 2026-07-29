---
pack: extensions
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# VectorRetrievalService

VectorRetrievalService microservice.

## Run locally

```bash
uvicorn services.vector_retrieval_service.main_app:app --host 0.0.0.0 --port 9412
```

## Docker Compose

```bash
docker-compose -f services/vector_retrieval_service/docker-compose.yml up --build
```
