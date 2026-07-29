---
pack: infrastructure
enabled_by: SHARDING_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Redis Shard Cluster Service

A FastAPI microservice that exposes Redis sharded-cluster operations:
sharding strategy, routing, rebalancing, replication, high availability,
failover, cross-shard query, backup/restore, monitoring and performance tests.

## Run

```bash
uvicorn services.redis_shard_service.main_app:app --host 0.0.0.0 --port 9502
```

## Docker Compose

```bash
cd services/redis_shard_service
docker-compose up -d
```
