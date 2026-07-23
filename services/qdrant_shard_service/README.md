# Qdrant Shard Cluster Service

A FastAPI microservice that exposes Qdrant sharded-cluster operations:
sharding strategy, routing, rebalancing, replication, high availability,
failover, cross-shard query, backup/restore, monitoring and performance tests.

## Run

```bash
uvicorn services.qdrant_shard_service.main_app:app --host 0.0.0.0 --port 9503
```

## Docker Compose

```bash
cd services/qdrant_shard_service
docker-compose up -d
```
