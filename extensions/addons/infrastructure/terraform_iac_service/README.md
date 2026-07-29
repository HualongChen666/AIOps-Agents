---
pack: infrastructure
enabled_by: PLUGINS_ENABLED
docker_profile: infrastructure
core_dependency: False
---

# Terraform IaC Service

A FastAPI microservice for Terraform IaC operations.

## Run

```bash
uvicorn services.terraform_iac_service.main_app:app --host 0.0.0.0 --port 9536
```

## Docker Compose

```bash
cd services/terraform_iac_service
docker-compose up -d
```
