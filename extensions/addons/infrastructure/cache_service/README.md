---
pack: infrastructure
enabled_by: SHARDING_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# CacheService

CacheService microservice.

## Run locally

```bash
uvicorn services.cache_service.main_app:app --host 0.0.0.0 --port 9411
```

## Docker Compose

```bash
docker-compose -f services/cache_service/docker-compose.yml up --build
```
