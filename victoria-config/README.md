# VictoriaMetrics Deployment Architecture

## Overview
VictoriaMetrics is a high-performance, cost-effective time series database that is Prometheus-compatible. This document describes the deployment architecture for AIOps Agent.

## Deployment Options

### 1. Single-Node Deployment (Recommended for Initial Setup)
**Use Case**: Development, testing, small-scale production (up to 1M metrics/sec)

**Architecture**:
- Single VictoriaMetrics instance
- Local storage persistence
- Simple configuration
- Easy to deploy and maintain

**Components**:
- VictoriaMetrics server (port 8428)
- VMAlert for alerting (port 8880)
- VMStorage for data storage
- Data persistence via Docker volumes

**Pros**:
- Simple setup
- Low resource requirements
- Easy to debug
- Suitable for most use cases

**Cons**:
- Single point of failure
- Limited scalability
- No high availability

### 2. Cluster Deployment (Recommended for Production)
**Use Case**: Medium to large-scale production (1M-10M metrics/sec)

**Architecture**:
- Multiple VMStorage nodes (data replication)
- VMSelect nodes (query routing)
- VMInsert nodes (write routing)
- Load balancer

**Components**:
- 3+ VMStorage nodes (replication factor 2)
- 2+ VMSelect nodes (query scalability)
- 2+ VMInsert nodes (write scalability)
- Load balancer (nginx/haproxy)

**Pros**:
- High availability
- Horizontal scalability
- Fault tolerance
- Better performance for high load

**Cons**:
- Complex setup
- Higher resource requirements
- More maintenance overhead

### 3. High Availability Deployment (Enterprise)
**Use Case**: Mission-critical production (10M+ metrics/sec)

**Architecture**:
- Multi-cluster setup
- Cross-region replication
- Disaster recovery
- Advanced monitoring

**Components**:
- Multiple clusters in different regions
- Global load balancer
- Automated failover
- Backup and restore procedures

**Pros**:
- Maximum availability
- Disaster recovery
- Global performance
- Enterprise-grade reliability

**Cons**:
- Very complex setup
- High cost
- Requires dedicated operations team

## Recommended Architecture for AIOps Agent

### Phase 1: Single-Node Deployment
Start with single-node deployment for simplicity and quick setup.

**Configuration**:
- VictoriaMetrics v1.97.0 or later
- 4 CPU cores minimum
- 8GB RAM minimum
- 100GB SSD storage minimum
- Retention: 30 days default, configurable

**Storage Layout**:
```
/victoria-data/
  ├── storage/           # Time series data
  ├── cache/             # Query cache
  └── backup/            # Backup snapshots
```

**Network**:
- HTTP port: 8428
- Prometheus scrape compatible: /api/v1/*
- Remote write: /api/v1/write

### Phase 2: Cluster Migration (Future)
When metrics volume exceeds single-node capacity, migrate to cluster deployment.

## Performance Considerations

### Data Retention
- Default: 30 days
- Hot data: 7 days (fast access)
- Warm data: 23 days (compressed)
- Cold data: Archive to S3 (optional)

### Compression
- VictoriaMetrics uses efficient compression (5-10x better than Prometheus)
- Automatic downsampling for old data
- Support for native histograms

### Query Optimization
- Use label selectors efficiently
- Avoid high cardinality labels
- Leverage recording rules for complex queries
- Use query cache for repeated queries

## Monitoring and Alerting

### Key Metrics to Monitor
- `vmmetrics_storage_size_bytes` - Storage usage
- `vmmetrics_request_duration_seconds` - Query latency
- `vmmetrics_rows_per_second` - Ingestion rate
- `vmmetrics_slow_queries_total` - Slow query count

### Alerting Rules
- High ingestion rate (> 1M samples/sec)
- High query latency (> 5s p95)
- High storage usage (> 80%)
- Service down

## Backup Strategy

### Backup Types
1. **Snapshot backups**: Daily snapshots of storage directory
2. **Remote write backup**: Stream to secondary VictoriaMetrics
3. **S3 backup**: Archive old data to object storage

### Retention
- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

## Security

### Authentication
- Basic auth (username/password)
- Token-based authentication
- TLS encryption for data in transit

### Network Security
- Firewall rules
- Network segmentation
- VPN access for remote management

## Migration Path

### From Prometheus to VictoriaMetrics
1. Deploy VictoriaMetrics alongside Prometheus
2. Configure dual-write (Prometheus -> VictoriaMetrics)
3. Verify data consistency
4. Switch queries to VictoriaMetrics
5. Decommission Prometheus

### From SQLite to VictoriaMetrics
1. Implement dual-write in metrics_router.py
2. Migrate historical data
3. Validate data integrity
4. Switch to VictoriaMetrics as primary
5. Keep SQLite as fallback
