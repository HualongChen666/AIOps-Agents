# AIOps Monitoring Stack - Deployment Guide

## Quick Start

### 1. Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 20GB disk space minimum

### 2. Installation

#### Linux/Mac:
```bash
cd monitoring
./deploy.sh install
```

#### Windows:
```powershell
cd monitoring
.\deploy.ps1 -Command install
```

### 3. Access Services
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

Key configurations:
- `GRAFANA_ADMIN_PASSWORD`: Change default password
- `POSTGRES_DATA_SOURCE_NAME`: Database connection string
- `REDIS_ADDR`: Redis connection string
- `SMTP_*`: Email alert configuration
- `SLACK_*`: Slack alert configuration

## Integration with AIOps Agent

### 1. Metrics Exporter
The `core/metrics_exporter.py` module provides Prometheus metrics export.

### 2. API Endpoint
Add to your FastAPI application:

```python
from core.metrics_exporter import get_metrics_exporter

app = FastAPI()
exporter = get_metrics_exporter()

@app.get("/metrics")
async def metrics():
    return exporter.get_metrics_response()
```

### 3. Record Metrics
```python
from core.metrics_exporter import record_api_request

# Record API request
record_api_request(
    method="GET",
    endpoint="/api/alerts",
    status=200,
    duration=0.123
)
```

## Management Commands

### Start Services
```bash
./deploy.sh start
```

### Stop Services
```bash
./deploy.sh stop
```

### Check Status
```bash
./deploy.sh status
```

### View Logs
```bash
./deploy.sh logs [service_name]
```

### Reload Prometheus
```bash
./deploy.sh reload
```

### Backup Data
```bash
./deploy.sh backup
```

### Restore Data
```bash
./deploy.sh restore backups/20240101_120000
```

## Dashboards

7 pre-configured dashboards are available:

1. **API Performance** (`aiops-api-performance`)
2. **AI Performance** (`aiops-ai-performance`)
3. **Knowledge Graph Performance** (`aiops-knowledge-graph-performance`)
4. **Workflow Performance** (`aiops-workflow-performance`)
5. **Resource Usage** (`aiops-resource-usage`)
6. **KPI/SLO** (`aiops-kpi-slo`)
7. **System Overview** (`aiops-system-overview`)

## Alert Rules

Pre-configured alert rules for:
- API performance (response time, error rate)
- AI performance (latency, token usage, failure rate)
- Knowledge graph (query latency, size)
- Workflow (execution time, failure rate, queue backlog)
- Resources (CPU, memory, disk, network)
- Database (connections, query performance, replication lag)
- SLO breaches (availability, latency, error budget)

## Troubleshooting

### Services Not Starting
```bash
# Check logs
docker-compose logs

# Check port conflicts
netstat -tuln | grep -E '9090|3001|9093'
```

### Prometheus Not Scraping
```bash
# Check targets
curl http://localhost:9090/api/v1/targets

# Check metrics endpoint
curl http://localhost:8000/metrics
```

### Grafana Dashboards Not Loading
```bash
# Check Grafana logs
docker-compose logs grafana

# Verify datasource
curl http://localhost:3001/api/datasources
```

## Security

1. Change default Grafana password
2. Configure SSL/TLS with Caddy
3. Restrict network access
4. Use environment variables for secrets
5. Enable authentication

## Support

For detailed documentation, see `monitoring/README.md`
