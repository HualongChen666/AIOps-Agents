# Performance Monitoring Service

A FastAPI microservice for Performance Monitoring operations.

## Run

```bash
uvicorn services.performance_monitoring_service.main_app:app --host 0.0.0.0 --port 9560
```

## Docker Compose

```bash
cd services/performance_monitoring_service
docker-compose up -d
```
