# Ansible Automation Service

A FastAPI microservice for Ansible Automation operations.

## Run

```bash
uvicorn services.ansible_automation_service.main_app:app --host 0.0.0.0 --port 9535
```

## Docker Compose

```bash
cd services/ansible_automation_service
docker-compose up -d
```
