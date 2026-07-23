# Kubernetes Orchestration Service

A FastAPI microservice for Kubernetes Orchestration operations.

## Run

```bash
uvicorn services.kubernetes_orchestration_service.main_app:app --host 0.0.0.0 --port 9537
```

## Docker Compose

```bash
cd services/kubernetes_orchestration_service
docker-compose up -d
```
