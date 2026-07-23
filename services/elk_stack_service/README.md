# ELK Stack Service

A FastAPI microservice for ELK Stack operations.

## Run

```bash
uvicorn services.elk_stack_service.main_app:app --host 0.0.0.0 --port 9532
```

## Docker Compose

```bash
cd services/elk_stack_service
docker-compose up -d
```
