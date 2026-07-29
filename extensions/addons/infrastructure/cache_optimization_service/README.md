---
pack: infrastructure
enabled_by: SHARDING_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Cache Optimization Service

A FastAPI microservice for Cache Optimization operations.

## Run

```bash
uvicorn services.cache_optimization_service.main_app:app --host 0.0.0.0 --port 9561
```

## Docker Compose

```bash
cd services/cache_optimization_service
docker-compose up -d
```
