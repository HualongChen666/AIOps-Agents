# Metrics Monitoring Service

A FastAPI microservice for Metrics Monitoring operations.

## Run

```bash
uvicorn services.metrics_monitoring_service.main_app:app --host 0.0.0.0 --port 9568
```

## Docker Compose

```bash
cd services/metrics_monitoring_service
docker-compose up -d
```
