# Loki Deployment Architecture

## Overview
Loki is a horizontally scalable, highly available, multi-tenant log aggregation system inspired by Prometheus. This document describes the deployment architecture for AIOps Agent.

## Deployment Options

### 1. Single-Node Deployment (Recommended for Initial Setup)
**Use Case**: Development, testing, small-scale production

**Architecture**:
- Single Loki instance (all-in-one mode)
- Local storage persistence
- Simple configuration
- Easy to deploy and maintain

**Components**:
- Loki server (port 3100)
- Promtail agent (port 9080)
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

### 2. Distributed Deployment (Recommended for Production)
**Use Case**: Medium to large-scale production

**Architecture**:
- Separate components for scalability
- Gateway for API access
- Distributor for log ingestion
- Ingester for log processing
- Querier for log queries
- Index gateway for index storage
- Storage backend (S3/GCS/Azure)

**Components**:
- 2+ Gateway instances (API access)
- 2+ Distributor instances (log ingestion)
- 3+ Ingester instances (log processing)
- 2+ Querier instances (log queries)
- 2+ Index Gateway instances (index storage)
- Object storage backend (S3/GCS)
- Load balancer

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
**Use Case**: Mission-critical production

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
- Loki v2.9.0 or later
- 2 CPU cores minimum
- 4GB RAM minimum
- 50GB SSD storage minimum
- Retention: 30 days default, configurable

**Storage Layout**:
```
/loki-data/
  ├── index/              # Log index
  ├── chunks/             # Log chunks
  └── compactor/          # Compaction cache
```

**Network**:
- HTTP port: 3100
- GRPC port: 9095
- Metrics port: 3100/metrics

### Phase 2: Distributed Migration (Future)
When log volume exceeds single-node capacity, migrate to distributed deployment.

## Performance Considerations

### Data Retention
- Default: 30 days
- Hot data: 7 days (fast access)
- Warm data: 23 days (compressed)
- Cold data: Archive to S3 (optional)

### Compression
- Loki uses gzip compression for log chunks
- Automatic chunk management
- Support for structured metadata

### Query Optimization
- Use label selectors efficiently
- Avoid high cardinality labels
- Leverage query cache for repeated queries
- Use stream selectors for filtering

## Monitoring and Alerting

### Key Metrics to Monitor
- `loki_write_bytes_total` - Bytes written
- `loki_read_bytes_total` - Bytes read
- `loki_ingester_flush_queue_length` - Flush queue length
- `loki_query_duration_seconds` - Query latency
- `loki_streams_created_total` - Streams created

### Alerting Rules
- High ingestion rate (> 10MB/sec)
- High query latency (> 5s p95)
- High storage usage (> 80%)
- Service down

## Backup Strategy

### Backup Types
1. **Snapshot backups**: Daily snapshots of storage directory
2. **Object storage backup**: Stream to S3/GCS
3. **Index backup**: Separate index backups

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

### From File-based Logging to Loki
1. Deploy Loki alongside existing logging
2. Configure Promtail to collect existing logs
3. Verify log ingestion
4. Switch applications to write to Loki
5. Decommission old logging system
