---
pack: security
enabled_by: SECURITY_SCANNING_ENABLED
docker_profile: security
core_dependency: False
---

# Security Scanning Service

A FastAPI microservice for Security Scanning operations.

## Run

```bash
uvicorn services.security_scanning_service.main_app:app --host 0.0.0.0 --port 9563
```

## Docker Compose

```bash
cd services/security_scanning_service
docker-compose up -d
```
