# AIOps Agent Monitoring Stack

Complete Prometheus/Grafana monitoring solution for the AIOps Agent platform.

## Overview

This monitoring stack provides comprehensive observability for the AIOps Agent platform, including:

- **API Performance Monitoring**: Track API response times, error rates, and throughput
- **AI/LLM Performance**: Monitor AI model latency, token usage, and costs
- **Knowledge Graph Metrics**: Track knowledge graph query performance and size
- **Workflow Monitoring**: Monitor workflow execution times and success rates
- **Resource Monitoring**: Track CPU, memory, disk, and network usage
- **KPI/SLO Tracking**: Monitor Service Level Objectives and Key Performance Indicators
- **System Overview**: High-level view of all system components

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AIOps Agent Platform                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   API Service│  │  AI Service  │  │KG Service    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │               │
│         └──────────────────┼──────────────────┘               │
│                            │                                   │
│                    ┌───────▼────────┐                         │
│                    │Metrics Exporter│                         │
│                    └───────┬────────┘                         │
└────────────────────────────┼────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Prometheus    │
                    │  (Time Series DB)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼────┐   ┌─────▼────┐   ┌─────▼────┐
        │  Grafana │   │Alertmanager│ │ Node Exp │
        │ (Dashboard)│ │ (Alerting) │ │ (System) │
        └──────────┘   └───────────┘   └──────────┘
```

## Components

### 1. Prometheus

Time-series database for collecting and storing metrics.

- **Port**: 9090
- **Configuration**: `monitoring/prometheus/prometheus.yml`
- **Data Retention**: 30 days, 50GB max
- **Scrape Interval**: 10-30 seconds

### 2. Grafana

Visualization and dashboard platform.

- **Port**: 3001
- **Default Credentials**: admin/admin
- **Dashboards**: 7 pre-configured dashboards
- **Auto-provisioning**: Enabled

### 3. Alertmanager

Alert routing and notification system.

- **Port**: 9093
- **Configuration**: `monitoring/alertmanager/alertmanager.yml`
- **Notification Channels**: Email, Slack

### 4. Node Exporter

System metrics collector.

- **Port**: 9100
- **Metrics**: CPU, memory, disk, network, load

### 5. PostgreSQL Exporter

Database metrics collector.

- **Port**: 9187
- **Metrics**: Connections, query performance, replication lag

### 6. Redis Exporter

Cache metrics collector.

- **Port**: 9121
- **Metrics**: Memory usage, hit rate, operations

### 7. Caddy

Reverse proxy and SSL termination.

- **Ports**: 80, 443
- **Configuration**: `monitoring/caddy/Caddyfile`

## Installation

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 20GB disk space minimum

### Quick Start (Linux/Mac)

```bash
cd monitoring
./deploy.sh install
```

### Quick Start (Windows)

```powershell
cd monitoring
.\deploy.ps1 -Command install
```

### Manual Installation

1. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. Start services:
```bash
docker-compose up -d
```

3. Verify services:
```bash
docker-compose ps
```

## Configuration

### Environment Variables

Edit `.env` file to configure:

```bash
# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password

# Database Exporter
POSTGRES_DATA_SOURCE_NAME=postgresql://user:password@host.docker.internal:5432/aiops?sslmode=disable

# Redis Exporter
REDIS_ADDR=redis://host.docker.internal:6379

# Email Alerts
SMTP_SERVER=smtp.gmail.com:587
SMTP_FROM=alertmanager@yourdomain.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Email Recipients
DEFAULT_EMAIL=admin@yourdomain.com
CRITICAL_EMAIL=oncall@yourdomain.com
WARNING_EMAIL=ops@yourdomain.com

# Slack Alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CRITICAL_CHANNEL=#aiops-critical
SLACK_WARNING_CHANNEL=#aiops-ops
```

### Prometheus Configuration

Edit `monitoring/prometheus/prometheus.yml` to:

- Add/modify scrape targets
- Adjust scrape intervals
- Configure retention settings
- Add custom alert rules

### Alertmanager Configuration

Edit `monitoring/alertmanager/alertmanager.yml` to:

- Configure notification routes
- Set up email/Slack integration
- Define inhibition rules
- Customize alert templates

## Dashboards

### 1. API Performance Dashboard

**UID**: `aiops-api-performance`

Metrics:
- API response time (p50, p95, p99)
- API error rate
- API request rate
- Requests by status code
- Connection pool status

### 2. AI Performance Dashboard

**UID**: `aiops-ai-performance`

Metrics:
- AI/LLM request latency
- Token usage rate
- Requests by model
- Model failure rate
- Cost rate
- Cache performance

### 3. Knowledge Graph Performance Dashboard

**UID**: `aiops-knowledge-graph-performance`

Metrics:
- Query latency (p50, p95, p99)
- Graph size (nodes, edges)
- Query rate
- Cache performance
- Queries by type

### 4. Workflow Performance Dashboard

**UID**: `aiops-workflow-performance`

Metrics:
- Execution time (p50, p95, p99)
- Failure rate
- Execution rate
- Queue size
- Executions by status

### 5. Resource Usage Dashboard

**UID**: `aiops-resource-usage`

Metrics:
- CPU usage
- Memory usage
- Disk usage
- Network I/O
- System load

### 6. KPI/SLO Dashboard

**UID**: `aiops-kpi-slo`

Metrics:
- SLO: API availability (99.9%)
- SLO: API latency p95 (<1s)
- SLO: Error budget remaining
- KPI: AI response time
- Availability over time
- Latency over time
- Error budget consumption

### 7. System Overview Dashboard

**UID**: `aiops-system-overview`

Metrics:
- API availability gauge
- API latency p95 gauge
- API error rate gauge
- CPU usage gauge
- Memory usage gauge
- Disk usage gauge
- Request rate by service
- Latency p95 by service
- System connections & queues
- Data & cache metrics

## Alert Rules

### API Performance Alerts

- **High API Response Time**: p95 > 1s (warning), > 5s (critical)
- **High API Error Rate**: > 5% (warning), > 15% (critical)

### AI Performance Alerts

- **High AI Latency**: p95 > 10s (warning), > 30s (critical)
- **High AI Token Usage**: > 1000 tokens/sec
- **High AI Model Failure Rate**: > 10%

### Knowledge Graph Alerts

- **High Query Latency**: p95 > 2s
- **Graph Size Alert**: > 1M nodes

### Workflow Alerts

- **High Execution Time**: p95 > 300s
- **High Failure Rate**: > 10%
- **Queue Backlog**: > 100 items

### Resource Alerts

- **High CPU Usage**: > 70% (warning), > 90% (critical)
- **High Memory Usage**: > 80% (warning), > 95% (critical)
- **High Disk Usage**: > 80% (warning), > 90% (critical)

### Database Alerts

- **High Connection Pool**: > 80%
- **Slow Queries**: p95 > 1s
- **Replication Lag**: > 10s

### SLO Alerts

- **SLO API Availability**: < 99.9%
- **SLO API Latency**: p95 > 1s
- **Error Budget Low**: < 99.5%

## Metrics Exporter

The `core/metrics_exporter.py` module provides Prometheus metrics export functionality.

### Integration with Existing Framework

The metrics exporter integrates with:

- `PerformanceDataCollector`: Collects performance metrics from database
- `PerformanceOptimizer`: Collects resource and cache metrics

### Usage

```python
from core.metrics_exporter import get_metrics_exporter, record_api_request

# Record API request
record_api_request(method="GET", endpoint="/api/alerts", status=200, duration=0.123)

# Get exporter instance
exporter = get_metrics_exporter()

# Record AI request
exporter.record_ai_request(
    model="gpt-4",
    operation="chat",
    duration=2.5,
    tokens=1500,
    cost=0.03
)

# Export metrics
metrics = exporter.export_metrics()
```

### Available Metrics

#### API Metrics
- `aiops_api_requests_total`
- `aiops_api_request_duration_seconds`
- `aiops_api_connections_active`
- `aiops_api_errors_total`

#### AI Metrics
- `aiops_ai_requests_total`
- `aiops_ai_request_duration_seconds`
- `aiops_ai_tokens_total`
- `aiops_ai_cost_usd`
- `aiops_ai_cache_hits_total`

#### Knowledge Graph Metrics
- `aiops_knowledge_graph_queries_total`
- `aiops_knowledge_graph_query_duration_seconds`
- `aiops_knowledge_graph_nodes_total`
- `aiops_knowledge_graph_edges_total`

#### Workflow Metrics
- `aiops_workflow_executions_total`
- `aiops_workflow_execution_duration_seconds`
- `aiops_workflow_queue_size`

#### Resource Metrics
- `aiops_cpu_usage_percent`
- `aiops_memory_usage_bytes`
- `aiops_disk_io_bytes`
- `aiops_network_io_bytes`

#### KPI/SLO Metrics
- `aiops_slo_availability`
- `aiops_slo_latency`
- `aiops_error_budget_remaining`
- `aiops_kpi_throughput`
- `aiops_kpi_success_rate`

## Management

### Start Services

```bash
./deploy.sh start
# or
docker-compose up -d
```

### Stop Services

```bash
./deploy.sh stop
# or
docker-compose down
```

### Restart Services

```bash
./deploy.sh restart
# or
docker-compose restart
```

### Check Status

```bash
./deploy.sh status
# or
docker-compose ps
```

### View Logs

```bash
# All services
./deploy.sh logs

# Specific service
./deploy.sh logs prometheus
# or
docker-compose logs -f prometheus
```

### Reload Prometheus

```bash
./deploy.sh reload
# or
curl -X POST http://localhost:9090/-/reload
```

### Backup Data

```bash
./deploy.sh backup
```

Backups are stored in `monitoring/backups/YYYYMMDD_HHMMSS/`

### Restore Data

```bash
./deploy.sh restore backups/20240101_120000
```

## Access URLs

- **Grafana**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Node Exporter**: http://localhost:9100/metrics
- **PostgreSQL Exporter**: http://localhost:9187/metrics
- **Redis Exporter**: http://localhost:9121/metrics

## Security Recommendations

1. **Change Default Credentials**: Update Grafana admin password
2. **Enable SSL/TLS**: Configure Caddy for HTTPS
3. **Network Isolation**: Use Docker networks to isolate services
4. **Authentication**: Enable Grafana authentication and user management
5. **Firewall**: Restrict access to monitoring ports
6. **Secrets Management**: Use environment variables or secret management tools

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Check port conflicts
netstat -tuln | grep -E '9090|3001|9093'
```

### Prometheus Not Scraping Metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check metrics endpoint
curl http://localhost:8000/metrics
```

### Grafana Dashboards Not Loading

```bash
# Check Grafana logs
docker-compose logs grafana

# Verify datasource configuration
curl http://localhost:3001/api/datasources
```

### Alertmanager Not Sending Alerts

```bash
# Check Alertmanager configuration
curl http://localhost:9093/api/v1/status

# Test SMTP configuration
# Use telnet or openssl to test SMTP server
```

## Performance Tuning

### Prometheus

- Adjust `--storage.tsdb.retention.time` for longer/shorter retention
- Increase `--storage.tsdb.retention.size` for more data
- Tune scrape intervals based on metric volume

### Grafana

- Increase `GF_INSTALL_PLUGINS` for additional panels
- Adjust `GF_SESSION_PROVIDER` for session management
- Configure `GF_DATABASE` for external database

### System Resources

- Monitor Docker resource usage
- Adjust container memory limits
- Use Docker Swarm or Kubernetes for scaling

## Integration with AIOps Agent

### Adding Metrics Endpoint

Add to your FastAPI application:

```python
from fastapi import FastAPI
from core.metrics_exporter import get_metrics_exporter

app = FastAPI()
exporter = get_metrics_exporter()

@app.get("/metrics")
async def metrics():
    return exporter.get_metrics_response()

# Middleware to record requests
@app.middleware("http")
async def record_requests(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    exporter.record_api_request(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        duration=duration
    )
    return response
```

### Scheduled Metrics Collection

Add to your application startup:

```python
import asyncio
from core.metrics_exporter import get_metrics_exporter

async def collect_metrics_periodically():
    exporter = get_metrics_exporter()
    while True:
        await exporter.collect_from_performance_data()
        await exporter.collect_from_performance_optimizer()
        await asyncio.sleep(60)  # Collect every minute

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(collect_metrics_periodically())
```

## Maintenance

### Regular Tasks

1. **Daily**: Check alert status and system health
2. **Weekly**: Review dashboard trends and adjust thresholds
3. **Monthly**: Backup data and review storage usage
4. **Quarterly**: Review and update alert rules and dashboards

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

### Cleanup

```bash
# Remove old containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune
```

## Support

For issues and questions:

1. Check logs: `./deploy.sh logs`
2. Review configuration files
3. Check Prometheus targets: http://localhost:9090/targets
4. Review Grafana datasource settings

## License

This monitoring configuration is part of the AIOps Agent project.
