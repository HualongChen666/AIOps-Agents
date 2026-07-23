# AIOps Agent Deployment Guide

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Docker (optional, for containerized deployment)
- Kubernetes (optional, for cluster deployment)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/AIOps_Agent.git
cd AIOps_Agent
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/aiops

# Redis
REDIS_URL=redis://localhost:6379

# AI Services
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=False
LOG_LEVEL=INFO

# SSL Verification
HTTPX_SSL_VERIFY=true
```

### Configuration Files

The application uses YAML configuration files in the `config/` directory:
- `development.yaml` - Development environment settings
- `staging.yaml` - Staging environment settings
- `production.yaml` - Production environment settings

## Database Setup

### 1. Create Database

```bash
createdb aiops
```

### 2. Run Migrations

```bash
alembic upgrade head
```

### 3. Verify Database Connection

```bash
python -c "from aiops_core.database import engine; print(engine.url)"
```

## Redis Setup

### Start Redis Server

```bash
# Linux/Mac
redis-server

# Windows
redis-server.exe
```

### Verify Redis Connection

```bash
redis-cli ping
# Should return: PONG
```

## Running the Application

### Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Docker Deployment

### Build Docker Image

```bash
docker build -t aiops-agent:latest .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

### Run Individual Container

```bash
docker run -d \
  --name aiops-agent \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@db:5432/aiops \
  -e REDIS_URL=redis://redis:6379 \
  aiops-agent:latest
```

## Kubernetes Deployment

### Deploy to Kubernetes

```bash
kubectl apply -f k8s/
```

### Check Deployment Status

```bash
kubectl get pods -l app=aiops-agent
kubectl get services aiops-agent
```

### Scale Deployment

```bash
kubectl scale deployment aiops-agent --replicas=3
```

## Monitoring

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health

# Readiness probe
curl http://localhost:8000/ready

# Detailed health
curl http://localhost:8000/api/v1/health/detailed
```

### Logs

```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log

# Docker logs
docker logs -f aiops-agent

# Kubernetes logs
kubectl logs -f deployment/aiops-agent
```

## Performance Tuning

### Database Connection Pool

Adjust database pool size in `config/production.yaml`:

```yaml
database:
  pool_size: 20
  max_overflow: 10
  pool_timeout: 30
```

### Redis Connection Pool

Adjust Redis pool settings:

```yaml
redis:
  max_connections: 50
  socket_timeout: 5
  socket_connect_timeout: 5
```

### Worker Processes

Adjust worker count based on CPU cores:

```bash
# 4 workers for 4-core system
uvicorn main:app --workers 4
```

## Security Considerations

### 1. SSL/TLS

Enable SSL in production:

```env
HTTPX_SSL_VERIFY=true
```

### 2. Secret Management

Use environment variables or secret management tools:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault

### 3. Network Security

- Use firewall rules to restrict access
- Enable network policies in Kubernetes
- Use VPN for remote access

### 4. Authentication

- Enable JWT authentication
- Use strong secret keys
- Implement token rotation

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL status
systemctl status postgresql

# Test connection
psql -U user -d aiops -h localhost
```

### Redis Connection Issues

```bash
# Check Redis status
redis-cli ping

# Check Redis logs
tail -f /var/log/redis/redis-server.log
```

### Application Startup Issues

```bash
# Check configuration
python -c "from config import settings; print(settings)"

# Check dependencies
pip check

# Run in debug mode
DEBUG=True uvicorn main:app --reload
```

## Backup and Recovery

### Database Backup

```bash
pg_dump aiops > backup_$(date +%Y%m%d).sql
```

### Database Restore

```bash
psql aiops < backup_20260702.sql
```

### Redis Backup

```bash
redis-cli SAVE
cp /var/lib/redis/dump.rdb backup/
```

## Scaling

### Horizontal Scaling

```bash
# Add more Kubernetes pods
kubectl scale deployment aiops-agent --replicas=5

# Add more Docker containers
docker-compose up -d --scale aiops-agent=3
```

### Vertical Scaling

- Increase CPU/memory allocation
- Optimize database queries
- Implement caching

## Maintenance

### Regular Tasks

- Daily: Monitor logs and metrics
- Weekly: Review security patches
- Monthly: Database maintenance
- Quarterly: Performance review

### Update Procedure

1. Backup database
2. Stop application
3. Update code
4. Run migrations
5. Restart application
6. Verify health checks

## Support

For deployment issues:
- Check logs: `logs/app.log`
- Review configuration: `config/production.yaml`
- Verify dependencies: `pip check`
- Test connectivity: Database, Redis, external APIs
